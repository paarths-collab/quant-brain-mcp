import yfinance as yf
import pandas as pd
import numpy as np
import re

class FinancialAgent:
    def __init__(self):
        pass

    async def execute(self, task: str):
        """Execute financial analysis task"""
        # Validate tickers with yfinance
        tickers = await self._extract_tickers(task)
        if not tickers:
            return {"error": "No tickers found"}

        results = {}
        for ticker in tickers:
            try:
                stock = yf.Ticker(ticker)
                info = stock.info
                hist = stock.history(period="6mo")
                
                if hist.empty:
                    results[ticker] = {"error": "No historical data"}
                    continue

                # Technicals
                current_price = hist["Close"].iloc[-1]
                sma_50 = hist["Close"].rolling(50).mean().iloc[-1]
                sma_200 = hist["Close"].rolling(200).mean().iloc[-1]
                
                # Risk
                returns = hist["Close"].pct_change().dropna()
                volatility = returns.std() * np.sqrt(252)

                results[ticker] = {
                    "current_price": current_price,
                    "market_cap": info.get("marketCap"),
                    "pe_ratio": info.get("trailingPE"),
                    "sma_50": sma_50,
                    "sma_200": sma_200,
                    "volatility_annual": volatility,
                    "val_metrics": {
                        "forward_pe": info.get("forwardPE"),
                        "peg_ratio": info.get("pegRatio"),
                        "price_to_book": info.get("priceToBook")
                    },
                    "sector": info.get("sector"),
                    "industry": info.get("industry"),
                    "recommendation": info.get("recommendationKey", "none")
                }
            except Exception as e:
                results[ticker] = {"error": str(e)}

        return {"analysis": results}

    async def _extract_tickers(self, task: str):
        # 1. Regex candidate extraction
        words = re.findall(r'\b[A-Z]{1,5}\b', task.upper())
        candidates = [w for w in words if w not in ["AND", "THE", "FOR", "IS", "TO"]]
        
        valid_tickers = []
        for cand in candidates:
            try:
                # Fast verification logic could be complex, for now simple check
                # Note: yf.Ticker(cand).info triggers a web call, which is slow. 
                # Better to just use the regex and let the execution loop handle 404s, 
                # OR do a quick check if "cand" looks like a real ticker (2+ chars)
                if len(cand) >= 2 or cand in ["C", "F", "T"]: 
                    valid_tickers.append(cand)
            except:
                continue
        return list(set(valid_tickers))[:3]
