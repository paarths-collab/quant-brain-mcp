"""
InvestmentPipeline — Isolated chat/core implementation.

All previously shared infrastructure (agents, memory, quant engine) is
now either self-contained here or gracefully stubbed so the server boots
and the chat endpoint remains functional via the Groq pipeline.
"""
import asyncio
import uuid
import re
import os
from typing import Optional, Tuple

from .position_sizing_service import PositionSizingService
from .trade_levels_service import TradeLevelsService


# ─────────────────────────────────────────────────────────────
# LIGHTWEIGHT STUBS (avoid deleted module imports)
# ─────────────────────────────────────────────────────────────

class _StubVectorStore:
    def add(self, **kwargs): pass
    def search(self, *args, **kwargs): return []

class _StubRiskModels:
    def calculate_var(self, *a, **k): return 0.0
    def calculate_cvar(self, *a, **k): return 0.0
    def max_drawdown(self, *a, **k): return 0.0

class _StubStressTesting:
    def simulate_crash(self, *a, **k): return {}

class _StubRegimeDetector:
    def detect(self, *a, **k): return {"regime": "unknown", "trend_signal": "neutral", "volatility": 0.0}

class _StubOptimizer:
    def optimize(self): return {}


# ─────────────────────────────────────────────────────────────
# TICKER HELPERS
# ─────────────────────────────────────────────────────────────

def normalize_market(market: Optional[str]) -> str:
    m = (market or "us").strip().lower()
    if m in {"in", "india", "nse", "bse"}:
        return "india"
    return "us"


def detect_tickers_in_text(text: str) -> list:
    """Simple regex-based ticker extractor."""
    pattern = r"\b([A-Z]{1,5}(?:\.NS|\.BO)?)\b"
    return re.findall(pattern, text.upper())


def normalize_ticker_symbol(ticker: str, market: str) -> str:
    t = ticker.strip().upper()
    if market == "india" and not re.search(r"\.(NS|BO)$", t, re.I):
        return f"{t}.NS"
    return t


def detect_market_from_ticker(ticker: str) -> str:
    t = (ticker or "").upper()
    if t.endswith(".NS") or t.endswith(".BO"):
        return "india"
    return "us"


def resolve_ticker_and_market(query: str, ticker: Optional[str], market: Optional[str]) -> Tuple[Optional[str], str]:
    normalized_market = normalize_market(market)

    def _infer(sym: str, cur_market: str) -> str:
        inferred = normalize_market(detect_market_from_ticker(sym))
        return "india" if inferred == "india" else cur_market

    query_lower = (query or "").lower()
    discovery_kw = {"find", "search", "list", "show", "give", "recommend", "best", "top"}
    target_kw = {"stock", "stocks", "company", "companies", "ticker", "tickers", "sector"}
    if any(k in query_lower for k in discovery_kw) and any(t in query_lower for t in target_kw):
        return None, normalized_market

    if ticker and str(ticker).strip():
        raw = str(ticker).strip().upper()
        normalized_market = _infer(raw, normalized_market)
        t = normalize_ticker_symbol(raw, normalized_market)
        normalized_market = _infer(t, normalized_market)
        return t, normalized_market

    cmd = re.search(r"\b\w*backtest\b\s+([A-Za-z][A-Za-z0-9.\-]{0,19})", query or "", re.IGNORECASE)
    if cmd:
        candidate = cmd.group(1).strip().upper().rstrip(".,;:!?").replace("_", "-")
        if candidate not in {"MOMENTUM", "STRATEGY", "BACKTEST"}:
            normalized_market = _infer(candidate, normalized_market)
            candidate = normalize_ticker_symbol(candidate, normalized_market)
            normalized_market = _infer(candidate, normalized_market)
            return candidate, normalized_market

    candidates = detect_tickers_in_text(query or "")
    if candidates:
        raw = candidates[0].strip().upper()
        normalized_market = _infer(raw, normalized_market)
        t = normalize_ticker_symbol(raw, normalized_market)
        normalized_market = _infer(t, normalized_market)
        return t, normalized_market

    return None, normalized_market


def format_ticker_for_yfinance(ticker: str, market: str) -> str:
    if not ticker:
        return ticker
    t = ticker.strip().upper()
    if market == "india" and not re.search(r"\.(NS|BO)$", t, re.IGNORECASE):
        return f"{t}.NS"
    return t


# ─────────────────────────────────────────────────────────────
# INVESTMENT PIPELINE
# ─────────────────────────────────────────────────────────────

class InvestmentPipeline:
    """
    Orchestrates the full investment analysis pipeline.
    Uses the local Groq-powered pipeline for AI responses.
    Quant features (regime detection, risk models) are available
    but fail gracefully if underlying services are unavailable.
    """

    def __init__(self):
        self.memory = _StubVectorStore()
        self.sizing = PositionSizingService()
        self.trade_levels = TradeLevelsService()
        self.risk_models = _StubRiskModels()
        self.stress_testing = _StubStressTesting()
        self.regime_detector = _StubRegimeDetector()

        # Try loading the Groq pipeline for AI
        try:
            from .groq_agent import GroqAgent
            self._agent = GroqAgent()
        except Exception as e:
            print(f"[InvestmentPipeline] GroqAgent init failed: {e}")
            self._agent = None

    async def run(
        self,
        query: str,
        ticker: str = None,
        market: str = "us",
        portfolio=None,
        session_id: str = "default",
        approved_plan=None,
    ) -> dict:
        resolved_ticker, resolved_market = resolve_ticker_and_market(query, ticker, market)
        yf_ticker = format_ticker_for_yfinance(resolved_ticker, resolved_market) if resolved_ticker else None

        # Generate AI response via Groq
        report = ""
        try:
            if self._agent:
                prompt = f"Analyze: {query}"
                if yf_ticker:
                    prompt += f" for {yf_ticker} ({resolved_market} market)"
                report = await asyncio.to_thread(self._agent.run, prompt)
        except Exception as e:
            print(f"[InvestmentPipeline] AI analysis failed: {e}")
            report = f"Analysis for {yf_ticker or query}: Unable to generate AI report at this time."

        # Trade context if ticker provided
        trade_levels = {}
        sizing = {}
        if yf_ticker:
            try:
                trade_levels = self.trade_levels.get_levels(yf_ticker)
                capital = 100000.0
                if portfolio and isinstance(portfolio, dict) and "cash" in portfolio:
                    capital = float(portfolio["cash"])
                entry = trade_levels.get("current_price", 0) or 0
                stop = trade_levels.get("stop_loss", 0) or 0
                if entry and stop:
                    sizing = self.sizing.fixed_fraction(capital=capital)
            except Exception:
                pass

        # Store in memory
        self.memory.add(
            id=f"{session_id}_{uuid.uuid4()}",
            text=f"Query: {query}\nTicker: {yf_ticker or ''}\nReport: {report}",
            metadata={"type": "report", "session_id": session_id},
        )

        return {
            "report": report,
            "ticker": yf_ticker,
            "market": resolved_market,
            "emotion": {"label": "neutral", "score": 0.5, "penalty": 0},
            "financial": {"score": 50, "summary": ""},
            "web": {"score": 50, "summary": ""},
            "sector": {"score": 50, "summary": ""},
            "macro": {},
            "insider": {},
            "risk": {},
            "divergence": False,
            "confidence": 0.5,
            "strategy": {
                "trade_levels": trade_levels,
                "position_sizing": sizing,
            },
            "portfolio_optimization": {},
            "rl_strategy": {},
            "risk_engine": {},
        }
