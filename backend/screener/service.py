import pandas as pd
import yfinance as yf
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
    def fetch_ohlcv(self, ticker: str, interval: str, period: str) -> pd.DataFrame:
        try:
            df = yf.download(ticker, period=period, interval=interval, progress=False, auto_adjust=True)
            if df.empty or len(df) < PARAMS["volume_ma_period"] + PARAMS["momentum_period"]:
                return pd.DataFrame()
            df.index = pd.to_datetime(df.index)
            return df
        except:
            return pd.DataFrame()

    def compute_signals(self, df: pd.DataFrame) -> Optional[Dict[str, Any]]:
        close = df["Close"].squeeze()
        volume = df["Volume"].squeeze()
        mom_period = PARAMS["momentum_period"]
        vol_period = PARAMS["volume_ma_period"]

        if len(close) < mom_period + vol_period:
            return None

        roc = ((close.iloc[-1] - close.iloc[-mom_period]) / close.iloc[-mom_period]) * 100
        avg_volume = volume.iloc[-vol_period - 1 : -1].mean()
        vol_ratio = volume.iloc[-1] / avg_volume if avg_volume > 0 else 0
        latest_close = float(close.iloc[-1])
        sma20 = float(close.iloc[-vol_period:].mean())
        
        return {
            "close": round(latest_close, 2),
            "roc_pct": round(float(roc), 2),
            "vol_ratio": round(float(vol_ratio), 2),
            "trend": "up" if latest_close > sma20 else "down",
            "as_of": df.index[-1].strftime("%Y-%m-%d %H:%M"),
        }

    def run_scan(self, timeframe: str = "1d") -> List[Dict[str, Any]]:
        tf_params = PARAMS["timeframes"].get(timeframe)
        if not tf_params:
            return []

        results = []
        for ticker in WATCHLIST:
            df = self.fetch_ohlcv(ticker, tf_params["interval"], tf_params["period"])
            if df.empty:
                continue
            
            sig = self.compute_signals(df)
            if not sig:
                continue
            
            # Simple classification logic
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
