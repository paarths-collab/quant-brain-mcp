INDICATOR_KNOWLEDGE = {
    "momentum": {
        "count": 40,
        "key_indicators": ["rsi", "macd", "stoch", "willr"],
        "purpose": "Measures the speed of price movement.",
        "logic": "RSI > 70 is overbought; MACD Histogram crossover suggests momentum shift.",
        "best_market": "Strongly trending or parabolic markets.",
    },
    "overlap": {
        "count": 34,
        "key_indicators": ["sma", "ema", "vwap", "supertrend"],
        "purpose": "Price-based overlays to identify trend direction.",
        "logic": "Price above SMA 200 is long-term bullish; Supertrend green = Buy.",
        "best_market": "Trending markets. Useless in sideways 'choppy' markets.",
    },
    "volatility": {
        "count": 14,
        "key_indicators": ["bbands", "atr", "kc"],
        "purpose": "Measures market fear and price range.",
        "logic": "High ATR = High risk; BBands Squeeze = Potential breakout coming.",
        "best_market": "High-fear markets or periods of extreme consolidation.",
    },
    "volume": {
        "count": 14,
        "key_indicators": ["obv", "cmf", "mfi", "ad"],
        "purpose": "Verifies if a move is backed by institutional 'Smart Money'.",
        "logic": "Rising price with falling OBV is a 'Fake-out'.",
        "best_market": "All. Volume is the ultimate truth-teller.",
    },
    "stats_misc": {
        "count": 52,
        "key_indicators": ["zscore", "skew", "kurtosis", "entropy"],
        "purpose": "Statistical probability of crashes or reversals.",
        "logic": "Z-Score < -2 is a statistical anomaly; high chance of mean reversion.",
        "best_market": "Identifying 'Black Swan' events or extreme value.",
    },
}
