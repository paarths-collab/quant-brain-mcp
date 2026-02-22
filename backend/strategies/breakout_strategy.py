import yfinance as yf
import numpy as np
import pandas as pd

class BreakoutStrategy:

    def run(self, ticker):
        try:
            df = yf.Ticker(ticker).history(period="1y")
            
            if df.empty:
                 return {
                    "strategy": "Breakout",
                    "return": 0.0,
                    "win_rate": 0.0,
                    "last_signal": 0,
                    "error": "No data found"
                }

            # 20-day High Breakout
            df["high_20"] = df["High"].rolling(20).max()
            
            # Signal: Price > Prev 20-day High
            # Using shift(1) for high_20 to avoid lookahead bias? 
            # User code: df["signal"] = np.where(df["Close"] > df["high_20"], 1, 0)
            # Assuming standard Donchian Channel breakout logic.
            df["signal"] = np.where(df["Close"] > df["high_20"], 1, 0)

            df["returns"] = df["Close"].pct_change()
            df["strategy_returns"] = df["signal"].shift(1) * df["returns"]

            total_return = (1 + df["strategy_returns"].fillna(0)).cumprod().iloc[-1] - 1
            
            non_zero_trades = df[df["strategy_returns"] != 0]
            if len(non_zero_trades) > 0:
                win_rate = (non_zero_trades["strategy_returns"] > 0).sum() / len(non_zero_trades)
            else:
                win_rate = 0.0

            # Equity Curve
            df["normalized_equity"] = (1 + df["strategy_returns"].fillna(0)).cumprod() * 100

            return {
                "strategy": "Breakout",
                "return": float(total_return * 100),
                "win_rate": float(win_rate * 100),
                "last_signal": int(df["signal"].iloc[-1]),
                "equity_curve": [
                    {"time": d.strftime("%Y-%m-%d"), "value": float(v)} 
                    for d, v in zip(df.index, df["normalized_equity"])
                ],
                "signals": [
                    {"time": d.strftime("%Y-%m-%d"), "type": "BUY" if s==1 else "SELL", "price": float(p)}
                    for d, s, p in zip(df.index, df["signal"].diff(), df["Close"])
                    if s != 0 and not np.isnan(s)
                ],
                 "price_data": [
                    {
                        "time": d.strftime("%Y-%m-%d"),
                        "open": float(o),
                        "high": float(h),
                        "low": float(l),
                        "close": float(c),
                        "volume": int(v)
                    }
                    for d, o, h, l, c, v in zip(df.index[-200:], df["Open"][-200:], df["High"][-200:], df["Low"][-200:], df["Close"][-200:], df["Volume"][-200:])
                ]
            }
        except Exception as e:
            return {
                "strategy": "Breakout",
                "return": 0.0,
                "win_rate": 0.0,
                "last_signal": 0,
                "error": str(e)
            }
