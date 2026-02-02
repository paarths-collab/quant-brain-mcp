
import yfinance as yf
import pandas as pd
# import streamlit as st
import plotly.graph_objects as go
from backtesting import Backtest, Strategy

# @st.cache_data 
def get_data(ticker, start, end, market):
    """ Standardized data fetching function. """
    df = yf.download(ticker, start=start, end=end, progress=False, auto_adjust=True)
    if df.empty: return pd.DataFrame()
    
    # Handle multi-level columns from yfinance
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    
    df.rename(columns={
        "open": "Open", "high": "High", "low": "Low", "close": "Close", "volume": "Volume"
    }, inplace=True, errors='ignore')
    
    # Safely convert column names to title case, handling potential tuples
    try:
        df.columns = [col[0].title() if isinstance(col, tuple) else col.title() for col in df.columns]
    except:
        df.columns = [str(col).title() for col in df.columns]
        
    # Ensure we have the required columns
    required_cols = ['Open', 'High', 'Low', 'Close', 'Volume']
    available_cols = [col for col in required_cols if col in df.columns]
    if len(available_cols) >= len(required_cols) - 1:  # Allow for missing volume
        return df[available_cols]
    else:
        return pd.DataFrame()  # Return empty if missing critical columns

class FibonacciPullback(Strategy):
    """
    Fibonacci Pullback Strategy implementation for backtesting.py library.
    
    This strategy looks for pullbacks to Fibonacci levels (specifically 38.2%) after an uptrend
    and enters long positions when price starts moving up again at these levels.
    """
    finalize_trades = True
    
    def init(self):
        self.highest_high = self.I(lambda x, n: pd.Series(x).rolling(self.lookback_period).max(), self.data.High, self.lookback_period)
        self.lowest_low = self.I(lambda x, n: pd.Series(x).rolling(self.lookback_period).min(), self.data.Low, self.lookback_period)

    def next(self):
        swing_range = self.highest_high[-1] - self.lowest_low[-1]
        if swing_range > 0:
            # Buy on a pullback to the 38.2% level if price starts moving up
            fib_level_38 = self.highest_high[-1] - 0.382 * swing_range
            if not self.position and self.data.Close[-1] < fib_level_38 and self.data.Close[-1] > self.data.Close[-2]:
                self.buy()
            # Exit if the price breaks the recent swing high
            elif self.position and self.data.Close[-1] > self.highest_high[-1]:
                self.position.close()

# --- Main Run Function (Callable by Portfolio Builder) ---
def run(ticker, start_date, end_date, market, initial_capital=100000, **kwargs):
    """ Main orchestrator function for the Fibonacci Pullback strategy. """
    
    lookback_period = kwargs.get('lookback', 50)
    
    # Set the parameters for the strategy class
    FibonacciPullback.lookback_period = lookback_period

    hist_df = get_data(ticker, start_date, end_date, market)
    if hist_df.empty: 
        return {"summary": {"Error": "Could not fetch data."}, "data": pd.DataFrame()}
    
    bt = Backtest(hist_df, FibonacciPullback, cash=initial_capital, commission=.002)
    stats = bt.run(finalize_trades=True)
    
    summary = {
        "Total Return %": f"{stats['Return [%]']:.2f}",
        "Sharpe Ratio": f"{stats['Sharpe Ratio']:.2f}",
        "Max Drawdown %": f"{stats['Max. Drawdown [%]']:.2f}",
        "Number of Trades": stats['# Trades']
    }
    
    # --- Prepare detailed data for professional plotting ---
    plot_df = hist_df.copy()
    plot_df['Equity_Curve'] = stats._equity_curve['Equity']
    
    # Recalculate indicators for plotting
    plot_df['Swing_High'] = plot_df['High'].rolling(lookback_period).max()
    plot_df['Swing_Low'] = plot_df['Low'].rolling(lookback_period).min()
    swing_range = plot_df['Swing_High'] - plot_df['Swing_Low']
    plot_df['Fib_38.2%'] = plot_df['Swing_High'] - 0.382 * swing_range
    plot_df['Fib_50.0%'] = plot_df['Swing_High'] - 0.500 * swing_range
    plot_df['Fib_61.8%'] = plot_df['Swing_High'] - 0.618 * swing_range
    
    trades = stats._trades
    
    return {"summary": summary, "data": plot_df, "trades": trades}

# --- Streamlit Visualization for Standalone Testing ---
