# File: utils/market_utils.py
# This is the centralized utility for market-specific configurations.

def get_market_config(market: str) -> dict:
    """
    Returns a configuration dictionary for a given market, including
    currency symbols, currency codes, and benchmark tickers.
    """
    market = market.upper()

    # --- Market Configurations ---
    if market in ["US", "USA"]:
        return {
            "currency_code": "USD",
            "currency_symbol": "$",
            "benchmark_ticker": "^GSPC",  # S&P 500
            "market_name": "United States"
        }
    elif market in ["IN", "INDIA"]:
        return {
            "currency_code": "INR",
            "currency_symbol": "₹",
            "benchmark_ticker": "^NSEI",  # Nifty 50
            "market_name": "India"
        }
    elif market in ["EU", "EUROPE", "EUR"]:
        return {
            "currency_code": "EUR",
            "currency_symbol": "€",
            "benchmark_ticker": "^STOXX50E",  # EURO STOXX 50
            "market_name": "Eurozone"
        }
    elif market in ["GB", "UK", "GBP"]:
        return {
            "currency_code": "GBP",
            "currency_symbol": "£",
            "benchmark_ticker": "^FTSE",  # FTSE 100
            "market_name": "United Kingdom"
        }
    elif market in ["JP", "JAPAN", "JPY"]:
        return {
            "currency_code": "JPY",
            "currency_symbol": "¥",
            "benchmark_ticker": "^N225",  # Nikkei 225
            "market_name": "Japan"
        }
    else:
        # Default to US market if no match is found
        return {
            "currency_code": "USD",
            "currency_symbol": "$",
            "benchmark_ticker": "^GSPC",
            "market_name": "United States"
        }

def get_currency_symbol(currency_code: str) -> str:
    """
    Returns the symbol for a given currency code.
    """
    symbols = {
        "USD": "$",
        "INR": "₹",
        "EUR": "€",
        "GBP": "£",
        "JPY": "¥"
    }
    return symbols.get(currency_code.upper(), "$") # Default to '$'