# core/strategies/rsi_reversal.py

import pandas as pd
from .base import Strategy


class RSIReversalStrategy(Strategy):
    """
    RSI Reversal Strategy (Mean Reversion)

    Long  → RSI crosses above oversold level
    Exit  → RSI crosses below overbought level
    """

    name = "RSI Reversal"

    def __init__(self, window: int = 14, lower: int = 30, upper: int = 70):
        if lower >= upper:
            raise ValueError("Lower bound must be less than upper bound")

        self.window = window
        self.lower = lower
        self.upper = upper

    def parameters(self) -> dict:
        return {
            "window": self.window,
            "lower": self.lower,
            "upper": self.upper
        }

    def generate_signals(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        Expected columns: ['Open', 'High', 'Low', 'Close']
        """

        df = data.copy()

        # --- RSI calculation (no external libs) ---
        delta = df["Close"].diff()

        gain = delta.clip(lower=0)
        loss = -delta.clip(upper=0)

        avg_gain = gain.rolling(self.window).mean()
        avg_loss = loss.rolling(self.window).mean()

        rs = avg_gain / avg_loss
        df["rsi"] = 100 - (100 / (1 + rs))

        # --- Signal columns ---
        df["signal"] = 0
        df["entry_long"] = None
        df["entry_short"] = None

        # --- Reversal logic ---
        bullish_reversal = (
            (df["rsi"] > self.lower) &
            (df["rsi"].shift(1) <= self.lower)
        )

        bearish_exit = (
            (df["rsi"] < self.upper) &
            (df["rsi"].shift(1) >= self.upper)
        )

        df.loc[bullish_reversal, "signal"] = 1
        df.loc[bullish_reversal, "entry_long"] = df["Close"]

        # Exit handled by backtesting engine (flat)
        df.loc[bearish_exit, "signal"] = 0

        return df


# import yfinance as yf
# import pandas as pd
# import ta
# from backtesting import Backtest, Strategy
# from backtesting.lib import crossover
# import streamlit as st
# import plotly.graph_objects as go
# from plotly.subplots import make_subplots


# @st.cache_data 
# def get_data(ticker, start, end, market):
#     """ Standardized data fetching function. """
#     df = yf.download(ticker, start=start, end=end, progress=False, auto_adjust=True)
#     if df.empty: return pd.DataFrame()
    
#     # Handle multi-level columns from yfinance
#     if isinstance(df.columns, pd.MultiIndex):
#         df.columns = df.columns.get_level_values(0)
    
#     df.rename(columns={
#         "open": "Open", "high": "High", "low": "Low", "close": "Close", "volume": "Volume"
#     }, inplace=True, errors='ignore')
    
#     # Safely convert column names to title case, handling potential tuples
#     try:
#         df.columns = [col[0].title() if isinstance(col, tuple) else col.title() for col in df.columns]
#     except:
#         df.columns = [str(col).title() for col in df.columns]
        
#     # Ensure we have the required columns
#     required_cols = ['Open', 'High', 'Low', 'Close', 'Volume']
#     available_cols = [col for col in required_cols if col in df.columns]
#     if len(available_cols) >= len(required_cols) - 1:  # Allow for missing volume
#         return df[available_cols]
#     else:
#         return pd.DataFrame()  # Return empty if missing critical columns

# class RsiReversal(Strategy):
#     """
#     RSI Reversal Strategy implementation for backtesting.py library.
    
#     This strategy buys when RSI crosses above the lower bound (oversold condition)
#     and sells when RSI crosses below the upper bound (overbought condition).
#     """
#     finalize_trades = True
    
#     def init(self):
#         self.rsi = self.I(ta.momentum.rsi, pd.Series(self.data.Close), window=self.rsi_window)

#     def next(self):
#         # Buy when RSI crosses above the lower bound (oversold)
#         if crossover(self.rsi, self.lower_bound):
#             self.buy()
#         # Sell (close position) when RSI crosses below the upper bound (overbought)
#         elif crossover(self.upper_bound, self.rsi):
#             self.position.close()

# # --- Main Run Function (Callable by Portfolio Builder) ---
# def run(ticker: str, start_date: str, end_date: str, market, initial_capital=100000, **kwargs) -> dict:
#     """ Main orchestrator function for the RSI Reversal strategy. """
    
#     lower_bound_param = kwargs.get('lower_bound', 30)
#     upper_bound_param = kwargs.get('upper_bound', 70)
#     rsi_window_param = kwargs.get('rsi_window', 14)

#     # Set the parameters for the strategy class
#     RsiReversal.lower_bound = lower_bound_param
#     RsiReversal.upper_bound = upper_bound_param
#     RsiReversal.rsi_window = rsi_window_param

#     hist_df = get_data(ticker, start_date, end_date, market)
#     if hist_df.empty: 
#         return {"summary": {"Error": "No data found."}, "data": pd.DataFrame()}

#     bt = Backtest(hist_df, RsiReversal, cash=initial_capital, commission=.002)
#     stats = bt.run(finalize_trades=True)
    
#     summary = {
#         "Total Return %": f"{stats['Return [%]']:.2f}",
#         "Sharpe Ratio": f"{stats['Sharpe Ratio']:.2f}",
#         "Max Drawdown %": f"{stats['Max. Drawdown [%]']:.2f}",
#         "Number of Trades": stats['# Trades']
#     }
    
#     # --- Prepare detailed data for professional plotting ---
#     plot_df = hist_df.copy()
#     plot_df['Equity_Curve'] = stats._equity_curve['Equity']
#     plot_df['RSI'] = ta.momentum.rsi(plot_df['Close'], window=rsi_window_param)
    
#     trades = stats._trades
    
#     return {"summary": summary, "data": plot_df, "trades": trades}

# # --- Streamlit Visualization for Standalone Testing ---
# if __name__ == "__main__":
#     st.set_page_config(page_title="RSI Reversal Strategy", layout="wide")
#     st.title("📈 RSI Reversal Strategy (Standalone)")

#     with st.sidebar:
#         st.header("⚙️ Configuration")
#         ticker = st.text_input("Ticker Symbol", "AAPL")
#         start_date = st.date_input("Start Date", pd.to_datetime("2022-01-01"))
#         end_date = st.date_input("End Date", pd.to_datetime("today"))
        
#         st.header("Strategy Parameters")
#         lower_bound = st.slider("RSI Lower Bound (Oversold)", 10, 40, 30)
#         upper_bound = st.slider("RSI Upper Bound (Overbought)", 60, 90, 70)
        
#         run_button = st.button("🔬 Run Backtest", use_container_width=True)
        
#     if run_button:
#         st.header(f"Results for {ticker}")
#         with st.spinner("Running backtest..."):
#             results = run(
#                 ticker=ticker, 
#                 start_date=start_date, 
#                 end_date=end_date, 
#                 market="USA",  # Default market for standalone testing
#                 lower_bound=lower_bound, 
#                 upper_bound=upper_bound
#             )
#             summary = results.get("summary", {})
#             backtest_df = results.get("data", pd.DataFrame())
#             trades_df = results.get("trades", pd.DataFrame())

#         if "Error" in summary:
#             st.error(summary["Error"])
#         elif not backtest_df.empty:
#             st.subheader("Performance Summary")
#             cols = st.columns(4)
#             cols[0].metric("Total Return", f"{summary.get('Total Return %', '0.00')}%")
#             cols[1].metric("Sharpe Ratio", summary.get('Sharpe Ratio', '0.00'))
#             cols[2].metric("Max Drawdown", f"{summary.get('Max Drawdown %', '0.00')}%")
#             cols[3].metric("Trades", summary.get('Number of Trades', 0))

#             # --- Professional Charting with Subplots ---
#             st.subheader("Price Chart with RSI, Trades & Equity")
#             fig = make_subplots(rows=2, cols=1, shared_xaxes=True, 
#                                 vertical_spacing=0.1, row_heights=[0.7, 0.3])

#             # Top Panel: Price, Equity, and Trades
#             fig.add_trace(go.Scatter(x=backtest_df.index, y=backtest_df['Close'], name='Price', line=dict(color='skyblue')), row=1, col=1)
#             fig.add_trace(go.Scatter(x=backtest_df.index, y=backtest_df['Equity_Curve'], name='Equity Curve', yaxis='y2', line=dict(color='purple', dash='dot')), row=1, col=1)
            
#             buy_signals = trades_df[trades_df['Size'] > 0]
#             sell_signals = trades_df[trades_df['Size'] < 0]
#             fig.add_trace(go.Scatter(x=buy_signals.index, y=buy_signals['EntryPrice'], mode='markers', name='Buy Signal', marker=dict(color='lime', size=10, symbol='triangle-up')), row=1, col=1)
#             fig.add_trace(go.Scatter(x=sell_signals.index, y=sell_signals['EntryPrice'], mode='markers', name='Sell Signal', marker=dict(color='red', size=10, symbol='triangle-down')), row=1, col=1)

#             # Bottom Panel: RSI
#             fig.add_trace(go.Scatter(x=backtest_df.index, y=backtest_df['RSI'], name='RSI', line=dict(color='orange')), row=2, col=1)
#             fig.add_hline(y=upper_bound, line_dash="dash", line_color="red", row=2, col=1, annotation_text="Overbought")
#             fig.add_hline(y=lower_bound, line_dash="dash", line_color="green", row=2, col=1, annotation_text="Oversold")

#             fig.update_layout(
#                 title_text=f"{ticker} RSI Reversal Backtest",
#                 xaxis_rangeslider_visible=False,
#                 yaxis=dict(title="Price ($)"),
#                 yaxis2=dict(title="Equity ($)", overlaying='y', side='right', showgrid=False)
#             )
#             fig.update_yaxes(title_text="RSI", row=2, col=1)
#             st.plotly_chart(fig, use_container_width=True)
# # import pandas as pd
# # import ta
# # from utils.data_loader import get_history
# # from backtesting import Backtest, Strategy
# # from backtesting.lib import crossover
# # import streamlit as st
# # import plotly.graph_objects as go

# # class RsiReversal(Strategy):
# #     lower_bound = 30
# #     upper_bound = 70
# #     rsi_window = 14

# #     def init(self):
# #         self.rsi = self.I(ta.momentum.rsi, pd.Series(self.data.Close), window=self.rsi_window)

# #     def next(self):
# #         if crossover(self.rsi, self.lower_bound):
# #             self.buy()
# #         elif crossover(self.upper_bound, self.rsi):
# #             self.position.close()

# # def run(ticker: str, start_date: str, end_date: str, cash=10_000, commission=.002, **kwargs) -> dict:
# #     hist_df = get_history(ticker, start_date, end_date)
# #     if hist_df.empty: return {"summary": {"Error": "No data found."}, "data": pd.DataFrame()}

# #     if isinstance(hist_df.columns, pd.MultiIndex):
# #         hist_df.columns = hist_df.columns.get_level_values(0)
# #     hist_df.columns = [col.title() for col in hist_df.columns]

# #     RsiReversal.lower_bound = kwargs.get('lower_bound', 30)
# #     RsiReversal.upper_bound = kwargs.get('upper_bound', 70)
    
# #     bt = Backtest(hist_df, RsiReversal, cash=cash, commission=commission)
# #     # --- FIX: Ensure final open trades are included in stats ---
# #     stats = bt.run(finalize_trades=True)
# #     # --- END OF FIX ---
    
# #     return {"summary": stats.to_dict(), "data": stats._equity_curve}

# # # ... (Streamlit UI remains unchanged) ...

# # # --- Streamlit Visualization ---
# # if __name__ == "__main__":
# #     st.set_page_config(page_title="RSI Reversal Strategy", layout="wide")
# #     st.title("📈 RSI Reversal Strategy Showcase")
# #     with st.sidebar:
# #         st.header("⚙️ Configuration")
# #         ticker = st.text_input("Ticker Symbol", "AAPL")
# #         start_date = st.date_input("Start Date", pd.to_datetime("2022-01-01"))
# #         end_date = st.date_input("End Date", pd.to_datetime("today"))
# #         lower_bound = st.slider("RSI Lower Bound (Oversold)", 10, 40, 30)
# #         upper_bound = st.slider("RSI Upper Bound (Overbought)", 60, 90, 70)
# #         run_button = st.button("🔬 Run Backtest", use_container_width=True)
# #     if run_button:
# #         st.header(f"Results for {ticker}")
# #         with st.spinner("Running backtest..."):
# #             results = run(ticker, str(start_date.date()), str(end_date.date()), lower_bound=lower_bound, upper_bound=upper_bound)
# #             summary = results.get("summary", {})
# #             equity_curve = results.get("data", pd.DataFrame())
# #             if "Error" in summary:
# #                 st.error(summary["Error"])
# #             elif not equity_curve.empty:
# #                 st.subheader("Performance Summary")
# #                 cols = st.columns(4)
# #                 cols[0].metric("Return [%]", f"{summary.get('Return [%]', 0):.2f}")
# #                 # ... (rest of the Streamlit UI is the same)
# #                 st.subheader("Equity Curve")
# #                 fig = go.Figure(go.Scatter(x=equity_curve.index, y=equity_curve['Equity']))
# #                 st.plotly_chart(fig, use_container_width=True)
# # # import yfinance as yf
# # import pandas as pd
# # import numpy as np
# # import streamlit as st
# # import plotly.graph_objects as go
# # from plotly.subplots import make_subplots

# # # --- Core Strategy & Backtesting Logic ---
# # def compute_rsi(series, period=14):
# #     delta = series.diff()
# #     gain = delta.clip(lower=0).fillna(0)
# #     loss = -delta.clip(upper=0).fillna(0)
# #     avg_gain = gain.rolling(window=period).mean()
# #     avg_loss = loss.rolling(window=period).mean()
# #     rs = avg_gain / avg_loss
# #     return 100 - (100 / (1 + rs))

# # def get_data(ticker, start, end):
# #     df = yf.download(ticker, start=start, end=end, progress=False)
# #     if df.empty: return pd.DataFrame()
# #     df.dropna(inplace=True)
# #     return df

# # def detect_divergence(df, window=30):
# #     df = df.copy()
# #     df['rsi'] = compute_rsi(df['Close'])
# #     df['trade'] = 0
# #     for i in range(window, len(df)):
# #         sub = df.iloc[i-window:i]
# #         lows = sub['Close'].nsmallest(2)
# #         if len(lows) == 2:
# #             idx1, idx2 = lows.index[0], lows.index[1]
# #             if sub.loc[idx2, 'Close'] < sub.loc[idx1, 'Close'] and sub.loc[idx2, 'rsi'] > sub.loc[idx1, 'rsi']:
# #                 df.iloc[i, df.columns.get_loc('trade')] = 1
# #         highs = sub['Close'].nlargest(2)
# #         if len(highs) == 2:
# #             idx1, idx2 = highs.index[0], highs.index[1]
# #             if sub.loc[idx2, 'Close'] > sub.loc[idx1, 'Close'] and sub.loc[idx2, 'rsi'] < sub.loc[idx1, 'rsi']:
# #                 df.iloc[i, df.columns.get_loc('trade')] = -1
# #     return df

# # def run_backtest(df, initial_capital=100000):
# #     df = df.copy()
# #     df['Position'] = df['trade'].replace(0, np.nan).ffill().fillna(0).shift(1)
# #     df['Strategy_Returns'] = df['Close'].pct_change() * df['Position']
# #     df['Equity_Curve'] = (1 + df['Strategy_Returns']).cumprod() * initial_capital
# #     return df

# # def calculate_performance_metrics(backtest_df, initial_capital):
# #     # (This function can be copied from other strategy files)
# #     if backtest_df.empty: return {}
# #     final_equity = backtest_df['Equity_Curve'].iloc[-1]
# #     total_return_pct = (final_equity / initial_capital - 1) * 100
# #     daily_returns = backtest_df['Strategy_Returns'].dropna()
# #     sharpe_ratio = np.sqrt(252) * daily_returns.mean() / daily_returns.std() if daily_returns.std() != 0 else 0
# #     peak = backtest_df['Equity_Curve'].cummax()
# #     drawdown = (backtest_df['Equity_Curve'] - peak) / peak
# #     max_drawdown_pct = drawdown.min() * 100
# #     trades = backtest_df[backtest_df['trade'] != 0]
# #     return {
# #         "Total Return %": f"{total_return_pct:.2f}", "Sharpe Ratio": f"{sharpe_ratio:.2f}",
# #         "Max Drawdown %": f"{max_drawdown_pct:.2f}", "Number of Trades": len(trades)
# #     }

# # # --- Orchestrator/API Entry Point ---
# # def run(ticker: str, start_date: str, end_date: str, **kwargs) -> dict:
# #     try:
# #         window = kwargs.get("window", 30)
# #         df = get_data(ticker, start_date, end_date)
# #         if df.empty:
# #             return {"summary": {"Error": "No data found."}, "data": pd.DataFrame()}
# #         df_signals = detect_divergence(df, window=window)
# #         df_backtest = run_backtest(df_signals)
# #         summary_metrics = calculate_performance_metrics(df_backtest, 100000)
# #         return {"summary": summary_metrics, "data": df_backtest}
# #     except Exception as e:
# #         return {"summary": {"Error": str(e)}, "data": pd.DataFrame()}

# # # --- Streamlit Visualization ---
# # if __name__ == "__main__":
# #     st.set_page_config(page_title="RSI Divergence Strategy", layout="wide")
# #     st.title("📈 RSI Divergence Reversal Strategy Showcase")
# #     with st.sidebar:
# #         st.header("⚙️ Configuration")
# #         ticker = st.text_input("Ticker Symbol", "AAPL")
# #         start_date = st.date_input("Start Date", pd.to_datetime("2022-01-01"))
# #         end_date = st.date_input("End Date", pd.to_datetime("today"))
# #         window = st.slider("Divergence Lookback Window (days)", 10, 100, 30)
# #         run_button = st.button("🔬 Run Backtest", use_container_width=True)
# #     if run_button:
# #         st.header(f"Results for {ticker}")
# #         with st.spinner("Running backtest..."):
# #             results = run(ticker, str(start_date), str(end_date), window=window)
# #             summary = results.get("summary", {})
# #             backtest_df = results.get("data", pd.DataFrame())
# #             if "Error" in summary:
# #                 st.error(summary["Error"])
# #             else:
# #                 st.subheader("Performance Summary")
# #                 cols = st.columns(4)
# #                 cols[0].metric("Total Return", f"{summary.get('Total Return %', 0)}%")
# #                 cols[1].metric("Sharpe Ratio", summary.get('Sharpe Ratio', 0))
# #                 cols[2].metric("Max Drawdown", f"{summary.get('Max Drawdown %', 0)}%")
# #                 cols[3].metric("Trades", summary.get('Number of Trades', 0))
# #                 st.subheader("Price, RSI & Divergence Signals")
# #                 fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.1, row_heights=[0.7, 0.3])
# #                 fig.add_trace(go.Scatter(x=backtest_df.index, y=backtest_df['Close'], name='Price'), row=1, col=1)
# #                 buy_signals = backtest_df[backtest_df['trade'] == 1]
# #                 sell_signals = backtest_df[backtest_df['trade'] == -1]
# #                 fig.add_trace(go.Scatter(x=buy_signals.index, y=buy_signals['Close'], mode='markers', name='Bullish Divergence (Buy)', marker=dict(color='green', size=10, symbol='triangle-up')), row=1, col=1)
# #                 fig.add_trace(go.Scatter(x=sell_signals.index, y=sell_signals['Close'], mode='markers', name='Bearish Divergence (Sell)', marker=dict(color='red', size=10, symbol='triangle-down')), row=1, col=1)
# #                 fig.add_trace(go.Scatter(x=backtest_df.index, y=backtest_df['rsi'], name='RSI'), row=2, col=1)
# #                 fig.add_hline(y=70, line_dash="dash", line_color="red", row=2, col=1)
# #                 fig.add_hline(y=30, line_dash="dash", line_color="green", row=2, col=1)
# #                 fig.update_layout(title_text=f"{ticker} Backtest: RSI Divergence Reversal", xaxis_rangeslider_visible=False)
# #                 st.plotly_chart(fig, use_container_width=True)