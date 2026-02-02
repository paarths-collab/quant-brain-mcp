


import yfinance as yf
import pandas as pd
import numpy as np
# import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
from typing import List

# --- Core Backtesting Logic ---
# @st.cache_data 
def run_backtest(ticker1, ticker2, start_date, end_date, lookback=30, entry_z=2.0, initial_capital=100000):
    """Runs a vectorized backtest for a pairs trading strategy."""
    data = yf.download([ticker1, ticker2], start=start_date, end=end_date, progress=False, auto_adjust=True)['Close']
    if data.empty or data.isnull().values.any() or len(data) < lookback:
        return pd.DataFrame()
    
    # Calculate spread and z-score
    data.dropna(inplace=True)
    beta = np.polyfit(data[ticker2], data[ticker1], 1)[0]
    data['Spread'] = data[ticker1] - beta * data[ticker2]
    data['Mean'] = data['Spread'].rolling(lookback).mean()
    data['STD'] = data['Spread'].rolling(lookback).std()
    data['Zscore'] = (data['Spread'] - data['Mean']) / data['STD']
    
    # Generate signals
    data['Signal'] = 0
    data.loc[data['Zscore'] > entry_z, 'Signal'] = -1  # Short the spread
    data.loc[data['Zscore'] < -entry_z, 'Signal'] = 1   # Long the spread
    data['Position'] = data['Signal'].shift(1).ffill().fillna(0)
    
    # Calculate returns and equity curve
    data['Strategy_Returns'] = data['Spread'].pct_change() * data['Position']
    data['Equity_Curve'] = (1 + data['Strategy_Returns']).cumprod() * initial_capital
    
    # Add beta to the final dataframe for reference
    data.attrs['beta'] = beta
    return data

def calculate_performance_metrics(backtest_df, initial_capital):
    """Calculates summary statistics for the backtest and formats them."""
    if backtest_df.empty: return {}
    
    final_equity = backtest_df['Equity_Curve'].iloc[-1]
    total_return_pct = (final_equity / initial_capital - 1) * 100
    daily_returns = backtest_df['Strategy_Returns'].dropna()
    sharpe_ratio = np.sqrt(252) * daily_returns.mean() / daily_returns.std() if daily_returns.std() != 0 else 0
    peak = backtest_df['Equity_Curve'].cummax()
    drawdown = (backtest_df['Equity_Curve'] - peak) / peak
    max_drawdown_pct = drawdown.min() * 100
    trades = backtest_df[backtest_df['Signal'] != backtest_df['Signal'].shift(1)]
    
    return {
        "Total Return %": f"{total_return_pct:.2f}",
        "Sharpe Ratio": f"{sharpe_ratio:.2f}",
        "Max Drawdown %": f"{max_drawdown_pct:.2f}",
        "Number of Trades": len(trades),
        "Hedge Ratio (Beta)": f"{backtest_df.attrs.get('beta', 0.0):.2f}"
    }

# --- Main Run Function (Callable by Portfolio Builder) ---
def run(tickers: List[str], start_date: str, end_date: str, initial_capital=100000, **kwargs) -> dict:
    """Main entry point for the Pairs Trading strategy."""
    if not isinstance(tickers, list) or len(tickers) != 2:
        return {"summary": {"Error": "Pairs Trading requires exactly two tickers."}, "data": pd.DataFrame()}
    
    try:
        df_backtest = run_backtest(
            tickers[0], 
            tickers[1], 
            start_date, 
            end_date,
            initial_capital=initial_capital,
            **kwargs
        )
        if df_backtest.empty:
            return {"summary": {"Error": "Could not fetch sufficient data for the pair."}, "data": pd.DataFrame()}
        
        summary_metrics = calculate_performance_metrics(df_backtest, initial_capital)
        
        # Rename the single ticker column to 'ticker' for portfolio builder consistency if needed
        summary_metrics['ticker'] = f"{tickers[0]}/{tickers[1]}"
        
        return {"summary": summary_metrics, "data": df_backtest}
    except Exception as e:
        return {"summary": {"Error": str(e)}, "data": pd.DataFrame()}

# --- Streamlit Visualization for Standalone Testing ---
