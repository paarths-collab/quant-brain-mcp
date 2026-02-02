# File: utils/portfolio_engine.py
# This is the backend logic for your application.

import pandas as pd
import numpy as np
import yfinance as yf

# --- Import all strategy run functions from the 'strategies' package ---
# --- Import all strategy run functions from the 'strategies' package ---
from ..strategies.breakout_strategy import run as run_breakout
from ..strategies.channel_trading import run as run_channel_trading
from ..strategies.ema_crossover import run as run_ema_crossover
from ..strategies.macd_strategy import run as run_macd_strategy
from ..strategies.mean_inversion import run as run_mean_inversion
from ..strategies.momentum_strategy import run as run_momentum_strategy
from ..strategies.pairs_trading import run as run_pairs_trading
from ..strategies.pullback_fibonacci import run as run_pullback_fibonacci
from ..strategies.reversal_strategy import run as run_reversal_strategy
from ..strategies.rsi_strategy import run as run_rsi_strategy
from ..strategies.sma_crossover import run as run_sma_crossover
from ..strategies.support_resistance import run as run_support_resistance

# --- Local Imports ---
from .market_utils import get_market_config

# --- Create the strategy mapping ---
STRATEGY_MAPPING = {
    "Breakout Strategy": run_breakout, "Channel Trading": run_channel_trading,
    "EMA Crossover": run_ema_crossover, "MACD Strategy": run_macd_strategy,
    "Mean Reversion": run_mean_inversion, "Momentum Strategy": run_momentum_strategy,
    "Pairs Trading": run_pairs_trading, "Fibonacci Pullback": run_pullback_fibonacci,
    "RSI Reversal": run_reversal_strategy, "RSI Momentum": run_rsi_strategy,
    "SMA Crossover": run_sma_crossover, "Support/Resistance": run_support_resistance,
}


class PortfolioEngine:
    """
    Engine for running portfolio backtests and calculations.
    """
    
    def get_benchmark_data(self, ticker, start, end, initial_capital):
        """
        Fetches benchmark data and calculates equity curve for comparison.
        """
        df = yf.download(ticker, start=start, end=end, progress=False)
        df['Returns'] = df['Close'].pct_change()
        df['Equity_Curve'] = initial_capital * (1 + df['Returns']).cumprod()
        return df


    def calculate_portfolio_metrics(self, equity_curve, start_date, end_date):
        """
        Calculates comprehensive portfolio performance metrics.
        """
        if equity_curve is None or equity_curve.empty: 
            return {}
        
        days = (pd.to_datetime(end_date) - pd.to_datetime(start_date)).days
        years = max(days / 365.25, 1/52)
        initial_capital = equity_curve.iloc[0]
        final_equity = equity_curve.iloc[-1]
        total_return_pct = (final_equity / initial_capital - 1) * 100
        cagr = ((final_equity / initial_capital) ** (1 / years) - 1) * 100
        daily_returns = equity_curve.pct_change().dropna()
        
        if daily_returns.empty or daily_returns.std() == 0:
            sharpe_ratio, annual_volatility = 0.0, 0.0
        else:
            annual_volatility = daily_returns.std() * np.sqrt(252) * 100
            sharpe_ratio = (daily_returns.mean() * 252) / (daily_returns.std() * np.sqrt(252))
        
        peak = equity_curve.cummax()
        drawdown = (equity_curve - peak) / peak
        max_drawdown_pct = drawdown.min() * 100
        
        return {
            "Total Return %": f"{total_return_pct:.2f}", "CAGR %": f"{cagr:.2f}",
            "Annual Volatility %": f"{annual_volatility:.2f}", "Sharpe Ratio": f"{sharpe_ratio:.2f}",
            "Max Drawdown %": f"{max_drawdown_pct:.2f}",
        }


    def build_portfolio(self, orchestrator, tickers, market, start_date, end_date, strategies_config, initial_capital=100000):
        """
        Builds and evaluates a portfolio using multiple strategies on given tickers.
        """
        # Convert strategies_config to the format expected by run_portfolio_backtest
        # We'll create selections where each strategy is applied to each ticker with equal weight
        selections = {}
        for i, strategy_name in enumerate(strategies_config):
            for j, ticker in enumerate(tickers):
                # Create a unique key for this combination
                key = f"{strategy_name}_{ticker}_{i}_{j}"
                
                # Define parameters for each strategy
                if strategy_name == "Momentum":
                    # Use the momentum strategy from the mapping
                    actual_strategy_name = "Momentum Strategy"
                    params = {"window": 20}  # Default window, can be adjusted
                elif strategy_name == "Mean Reversion (Bollinger Bands)":
                    actual_strategy_name = "Mean Reversion"
                    params = {"window": 20, "std_dev": 2}  # Default values
                elif strategy_name == "Sma Crossover":
                    actual_strategy_name = "SMA Crossover"
                    params = {"short_window": 20, "long_window": 50}  # Default values
                else:
                    # Default to Momentum Strategy if unknown
                    actual_strategy_name = "Momentum Strategy"
                    params = {"window": 20}
                
                # Calculate equal weight for each strategy-ticker combination
                weight = 1.0 / (len(strategies_config) * len(tickers))
                
                selections[key] = {
                    "name": actual_strategy_name,
                    "ticker": ticker,
                    "weight": weight,
                    "params": params
                }
        
        # Run the portfolio backtest using the existing function
        portfolio_df, metrics, errors = self.run_portfolio_backtest(
            selections=selections,
            start_date=start_date,
            end_date=end_date,
            initial_capital=initial_capital,
            market=market
        )
        
        # Prepare the results in the expected format
        results = {
            "equity_curve": portfolio_df['Equity_Curve'] if not portfolio_df.empty else pd.Series(dtype=float),
            "metrics": metrics,
            "weights": {key: selection['weight'] for key, selection in selections.items()},
            "currency_symbol": "$",  # Default currency symbol
            "benchmark": "SPY",  # Default benchmark
            "data": portfolio_df
        }
        
        # Add error information if any occurred
        if errors:
            results["errors"] = errors
        
        return results


    def run_portfolio_backtest(self, selections, start_date, end_date, initial_capital, market="US"):
        """
        Runs a portfolio backtest combining multiple strategies with specified weights.
        """
        all_equity_curves = {}
        error_messages = []
        
        for key, params in selections.items():
            strategy_name = params['name']
            run_func = STRATEGY_MAPPING[strategy_name]
            # Add market parameter to run_params
            run_params = {"start_date": start_date, "end_date": end_date, "market": market, "initial_capital": initial_capital, **params['params']}
            
            if strategy_name == "Pairs Trading":
                tickers = [t.strip().upper() for t in params["ticker"].split(",")]
                if len(tickers) != 2:
                    error_messages.append(f"Pairs Trading requires exactly two tickers for '{key}'. Skipping.")
                    continue
                run_params["tickers"] = tickers
            else:
                run_params["ticker"] = params["ticker"]
            
            results = run_func(**run_params)
            if "Error" in results.get("summary", {}) or results.get("data", pd.DataFrame()).empty:
                error_messages.append(f"Backtest for {strategy_name} on {params['ticker']} failed. Skipping.")
                continue
            
            all_equity_curves[key] = {"equity": results["data"]['Equity_Curve'], "weight": params['weight']}

        if not all_equity_curves: 
            return pd.DataFrame(), {}, error_messages
        
        portfolio_df = pd.DataFrame()
        for key, data in all_equity_curves.items():
            strategy_returns = data['equity'].pct_change().fillna(0)
            portfolio_df[f'{key}_weighted_returns'] = strategy_returns * data['weight']

        portfolio_df['Total_Returns'] = portfolio_df.sum(axis=1)
        portfolio_df['Equity_Curve'] = (1 + portfolio_df['Total_Returns']).cumprod() * initial_capital
        portfolio_df.loc[portfolio_df.index[0], 'Equity_Curve'] = initial_capital
        
        metrics = self.calculate_portfolio_metrics(portfolio_df['Equity_Curve'], start_date, end_date)
        return portfolio_df, metrics, error_messages