from __future__ import annotations

INDIAN_SECTORS = {
    "Private Banks": {
        "index": "^NSEBANK",
        "tickers": ["ICICIBANK.NS", "HDFCBANK.NS", "AXISBANK.NS", "KOTAKBANK.NS"],
    },
    "IT Services": {
        "index": "^CNXIT",
        "tickers": ["TCS.NS", "INFY.NS", "HCLTECH.NS", "WIPRO.NS"],
    },
    "Energy": {
        "index": "^CNXENERGY",
        "tickers": ["RELIANCE.NS", "ONGC.NS", "IOC.NS", "BPCL.NS"],
    },
    "Automobiles": {
        "index": "^CNXAUTO",
        "tickers": ["TATAMOTORS.NS", "M&M.NS", "BAJAJ-AUTO.NS", "EICHERMOT.NS"],
    },
    "FMCG": {
        "index": "^CNXFMCG",
        "tickers": ["HINDUNILVR.NS", "ITC.NS", "NESTLEIND.NS", "BRITANNIA.NS"],
    },
    "Pharma": {
        "index": "^CNXPHARMA",
        "tickers": ["SUNPHARMA.NS", "DRREDDY.NS", "CIPLA.NS", "DIVISLAB.NS"],
    },
    "Metals": {
        "index": "^CNXMETAL",
        "tickers": ["TATASTEEL.NS", "JSWSTEEL.NS", "HINDALCO.NS", "SAIL.NS"],
    },
    "Realty": {
        "index": "^CNXREALTY",
        "tickers": ["DLF.NS", "GODREJPROP.NS", "OBEROIRLTY.NS", "PRESTIGE.NS"],
    },
}

US_SECTORS = {
    "Technology": {
        "index": "XLK",
        "tickers": ["AAPL", "MSFT", "NVDA", "AVGO"],
    },
    "Financials": {
        "index": "XLF",
        "tickers": ["JPM", "BAC", "GS", "MS"],
    },
    "Energy": {
        "index": "XLE",
        "tickers": ["XOM", "CVX", "COP", "SLB"],
    },
    "Health Care": {
        "index": "XLV",
        "tickers": ["JNJ", "UNH", "LLY", "PFE"],
    },
    "Consumer Discretionary": {
        "index": "XLY",
        "tickers": ["AMZN", "TSLA", "HD", "MCD"],
    },
    "Industrials": {
        "index": "XLI",
        "tickers": ["GE", "CAT", "HON", "UPS"],
    },
}
