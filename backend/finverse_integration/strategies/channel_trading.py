import pandas as pd
# import streamlit as st
import plotly.graph_objects as go
from backtesting import Backtest, Strategy

# --- CORRECT: Import the single, centralized get_data function ---
from ..utils.data_loader import get_data
from ..utils.market_utils import get_market_config

class ChannelTrading(Strategy):
    """
    Channel Trading Strategy implementation for backtesting.py library.
    
    This strategy implements Donchian Channel breakout trading, where it goes long
    when the price breaks above the upper channel (highest high over lookback period)
    and goes short when the price breaks below the lower channel (lowest low over lookback period).
    """
    
    def init(self):
        # Donchian Channels: Highest high and lowest low over the lookback period.
        self.upper_band = self.I(lambda x: pd.Series(x).rolling(self.lookback_period).max(), self.data.High)
        self.lower_band = self.I(lambda x: pd.Series(x).rolling(self.lookback_period).min(), self.data.Low)

    def next(self):
        # If the price breaks above the previous bar's upper band, close any short and go long.
        if self.data.Close[-1] > self.upper_band[-2]:
            self.position.close()
            self.buy()
        # If the price breaks below the previous bar's lower band, close any long and go short.
        elif self.data.Close[-1] < self.lower_band[-2]:
            self.position.close()
            self.sell()

# --- Main Run Function (Callable by Portfolio Builder) ---
def run(ticker: str, start_date: str, end_date: str, market: str = "US", initial_capital=100000, **kwargs) -> dict:
    """ Main orchestrator function for the Channel Trading strategy. """
    
    channel_period = kwargs.get('period', 20)

    # Set the lookback period for the strategy class
    ChannelTrading.lookback_period = channel_period

    # --- CORRECT: Call the centralized get_data function with the market ---
    hist_df = get_data(ticker, start_date, end_date, market=market)
    if hist_df.empty:
        return {"summary": {"Error": "No data found."}, "data": pd.DataFrame()}

    # CORRECT CODE:
    bt = Backtest(hist_df, ChannelTrading, cash=initial_capital, commission=.002, finalize_trades=True) # <-- CORRECT PLACE
    stats = bt.run()

    summary = {
        "Total Return %": f"{stats['Return [%]']:.2f}",
        "Sharpe Ratio": f"{stats['Sharpe Ratio']:.2f}",
        "Max Drawdown %": f"{stats['Max. Drawdown [%]']:.2f}",
        "Number of Trades": stats['# Trades']
    }
    
    # --- Prepare detailed data for professional plotting ---
    plot_df = hist_df.copy()
    plot_df['Equity_Curve'] = stats._equity_curve['Equity']
    # Recalculate channels using a shift to align with the strategy logic for plotting
    plot_df['Upper_Band'] = plot_df['High'].rolling(channel_period).max().shift(1)
    plot_df['Lower_Band'] = plot_df['Low'].rolling(channel_period).min().shift(1)
    
    trades = stats._trades
    
    return {"summary": summary, "data": plot_df, "trades": trades}

# --- Streamlit Visualization for Standalone Testing ---
