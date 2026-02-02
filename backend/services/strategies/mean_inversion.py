# # File: strategies/mean_inversion.py

# core/strategies/mean_reversion.py

import pandas as pd
from .base import Strategy


class MeanReversionStrategy(Strategy):
    """
    Mean Reversion Strategy (Bollinger Bands style)

    Long  → Price below lower band
    Exit  → Price reverts back to mean
    """

    name = "Mean Reversion"

    def __init__(self, window: int = 20, num_std: float = 2.0):
        self.window = window
        self.num_std = num_std

    def parameters(self) -> dict:
        return {
            "window": self.window,
            "num_std": self.num_std
        }

    def generate_signals(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        Expected columns: ['Open', 'High', 'Low', 'Close']
        """

        df = data.copy()

        # --- Rolling statistics ---
        df["ma"] = df["Close"].rolling(self.window).mean()
        df["std"] = df["Close"].rolling(self.window).std()

        df["upper_band"] = df["ma"] + (df["std"] * self.num_std)
        df["lower_band"] = df["ma"] - (df["std"] * self.num_std)

        # --- Signal columns ---
        df["signal"] = 0
        df["entry_long"] = None
        df["entry_short"] = None

        # --- Mean reversion logic ---
        long_entry = df["Close"] < df["lower_band"]
        exit_long = df["Close"] > df["ma"]

        df.loc[long_entry, "signal"] = 1
        df.loc[long_entry, "entry_long"] = df["Close"]

        # Exit signal (flat, handled by backtesting engine)
        df.loc[exit_long, "signal"] = 0

        return df

# import pandas as pd
# import streamlit as st
# import plotly.graph_objects as go
# from backtesting import Backtest, Strategy
# import ta

# # --- CORRECT: Import the single, centralized get_data function ---
# from backend.services.data_loader import get_data

# class MeanReversion(Strategy):
#     """
#     Mean Reversion Strategy implementation for backtesting.py library.
    
#     This strategy buys when the price falls below the lower Bollinger Band (mean - n*std)
#     and sells when the price rises above the moving average (mean reversion).
#     """
    
#     def init(self):
#         close = pd.Series(self.data.Close)
#         self.ma = self.I(ta.trend.sma_indicator, close, window=self.ma_window)
#         rolling_std = self.I(lambda x, n: pd.Series(x).rolling(n).std(), close, self.ma_window)
#         self.upper_band = self.ma + (rolling_std * self.std_multiplier)
#         self.lower_band = self.ma - (rolling_std * self.std_multiplier)

#     def next(self):
#         if not self.position and self.data.Close[-1] < self.lower_band[-1]:
#             self.buy()
#         elif self.position and self.data.Close[-1] > self.ma[-1]:
#             self.position.close()

# # --- Main Run Function (Callable by Portfolio Builder) ---
# def run(ticker: str, start_date: str, end_date: str, market, initial_capital=100000, **kwargs) -> dict:
#     """ Main orchestrator function for the Mean Reversion strategy. """
    
#     window_period = kwargs.get("window", 20)
#     std_devs = kwargs.get("num_std", 2.0)
    
#     # Set the parameters for the strategy class
#     MeanReversion.ma_window = window_period
#     MeanReversion.std_multiplier = std_devs

#     # --- CORRECT: Call the centralized get_data function ---
#     hist_df = get_data(ticker, start_date, end_date, market)
#     if hist_df.empty:
#         return {"summary": {"Error": "No data found."}, "data": pd.DataFrame()}

#     bt = Backtest(hist_df, MeanReversion, cash=initial_capital, commission=.002, finalize_trades=True)
#     stats = bt.run()
    
#     summary = {
#         "Total Return %": f"{stats['Return [%]']:.2f}",
#         "Sharpe Ratio": f"{stats['Sharpe Ratio']:.2f}",
#         "Max Drawdown %": f"{stats['Max. Drawdown [%]']:.2f}",
#         "Number of Trades": stats['# Trades']
#     }
    
#     plot_df = hist_df.copy()
#     plot_df['Equity_Curve'] = stats._equity_curve['Equity']
#     plot_df['MA'] = plot_df['Close'].rolling(window_period).mean()
#     plot_df['STD'] = plot_df['Close'].rolling(window_period).std()
#     plot_df['Upper_Band'] = plot_df['MA'] + (plot_df['STD'] * std_devs)
#     plot_df['Lower_Band'] = plot_df['MA'] - (plot_df['STD'] * std_devs)
    
#     trades = stats._trades
    
#     return {"summary": summary, "data": plot_df, "trades": trades}

# # --- Streamlit UI for Standalone Testing ---
# if __name__ == "__main__":
#     st.set_page_config(page_title="Mean Reversion Strategy", layout="wide")
#     st.title("📈 Mean Reversion Strategy (Standalone)")

#     with st.sidebar:
#         st.header("⚙️ Configuration")
#         ticker = st.text_input("Ticker Symbol", "BTC-USD")
#         start_date = st.date_input("Start Date", pd.to_datetime("2022-01-01"))
#         end_date = st.date_input("End Date", pd.to_datetime("today"))
        
#         st.header("Strategy Parameters")
#         window = st.slider("Moving Average Window", 10, 100, 20)
#         num_std = st.slider("Number of Standard Deviations", 1.0, 3.0, 2.0, 0.1)
        
#         run_button = st.button("🔬 Run Backtest", use_container_width=True)

#     if run_button:
#         st.header(f"Results for {ticker}")
#         with st.spinner("Running backtest..."):
#             results = run(
#                 ticker=ticker, 
#                 start_date=start_date, 
#                 end_date=end_date, 
#                 market="USA",  # Default market for standalone testing
#                 window=window, 
#                 num_std=num_std
#             )
#             summary = results.get("summary", {})
#             backtest_df = results.get("data", pd.DataFrame())
#             trades_df = results.get("trades", pd.DataFrame())

#             if "Error" in summary:
#                 st.error(summary["Error"])
#             elif not backtest_df.empty:
#                 st.subheader("Performance Summary")
#                 cols = st.columns(4)
#                 cols[0].metric("Total Return", f"{summary.get('Total Return %', '0.00')}%")
#                 cols[1].metric("Sharpe Ratio", summary.get('Sharpe Ratio', '0.00'))
#                 cols[2].metric("Max Drawdown", f"{summary.get('Max Drawdown %', '0.00')}%")
#                 cols[3].metric("Trades", summary.get('Number of Trades', 0))

#                 st.subheader("Price Chart with Bollinger Bands, Trades & Equity")
#                 fig = go.Figure()

#                 fig.add_trace(go.Scatter(x=backtest_df.index, y=backtest_df['Close'], name='Price', line=dict(color='skyblue')))
#                 fig.add_trace(go.Scatter(x=backtest_df.index, y=backtest_df['Upper_Band'], name='Upper Band', line=dict(color='orange', dash='dash')))
#                 fig.add_trace(go.Scatter(x=backtest_df.index, y=backtest_df['Lower_Band'], name='Lower Band', line=dict(color='orange', dash='dash')))
#                 fig.add_trace(go.Scatter(x=backtest_df.index, y=backtest_df['Equity_Curve'], name='Equity Curve', yaxis='y2', line=dict(color='purple', dash='dot')))
                
#                 buy_signals = trades_df[trades_df['Size'] > 0]
#                 sell_signals = trades_df[trades_df['Size'] < 0]
#                 fig.add_trace(go.Scatter(x=buy_signals.index, y=buy_signals['EntryPrice'], mode='markers', name='Buy Signal', marker=dict(color='lime', size=10, symbol='triangle-up')))
#                 fig.add_trace(go.Scatter(x=sell_signals.index, y=sell_signals['EntryPrice'], mode='markers', name='Sell Signal', marker=dict(color='red', size=10, symbol='triangle-down')))

#                 fig.update_layout(
#                     title_text=f"{ticker} Mean Reversion Backtest",
#                     yaxis=dict(title="Price ($)"),
#                     yaxis2=dict(title="Equity ($)", overlaying='y', side='right', showgrid=False)
#                 )
#                 st.plotly_chart(fig, use_container_width=True)
