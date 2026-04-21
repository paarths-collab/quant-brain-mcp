from __future__ import annotations

from typing import Any

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


def get_deep_fundamentals(ticker: str) -> dict[str, Any]:
    """Fetch deep fundamentals from yfinance for a single ticker."""
    normalized = _normalize_ticker(ticker)
    t = yf.Ticker(normalized)
    info = t.info or {}

    def _num(key: str, default: float = 0.0) -> float:
        val = info.get(key, default)
        try:
            return float(val) if val is not None else float(default)
        except Exception:
            return float(default)

    market_cap = _num("marketCap", 0.0)
    if normalized.endswith((".NS", ".BO")):
        market_cap_fmt = f"₹{market_cap / 1e7:.2f} Cr"
    else:
        market_cap_fmt = f"${market_cap / 1e9:.2f} B"

    return {
        "Company": info.get("longName") or info.get("shortName") or normalized,
        "Sector": info.get("sector"),
        "PE_Ratio": round(_num("trailingPE"), 2),
        "PB_Ratio": round(_num("priceToBook"), 2),
        "Debt_to_Equity": round(_num("debtToEquity"), 2),
        "ROE": f"{_num('returnOnEquity') * 100:.2f}%",
        "Market_Cap": market_cap_fmt,
        "Dividend_Yield": f"{_num('dividendYield') * 100:.2f}%",
        "Short_Ratio": info.get("shortRatio"),
    }


def get_company_info(ticker: Any) -> dict[str, Any]:
    """Return a structured company profile with business and market context."""
    normalized = _normalize_ticker(ticker)
    if not normalized:
        return {"error": "ticker is required and must be a non-empty string", "ticker": ticker}

    base_df, err = fetch_data(normalized)
    if err:
        return {"error": err, "ticker": normalized}

    try:
        t = yf.Ticker(normalized)
        info = t.info or {}
    except Exception as exc:
        return {"error": f"Failed to fetch company profile for {normalized}: {exc}", "ticker": normalized}

    def _pick(*keys: str, default=None):
        for key in keys:
            value = info.get(key)
            if value not in (None, "", [], {}):
                return value
        return default

    fundamentals = {
        "Name": _pick("longName", "shortName", default=normalized),
        "PE_Ratio": _pick("trailingPE"),
        "Forward_PE": _pick("forwardPE"),
        "Market_Cap": f"₹{(_pick('marketCap', default=0) or 0) / 1e7:.2f} Cr" if normalized.endswith((".NS", ".BO")) else _pick("marketCap"),
        "Dividend_Yield": f"{((_pick('dividendYield', default=0) or 0) * 100):.2f}%",
        "ROE": f"{((_pick('returnOnEquity', default=0) or 0) * 100):.2f}%",
        "Debt_To_Equity": _pick("debtToEquity"),
    }

    deep_fundamentals = get_deep_fundamentals(normalized)

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
            {"name": "yfinance historical OHLCV", "period": "2y", "interval": "1d"},
        ],
        "reproducibility": {
            "ticker": normalized,
            "source": "yfinance",
            "window": "2y",
            "interval": "1d",
        },
        "confidence": 0.92 if info else 0.55,
        "status": "ok",
    }
