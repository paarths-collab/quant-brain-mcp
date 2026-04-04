from backend.services.market_data import market_service
from backend.services.technical_analysis import technical_service
import numpy as np
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from typing import List, Dict, Any, Optional

# --- Configuration ---
IST = ZoneInfo("Asia/Kolkata")

WATCHLIST = [
    "HDFCBANK.NS", "ICICIBANK.NS", "SBIN.NS", "AXISBANK.NS", "KOTAKBANK.NS",
    "BAJFINANCE.NS", "BAJAJFINSV.NS", "SBILIFE.NS", "HDFCLIFE.NS", "SHRIRAMFIN.NS",
    "JIOFIN.NS", "TCS.NS", "INFY.NS", "HCLTECH.NS", "TECHM.NS", "WIPRO.NS",
    "RELIANCE.NS", "ONGC.NS", "COALINDIA.NS", "POWERGRID.NS", "NTPC.NS",
    "MARUTI.NS", "M&M.NS", "BAJAJ-AUTO.NS", "EICHERMOT.NS", "HINDUNILVR.NS",
    "ITC.NS", "NESTLEIND.NS", "TATACONSUM.NS", "ASIANPAINT.NS", "TRENT.NS",
    "TATASTEEL.NS", "JSWSTEEL.NS", "HINDALCO.NS", "ADANIENT.NS", "SUNPHARMA.NS",
    "CIPLA.NS", "DRREDDY.NS", "APOLLOHOSP.NS", "MAXHEALTH.NS", "LT.NS",
    "GRASIM.NS", "ULTRACEMCO.NS", "BHARTIARTL.NS", "ADANIPORTS.NS", "BEL.NS",
    "INDIGO.NS", "ETERNAL.NS", "TITAN.NS",
]

PARAMS = {
    "momentum_period": 14,
    "volume_ma_period": 20,
    "min_momentum_pct": 2.0,
    "max_momentum_pct": -2.0,
    "volume_spike_multiplier": 1.5,
    "timeframes": {
        "1d": {"period": "6mo",  "interval": "1d"},
        "1h": {"period": "30d",  "interval": "1h"},
        "15m": {"period": "5d",  "interval": "15m"},
    }
}

class ScreenerService:
    def run_scan(self, timeframe: str = "1d") -> List[Dict[str, Any]]:
        tf_params = PARAMS["timeframes"].get(timeframe)
        if not tf_params:
            return []

        results = []
        for ticker in WATCHLIST:
            # 1. Fetch OHLCV using unified service
            df = market_service.fetch_ohlcv(
                ticker, 
                interval=tf_params["interval"], 
                period=tf_params["period"],
                market="india"
            )
            
            if df.empty:
                continue
            
            # 2. Compute signals using unified service
            sig = technical_service.compute_signals(
                df, 
                mom_period=PARAMS["momentum_period"], 
                vol_period=PARAMS["volume_ma_period"]
            )
            
            if not sig:
                continue
            
            # 3. Simple classification logic (Standardized at domain level)
            label = "SKIP"
            if sig["roc_pct"] >= PARAMS["min_momentum_pct"] and sig["vol_ratio"] >= PARAMS["volume_spike_multiplier"]:
                label = "LONG"
            elif sig["roc_pct"] <= PARAMS["max_momentum_pct"] and sig["vol_ratio"] >= PARAMS["volume_spike_multiplier"]:
                label = "SHORT"
            elif sig["vol_ratio"] >= PARAMS["volume_spike_multiplier"]:
                label = "WATCH"
            
            if label != "SKIP":
                results.append({
                    "ticker": ticker.replace(".NS", ""),
                    "signal": label,
                    **sig
                })
        
        # Sort results
        order = {"LONG": 0, "SHORT": 1, "WATCH": 2}
        results.sort(key=lambda x: (order.get(x["signal"], 3), -x["vol_ratio"]))
        return results
