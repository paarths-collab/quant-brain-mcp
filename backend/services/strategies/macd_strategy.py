
# core/strategies/macd_crossover.py

import pandas as pd
from .base import Strategy


class MACDCrossoverStrategy(Strategy):
    """
    MACD Crossover Strategy

    Long  → MACD crosses above Signal
    Short → MACD crosses below Signal
    """

    name = "MACD Crossover"

    def __init__(self, fast: int = 12, slow: int = 26, signal: int = 9):
        if fast >= slow:
            raise ValueError("Fast period must be less than slow period")

        self.fast = fast
        self.slow = slow
        self.signal = signal

    def parameters(self) -> dict:
        return {
            "fast": self.fast,
            "slow": self.slow,
            "signal": self.signal
        }

    def generate_signals(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        Expected columns: ['Open', 'High', 'Low', 'Close']
        """

        df = data.copy()

        # --- EMA calculations ---
        ema_fast = df["Close"].ewm(span=self.fast, adjust=False).mean()
        ema_slow = df["Close"].ewm(span=self.slow, adjust=False).mean()

        # --- MACD components ---
        df["macd"] = ema_fast - ema_slow
        df["macd_signal"] = df["macd"].ewm(span=self.signal, adjust=False).mean()
        df["macd_hist"] = df["macd"] - df["macd_signal"]

        # --- Signal columns ---
        df["signal"] = 0
        df["entry_long"] = None
        df["entry_short"] = None

        # --- Crossover logic (no lookahead bias) ---
        bullish_cross = (
            (df["macd"] > df["macd_signal"]) &
            (df["macd"].shift(1) <= df["macd_signal"].shift(1))
        )

        bearish_cross = (
            (df["macd"] < df["macd_signal"]) &
            (df["macd"].shift(1) >= df["macd_signal"].shift(1))
        )

        df.loc[bullish_cross, "signal"] = 1
        df.loc[bullish_cross, "entry_long"] = df["Close"]

        df.loc[bearish_cross, "signal"] = -1
        df.loc[bearish_cross, "entry_short"] = df["Close"]

        return df
# import pandas as pd
# import streamlit as st
# import plotly.graph_objects as go
# from backtesting import Backtest, Strategy
# from backtesting.lib import crossover
# import ta # Make sure you have the 'ta' library installed (pip install ta)

# # --- CORRECT: Import the single, centralized get_data function ---
# from backend.services.data_loader import get_data
# from backend.services.market_utils import get_market_config

# class MacdCross(Strategy):
#     """
#     MACD Crossover Strategy implementation for backtesting.py library.
    
#     This strategy generates buy signals when the MACD line crosses above the signal line
#     and sell signals when the MACD line crosses below the signal line.
#     """
    
#     def init(self):
#         close = pd.Series(self.data.Close)
#         self.macd_line = self.I(ta.trend.macd, close, window_fast=self.fast_ema, window_slow=self.slow_ema)
#         self.macd_signal_line = self.I(ta.trend.macd_signal, close, window_fast=self.fast_ema, window_slow=self.slow_ema, window_sign=self.signal_ema)

#     def next(self):
#         if crossover(self.macd_line, self.macd_signal_line):
#             self.position.close()
#             self.buy()
#         elif crossover(self.macd_signal_line, self.macd_line):
#             self.position.close()
#             self.sell()

# # --- Main Run Function (Callable by Portfolio Builder) ---
# def run(ticker, start_date, end_date, market: str = "US", initial_capital=100000, **kwargs):
#     """ Main orchestrator function for the MACD Crossover strategy. """
    
#     # Get strategy-specific parameters from kwargs
#     fast_period = kwargs.get('fast', 12)
#     slow_period = kwargs.get('slow', 26)
#     signal_period = kwargs.get('signal', 9)
    
#     # Set the parameters for the strategy class
#     MacdCross.fast_ema = fast_period
#     MacdCross.slow_ema = slow_period
#     MacdCross.signal_ema = signal_period

#     # --- CORRECT: Call the centralized get_data function with the market ---
#     hist_df = get_data(ticker, start_date, end_date, market=market)
#     if hist_df.empty:
#         return {"summary": {"Error": "Could not fetch data."}, "data": pd.DataFrame()}
    
#     bt = Backtest(hist_df, MacdCross, cash=initial_capital, commission=.002, finalize_trades=True)
#     stats = bt.run()

#     summary = {
#         "Total Return %": f"{stats['Return [%]']:.2f}",
#         "Sharpe Ratio": f"{stats['Sharpe Ratio']:.2f}",
#         "Max Drawdown %": f"{stats['Max. Drawdown [%]']:.2f}",
#         "Number of Trades": stats['# Trades']
#     }
    
#     plot_df = hist_df.copy()
#     plot_df['Equity_Curve'] = stats._equity_curve['Equity']
    
#     return {"summary": summary, "data": plot_df}

# # --- Streamlit UI for Standalone Testing ---
# # This part only runs when you execute this script directly
# if __name__ == "__main__":
#     st.set_page_config(page_title="MACD Crossover Backtester", layout="wide")
#     st.title("📈 MACD Crossover Strategy (Standalone)")

#     with st.sidebar:
#         st.header("⚙️ Configuration")
#         ticker = st.text_input("Ticker Symbol", "GOOGL")
#         start_date = st.date_input("Start Date", pd.to_datetime("2022-01-01"))
#         end_date = st.date_input("End Date", pd.to_datetime("today"))
#         market = st.selectbox("Market", ["US", "INDIA", "EUROPE", "UK", "JAPAN"], index=0)
        
#         st.header("Strategy Parameters")
#         fast_period = st.slider("Fast EMA Period", 5, 50, 12)
#         slow_period = st.slider("Slow EMA Period", 20, 100, 26)
#         signal_period = st.slider("Signal EMA Period", 5, 50, 9)
        
#         run_button = st.button("🔬 Run Backtest", use_container_width=True)

#     if run_button:
#         if fast_period >= slow_period:
#             st.error("Error: Fast EMA period must be less than Slow EMA period.")
#         else:
#             st.header(f"Results for {ticker}")
            
#             with st.spinner("Running backtest..."):
#                 results = run(
#                     ticker=ticker, 
#                     start_date=start_date, 
#                     end_date=end_date, 
#                     market=market,
#                     fast=fast_period, 
#                     slow=slow_period,
#                     signal=signal_period
#                 )
#                 summary = results.get("summary", {})
#                 backtest_df = results.get("data", pd.DataFrame())

#             if "Error" in summary:
#                 st.error(summary["Error"])
#             elif not backtest_df.empty:
#                 st.subheader("Performance Summary")
#                 cols = st.columns(4)
#                 cols[0].metric("Total Return", f"{summary.get('Total Return %', '0.00')}%")
#                 cols[1].metric("Sharpe Ratio", summary.get('Sharpe Ratio', '0.00'))
#                 cols[2].metric("Max Drawdown", f"{summary.get('Max Drawdown %', '0.00')}%")
#                 cols[3].metric("Trades", summary.get('Number of Trades', 0))

#                 st.subheader("Equity Curve")
#                 fig = go.Figure()
#                 fig.add_trace(go.Scatter(x=backtest_df.index, y=backtest_df['Equity_Curve'], name='Equity'))
#                 fig.update_layout(
#                     yaxis=dict(title=f"Equity ({get_market_config(market)['currency_symbol']})")
#                 )
#                 st.plotly_chart(fig, use_container_width=True)

