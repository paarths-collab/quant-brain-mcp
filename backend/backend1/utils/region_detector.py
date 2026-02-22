import re

INDIA_KEYWORDS = [
    "india", "nse", "bse", "sensex", "nifty",
    "tcs", "reliance", "hdfc", "infosys", ".ns",
    "mumbai", "rupee", "inr"
]

US_KEYWORDS = [
    "us", "usa", "america", "nasdaq", "nyse", "s&p", "sp500",
    "dow", "apple", "microsoft", "tesla", "dollar", "usd"
]

def detect_region(query):
    """
    Detects if the query is targeting the US or Indian market.
    Defaults to US if ambiguous.
    """
    q = query.lower()

    for word in INDIA_KEYWORDS:
        if word in q:
            return "India"

    for word in US_KEYWORDS:
        if word in q:
            return "US"

    # Default to India
    return "India"
