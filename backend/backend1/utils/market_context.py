import yfinance as yf
import logging

def get_market_context(region):
    """
    Fetches market context (Index P/E and Risk-Free Rate) for the specified region.
    """
    try:
        if region == "US":
            index_symbol = "^GSPC"   # S&P 500
            rf_symbol = "^TNX"       # 10-Year Treasury Yield
        elif region == "India":
            index_symbol = "^NSEI"   # Nifty 50
            # For India, we can use 10y bond yield if available on Yahoo, 
            # or proxy. ^IGDB is not always reliable. 
            # Using specific ticker or fallback. 
            # For now, let's try to find a proxy or default to a fixed rate if fetch fails.
            rf_symbol = "^TNX" # Fallback to US rate for now if India specific not found easily, or use fixed.
            # actually better to use a fixed conservative rate if API fails for India 
            # or look for "^IGS" (India Govt Bond) if it exists. 
            # Let's stick to US ^TNX as a global proxy or hardcode 7% for India if we want realism.
            # But let's try to fetch US rate as baseline.

        else:
            return None

        # Fetch Index Info for P/E
        # Note: yf.Ticker(index).info might be slow or rate limited.
        # We handle errors gracefully.
        
        index_ticker = yf.Ticker(index_symbol)
        try:
            # fast_info might be better for some data, but info has trailingPE
            info = index_ticker.info 
            trailing_pe = info.get("trailingPE")
            if trailing_pe is None:
                # Fallback defaults
                trailing_pe = 25.0 if region == "US" else 22.0
        except Exception:
            trailing_pe = 25.0 if region == "US" else 22.0

        # Fetch Risk Free Rate
        try:
            rf_ticker = yf.Ticker(rf_symbol)
            # get recent close
            hist = rf_ticker.history(period="5d")
            if not hist.empty:
                rf_rate = hist["Close"].iloc[-1] / 100.0 # Convert 4.5 to 0.045
            else:
                rf_rate = 0.045
        except Exception:
            rf_rate = 0.045

        # Adjust for India inflation/rate differential manually if using US proxy
        if region == "India" and rf_symbol == "^TNX":
            rf_rate = 0.07 # Approx 7% for India 10Y

        return {
            "index": index_symbol,
            "element_pe": trailing_pe, # Kept generic naming or specific? adhering to plan: trailing_pe
            "trailing_pe": trailing_pe,
            "risk_free_rate": rf_rate
        }

    except Exception as e:
        print(f"Error fetching market context: {e}")
        # robust fallbacks
        if region == "India":
             return {"index": "^NSEI", "trailing_pe": 22.0, "risk_free_rate": 0.07}
        return {"index": "^GSPC", "trailing_pe": 25.0, "risk_free_rate": 0.045}
