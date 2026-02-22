import yfinance as yf
import pandas as pd

class InsiderAgent:

    def analyze(self, ticker):
        try:
            stock = yf.Ticker(ticker)
            insiders = stock.insider_transactions
            
            if insiders is None or insiders.empty:
                 return {
                    "activity": "unknown", 
                    "score": 50, 
                    "summary": "No insider transactions data available."
                }

            # Normalize columns if needed (Yahoo's structure varies slightly by version)
            # Typically has: 'Shares', 'Value', 'Text', 'Start Date', 'Ownership', etc.
            # But the user requested generic 'Transaction' check.
            # Yahoo often returns a dataframe with 'Shares', 'Value', 'Text', 'Start Date'.
            # 'Text' usually contains "Sale at price..." or "Purchase at price..."
            
            recent = insiders.head(5)
            
            # Simple heuristic since 'Transaction' column might not strictly exist in all yahoo versions as "Buy"/"Sell"
            # We often check the 'Text' or 'Shares' (negative = sell).
            # Assuming 'Text' contains keywords or 'Shares' sign (if available).
            
            # Let's try to infer from 'Text' provided by yfinance or fallback to 0.
            buy_count = 0
            if "Text" in recent.columns:
                buy_count = sum(recent["Text"].str.contains("Purchase", case=False, na=False))
            
            # Logic: > 2 buys in top 5 transactions = Bullish
            if buy_count >= 3:
                summary = "Insider activity skews bullish (multiple purchases)."
                score = 70
            elif buy_count == 0:
                summary = "No recent insider purchases detected (neutral-to-bearish)."
                score = 45
            else:
                summary = "Mixed insider activity (limited purchases)."
                score = 55
            
            # Convert timestamps to str for JSON serialization
            recent_dict = recent.reset_index(drop=True).to_dict()
            # Clean up potential Timestamp objects in dict values
            
            return {
                "recent_activity": "Simulated/Raw Data", # Keeping it simple for the contract
                "buy_count_last_5": int(buy_count),
                "score": score,
                "summary": summary,
                "raw_data_snippet": str(recent_dict)[:200] # Truncate for safety
            }
        except Exception as e:
            print(f"InsiderAgent Error: {e}")
            return {"error": str(e), "score": 50, "summary": "Insider data lookup failed."}
