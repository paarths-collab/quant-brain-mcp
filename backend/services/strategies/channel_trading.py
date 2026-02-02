# core/strategies/channel_trading.py

import pandas as pd
from .base import Strategy


class ChannelTradingStrategy(Strategy):
    """
    Donchian Channel Trading Strategy

    Long  → Price breaks above upper channel
    Short → Price breaks below lower channel
    """

    name = "Donchian Channel Trading"

    def __init__(self, period: int = 20):
        self.period = period

    def parameters(self) -> dict:
        return {"period": self.period}

    def generate_signals(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        Expected columns: ['Open', 'High', 'Low', 'Close']
        """

        df = data.copy()

        # Donchian Channels (shifted to avoid lookahead bias)
        df["upper_channel"] = df["High"].rolling(self.period).max().shift(1)
        df["lower_channel"] = df["Low"].rolling(self.period).min().shift(1)

        # Signal columns
        df["signal"] = 0
        df["entry_long"] = None
        df["entry_short"] = None

        long_cond = df["Close"] > df["upper_channel"]
        short_cond = df["Close"] < df["lower_channel"]

        df.loc[long_cond, "signal"] = 1
        df.loc[long_cond, "entry_long"] = df["Close"]

        df.loc[short_cond, "signal"] = -1
        df.loc[short_cond, "entry_short"] = df["Close"]

        return df


# import pandas as pd
# import streamlit as st
# import plotly.graph_objects as go
# from backtesting import Backtest, Strategy

# # --- CORRECT: Import the single, centralized get_data function ---
# from backend.services.data_loader import get_data
# from backend.services.market_utils import get_market_config

# class ChannelTrading(Strategy):
#     """
#     Channel Trading Strategy implementation for backtesting.py library.
    
#     This strategy implements Donchian Channel breakout trading, where it goes long
#     when the price breaks above the upper channel (highest high over lookback period)
#     and goes short when the price breaks below the lower channel (lowest low over lookback period).
#     """
    
#     def init(self):
#         # Donchian Channels: Highest high and lowest low over the lookback period.
#         self.upper_band = self.I(lambda x: pd.Series(x).rolling(self.lookback_period).max(), self.data.High)
#         self.lower_band = self.I(lambda x: pd.Series(x).rolling(self.lookback_period).min(), self.data.Low)

#     def next(self):
#         # If the price breaks above the previous bar's upper band, close any short and go long.
#         if self.data.Close[-1] > self.upper_band[-2]:
#             self.position.close()
#             self.buy()
#         # If the price breaks below the previous bar's lower band, close any long and go short.
#         elif self.data.Close[-1] < self.lower_band[-2]:
#             self.position.close()
#             self.sell()

# # --- Main Run Function (Callable by Portfolio Builder) ---
# def run(ticker: str, start_date: str, end_date: str, market: str = "US", initial_capital=100000, **kwargs) -> dict:
#     """ Main orchestrator function for the Channel Trading strategy. """
    
#     channel_period = kwargs.get('period', 20)

#     # Set the lookback period for the strategy class
#     ChannelTrading.lookback_period = channel_period

#     # --- CORRECT: Call the centralized get_data function with the market ---
#     hist_df = get_data(ticker, start_date, end_date, market=market)
#     if hist_df.empty:
#         return {"summary": {"Error": "No data found."}, "data": pd.DataFrame()}

#     # CORRECT CODE:
#     bt = Backtest(hist_df, ChannelTrading, cash=initial_capital, commission=.002, finalize_trades=True) # <-- CORRECT PLACE
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
#     # Recalculate channels using a shift to align with the strategy logic for plotting
#     plot_df['Upper_Band'] = plot_df['High'].rolling(channel_period).max().shift(1)
#     plot_df['Lower_Band'] = plot_df['Low'].rolling(channel_period).min().shift(1)
    
#     trades = stats._trades
    
#     return {"summary": summary, "data": plot_df, "trades": trades}

# # --- Streamlit Visualization for Standalone Testing ---
# if __name__ == "__main__":
#     st.set_page_config(page_title="Channel Trading Strategy", layout="wide")
#     st.title("📈 Channel Trading Strategy (Standalone)")

#     with st.sidebar:
#         st.header("⚙️ Configuration")
#         ticker = st.text_input("Ticker Symbol", "MSFT")
#         start_date = st.date_input("Start Date", pd.to_datetime("2022-01-01"))
#         end_date = st.date_input("End Date", pd.to_datetime("today"))
#         market = st.selectbox("Market", ["US", "INDIA", "EUROPE", "UK", "JAPAN"], index=0)
        
#         st.header("Strategy Parameters")
#         period = st.slider("Channel Period (days)", 10, 100, 20)
        
#         run_button = st.button("🔬 Run Backtest", use_container_width=True)

#     if run_button:
#         st.header(f"Results for {ticker}")
#         with st.spinner("Running backtest..."):
#             results = run(
#                 ticker=ticker,
#                 start_date=start_date,
#                 end_date=end_date,
#                 market=market,
#                 period=period
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

#             # --- Professional Charting ---
#             st.subheader("Price Chart with Donchian Channels, Trades & Equity")
#             fig = go.Figure()

#             # Price, Channels, and Equity Curve
#             fig.add_trace(go.Scatter(x=backtest_df.index, y=backtest_df['Close'], name='Price', line=dict(color='skyblue')))
#             fig.add_trace(go.Scatter(x=backtest_df.index, y=backtest_df['Upper_Band'], name='Upper Channel', line=dict(color='lightcoral', dash='dash')))
#             fig.add_trace(go.Scatter(x=backtest_df.index, y=backtest_df['Lower_Band'], name='Lower Channel', line=dict(color='lightgreen', dash='dash')))
#             fig.add_trace(go.Scatter(x=backtest_df.index, y=backtest_df['Equity_Curve'], name='Equity Curve', yaxis='y2', line=dict(color='purple', dash='dot')))
            
#             # Trade Markers
#             buy_signals = trades_df[trades_df['Size'] > 0]
#             sell_signals = trades_df[trades_df['Size'] < 0]
#             fig.add_trace(go.Scatter(x=buy_signals.index, y=buy_signals['EntryPrice'], mode='markers', name='Go Long', marker=dict(color='lime', size=10, symbol='triangle-up')))
#             fig.add_trace(go.Scatter(x=sell_signals.index, y=sell_signals['EntryPrice'], mode='markers', name='Go Short', marker=dict(color='red', size=10, symbol='triangle-down')))

#             fig.update_layout(
#                 title_text=f"{ticker} Donchian Channel Backtest",
#                 xaxis_rangeslider_visible=False,
#                 yaxis=dict(title=f"Price ({get_market_config(market)['currency_symbol']})"),
#                 yaxis2=dict(title=f"Equity ({get_market_config(market)['currency_symbol']})", overlaying='y', side='right', showgrid=False)
#             )
#             st.plotly_chart(fig, use_container_width=True)