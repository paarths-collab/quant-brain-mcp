import yfinance as yf
import numpy as np


class FinancialAnalystAgent:

    def run(self, task: str, state=None):
        # 1. Direct Ticker check (No parsing if it's already a ticker)
        # Assuming task is the ticker if it has no spaces and is < 12 chars
        if " " not in task.strip() and len(task.strip()) < 12:
            ticker = task.strip().upper()
            print(f"DEBUG: Using direct ticker: {ticker}")
        else:
            print(f"DEBUG: Extracting ticker from task: {task}")
            ticker = self._extract_ticker(task)
            print(f"DEBUG: Extracted ticker: {ticker}")

        if not ticker:
            return {"error": "No ticker found in task"}

        try:
            stock = yf.Ticker(ticker)
            info = stock.info
            
            # Check for delisting/no data
            if not info or "regularMarketPrice" not in info and "currentPrice" not in info:
                 # Check history as backup for price
                 hist = stock.history(period="1d")
                 if hist.empty:
                      return {"error": f"No data found for {ticker} (possibly delisted)"}
                 current_price = hist["Close"].iloc[-1]
            else:
                 current_price = info.get("currentPrice") or info.get("regularMarketPrice")

            # NO HARDCODED DEFAULTS as per user request
            # Let them be None if missing
            return {
                "ticker": ticker,
                "current_price": float(current_price) if current_price else None,
                "market_cap": info.get("marketCap"),
                "metrics": {
                    "revenue_growth_qtr_yoy": info.get("revenueGrowth"),
                    "earnings_growth_qtr_yoy": info.get("earningsGrowth"),
                    "trailing_pe": info.get("trailingPE"),
                    "forward_pe": info.get("forwardPE"),
                    "peg_ratio": info.get("pegRatio"),
                    "price_to_book": info.get("priceToBook"),
                    "beta": info.get("beta"),
                    "volatility_1y": hist["Close"].pct_change().std() * (252**0.5) if not hist.empty else None
                },
                "sector": info.get("sector"),
                "industry": info.get("industry"),
                "recommendation": info.get("recommendationKey", "none")
            }
        except Exception as e:
            return {"error": str(e)}

    def _extract_ticker(self, text):
        import re
        # 1. Regex candidate extraction (2-5 chars to avoid single letters like 'I', 'A')
        # Also include common single letters if needed (C, F, T) but verify later
        candidates = re.findall(r'\b[A-Z]{1,5}(?:\.[A-Z]{2})?\b', text)
        
        valid_tickets = []
        for cand in candidates:
            if cand in ["AI", "THE", "FOR", "IS", "TO", "OF", "AND"]:
                continue
            
            # Simple heuristic: Real tickers often have financial output. 
            # Ideally we check yf.Ticker(cand).fast_info but that can be slow.
            # For now, trust regex but exclude common words.
            if len(cand) >= 2 or cand in ["C", "F", "T", "O", "X"]:
                valid_tickets.append(cand)
                
        return valid_tickets[0] if valid_tickets else None
