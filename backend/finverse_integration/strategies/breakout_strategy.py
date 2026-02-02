# File: strategies/breakout_strategy.py

import pandas as pd
# import streamlit as st
import plotly.graph_objects as go
from backtesting import Backtest, Strategy

# --- CORRECT: Import the single, centralized get_data function ---
from ..utils.data_loader import get_data
from ..utils.market_utils import get_market_config


class Breakout(Strategy):
    """
    Breakout Strategy implementation for backtesting.py library.
    
    This strategy identifies breakouts above resistance levels or below support levels 
    to enter trades. It uses rolling maximum and minimum values over a lookback period
    to determine breakout points.
    """
    
    def init(self):
        """
        Initialize the strategy by defining indicators used for trading signals.
        """
        # Calculate rolling max of the high and min of the low over the lookback period
        self.highs = self.I(lambda x: pd.Series(x).rolling(self.lookback).max(), self.data.High)
        self.lows = self.I(lambda x: pd.Series(x).rolling(self.lookback).min(), self.data.Low)

    def next(self):
        """
        Define the trading logic for each time step in the backtest.
        """
        # A breakout occurs if the closing price exceeds the highest high of the *previous* N bars
        if self.data.Close[-1] > self.highs[-2]:
            self.position.close()  # Close any short position
            self.buy()
        # A breakdown occurs if the closing price falls below the lowest low of the *previous* N bars
        elif self.data.Close[-1] < self.lows[-2]:
            self.position.close()  # Close any long position
            self.sell()


def run(ticker: str, start_date: str, end_date: str, market: str = "US", initial_capital=100000, **kwargs) -> dict:
    """
    Main orchestrator function for the Breakout strategy.
    
    Args:
        ticker (str): The stock ticker symbol to analyze
        start_date (str): Start date in 'YYYY-MM-DD' format
        end_date (str): End date in 'YYYY-MM-DD' format
        market (str): Market identifier for currency and data formatting (default: "US")
        initial_capital (float): Initial capital for the backtest (default: 100,000)
        **kwargs: Additional keyword arguments (e.g., 'lookback' for lookback period)
        
    Returns:
        dict: Dictionary containing backtest summary, data, and trades
    """
    
    lookback_period = kwargs.get('lookback', 20)

    # Set the lookback period for the strategy class
    Breakout.lookback = lookback_period

    # --- CORRECT: Call the centralized get_data function with the market ---
    hist_df = get_data(ticker, start_date, end_date, market=market)
    if hist_df.empty:
        return {"summary": {"Error": "No data found."}, "data": pd.DataFrame()}

    # CORRECT CODE:
    bt = Backtest(hist_df, Breakout, cash=initial_capital, commission=.002, finalize_trades=True)  # <-- CORRECT PLACE
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
    plot_df['Breakout_High'] = plot_df['High'].rolling(lookback_period).max().shift(1)  # Shift for correct plotting
    plot_df['Breakout_Low'] = plot_df['Low'].rolling(lookback_period).min().shift(1)   # Shift for correct plotting
    
    trades = stats._trades
    
    return {"summary": summary, "data": plot_df, "trades": trades}


# --- Streamlit Visualization for Standalone Testing ---
