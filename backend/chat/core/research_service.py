"""
Isolated research_service for chat/core.
Refactored to use unified MarketDataService.
Ensures 100% architectural consistency and resolves direct yfinance usage.
"""
from typing import Dict, Any
from backend.services.market_data import market_service

def generate_research_report(ticker: str, market: str = "us") -> Dict[str, Any]:
    """
    [DELEGATED] Generate a structured research report using unified MarketDataService.
    """
    try:
        # MarketDataService handles normalization and safety
        info = market_service.get_fundamentals(ticker)
        
        if not info:
             return {"ticker": ticker.upper(), "error": "No data found", "status": "error"}

        name = info.get("longName") or info.get("shortName") or ticker
        sector = info.get("sector", "N/A")
        industry = info.get("industry", "N/A")
        pe = info.get("forwardPE") or info.get("trailingPE")
        market_cap = info.get("marketCap")
        price = info.get("currentPrice") or info.get("regularMarketPrice")
        fifty_two_high = info.get("fiftyTwoWeekHigh")
        fifty_two_low = info.get("fiftyTwoWeekLow")
        summary = info.get("longBusinessSummary", "No summary available.")

        return {
            "ticker": ticker.upper(),
            "name": name,
            "sector": sector,
            "industry": industry,
            "price": price,
            "pe_ratio": pe,
            "market_cap": market_cap,
            "52w_high": fifty_two_high,
            "52w_low": fifty_two_low,
            "summary": summary[:500] if summary else "N/A",
            "status": "success",
        }
    except Exception as e:
        print(f"[research_service] generate_research_report({ticker}) failed: {e}")
        return {"ticker": ticker, "error": str(e), "status": "error"}

def get_fundamentals_summary(ticker: str) -> Dict[str, Any]:
    """Return key fundamental metrics for a ticker."""
    return generate_research_report(ticker)
