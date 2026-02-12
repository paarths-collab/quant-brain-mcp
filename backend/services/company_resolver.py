from functools import lru_cache

import yfinance as yf

from backend.services.data_loader import format_ticker, _get_indian_symbols_set


COMPANY_OVERRIDES = {
    "RELIANCE": "Reliance Industries Limited",
    "TCS": "Tata Consultancy Services",
    "INFY": "Infosys Limited",
    "HDFCBANK": "HDFC Bank Limited",
}

def _detect_market(ticker: str, market: str | None) -> str:
    if market:
        market_upper = market.upper()
        if market_upper in {"IN", "INDIA"}:
            return "IN"
        if market_upper in {"US", "USA"}:
            return "US"
    cleaned = (ticker or "").upper()
    if cleaned.endswith(".NS") or cleaned.endswith(".BO"):
        return "IN"
    base = cleaned.replace(".NS", "").replace(".BO", "")
    try:
        if base in _get_indian_symbols_set():
            return "IN"
    except Exception:
        pass
    return "US"


@lru_cache(maxsize=256)
def resolve_company_identity(ticker: str, market: str | None):
    cleaned = (ticker or "").upper().replace(".NS", "").replace(".BO", "")
    market_upper = _detect_market(ticker, market)

    yf_ticker = format_ticker(cleaned, market_upper)
    company_name = None

    try:
        info = yf.Ticker(yf_ticker).info or {}
        company_name = info.get("longName") or info.get("shortName")
    except Exception:
        company_name = None

    if not company_name:
        company_name = COMPANY_OVERRIDES.get(cleaned, cleaned)

    if market_upper in {"IN", "INDIA"}:
        return {
            "ticker": cleaned,
            "company": company_name,
            "exchange": "NSE",
            "currency": "INR",
        }

    return {
        "ticker": cleaned,
        "company": company_name,
        "exchange": "NASDAQ/NYSE",
        "currency": "USD",
    }
