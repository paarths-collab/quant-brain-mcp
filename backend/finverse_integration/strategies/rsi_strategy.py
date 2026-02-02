import pandas as pd
import numpy as np
# import streamlit as st
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# --- CORRECT: Import the single, centralized get_data function ---
from ..utils.data_loader import get_data

def compute_rsi(series, period=14):
    delta = series.diff()
    gain = delta.clip(lower=0).fillna(0)
    loss = -delta.clip(upper=0).fillna(0)
    avg_gain = gain.rolling(window=period).mean()
    avg_loss = loss.rolling(window=period).mean()
    if avg_loss is None or avg_loss.equals(pd.Series(0, index=avg_loss.index)):
        rs = np.inf
    else:
        rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))


def generate_signals(df, rsi_period=14, lower=40, upper=60, momentum_filter=True):
    df = df.copy()
    df['rsi'] = compute_rsi(df['Close'], rsi_period)
    df['ma20'] = df['Close'].rolling(window=20).mean()
    df['trade'] = 0
    for i in range(1, len(df)):
        if df.iloc[i-1]['rsi'] < lower and df.iloc[i]['rsi'] >= lower:
            if not momentum_filter or df.iloc[i]['Close'] > df.iloc[i]['ma20']:
                df.iloc[i, df.columns.get_loc('trade')] = 1
        elif df.iloc[i-1]['rsi'] > upper and df.iloc[i]['rsi'] <= upper:
            df.iloc[i, df.columns.get_loc('trade')] = -1
    return df

def run_backtest(df, init_cash=100000):
    df = df.copy().reset_index()
    cash, position, shares = init_cash, 0, 0
    trades = []
    # FIX: Rename 'equity' to 'Equity_Curve' for standardization
    df['Equity_Curve'] = float(init_cash)
    if df.empty: return pd.DataFrame(), []
    for i in range(len(df)-1):
        df.loc[i, 'Equity_Curve'] = cash + (shares * df.loc[i, 'Close'])
        trade_signal = df.loc[i, 'trade']
        next_day_open = df.loc[i+1, 'Open']
        if trade_signal == 1 and position == 0:
            shares_to_buy = cash // next_day_open
            if shares_to_buy > 0:
                cash -= shares_to_buy * next_day_open
                position, shares = 1, shares_to_buy
                trades.append({'date': df.loc[i+1, 'Date'], 'type': 'BUY', 'price': next_day_open, 'shares': shares})
        elif trade_signal == -1 and position == 1:
            cash += shares * next_day_open
            trades.append({'date': df.loc[i+1, 'Date'], 'type': 'SELL', 'price': next_day_open, 'shares': shares})
            shares, position = 0, 0
    df.loc[len(df)-1, 'Equity_Curve'] = float(cash + (shares * df.loc[len(df)-1, 'Close']))
    return df.set_index('Date'), trades

def calculate_performance_metrics(backtest_df, trades_list, initial_capital):
    if backtest_df.empty: return {}
    # FIX: Use 'Equity_Curve' column
    final_equity = backtest_df['Equity_Curve'].iloc[-1]
    total_return_pct = (final_equity / initial_capital - 1) * 100
    daily_returns = backtest_df['Equity_Curve'].pct_change().dropna()
    sharpe_ratio = np.sqrt(252) * daily_returns.mean() / daily_returns.std() if daily_returns.std() != 0 else 0
    peak = backtest_df['Equity_Curve'].cummax()
    drawdown = (backtest_df['Equity_Curve'] - peak) / peak
    max_drawdown_pct = drawdown.min() * 100
    win_rate = 0
    if trades_list:
        trades_df = pd.DataFrame(trades_list)
        buy_prices = trades_df[trades_df['type'] == 'BUY']['price']
        sell_prices = trades_df[trades_df['type'] == 'SELL']['price']
        min_len = min(len(buy_prices), len(sell_prices))
        if min_len > 0:
            trade_returns = (sell_prices.values[:min_len] - buy_prices.values[:min_len]) / buy_prices.values[:min_len]
            win_rate = (trade_returns > 0).mean() * 100
    return {
        "Total Return %": f"{total_return_pct:.2f}", "Sharpe Ratio": f"{sharpe_ratio:.2f}",
        "Max Drawdown %": f"{max_drawdown_pct:.2f}", "Win Rate %": f"{win_rate:.2f}",
        "Number of Trades": len(trades_list) // 2
    }

# --- Orchestrator/API Entry Point ---
# FIX: Add 'initial_capital' to the function signature
def run(ticker: str, start_date: str, end_date: str, market, initial_capital=100000, **kwargs) -> dict:
    try:
        rsi_lower = kwargs.get("rsi_lower", 40)
        rsi_upper = kwargs.get("rsi_upper", 60)
        df = get_data(ticker, start_date, end_date, market)
        if df.empty:
            return {"summary": {"Error": "No data found."}, "data": pd.DataFrame()}
        df_signals = generate_signals(df, lower=rsi_lower, upper=rsi_upper)
        # FIX: Pass 'initial_capital' down to the backtester
        df_backtest, trades = run_backtest(df_signals, init_cash=initial_capital)
        summary_metrics = calculate_performance_metrics(df_backtest, trades, initial_capital)
        return {"summary": summary_metrics, "data": df_backtest, "trades": trades}
    except Exception as e:
        return {"summary": {"Error": str(e)}, "data": pd.DataFrame()}

# --- Streamlit Visualization ---
