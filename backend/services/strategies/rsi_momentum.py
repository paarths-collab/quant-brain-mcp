# core/strategies/rsi_momentum.py

import pandas as pd
from .base import Strategy


class RSIMomentumStrategy(Strategy):
    """
    RSI Momentum Strategy

    Long Entry:
    - RSI crosses above lower threshold (e.g. 40)
    - Price is above trend MA (momentum confirmation)

    Exit:
    - RSI crosses below upper threshold (e.g. 60)
    """

    name = "RSI Momentum"

    def __init__(
        self,
        rsi_window: int = 14,
        lower: int = 40,
        upper: int = 60,
        trend_window: int = 20,
        use_trend_filter: bool = True,
    ):
        if lower >= upper:
            raise ValueError("Lower RSI bound must be less than upper bound")

        self.rsi_window = rsi_window
        self.lower = lower
        self.upper = upper
        self.trend_window = trend_window
        self.use_trend_filter = use_trend_filter


    @property
    def parameters(self) -> dict:
        return {
            "rsi_window": self.rsi_window,
            "lower": self.lower,
            "upper": self.upper,
            "trend_window": self.trend_window,
            "use_trend_filter": self.use_trend_filter,
        }


    def generate_signals(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        Expected columns: ['Open', 'High', 'Low', 'Close']
        """

        df = data.copy()

        # --- RSI calculation ---
        delta = df["Close"].diff()
        gain = delta.clip(lower=0)
        loss = -delta.clip(upper=0)

        avg_gain = gain.rolling(self.rsi_window).mean()
        avg_loss = loss.rolling(self.rsi_window).mean()

        rs = avg_gain / avg_loss
        df["rsi"] = 100 - (100 / (1 + rs))

        # --- Trend filter ---
        df["trend_ma"] = df["Close"].rolling(self.trend_window).mean()

        # --- Signal columns ---
        df["signal"] = 0
        df["entry_long"] = None
        df["entry_short"] = None

        # --- Entry logic ---
        rsi_cross_up = (
            (df["rsi"] >= self.lower) &
            (df["rsi"].shift(1) < self.lower)
        )

        trend_ok = df["Close"] > df["trend_ma"]
        long_entry = rsi_cross_up & (trend_ok if self.use_trend_filter else True)

        # --- Exit logic ---
        rsi_cross_down = (
            (df["rsi"] <= self.upper) &
            (df["rsi"].shift(1) > self.upper)
        )

        position = 0
        for i in range(len(df)):
            if long_entry.iloc[i]:
                position = 1
                df.loc[df.index[i], "entry_long"] = df.loc[df.index[i], "Close"]
            elif rsi_cross_down.iloc[i]:
                position = 0
            df.loc[df.index[i], "signal"] = position

        return df

# import pandas as pd
# import numpy as np
# import streamlit as st
# import plotly.graph_objects as go
# from plotly.subplots import make_subplots

# # --- CORRECT: Import the single, centralized get_data function ---
# from backend.services.data_loader import get_data

# def compute_rsi(series, period=14):
#     delta = series.diff()
#     gain = delta.clip(lower=0).fillna(0)
#     loss = -delta.clip(upper=0).fillna(0)
#     avg_gain = gain.rolling(window=period).mean()
#     avg_loss = loss.rolling(window=period).mean()
#     if avg_loss is None or avg_loss.equals(pd.Series(0, index=avg_loss.index)):
#         rs = np.inf
#     else:
#         rs = avg_gain / avg_loss
#     return 100 - (100 / (1 + rs))


# def generate_signals(df, rsi_period=14, lower=40, upper=60, momentum_filter=True):
#     df = df.copy()
#     df['rsi'] = compute_rsi(df['Close'], rsi_period)
#     df['ma20'] = df['Close'].rolling(window=20).mean()
#     df['trade'] = 0
#     for i in range(1, len(df)):
#         if df.iloc[i-1]['rsi'] < lower and df.iloc[i]['rsi'] >= lower:
#             if not momentum_filter or df.iloc[i]['Close'] > df.iloc[i]['ma20']:
#                 df.iloc[i, df.columns.get_loc('trade')] = 1
#         elif df.iloc[i-1]['rsi'] > upper and df.iloc[i]['rsi'] <= upper:
#             df.iloc[i, df.columns.get_loc('trade')] = -1
#     return df

# def run_backtest(df, init_cash=100000):
#     df = df.copy().reset_index()
#     cash, position, shares = init_cash, 0, 0
#     trades = []
#     # FIX: Rename 'equity' to 'Equity_Curve' for standardization
#     df['Equity_Curve'] = float(init_cash)
#     if df.empty: return pd.DataFrame(), []
#     for i in range(len(df)-1):
#         df.loc[i, 'Equity_Curve'] = cash + (shares * df.loc[i, 'Close'])
#         trade_signal = df.loc[i, 'trade']
#         next_day_open = df.loc[i+1, 'Open']
#         if trade_signal == 1 and position == 0:
#             shares_to_buy = cash // next_day_open
#             if shares_to_buy > 0:
#                 cash -= shares_to_buy * next_day_open
#                 position, shares = 1, shares_to_buy
#                 trades.append({'date': df.loc[i+1, 'Date'], 'type': 'BUY', 'price': next_day_open, 'shares': shares})
#         elif trade_signal == -1 and position == 1:
#             cash += shares * next_day_open
#             trades.append({'date': df.loc[i+1, 'Date'], 'type': 'SELL', 'price': next_day_open, 'shares': shares})
#             shares, position = 0, 0
#     df.loc[len(df)-1, 'Equity_Curve'] = float(cash + (shares * df.loc[len(df)-1, 'Close']))
#     return df.set_index('Date'), trades

# def calculate_performance_metrics(backtest_df, trades_list, initial_capital):
#     if backtest_df.empty: return {}
#     # FIX: Use 'Equity_Curve' column
#     final_equity = backtest_df['Equity_Curve'].iloc[-1]
#     total_return_pct = (final_equity / initial_capital - 1) * 100
#     daily_returns = backtest_df['Equity_Curve'].pct_change().dropna()
#     sharpe_ratio = np.sqrt(252) * daily_returns.mean() / daily_returns.std() if daily_returns.std() != 0 else 0
#     peak = backtest_df['Equity_Curve'].cummax()
#     drawdown = (backtest_df['Equity_Curve'] - peak) / peak
#     max_drawdown_pct = drawdown.min() * 100
#     win_rate = 0
#     if trades_list:
#         trades_df = pd.DataFrame(trades_list)
#         buy_prices = trades_df[trades_df['type'] == 'BUY']['price']
#         sell_prices = trades_df[trades_df['type'] == 'SELL']['price']
#         min_len = min(len(buy_prices), len(sell_prices))
#         if min_len > 0:
#             trade_returns = (sell_prices.values[:min_len] - buy_prices.values[:min_len]) / buy_prices.values[:min_len]
#             win_rate = (trade_returns > 0).mean() * 100
#     return {
#         "Total Return %": f"{total_return_pct:.2f}", "Sharpe Ratio": f"{sharpe_ratio:.2f}",
#         "Max Drawdown %": f"{max_drawdown_pct:.2f}", "Win Rate %": f"{win_rate:.2f}",
#         "Number of Trades": len(trades_list) // 2
#     }

# # --- Orchestrator/API Entry Point ---
# # FIX: Add 'initial_capital' to the function signature
# def run(ticker: str, start_date: str, end_date: str, market, initial_capital=100000, **kwargs) -> dict:
#     try:
#         rsi_lower = kwargs.get("rsi_lower", 40)
#         rsi_upper = kwargs.get("rsi_upper", 60)
#         df = get_data(ticker, start_date, end_date, market)
#         if df.empty:
#             return {"summary": {"Error": "No data found."}, "data": pd.DataFrame()}
#         df_signals = generate_signals(df, lower=rsi_lower, upper=rsi_upper)
#         # FIX: Pass 'initial_capital' down to the backtester
#         df_backtest, trades = run_backtest(df_signals, init_cash=initial_capital)
#         summary_metrics = calculate_performance_metrics(df_backtest, trades, initial_capital)
#         return {"summary": summary_metrics, "data": df_backtest, "trades": trades}
#     except Exception as e:
#         return {"summary": {"Error": str(e)}, "data": pd.DataFrame()}

# # --- Streamlit Visualization ---
# if __name__ == "__main__":
#     st.set_page_config(page_title="RSI Momentum Strategy", layout="wide")
#     st.title("📈 RSI Momentum Strategy (Standalone)")
#     with st.sidebar:
#         st.header("⚙️ Configuration")
#         ticker = st.text_input("Ticker Symbol", "AMD")
#         start_date = st.date_input("Start Date", pd.to_datetime("2022-01-01"))
#         end_date = st.date_input("End Date", pd.to_datetime("today"))
#         # FIX: Add initial_capital to the UI
#         initial_capital = st.number_input("Initial Capital", 1000, 1000000, 100000)
        
#         st.header("Strategy Parameters")
#         rsi_lower = st.slider("RSI Lower Threshold", 10, 45, 40)
#         rsi_upper = st.slider("RSI Upper Threshold", 55, 90, 60)
#         run_button = st.button("🔬 Run Backtest", use_container_width=True)
        
#     if run_button:
#         st.header(f"Results for {ticker}")
#         with st.spinner("Running backtest..."):
#             results = run(
#                 ticker, 
#                 start_date, 
#                 end_date,
#                 market="USA",  # Default market for standalone testing
#                 initial_capital=initial_capital, # Pass capital from UI
#                 rsi_lower=rsi_lower, 
#                 rsi_upper=rsi_upper
#             )
#             summary = results.get("summary", {})
#             backtest_df = results.get("data", pd.DataFrame())
#             trades_list = results.get("trades", [])
            
#         if "Error" in summary:
#             st.error(summary["Error"])
#         elif not backtest_df.empty:
#             st.subheader("Performance Summary")
#             cols = st.columns(5)
#             cols[0].metric("Total Return", f"{summary.get('Total Return %', '0.00')}%")
#             cols[1].metric("Sharpe Ratio", summary.get('Sharpe Ratio', '0.00'))
#             cols[2].metric("Max Drawdown", f"{summary.get('Max Drawdown %', '0.00')}%")
#             cols[3].metric("Win Rate", f"{summary.get('Win Rate %', '0.00')}%")
#             cols[4].metric("Trades", summary.get('Number of Trades', 0))
            
#             st.subheader("Price, RSI & Equity Curve")
#             fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.1, row_heights=[0.7, 0.3])
            
#             fig.add_trace(go.Scatter(x=backtest_df.index, y=backtest_df['Close'], name='Price'), row=1, col=1)
#             # FIX: Plot the 'Equity_Curve' column
#             fig.add_trace(go.Scatter(x=backtest_df.index, y=backtest_df['Equity_Curve'], name='Equity Curve', yaxis='y2'), row=1, col=1)
            
#             trades_df = pd.DataFrame(trades_list)
#             if not trades_df.empty:
#                 buy_signals = trades_df[trades_df['type'] == 'BUY']
#                 sell_signals = trades_df[trades_df['type'] == 'SELL']
#                 fig.add_trace(go.Scatter(x=buy_signals['date'], y=buy_signals['price'], mode='markers', name='Buy Signal', marker=dict(color='lime', size=10, symbol='triangle-up')), row=1, col=1)
#                 fig.add_trace(go.Scatter(x=sell_signals['date'], y=sell_signals['price'], mode='markers', name='Sell Signal', marker=dict(color='red', size=10, symbol='triangle-down')), row=1, col=1)
                
#             fig.add_trace(go.Scatter(x=backtest_df.index, y=backtest_df['rsi'], name='RSI'), row=2, col=1)
#             fig.add_hline(y=rsi_upper, line_dash="dash", line_color="red", row=2, col=1)
#             fig.add_hline(y=rsi_lower, line_dash="dash", line_color="green", row=2, col=1)
            
#             fig.update_layout(title_text=f"{ticker} Backtest: RSI Momentum", xaxis_rangeslider_visible=False, yaxis2=dict(title="Equity ($)", overlaying='y', side='right'))
#             st.plotly_chart(fig, use_container_width=True)
