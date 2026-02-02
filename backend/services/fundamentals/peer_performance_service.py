"""
peer_performance_service.py

Calculates relative price performance vs peers.
"""

import yfinance as yf
from typing import List, Dict


class PeerPerformanceService:
    def compare_performance(
        self,
        symbols: List[str],
        period: str = "6mo"
    ) -> List[Dict]:
        data = yf.download(symbols, period=period, progress=False)["Adj Close"]

        results = []
        for symbol in symbols:
            try:
                series = data[symbol]
                perf = (series.iloc[-1] / series.iloc[0] - 1) * 100
                results.append({
                    "symbol": symbol,
                    "return_pct": round(perf, 2)
                })
            except Exception:
                continue

        return results
