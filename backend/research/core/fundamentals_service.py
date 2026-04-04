"""
Isolated fundamentals_service for research/core.
Self-contained fundamental data fetching using unified MarketDataService.
"""
from typing import Dict, Any, Optional
from backend.services.market_data import market_service

def get_fundamentals_summary(ticker: str) -> Dict[str, Any]:
    """
    Fetch comprehensive fundamental data for a ticker using unified market_service.
    Returns a structured dict ready for research reports.
    """
    try:
        ticker = ticker.strip().upper()
        # MarketDataService handles normalization and safety
        info = market_service.get_fundamentals(ticker)
        
        if not info:
             return {"ticker": ticker, "error": "No fundamental data found.", "status": "error"}

        # Valuation
        pe = info.get("forwardPE") or info.get("trailingPE")
        pb = info.get("priceToBook")
        ps = info.get("priceToSalesTrailing12Months")
        ev_ebitda = info.get("enterpriseToEbitda")
        market_cap = info.get("marketCap")

        # Profitability
        roe = info.get("returnOnEquity")
        roa = info.get("returnOnAssets")
        profit_margin = info.get("profitMargins")
        gross_margin = info.get("grossMargins")
        operating_margin = info.get("operatingMargins")

        # Growth
        revenue_growth = info.get("revenueGrowth")
        earnings_growth = info.get("earningsGrowth")
        earnings_quarterly_growth = info.get("earningsQuarterlyGrowth")

        # Balance sheet
        debt_to_equity = info.get("debtToEquity")
        current_ratio = info.get("currentRatio")
        free_cashflow = info.get("freeCashflow")
        total_cash = info.get("totalCash")
        total_debt = info.get("totalDebt")

        # Dividends
        dividend_yield = info.get("dividendYield")
        payout_ratio = info.get("payoutRatio")

        # Price
        price = info.get("currentPrice") or info.get("regularMarketPrice")
        target_mean = info.get("targetMeanPrice")
        fifty_two_high = info.get("fiftyTwoWeekHigh")
        fifty_two_low = info.get("fiftyTwoWeekLow")
        beta = info.get("beta")

        return {
            "ticker": ticker,
            "name": info.get("longName") or info.get("shortName") or ticker,
            "sector": info.get("sector", "N/A"),
            "industry": info.get("industry", "N/A"),
            "description": (info.get("longBusinessSummary") or "")[:600],
            "valuation": {
                "pe_ratio": round(pe, 2) if pe else None,
                "pb_ratio": round(pb, 2) if pb else None,
                "ps_ratio": round(ps, 2) if ps else None,
                "ev_ebitda": round(ev_ebitda, 2) if ev_ebitda else None,
                "market_cap": market_cap,
            },
            "profitability": {
                "roe": round(roe * 100, 2) if roe else None,
                "roa": round(roa * 100, 2) if roa else None,
                "profit_margin": round(profit_margin * 100, 2) if profit_margin else None,
                "gross_margin": round(gross_margin * 100, 2) if gross_margin else None,
                "operating_margin": round(operating_margin * 100, 2) if operating_margin else None,
            },
            "growth": {
                "revenue_growth": round(revenue_growth * 100, 2) if revenue_growth else None,
                "earnings_growth": round(earnings_growth * 100, 2) if earnings_growth else None,
                "quarterly_earnings_growth": round(earnings_quarterly_growth * 100, 2) if earnings_quarterly_growth else None,
            },
            "balance_sheet": {
                "debt_to_equity": round(debt_to_equity, 2) if debt_to_equity else None,
                "current_ratio": round(current_ratio, 2) if current_ratio else None,
                "free_cashflow": free_cashflow,
                "total_cash": total_cash,
                "total_debt": total_debt,
            },
            "dividend": {
                "yield": round(dividend_yield * 100, 2) if dividend_yield else None,
                "payout_ratio": round(payout_ratio * 100, 2) if payout_ratio else None,
            },
            "price_info": {
                "current_price": price,
                "target_price": target_mean,
                "52w_high": fifty_two_high,
                "52w_low": fifty_two_low,
                "beta": round(beta, 2) if beta else None,
            },
            "status": "success",
        }
    except Exception as e:
        print(f"[fundamentals_service] get_fundamentals_summary({ticker}) failed: {e}")
        return {"ticker": ticker, "error": str(e), "status": "error"}
