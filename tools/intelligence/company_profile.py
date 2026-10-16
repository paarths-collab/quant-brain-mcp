from __future__ import annotations

from typing import Any
from datetime import datetime, timezone
import math

import yfinance as yf
import pandas as pd

from core.data_loader import fetch_data


def _normalize_ticker(ticker: Any) -> str:
    """Coerce the incoming ticker to a usable symbol string.

    The MCP layer should pass a string, but some client/tooling paths can
    accidentally hand us a DataFrame or other object. In that case, try to
    recover a ticker from obvious metadata before failing with a clear error.
    """
    if isinstance(ticker, str):
        normalized = ticker.strip().upper()
        if normalized:
            return normalized

    if isinstance(ticker, pd.DataFrame):
        for key in ("ticker", "symbol", "Ticker", "Symbol"):
            if key in ticker.attrs and ticker.attrs[key]:
                return str(ticker.attrs[key]).strip().upper()
        if len(ticker.columns) == 1:
            column_name = str(ticker.columns[0]).strip().upper()
            if column_name:
                return column_name

    if isinstance(ticker, pd.Series):
        for key in ("ticker", "symbol", "Ticker", "Symbol"):
            if key in ticker.index and pd.notna(ticker.get(key)):
                return str(ticker.get(key)).strip().upper()

    return str(ticker).strip().upper()


def _number(value: Any) -> float | None:
    if isinstance(value, bool):
        return None
    try:
        number = float(value)
        return number if math.isfinite(number) else None
    except (TypeError, ValueError, OverflowError):
        return None


def _formatted(value: Any, suffix: str = "", multiplier: float = 1) -> str | None:
    number = _number(value)
    return f"{number * multiplier:.2f}{suffix}" if number is not None else None


def get_deep_fundamentals(ticker: str, *, info: dict | None = None) -> dict[str, Any]:
    """Fetch deep fundamentals from yfinance for a single ticker."""
    normalized = _normalize_ticker(ticker)
    if info is None:
        info = yf.Ticker(normalized).info or {}
    market_cap = _number(info.get("marketCap"))
    if market_cap is None:
        market_cap_fmt = None
    elif info.get("currency") == "INR" or normalized.endswith((".NS", ".BO")):
        market_cap_fmt = f"₹{market_cap / 1e7:.2f} Cr"
    else:
        market_cap_fmt = f"{market_cap / 1e9:.2f} B {info.get('currency') or '(currency unknown)'}"

    return {
        "Company": info.get("longName") or info.get("shortName") or normalized,
        "Sector": info.get("sector"),
        "PE_Ratio": _number(info.get("trailingPE")),
        "PB_Ratio": _number(info.get("priceToBook")),
        "Debt_to_Equity": _number(info.get("debtToEquity")),
        "Debt_to_Equity_Unit": "percent",
        "ROE": _formatted(info.get("returnOnEquity"), "%", 100),
        "Market_Cap": market_cap_fmt,
        # yfinance's dividendYield already returns a percent value (2.42 == 2.42%),
        # not a fraction -- do not multiply by 100 again (bug: previously showed
        # "242.00%" for a stock yielding 2.42%).
        "Dividend_Yield": _formatted(info.get("dividendYield"), "%"),
        "Short_Ratio": _number(info.get("shortRatio")),
    }


def get_company_info(ticker: Any) -> dict[str, Any]:
    """Return a structured company profile with business and market context."""
    normalized = _normalize_ticker(ticker)
    if not normalized:
        return {"error": "ticker is required and must be a non-empty string", "ticker": ticker}

    try:
        t = yf.Ticker(normalized)
        info = t.info or {}
    except Exception as exc:
        return {"error": f"Failed to fetch company profile for {normalized}: {exc}", "ticker": normalized}
    if not info:
        return {"error": "No company profile data available", "ticker": normalized}

    def _pick(*keys: str, default=None):
        numeric = {"trailingPE", "forwardPE", "marketCap", "priceToBook", "dividendYield",
                   "returnOnEquity", "debtToEquity", "beta", "fiftyTwoWeekHigh", "fiftyTwoWeekLow", "fullTimeEmployees"}
        for key in keys:
            value = info.get(key)
            if value not in (None, "", [], {}):
                return _number(value) if key in numeric else value
        return default

    fundamentals = {
        "Name": _pick("longName", "shortName", default=normalized),
        "PE_Ratio": _pick("trailingPE"),
        "Forward_PE": _pick("forwardPE"),
        "Market_Cap": _formatted(_pick("marketCap"), " Cr INR", 1e-7) if normalized.endswith((".NS", ".BO")) else _number(_pick("marketCap")),
        # See get_deep_fundamentals: dividendYield from yfinance is already a
        # percent value, so it must not be multiplied by 100 again.
        "Dividend_Yield": _formatted(_pick("dividendYield"), "%"),
        "ROE": _formatted(_pick("returnOnEquity"), "%", 100),
        "Debt_To_Equity": _number(_pick("debtToEquity")),
        "Debt_To_Equity_Unit": "percent",
    }

    deep_fundamentals = get_deep_fundamentals(normalized, info=info)
    debt_pct = _number(_pick("debtToEquity"))
    fetched_at = datetime.now(timezone.utc).isoformat()

    return {
        "ticker": normalized,
        "company_name": _pick("shortName", "longName", default=normalized),
        "sector": _pick("sector"),
        "industry": _pick("industry"),
        "country": _pick("country"),
        "exchange": _pick("exchange"),
        "market_cap": _pick("marketCap"),
        "beta": _pick("beta"),
        "trailing_pe": _pick("trailingPE"),
        "forward_pe": _pick("forwardPE"),
        "price_to_book": _pick("priceToBook"),
        "dividend_yield": _pick("dividendYield"),
        "debt_to_equity_percent": debt_pct,
        "debt_to_equity_ratio": debt_pct / 100 if debt_pct is not None else None,
        "field_units": {
            "debt_to_equity_percent": "percent (9.83 means 9.83%, not 9.83 times)",
            "debt_to_equity_ratio": "times (debt divided by equity)",
            "fundamentals.Debt_To_Equity": "percent",
            "deep_fundamentals.Debt_to_Equity": "percent",
            "dividend_yield": "percent",
            "trailing_pe": "times; trailing earnings",
            "forward_pe": "times; provider forward estimate, estimate date unknown",
            "price_to_book": "times",
            "market_cap": info.get("currency") or "unknown quote currency",
        },
        "52_week_high": _pick("fiftyTwoWeekHigh"),
        "52_week_low": _pick("fiftyTwoWeekLow"),
        "website": _pick("website"),
        "employees": _pick("fullTimeEmployees"),
        "summary": _pick("longBusinessSummary"),
        "financial_currency": _pick("financialCurrency"),
        "fundamentals": fundamentals,
        "deep_fundamentals": deep_fundamentals,
        "source": [
            {"name": "yfinance.Ticker.info", "ticker": normalized},
        ],
        "reproducibility": {
            "ticker": normalized,
            "source": "yfinance",
            "provider_fields": {"debt_to_equity_percent": "debtToEquity", "debt_to_equity_ratio": "debtToEquity / 100"},
            "retrieved_at": fetched_at,
        },
        "retrieved_at": fetched_at,
        "valuation_as_of": None,
        "freshness_status": "unknown",
        "confidence": None,
        "confidence_basis": "Unverified provider snapshot; no calibrated accuracy probability is available.",
        "warnings": [
            "Retrieval time is not a financial reporting date or valuation observation time.",
            "Forward estimates and valuation dates are not verified; missing values are null, not zero.",
            "Legacy debt-to-equity fields retain the provider percent unit; use debt_to_equity_ratio for a multiple.",
        ],
        "status": "ok",
    }
