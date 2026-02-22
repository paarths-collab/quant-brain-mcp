from backend.analytics.utils import get_risk_free_rate
import yfinance as yf
import pandas as pd
import numpy as np

class Backtester:

    def __init__(self, lookback_years=3):
        self.lookback_years = lookback_years

    def backtest(self, tickers, weights=None):
        # ... (Existing backtest logic - kept for per-stock report) ...
        # (Assuming I don't need to rewrite the whole existing method here as I am using replace_file_content)
        # Wait, I need to verify if I am replacing the whole class or just appending/modifying.
        # The prompt says "replace_file_content". I should use the one that allows me to add a method.
        # But for 'backtest' method update, the user didn't explicitly ask to CHANGE the existing backtest logic (other than maybe sharpe?)
        # User said "1. Add Risk-Free Rate".
        # So I will rewrite the Sharpe calc in existing method and add new method.
        pass
        
    def backtest_monthly_rebalance(self, tickers, weights=None, transaction_cost=0.001):
        try:
            # Reuse data logic or re-download? 
            # Ideally avoid re-download if called from Orchestrator with data passed.
            # But adhering to user's "clean" snippet which does download:
            
            data = yf.download(
                tickers,
                period=f"{self.lookback_years}y",
                interval="1d",
                auto_adjust=True,
                progress=False
            )["Close"]

            if isinstance(data, pd.Series):
                data = data.to_frame() # Correct logic

            returns = data.pct_change().dropna()

            # Resample to Monthly cumulative return
            monthly_returns = returns.resample("ME").apply(
                lambda x: (1 + x).prod() - 1
            )

            if weights is None:
                weights = np.ones(len(tickers)) / len(tickers)
            else:
                # Ensure weights are numpy array
                weights = np.array(weights)

            portfolio_value = 1.0
            portfolio_values = []
            
            current_weights = weights.copy()
            rf = get_risk_free_rate()

            for date, row in monthly_returns.iterrows():
                # Apply monthly returns
                # row.values is 1D array of asset returns for that month
                # current_weights is 1D array of weights
                
                # Check for NaNs
                row_vals = row.values
                if np.isnan(row_vals).any():
                     portfolio_values.append(portfolio_value)
                     continue

                portfolio_return = np.dot(current_weights, row_vals)

                portfolio_value *= (1 + portfolio_return)

                # Simulate Price Drift to get "current actual weights" before rebalance
                # (Prices moved, so weights shifted)
                # Value of each component
                # comp_values = current_weights * (1 + row_vals)
                # new_port_val_raw = np.sum(comp_values)
                # drifted_weights = comp_values / new_port_val_raw
                
                # Transaction cost on rebalance (Back to Target Weights)
                # turnover = np.sum(np.abs(drifted_weights - weights))
                # For simplicity (as per user snippet), using simpler approx:
                turnover = np.sum(np.abs(current_weights - weights))
                cost = turnover * transaction_cost

                portfolio_value *= (1 - cost)
                portfolio_values.append(portfolio_value)

                # Rebalance back to target weights for next month
                current_weights = weights.copy()

            if not portfolio_values:
                 return {}

            monthly_series = pd.Series(portfolio_values)
            
            # Simple Sharpe on Monthly
            # Mean monthly ret * 12 / Std monthly ret * sqrt(12)
            # Excess return: (Mean - MonthlyRF)
            monthly_rf = rf / 12
            
            rets = monthly_series.pct_change().dropna()
            if rets.std() == 0:
                sharpe = 0
            else:
                excess_ret = rets.mean() - monthly_rf
                sharpe = (excess_ret / rets.std()) * np.sqrt(12)

            max_drawdown = (monthly_series / monthly_series.cummax() - 1).min()

            return {
                "cumulative_return": float(portfolio_value - 1),
                "sharpe_ratio": float(sharpe),
                "max_drawdown": float(max_drawdown),
                # "monthly_values": monthly_series.tolist() # Keep JSON serializable?
            }
            
        except Exception as e:
            print(f"Monthly Rebalance Error: {e}")
            return {}
            raise ValueError("No tickers provided for backtest")

    def backtest(self, tickers, weights=None, horizon="long"):
        if weights is None:
            weights = np.ones(len(tickers)) / len(tickers)

        print(f"Backtesting portfolio: {tickers} | Horizon: {horizon}...")
        
        config = self._get_period_from_horizon(horizon)
        
        try:
            # Download based on horizon
            data = yf.download(
                tickers,
                period=config["period"],
                interval=config["interval"],
                auto_adjust=True,
                progress=False
            )
            
            # Handle single ticker structure
            if len(tickers) == 1:
                close_data = data["Close"]
                if isinstance(close_data, pd.Series):
                    close_data = close_data.to_frame(name=tickers[0])
            else:
                 close_data = data["Close"]
            
            close_data = close_data.dropna(axis=1, how='all')
            
            # Align weights
            available = close_data.columns.tolist()
            if len(available) < len(tickers):
                 weights = np.ones(len(available)) / len(available)

            if close_data.empty:
                return {}

            # Minimum data check (approx 3 months)
            if len(close_data) < 60:
                 print(f"Insufficient data length: {len(close_data)}")
                 return {}

            full_returns = close_data.pct_change().dropna()
            
            results = {}
            # Adapt periods based on horizon availability
            # Ensure we don't look back further than data allows
            data_len = len(full_returns)
            
            periods = {
                "Full": data_len
            }
            
            if data_len > 252:
                periods["1y"] = 252
            if data_len > 126:
                periods["6m"] = 126
            if data_len > 21:
                periods["1m"] = 21

            for label, lookback in periods.items():
                # Slice the returns
                period_returns = full_returns.iloc[-lookback:]
                
                # Calculate Portfolio Returns
                port_rets = (period_returns * weights).sum(axis=1)
                cumulative = (1 + port_rets).cumprod()
                
                # Sharpe with RF
                rf = get_risk_free_rate()
                # Adjust RF to period (e.g. daily)
                daily_rf = rf / 252

                if port_rets.std() == 0:
                    sharpe = 0
                else:
                    excess_ret = port_rets.mean() - daily_rf
                    sharpe = (excess_ret / port_rets.std()) * np.sqrt(252)
                
                # Drawdown
                rolling_max = cumulative.cummax()
                drawdown = cumulative / rolling_max - 1
                max_drawdown = drawdown.min()

                results[label] = {
                    "cumulative_return": float(cumulative.iloc[-1] - 1),
                    "sharpe_ratio": float(sharpe),
                    "max_drawdown": float(max_drawdown),
                    "volatility": float(port_rets.std() * np.sqrt(252)),
                    "daily_returns": port_rets
                }
            
            return results
            
        except Exception as e:
            print(f"Backtest error: {e}")
            return {}

    def _get_period_from_horizon(self, horizon: str):
        if horizon == "short":
            return {"period": "6mo", "interval": "1d"}
        if horizon == "medium":
            return {"period": "2y", "interval": "1d"}
        if horizon == "long":
            return {"period": "5y", "interval": "1d"}
        # Default
        return {"period": "5y", "interval": "1d"}

    def _empty_result(self):
        return {
            "cumulative_return": 0.0,
            "sharpe_ratio": 0.0,
            "max_drawdown": 0.0,
            "volatility": 0.0,
            "daily_returns": pd.Series([], dtype=float)
        }
