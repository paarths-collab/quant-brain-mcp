import yfinance as yf

def get_risk_free_rate():
    """
    Fetches the 10-Year US Treasury Yield (^TNX) and converts it to a decimal.
    Example: 4.5% -> 0.045
    """
    try:
        # ^TNX is CBOE Interest Rate 10 Year T Note
        tnx = yf.Ticker("^TNX")
        hist = tnx.history(period="5d")
        if hist.empty:
            return 0.04 # Fallback to 4% if fail
        
        rate = hist["Close"].iloc[-1]
        return rate / 100.0 
    except Exception as e:
        print(f"Error fetching Risk-Free Rate: {e}. Defaulting to 4%.")
        return 0.04 # Fallback
