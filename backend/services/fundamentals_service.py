import yfinance as yf
from typing import Dict, Any, Optional
from datetime import datetime


def _format_ex_dividend_date(raw: Optional[float]) -> Optional[str]:
    if raw is None:
        return None
    try:
        return datetime.utcfromtimestamp(int(raw)).strftime("%Y-%m-%d")
    except Exception:
        return None

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
                # Valuation
                "peRatio": info.get("trailingPE"),
                "forwardPE": info.get("forwardPE"),
                "pegRatio": info.get("pegRatio"),
                "priceToBook": info.get("priceToBook"),
                "enterpriseToEbitda": info.get("enterpriseToEbitda"),
                "enterpriseValue": info.get("enterpriseValue"),
                # Financial Health
                "debtToEquity": info.get("debtToEquity"),
                "currentRatio": info.get("currentRatio"),
                "freeCashflow": info.get("freeCashflow"),
                # Profitability
                "roe": info.get("returnOnEquity"),
                "operatingMargins": info.get("operatingMargins"),
                # Dividends
                "dividendYield": info.get("dividendYield"),
                "payoutRatio": info.get("payoutRatio"),
                "exDividendDate": _format_ex_dividend_date(info.get("exDividendDate")),
                # Risk
                "beta": info.get("beta"),
                "shortRatio": info.get("shortRatio"),
                "shortPercentOfFloat": info.get("shortPercentOfFloat"),
                # Growth
                "revenueGrowth": info.get("revenueGrowth"),
                "epsGrowth": info.get("earningsGrowth"),
                # Analyst
                "recommendationKey": info.get("recommendationKey"),
                "targetMeanPrice": info.get("targetMeanPrice"),
                "numberOfAnalystOpinions": info.get("numberOfAnalystOpinions"),
                # Misc
                "roic": None, # yfinance often lacks ROIC directly, omit or calc if needed
            }
        }
        return summary
    except Exception as e:
        print(f"Error fetching fundamentals for {symbol}: {e}")
        return {}
