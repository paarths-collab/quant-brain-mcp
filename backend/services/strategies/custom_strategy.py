import pandas as pd
import streamlit as st
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from backtesting import Backtest, Strategy
from backtesting.lib import crossover
import ta

# --- CORRECT: Import the single, centralized get_data function ---
from backend.services.data_loader import get_data
from backend.services.market_utils import get_market_config

# --- Main Run Function (Callable by Portfolio Builder) ---
def run(ticker, start_date, end_date, market: str = "US", initial_capital=100000, **kwargs):
    """ Main orchestrator function for the MACD Crossover strategy. """
    
    fast_period = kwargs.get('fast', 12)
    slow_period = kwargs.get('slow', 26)
    signal_period = kwargs.get('signal', 9)
    
    class MacdCross(Strategy):
        fast = fast_period
        slow = slow_period
        signal = signal_period

        def init(self):
            close = pd.Series(self.data.Close)
            self.macd_line = self.I(ta.trend.macd, close, window_fast=self.fast, window_slow=self.slow)
            self.macd_signal_line = self.I(ta.trend.macd_signal, close, window_fast=self.fast, window_slow=self.slow, window_sign=self.signal)

        def next(self):
            if crossover(self.macd_line, self.macd_signal_line):
                self.position.close()
                self.buy()
            elif crossover(self.macd_signal_line, self.macd_line):
                self.position.close()
                self.sell()

    # --- CORRECT: Call the centralized get_data function with the market ---
    hist_df = get_data(ticker, start_date, end_date, market=market)
    if hist_df.empty:
        return {"summary": {"Error": "Could not fetch data."}, "data": pd.DataFrame()}
    
    bt = Backtest(hist_df, MacdCross, cash=initial_capital, commission=.002, finalize_trades=True)
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
    plot_df['MACD_Line'] = ta.trend.macd(plot_df['Close'], window_fast=fast_period, window_slow=slow_period)
    plot_df['MACD_Signal'] = ta.trend.macd_signal(plot_df['Close'], window_fast=fast_period, window_slow=slow_period, window_sign=signal_period)
    plot_df['MACD_Hist'] = ta.trend.macd_diff(plot_df['Close'], window_fast=fast_period, window_slow=slow_period, window_sign=signal_period)
    
    trades = stats._trades
    
    return {"summary": summary, "data": plot_df, "trades": trades}

# --- Streamlit Visualization for Standalone Testing ---
if __name__ == "__main__":
    st.set_page_config(page_title="MACD Crossover Strategy", layout="wide")
    st.title("📈 MACD Crossover Strategy (Standalone)")

    with st.sidebar:
        st.header("⚙️ Configuration")
        ticker = st.text_input("Ticker Symbol", "GOOGL")
        start_date = st.date_input("Start Date", pd.to_datetime("2022-01-01"))
        end_date = st.date_input("End Date", pd.to_datetime("today"))
        market = st.selectbox("Market", ["US", "INDIA", "EUROPE", "UK", "JAPAN"], index=0)
        
        st.header("Strategy Parameters")
        fast_period = st.slider("Fast EMA Period", 5, 50, 12)
        slow_period = st.slider("Slow EMA Period", 20, 100, 26)
        signal_period = st.slider("Signal EMA Period", 5, 50, 9)
        
        run_button = st.button("🔬 Run Backtest", use_container_width=True)

    if run_button:
        if fast_period >= slow_period:
            st.error("Error: Fast EMA period must be less than Slow EMA period.")
        else:
            st.header(f"Results for {ticker}")
            with st.spinner("Running backtest..."):
                results = run(
                    ticker=ticker,
                    start_date=start_date,
                    end_date=end_date,
                    market=market,
                    fast=fast_period,
                    slow=slow_period,
                    signal=signal_period
                )
                summary = results.get("summary", {})
                backtest_df = results.get("data", pd.DataFrame())
                trades_df = results.get("trades", pd.DataFrame())

            if "Error" in summary:
                st.error(summary["Error"])
            elif not backtest_df.empty:
                st.subheader("Performance Summary")
                cols = st.columns(4)
                cols[0].metric("Total Return", f"{summary.get('Total Return %', '0.00')}%")
                cols[1].metric("Sharpe Ratio", summary.get('Sharpe Ratio', '0.00'))
                cols[2].metric("Max Drawdown", f"{summary.get('Max Drawdown %', '0.00')}%")
                cols[3].metric("Trades", summary.get('Number of Trades', 0))

                # --- Professional Charting with Subplots ---
                st.subheader("Price Chart with MACD, Trades & Equity")
                fig = make_subplots(rows=2, cols=1, shared_xaxes=True, 
                                    vertical_spacing=0.1, row_heights=[0.7, 0.3])

                # Top Panel: Price, Equity, and Trades
                fig.add_trace(go.Scatter(x=backtest_df.index, y=backtest_df['Close'], name='Price', line=dict(color='skyblue')), row=1, col=1)
                fig.add_trace(go.Scatter(x=backtest_df.index, y=backtest_df['Equity_Curve'], name='Equity Curve', yaxis='y2', line=dict(color='purple', dash='dot')), row=1, col=1)
                
                buy_signals = trades_df[trades_df['Size'] > 0]
                sell_signals = trades_df[trades_df['Size'] < 0]
                fig.add_trace(go.Scatter(x=buy_signals.index, y=buy_signals['EntryPrice'], mode='markers', name='Buy Signal', marker=dict(color='lime', size=10, symbol='triangle-up')), row=1, col=1)
                fig.add_trace(go.Scatter(x=sell_signals.index, y=sell_signals['EntryPrice'], mode='markers', name='Sell Signal', marker=dict(color='red', size=10, symbol='triangle-down')), row=1, col=1)

                # Bottom Panel: MACD
                colors = ['green' if val >= 0 else 'red' for val in backtest_df['MACD_Hist']]
                fig.add_trace(go.Bar(x=backtest_df.index, y=backtest_df['MACD_Hist'], name='Histogram', marker_color=colors), row=2, col=1)
                fig.add_trace(go.Scatter(x=backtest_df.index, y=backtest_df['MACD_Line'], name='MACD Line', line=dict(color='blue')), row=2, col=1)
                fig.add_trace(go.Scatter(x=backtest_df.index, y=backtest_df['MACD_Signal'], name='Signal Line', line=dict(color='orange')), row=2, col=1)
                
                fig.update_layout(
                    title_text=f"{ticker} MACD Crossover Backtest",
                    xaxis_rangeslider_visible=False,
                    yaxis=dict(title=f"Price ({get_market_config(market)['currency_symbol']})"),
                    yaxis2=dict(title=f"Equity ({get_market_config(market)['currency_symbol']})", overlaying='y', side='right', showgrid=False)
                )
                fig.update_yaxes(title_text="MACD", row=2, col=1)
                st.plotly_chart(fig, use_container_width=True)