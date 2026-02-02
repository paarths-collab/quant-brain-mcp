# File: strategies/mean_inversion.py

import pandas as pd
# import streamlit as st
import plotly.graph_objects as go
from backtesting import Backtest, Strategy
import ta

# --- CORRECT: Import the single, centralized get_data function ---
from ..utils.data_loader import get_data

class MeanReversion(Strategy):
    """
    Mean Reversion Strategy implementation for backtesting.py library.
    
    This strategy buys when the price falls below the lower Bollinger Band (mean - n*std)
    and sells when the price rises above the moving average (mean reversion).
    """
    
    def init(self):
        close = pd.Series(self.data.Close)
        self.ma = self.I(ta.trend.sma_indicator, close, window=self.ma_window)
        rolling_std = self.I(lambda x, n: pd.Series(x).rolling(n).std(), close, self.ma_window)
        self.upper_band = self.ma + (rolling_std * self.std_multiplier)
        self.lower_band = self.ma - (rolling_std * self.std_multiplier)

    def next(self):
        if not self.position and self.data.Close[-1] < self.lower_band[-1]:
            self.buy()
        elif self.position and self.data.Close[-1] > self.ma[-1]:
            self.position.close()

# --- Main Run Function (Callable by Portfolio Builder) ---
def run(ticker: str, start_date: str, end_date: str, market, initial_capital=100000, **kwargs) -> dict:
    """ Main orchestrator function for the Mean Reversion strategy. """
    
    window_period = kwargs.get("window", 20)
    std_devs = kwargs.get("num_std", 2.0)
    
    # Set the parameters for the strategy class
    MeanReversion.ma_window = window_period
    MeanReversion.std_multiplier = std_devs

    # --- CORRECT: Call the centralized get_data function ---
    hist_df = get_data(ticker, start_date, end_date, market)
    if hist_df.empty:
        return {"summary": {"Error": "No data found."}, "data": pd.DataFrame()}

    bt = Backtest(hist_df, MeanReversion, cash=initial_capital, commission=.002, finalize_trades=True)
    stats = bt.run()
    
    summary = {
        "Total Return %": f"{stats['Return [%]']:.2f}",
        "Sharpe Ratio": f"{stats['Sharpe Ratio']:.2f}",
        "Max Drawdown %": f"{stats['Max. Drawdown [%]']:.2f}",
        "Number of Trades": stats['# Trades']
    }
    
    plot_df = hist_df.copy()
    plot_df['Equity_Curve'] = stats._equity_curve['Equity']
    plot_df['MA'] = plot_df['Close'].rolling(window_period).mean()
    plot_df['STD'] = plot_df['Close'].rolling(window_period).std()
    plot_df['Upper_Band'] = plot_df['MA'] + (plot_df['STD'] * std_devs)
    plot_df['Lower_Band'] = plot_df['MA'] - (plot_df['STD'] * std_devs)
    
    trades = stats._trades
    
    return {"summary": summary, "data": plot_df, "trades": trades}

# --- Streamlit UI for Standalone Testing ---
