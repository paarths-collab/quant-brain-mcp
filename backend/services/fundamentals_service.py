import yfinance as yf
from typing import Dict, Any

def get_fundamentals_summary(symbol: str) -> Dict[str, Any]:
    """
    Aggregates profile and key metrics using yfinance.
    """
    try:
        ticker = yf.Ticker(symbol)
        info = ticker.info or {}
        
        # Map yfinance info to our schema
        summary = {
            "symbol": symbol,
            "name": info.get("shortName"),
            "sector": info.get("sector"),
            "industry": info.get("industry"),
            "description": info.get("longBusinessSummary"),
            "price": info.get("currentPrice") or info.get("regularMarketPrice"),
            "marketCap": info.get("marketCap"),
            "currency": info.get("currency"),
            "exchange": info.get("exchange"),
            "website": info.get("website"),
            "metrics": {
                "peRatio": info.get("trailingPE"),
                "pegRatio": info.get("pegRatio"),
                "priceToBook": info.get("priceToBook"),
                "dividendYield": info.get("dividendYield"),
                "roe": info.get("returnOnEquity"),
                "roic": None, # yfinance often lacks ROIC directly, omit or calc if needed
                "debtToEquity": info.get("debtToEquity"),
                "revenueGrowth": info.get("revenueGrowth"),
                "epsGrowth": info.get("earningsGrowth") 
            }
        }
        return summary
    except Exception as e:
        print(f"Error fetching fundamentals for {symbol}: {e}")
        return {}
