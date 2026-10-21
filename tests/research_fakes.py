"""Deterministic stand-ins for the model and market-data providers. No network, no paid calls."""
import asyncio
import threading

KNOWN_SYMBOLS = frozenset({"TCS.NS", "RELIANCE.NS", "INFY.NS", "HDFCBANK.NS", "WIPRO.NS"})

EVIDENCE = {"id": "company_e1", "url": "https://example.com/results", "title": "Results",
            "retrieved_at": "2026-01-01T10:00:00Z", "source_type": "company", "excerpt": "Revenue increased"}
CLAIM = {"id": "company_c1", "text": "Revenue increased", "evidence_ids": ["company_e1"], "kind": "fact"}


class FakeMarketData:
    """Instrument resolver backed by a fixed table instead of a live market-data feed."""

    def __init__(self, known=KNOWN_SYMBOLS, unsupported=None, failing=()):
        self.known = set(known)
        self.unsupported = dict(unsupported or {})  # symbol -> info mapping with a non-NSE exchange/type
        self.failing = set(failing)
        self.calls = []

    def __call__(self, symbol):
        self.calls.append(symbol)
        if symbol in self.failing:
            raise ConnectionError("https://provider.example/quote?token=SECRET_PRIVATE_VALUE")
        if symbol in self.unsupported:
            return self.unsupported[symbol]
        return {"symbol": symbol, "exchange": "NSE", "quote_type": "EQUITY"} if symbol in self.known else None


class ScriptedRuntime:
    """Fake model provider: one valid, evidence-citing answer per role.

    fail_at   raise from that role's call (message carries a fake secret to prove it is not leaked)
    block_at  park inside that role's call until the task is cancelled
    """

    def __init__(self, fail_at=None, block_at=None):
        self.fail_at = fail_at
        self.block_at = block_at
        self.roles = []
        self.started = threading.Event()
        self.cleaned = threading.Event()

    async def run(self, role, prompt):
        self.roles.append(role)
        if role == self.block_at:
            self.started.set()
            try:
                await asyncio.Event().wait()
            finally:
                self.cleaned.set()
        if role == self.fail_at:
            raise RuntimeError("https://provider.example/?token=SECRET_PRIVATE_VALUE")
        result = {"summary": role}
        if role == "company":
            result.update(evidence=[EVIDENCE], claims=[CLAIM])
        if role == "auditor":
            result.update(verified_claim_ids=["company_c1"], outcome="supported")
        if role == "synthesizer":
            result.update(claims=[CLAIM], outcome="supported", confidence="moderate")
        return result
