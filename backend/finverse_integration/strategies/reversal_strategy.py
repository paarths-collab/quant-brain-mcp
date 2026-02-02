import yfinance as yf
import pandas as pd
import ta
from backtesting import Backtest, Strategy
from backtesting.lib import crossover
# import streamlit as st
import plotly.graph_objects as go
from plotly.subplots import make_subplots


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

class RsiReversal(Strategy):
    """
    RSI Reversal Strategy implementation for backtesting.py library.
    
    This strategy buys when RSI crosses above the lower bound (oversold condition)
    and sells when RSI crosses below the upper bound (overbought condition).
    """
    finalize_trades = True
    
    def init(self):
        self.rsi = self.I(ta.momentum.rsi, pd.Series(self.data.Close), window=self.rsi_window)

    def next(self):
        # Buy when RSI crosses above the lower bound (oversold)
        if crossover(self.rsi, self.lower_bound):
            self.buy()
        # Sell (close position) when RSI crosses below the upper bound (overbought)
        elif crossover(self.upper_bound, self.rsi):
            self.position.close()

# --- Main Run Function (Callable by Portfolio Builder) ---
def run(ticker: str, start_date: str, end_date: str, market, initial_capital=100000, **kwargs) -> dict:
    """ Main orchestrator function for the RSI Reversal strategy. """
    
    lower_bound_param = kwargs.get('lower_bound', 30)
    upper_bound_param = kwargs.get('upper_bound', 70)
    rsi_window_param = kwargs.get('rsi_window', 14)

    # Set the parameters for the strategy class
    RsiReversal.lower_bound = lower_bound_param
    RsiReversal.upper_bound = upper_bound_param
    RsiReversal.rsi_window = rsi_window_param

    hist_df = get_data(ticker, start_date, end_date, market)
    if hist_df.empty: 
        return {"summary": {"Error": "No data found."}, "data": pd.DataFrame()}

    bt = Backtest(hist_df, RsiReversal, cash=initial_capital, commission=.002)
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
    plot_df['RSI'] = ta.momentum.rsi(plot_df['Close'], window=rsi_window_param)
    
    trades = stats._trades
    
    return {"summary": summary, "data": plot_df, "trades": trades}

# --- Streamlit Visualization for Standalone Testing ---
