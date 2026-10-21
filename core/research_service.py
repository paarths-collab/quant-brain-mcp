"""Single-process durable research queue with explicit cancellation and budgets."""
from __future__ import annotations

import asyncio
from concurrent.futures import ThreadPoolExecutor
import fcntl
import os
import re
import threading
from typing import Callable

from core.research_store import ResearchStore
from core.research_workflow import run_research


class InstrumentLookupError(RuntimeError):
    """The market-data lookup itself failed, so the symbol could not be judged either way."""


def default_instrument_resolver(symbol: str) -> dict | None:
    """Look a normalized NSE symbol (e.g. ``TCS.NS``) up in the market-data provider.

    Returns a mapping for a known instrument and None for an unknown one. Raises
    InstrumentLookupError when the provider failed, which is not the same as the
    symbol not existing. The provider's own message is never surfaced: it can
    carry request URLs.
    """
    from core.data_loader import fetch_stock_data

    result = fetch_stock_data(symbol, period='5d')
    if isinstance(result, dict) and 'error' in result:
        if result['error'].startswith('No data found'):
            return None
        raise InstrumentLookupError('market-data lookup failed')
    return {'symbol': symbol, 'exchange': 'NSE'}


class ResearchService:
    def __init__(self, store=None, runtime_factory: Callable | None = None, timeout=900,
                 instrument_resolver: Callable[[str], dict | None] | None = None):
        self.store = store or ResearchStore()
        self.runtime_factory = runtime_factory
        # Injectable so tests (and other market-data providers) never need a live feed.
        self.instrument_resolver = instrument_resolver or default_instrument_resolver
        self.timeout = timeout
        self._guard = threading.RLock()
        self._executor = None
        self._file_lock = None
        self._running = {}
        self._futures = {}
        self._closing = False

    def _initialize(self):
        if self._executor is not None:
            return
        path = self.store.path
        path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        fd = os.open(str(path) + '.worker.lock', os.O_CREAT | os.O_RDWR, 0o600)
        lock = os.fdopen(fd, 'w')
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError:
            lock.close()
            raise ValueError('Research worker already active. Run one outer server worker per research database.') from None
        self._file_lock = lock
        self.store.recover_interrupted()
        self._executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix='quant-research')

    @staticmethod
    def normalize_tickers(tickers):
        if not isinstance(tickers, list) or not 1 <= len(tickers) <= 5 or not all(isinstance(item, str) for item in tickers):
            raise ValueError('Provide 1–5 NSE stock symbols')
        result = []
        for raw in tickers:
            symbol = raw.strip().upper()
            if symbol.endswith('.NS'):
                symbol = symbol[:-3]
            if not re.fullmatch(r'[A-Z0-9][A-Z0-9&-]{0,29}', symbol):
                raise ValueError('Use NSE symbols such as RELIANCE.NS or TCS.NS; other markets are not supported')
            symbol += '.NS'
            if symbol not in result:
                result.append(symbol)
        return result

    def validate_instruments(self, symbols):
        """Reject unknown or unsupported symbols; called before any job exists.

        The resolver receives normalized symbols (``TCS.NS``) and returns a
        mapping for a known instrument or None for an unknown one. An
        ``exchange`` other than NSE or a ``quote_type`` other than EQUITY marks
        it unsupported. All problems are reported together.
        """
        unknown, unsupported, unverified = [], [], []
        for symbol in symbols:
            try:
                info = self.instrument_resolver(symbol)
            except Exception:
                unverified.append(symbol)
                continue
            if not info:
                unknown.append(symbol)
            elif str(info.get('exchange', 'NSE')).upper() not in {'NSE', 'NSI'}:
                unsupported.append(f"{symbol} (listed on {info['exchange']}, not NSE)")
            elif str(info.get('quote_type', 'EQUITY')).upper() != 'EQUITY':
                unsupported.append(f"{symbol} ({info['quote_type']}, not an equity)")
        problems = []
        if unknown:
            problems.append('Unknown NSE symbol(s): ' + ', '.join(unknown) + '. Check the spelling; examples: RELIANCE.NS, TCS.NS')
        if unsupported:
            problems.append('Unsupported instrument(s): ' + ', '.join(unsupported))
        if unverified:
            problems.append('Could not verify symbol(s) ' + ', '.join(unverified) + ': market-data lookup failed; retry shortly')
        if problems:
            raise ValueError('. '.join(problems))

    def start(self, owner, question, tickers, depth='standard'):
        if not owner:
            raise ValueError('Authentication required')
        if not isinstance(question, str) or not question.strip() or len(question) > 12000:
            raise ValueError('Question must contain 1–12000 characters')
        if depth not in {'quick', 'standard', 'deep'}:
            raise ValueError('Depth must be quick, standard, or deep')
        tickers = self.normalize_tickers(tickers)
        # Before the worker, database or any job exists: nothing is left behind on rejection.
        self.validate_instruments(tickers)
        if self.runtime_factory is None:
            from core.research_runtime import CodexResearchRuntime
            # Validate configuration before accepting work; model sign-in is
            # verified by the SDK in the worker, never by reading token files.
            runtime_factory = CodexResearchRuntime
        else:
            runtime_factory = self.runtime_factory
        with self._guard:
            if self._closing:
                raise ValueError('Research service is closed; create a new service instance')
            self._initialize()
            if self.store.active_count() >= 4 or self.store.active_count(owner) >= 2:
                raise ValueError('Research queue is full; wait for a job or cancel one')
            job = self.store.create(owner, question.strip(), tickers, depth)
            future = self._executor.submit(self._execute, owner, job['id'], runtime_factory)
            self._futures[job['id']] = future
            future.add_done_callback(lambda _: self._forget(job['id']))
        return self.status(owner, job['id'])

    def _forget(self, job_id):
        with self._guard:
            self._futures.pop(job_id, None)

    def _execute(self, owner, job_id, factory):
        async def work():
            task = asyncio.current_task()
            with self._guard:
                if self._closing:
                    return
                self._running[job_id] = (asyncio.get_running_loop(), task)
            try:
                job = self.store.get(owner, job_id)
                if job['status'] == 'cancelled':
                    return
                self.store.update(owner, job_id, status='running', stage='initializing')
                runtime = factory()
                async def event(role, payload):
                    if self.store.get(owner, job_id)['status'] == 'cancelled':
                        raise asyncio.CancelledError
                    self.store.update(owner, job_id, stage=role)
                    self.store.event(owner, job_id, role, payload)
                report = await asyncio.wait_for(run_research(job['question'], job['tickers'], job['depth'],
                    runtime=runtime, on_event=event), timeout=self.timeout)
                self.store.update(owner, job_id, status='completed', stage='completed', report=report.model_dump(mode='json'))
            except asyncio.CancelledError:
                self.store.cancel(owner, job_id)
            except TimeoutError:
                self.store.update(owner, job_id, status='failed', stage='timeout', error='Research time budget exceeded. Try quick mode or fewer companies.')
            except Exception as exc:
                # Preserve safe actionable configuration errors only. Upstream
                # exceptions may contain request data or credential-bearing URLs.
                from core.research_runtime import ResearchConfigurationError
                message = str(exc) if isinstance(exc, ResearchConfigurationError) else 'Research failed: provider, tool, or evidence validation error. Check local runtime setup and retry.'
                self.store.update(owner, job_id, status='failed', stage='failed', error=message)
            finally:
                with self._guard:
                    self._running.pop(job_id, None)
        asyncio.run(work())

    def _recover_before_read(self):
        """Fail jobs orphaned by a previous process before anyone reads them.

        Recovery otherwise only ran when a new job was started, so a client
        polling after a restart saw a dead job as "running" indefinitely.
        """
        with self._guard:
            if not self._closing:
                self._initialize()

    def status(self, owner, job_id):
        self._recover_before_read()
        job = self.store.get(owner, job_id)
        if job is None:
            return {'error': 'Research job not found'}
        return {k: job[k] for k in ('id', 'status', 'stage', 'created', 'updated', 'tickers', 'depth', 'error')}

    def report(self, owner, job_id):
        self._recover_before_read()
        job = self.store.get(owner, job_id)
        if job is None:
            return {'error': 'Research job not found'}
        if job['status'] != 'completed':
            return {'status': job['status'], 'stage': job['stage'], 'error': job['error'], 'report': None}
        return {'id': job_id, 'status': 'completed', 'report': job['report'], 'events': job['events']}

    def cancel(self, owner, job_id):
        with self._guard:
            if not self._closing:
                self._initialize()
            job = self.store.cancel(owner, job_id)
            if job is None:
                return {'error': 'Research job not found'}
            if job['status'] == 'cancelled':
                future = self._futures.get(job_id)
                if future:
                    future.cancel()
                active = self._running.get(job_id)
                if active:
                    active[0].call_soon_threadsafe(active[1].cancel)
        return self.status(owner, job_id)

    def close(self):
        with self._guard:
            if self._closing:
                return
            self._closing = True
            for loop, task in list(self._running.values()):
                loop.call_soon_threadsafe(task.cancel)
            executor = self._executor
        if executor:
            executor.shutdown(wait=True, cancel_futures=True)
            self.store.recover_interrupted()
        if self._file_lock:
            self._file_lock.close()
        self._executor = None
        self._file_lock = None


_service = None
_service_guard = threading.Lock()


def get_research_service():
    global _service
    if os.getenv('QUANT_RESEARCH_ENABLED', '').lower() not in {'1', 'true'}:
        raise ValueError('Research agents are disabled. Set QUANT_RESEARCH_ENABLED=1 after configuring the Codex runtime.')
    with _service_guard:
        if _service is None:
            _service = ResearchService()
    return _service


class ResearchLifecycle:
    """Cleanup only at ASGI server shutdown, never FastMCP per-request lifespan."""
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        global _service
        if scope["type"] != "lifespan":
            return await self.app(scope, receive, send)
        try:
            await self.app(scope, receive, send)
        finally:
            with _service_guard:
                service, _service = _service, None
            if service is not None:
                await asyncio.to_thread(service.close)
