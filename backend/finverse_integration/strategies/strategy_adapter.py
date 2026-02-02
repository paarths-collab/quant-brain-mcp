import pandas as pd
from backtesting import Backtest

# --- Import the STRATEGY CLASSES THEMSELVES, not their run functions ---
from strategies.breakout_strategy import Breakout
from strategies.channel_trading import ChannelTrading
from strategies.ema_crossover import EmaCross
from strategies.macd_strategy import MacdCross
from strategies.mean_inversion import MeanReversion
from strategies.momentum_strategy import Momentum
from strategies.pullback_fibonacci import FibonacciPullback
from strategies.reversal_strategy import RsiReversal
from strategies.sma_crossover import SmaCross
from strategies.support_resistance import SupportResistance

# --- Import the ONE, CORRECT data loader ---
from ..utils.data_loader import get_data

# --- Create a mapping of names to the STRATEGY CLASSES ---
STRATEGY_CLASS_MAPPING = {
    "Breakout Strategy": Breakout,
    "Channel Trading": ChannelTrading,
    "EMA Crossover": EmaCross,
    "MACD Strategy": MacdCross,
    "Mean Reversion": MeanReversion,
    "Momentum Strategy": Momentum,
    "Fibonacci Pullback": FibonacciPullback,
    "RSI Reversal": RsiReversal,
    "SMA Crossover": SmaCross,
    "Support/Resistance": SupportResistance,
}

# --- This is the MASTER RUN FUNCTION that the portfolio engine will call ---
def run_strategy(strategy_name: str, ticker: str, start_date: str, end_date: str, market, initial_capital=100000, **kwargs) -> dict:
    """
    A single, standardized function to run any backtesting.py-based strategy.
    It ensures the correct, robust data is used for every backtest.
    """
    # 1. Get the correct Strategy Class from the mapping
    StrategyClass = STRATEGY_CLASS_MAPPING.get(strategy_name)
    if not StrategyClass:
        return {"summary": {"Error": f"Strategy '{strategy_name}' not found in adapter."}, "data": pd.DataFrame()}

    # 2. Use the central, robust get_data function
    hist_df = get_data(ticker, start_date, end_date, market)
    if hist_df.empty:
        return {"summary": {"Error": "Could not fetch valid data for backtest."}, "data": pd.DataFrame()}

    # 3. Dynamically set strategy parameters from kwargs
    # This is a more robust way to handle parameters
    for param, value in kwargs.items():
        if hasattr(StrategyClass, param):
            setattr(StrategyClass, param, value)

    # 4. Instantiate and run the backtest
    bt = Backtest(hist_df, StrategyClass, cash=initial_capital, commission=.002, finalize_trades=True)
    stats = bt.run()

    # 5. Format and return the results in the standard way
    summary = {
        "Total Return %": f"{stats['Return [%]']:.2f}",
        "Sharpe Ratio": f"{stats['Sharpe Ratio']:.2f}",
        "Max Drawdown %": f"{stats['Max. Drawdown [%]']:.2f}",
        "Number of Trades": stats['# Trades']
    }
    plot_df = pd.DataFrame({'Equity_Curve': stats._equity_curve['Equity']})
    
    return {"summary": summary, "data": plot_df}
