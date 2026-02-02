# # File: strategies/ema_crossover.py

# core/strategies/ema_crossover.py

import pandas as pd
from .base import Strategy


class EMACrossoverStrategy(Strategy):
    """
    EMA Crossover Strategy

    Long  → Fast EMA crosses above Slow EMA
    Short → Fast EMA crosses below Slow EMA
    """

    name = "EMA Crossover"

    def __init__(self, fast: int = 20, slow: int = 50):
        if fast >= slow:
            raise ValueError("Fast EMA period must be less than Slow EMA period")

        self.fast = fast
        self.slow = slow

    def parameters(self) -> dict:
        return {
            "fast": self.fast,
            "slow": self.slow
        }

    def generate_signals(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        Expected columns: ['Open', 'High', 'Low', 'Close']
        """

        df = data.copy()

        # EMA calculations
        df["ema_fast"] = df["Close"].ewm(span=self.fast, adjust=False).mean()
        df["ema_slow"] = df["Close"].ewm(span=self.slow, adjust=False).mean()

        # Signal columns
        df["signal"] = 0
        df["entry_long"] = None
        df["entry_short"] = None

        # Crossover logic
        bullish_cross = (
            (df["ema_fast"] > df["ema_slow"]) &
            (df["ema_fast"].shift(1) <= df["ema_slow"].shift(1))
        )

        bearish_cross = (
            (df["ema_fast"] < df["ema_slow"]) &
            (df["ema_fast"].shift(1) >= df["ema_slow"].shift(1))
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

# # --- CORRECT: Import the single, centralized get_data function ---
# from backend.services.data_loader import get_data

# class EmaCross(Strategy):
#     """
#     EMA Crossover Strategy implementation for backtesting.py library.
    
#     This strategy generates buy signals when the fast EMA crosses above the slow EMA
#     and sell signals when the fast EMA crosses below the slow EMA.
#     """
    
#     def init(self):
#         self.ema1 = self.I(lambda x, n: pd.Series(x).ewm(span=n, adjust=False).mean(), self.data.Close, self.fast_ema_period)
#         self.ema2 = self.I(lambda x, n: pd.Series(x).ewm(span=n, adjust=False).mean(), self.data.Close, self.slow_ema_period)

#     def next(self):
#         if crossover(self.ema1, self.ema2):
#             self.buy()
#         elif crossover(self.ema2, self.ema1):
#             self.sell()

# # --- Main Run Function (Callable by Portfolio Builder) ---
# def run(ticker, start_date, end_date, market, initial_capital=100000, **kwargs):
#     """ Main orchestrator function for the EMA Crossover strategy. """
    
#     fast_period = kwargs.get('fast', 20)
#     slow_period = kwargs.get('slow', 50)
    
#     # Set the parameters for the strategy class
#     EmaCross.fast_ema_period = fast_period
#     EmaCross.slow_ema_period = slow_period

#     hist_df = get_data(ticker, start_date, end_date, market)
#     if hist_df.empty:
#         return {"summary": {"Error": "Could not fetch data."}, "data": pd.DataFrame()}
    
#     bt = Backtest(hist_df, EmaCross, cash=initial_capital, commission=.002, finalize_trades=True)
#     stats = bt.run()

#     summary = {
#         "Total Return %": f"{stats['Return [%]']:.2f}",
#         "Sharpe Ratio": f"{stats['Sharpe Ratio']:.2f}",
#         "Max Drawdown %": f"{stats['Max. Drawdown [%]']:.2f}",
#         "Number of Trades": stats['# Trades']
#     }
    
#     # --- Prepare detailed data for professional plotting ---
#     plot_df = hist_df.copy()
#     plot_df['Equity_Curve'] = stats._equity_curve['Equity']
#     plot_df['EMA_Fast'] = plot_df['Close'].ewm(span=fast_period, adjust=False).mean()
#     plot_df['EMA_Slow'] = plot_df['Close'].ewm(span=slow_period, adjust=False).mean()
    
#     trades = stats._trades
    
#     return {"summary": summary, "data": plot_df, "trades": trades}

# # --- Streamlit UI for Standalone Testing ---
# if __name__ == "__main__":
#     st.set_page_config(page_title="EMA Crossover Backtester", layout="wide")
#     st.title("📈 EMA Crossover Strategy (Standalone)")

#     with st.sidebar:
#         st.header("⚙️ Configuration")
#         ticker = st.text_input("Ticker Symbol", "AAPL")
#         start_date = st.date_input("Start Date", pd.to_datetime("2022-01-01"))
#         end_date = st.date_input("End Date", pd.to_datetime("today"))
        
#         st.header("Strategy Parameters")
#         fast_period = st.slider("Fast EMA Period", 5, 100, 20)
#         slow_period = st.slider("Slow EMA Period", 20, 300, 50)
        
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
#                     market="USA",  # Default market for standalone testing
#                     fast=fast_period, 
#                     slow=slow_period
#                 )
#                 summary = results.get("summary", {})
#                 backtest_df = results.get("data", pd.DataFrame())
#                 trades_df = results.get("trades", pd.DataFrame())

#             if "Error" in summary:
#                 st.error(summary["Error"])
#             elif not backtest_df.empty:
#                 st.subheader("Performance Summary")
#                 cols = st.columns(4)
#                 cols[0].metric("Total Return", f"{summary.get('Total Return %', '0.00')}%")
#                 cols[1].metric("Sharpe Ratio", summary.get('Sharpe Ratio', '0.00'))
#                 cols[2].metric("Max Drawdown", f"{summary.get('Max Drawdown %', '0.00')}%")
#                 cols[3].metric("Trades", summary.get('Number of Trades', 0))

#                 # --- Professional Charting ---
#                 st.subheader("Price Chart with EMA Crossover, Trades & Equity")
#                 fig = go.Figure()

#                 # Price, EMAs, and Equity Curve
#                 fig.add_trace(go.Scatter(x=backtest_df.index, y=backtest_df['Close'], name='Price', line=dict(color='skyblue')))
#                 fig.add_trace(go.Scatter(x=backtest_df.index, y=backtest_df['EMA_Fast'], name=f'EMA {fast_period}', line=dict(color='green', dash='dash')))
#                 fig.add_trace(go.Scatter(x=backtest_df.index, y=backtest_df['EMA_Slow'], name=f'EMA {slow_period}', line=dict(color='red', dash='dash')))
#                 fig.add_trace(go.Scatter(x=backtest_df.index, y=backtest_df['Equity_Curve'], name='Equity Curve', yaxis='y2', line=dict(color='purple', dash='dot')))
                
#                 # Trade Markers
#                 buy_signals = trades_df[trades_df['Size'] > 0]
#                 sell_signals = trades_df[trades_df['Size'] < 0]
#                 fig.add_trace(go.Scatter(x=buy_signals.index, y=buy_signals['EntryPrice'], mode='markers', name='Buy Signal', marker=dict(color='lime', size=10, symbol='triangle-up')))
#                 fig.add_trace(go.Scatter(x=sell_signals.index, y=sell_signals['EntryPrice'], mode='markers', name='Sell Signal', marker=dict(color='red', size=10, symbol='triangle-down')))

#                 fig.update_layout(
#                     title_text=f"{ticker} EMA Crossover Backtest ({fast_period}/{slow_period})",
#                     xaxis_rangeslider_visible=False,
#                     yaxis=dict(title="Price ($)"),
#                     yaxis2=dict(title="Equity ($)", overlaying='y', side='right', showgrid=False)
#                 )
#                 st.plotly_chart(fig, use_container_width=True)
