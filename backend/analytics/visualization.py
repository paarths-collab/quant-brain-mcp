import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns # Optional but nice, falling back to pure plt if needed

class PortfolioVisualizer:

    def __init__(self):
        # Set style
        plt.style.use('bmh') 

    def _add_gist(self, text):
        """Adds a explanatory footer to the chart."""
        plt.subplots_adjust(bottom=0.2) # Make room
        plt.figtext(
            0.5, 0.05, 
            f"ANALYSIS: {text}", 
            ha="center", 
            fontsize=10, 
            style='italic',
            bbox={"facecolor":"orange", "alpha":0.1, "pad":5},
            wrap=True
        )

    def plot_equity_and_drawdown(self, portfolio_values):
        if portfolio_values is None:
            return

        # Ensure numeric pandas series
        if isinstance(portfolio_values, list):
            portfolio_values = pd.Series(portfolio_values)
        if len(portfolio_values) == 0:
            return
            
        drawdown = portfolio_values / portfolio_values.cummax() - 1

        fig, ax = plt.subplots(2, 1, figsize=(10, 8), sharex=True)

        ax[0].plot(portfolio_values, label="Equity Curve")
        ax[0].set_title("Portfolio Equity Curve")
        ax[0].legend()
        ax[0].grid(True)

        ax[1].plot(drawdown, color="red", label="Drawdown", alpha=0.6)
        ax[1].fill_between(drawdown.index, drawdown, color="red", alpha=0.1)
        ax[1].set_title("Drawdown")
        ax[1].legend()
        ax[1].grid(True)

        
        total_ret = (portfolio_values.iloc[-1] / portfolio_values.iloc[0]) - 1
        max_dd = drawdown.min()
        
        action = "Consider hedging or reducing size." if max_dd < -0.15 else "Drawdown acceptable. Hold."
        
        self._add_gist(f"ANALYSIS: Total Return: {total_ret:.1%}. Max Drawdown: {max_dd:.1%}. {action}")

        plt.show(block=False)
        plt.pause(0.1)

    def plot_rolling_sharpe(self, returns, rf=0.04):
        if returns is None or returns.empty:
            return

        window = 63  # 3 months ~ 63 days
        # Adjust RF to daily
        daily_rf = rf/252
        
        excess = returns - daily_rf
        
        # Calculate Rolling Sharpe
        rolling_mean = excess.rolling(window).mean()
        rolling_std = excess.rolling(window).std()
        
        rolling_sharpe = (rolling_mean / rolling_std) * np.sqrt(252)

        plt.figure(figsize=(10,5))
        
        if isinstance(returns, pd.DataFrame):
            for col in returns.columns[:5]: # Limit to top 5
                plt.plot(rolling_sharpe[col], label=col, alpha=0.7)
            plt.legend()
        else:
             plt.plot(rolling_sharpe, label="Portfolio")

        plt.title(f"Rolling Sharpe Ratio ({window} Days)")
        plt.axhline(0, linestyle="--", color="black", alpha=0.5)
        plt.ylabel("Sharpe Ratio")
        
        # Stats
        if isinstance(rolling_sharpe, pd.DataFrame):
            # Take mean of columns for stats
            avg_sharpe = rolling_sharpe.mean().mean()
            curr_sharpe = rolling_sharpe.iloc[-1].mean()
        else:
            avg_sharpe = rolling_sharpe.mean()
            curr_sharpe = rolling_sharpe.iloc[-1]
            
        trend = "Improving" if curr_sharpe > avg_sharpe else "Declining"
        action = "Review strategy logic." if curr_sharpe < 1.0 or trend == "Declining" else "Strategy healthy. Maintain."

        self._add_gist(f"ANALYSIS: Avg Sharpe: {avg_sharpe:.2f}. Current: {curr_sharpe:.2f} ({trend}). {action}")

        plt.show(block=False)
        plt.pause(0.1)

    def plot_efficient_frontier(self, returns):
        if returns is None or returns.empty or len(returns.columns) < 2:
            return

        mean = returns.mean() * 252
        cov = returns.cov() * 252
        
        num_assets = len(returns.columns)
        results = []

        for _ in range(2000): # 2000 sims
            w = np.random.random(num_assets)
            w /= w.sum()

            ret = np.dot(w, mean)
            vol = np.sqrt(w @ cov @ w)

            results.append((vol, ret))

        vols, rets = zip(*results)
        sharpes = np.array(rets)/np.array(vols)

        plt.figure(figsize=(8,6))
        plt.scatter(vols, rets, c=sharpes, cmap='viridis', marker='.', alpha=0.5)
        plt.colorbar(label='Sharpe Ratio')
        plt.xlabel("Volatility (Risk)")
        plt.ylabel("Expected Return")
        plt.title("Efficient Frontier (Monte Carlo Simulation)")
        
        vols, rets = zip(*results)
        sharpes = np.array(rets)/np.array(vols)
        
        # Find best
        max_idx = np.argmax(sharpes)
        best_s = sharpes[max_idx]
        best_r = rets[max_idx]
        best_v = vols[max_idx]

        plt.figure(figsize=(8,6))
        plt.scatter(vols, rets, c=sharpes, cmap='viridis', marker='.', alpha=0.5)
        plt.colorbar(label='Sharpe Ratio')
        plt.xlabel("Volatility (Risk)")
        plt.ylabel("Expected Return")
        plt.title("Efficient Frontier (Monte Carlo Simulation)")
        
        # Plot star
        plt.scatter(best_v, best_r, color='red', marker='*', s=200, label=f"Max Sharpe ({best_s:.2f})")
        plt.legend()
        
        self._add_gist(f"ANALYSIS: Max Potential Sharpe: {best_s:.2f}. ACTION: Target these optimal weights to maximize efficiency.")

        plt.show(block=False)
        plt.pause(0.1)

    def plot_monte_carlo_distribution(self, simulation_results):
        if simulation_results is None:
            return

        # simulation_results could be dict with 'distribution' or list
        if isinstance(simulation_results, dict) and 'distribution' in simulation_results:
             vals = simulation_results['distribution']
        elif isinstance(simulation_results, list):
             vals = simulation_results
        else:
             vals = simulation_results

        plt.figure(figsize=(8,5))
        plt.hist(vals, bins=50, alpha=0.7, color='steelblue', edgecolor='black')
        plt.title("Monte Carlo Return Distribution (1 Year)")
        
        
        var_5 = np.percentile(vals, 5)
        mean_val = np.mean(vals)
        
        plt.axvline(var_5, color="red", linestyle="--", label=f"5% VaR: {var_5:.1%}")
        plt.legend()
        
        action = "Heavy tail risk. Cushion with cash." if var_5 < -0.10 else "Risk within normal limits."
        
        self._add_gist(f"ANALYSIS: Expected Return: {mean_val:.1%}. Worst Case (VaR 95%): {var_5:.1%}. {action}")

        plt.show(block=False)
        plt.pause(0.1)

    def plot_monte_carlo_paths(self, paths):
        if paths is None or len(paths) == 0:
            return
            
        plt.figure(figsize=(10,6))
        
        limit = min(len(paths), 50) # Plot max 50 paths
        for path in paths[:limit]:
            if isinstance(path, (list, np.ndarray)):
                 cumulative = np.cumprod(1 + np.array(path)) - 1
                 plt.plot(cumulative, alpha=0.2, color='blue')

        plt.title(f"Monte Carlo Simulated Paths ({limit} samples)")
        plt.ylabel("Cumulative Return")
        plt.xlabel("Days")
        

        plt.title(f"Monte Carlo Simulated Paths ({limit} samples)")
        plt.ylabel("Cumulative Return")
        plt.xlabel("Days")
        
        # Calc spread
        final_values = [np.prod(1+np.array(p))-1 for p in paths[:limit] if isinstance(p, (list, np.ndarray))]
        if final_values:
            spread_min = min(final_values)
            spread_max = max(final_values)
            spread_range = spread_max - spread_min
            action = "High uncertainty. Reduce position size." if spread_range > 0.5 else "Outlook stable."
            self._add_gist(f"ANALYSIS: Outcomes range from {spread_min:.1%} to {spread_max:.1%}. {action}")
        else:
            self._add_gist("Visualizing the 'Multiverse' of your portfolio. Flatter clusters = predictable. Wild spreads = high uncertainty.")

        plt.show(block=False)
        plt.pause(0.1)

    def plot_regimes(self, returns, regimes):
        if returns is None or returns.empty or not regimes:
            return
            
        # If returns is DF, take mean
        if isinstance(returns, pd.DataFrame):
             market_ret = returns.mean(axis=1) * 100 # Percent
        else:
             market_ret = returns * 100

        # Create DataFrame
        df = pd.DataFrame({'Return': market_ret, 'Regime': regimes}, index=returns.index[-len(regimes):])
        
        plt.figure(figsize=(10,6))
        
        # Scatter plot colored by regime
        sns.scatterplot(data=df, x=df.index, y='Return', hue='Regime', palette='coolwarm', s=20)
        
        plt.title("Market Regimes (HMM Classification)")
        plt.ylabel("Daily Return %")
        

        
        current_state = regimes[-1]
        state_desc = "Low Volatility / Bullish" if current_state == 0 else "High Volatility / Bearish" # Heuristic
        action = "Defensive mode. Hedge or reduce beta." if current_state == 1 else "Aggressive mode. Buy dips."
        
        self._add_gist(f"ANALYSIS: Current Regime: {current_state} ({state_desc}). ACTION: {action}")

        plt.show(block=False)
        plt.pause(0.1)

    def plot_walk_forward(self, walk_forward_results):
        if not walk_forward_results or "walk_forward_returns" not in walk_forward_results:
            return
            
        wf_returns = walk_forward_results["walk_forward_returns"]
        cumulative = np.cumsum(wf_returns)

        plt.figure(figsize=(8,5))
        plt.plot(cumulative, marker='o', linestyle='-')
        plt.title("Walk-Forward Test: Cumulative Profit")
        plt.ylabel("Cumulative Return")
        plt.xlabel("Test Folding Step")
        plt.grid(True)
        

        
        final_ret = cumulative[-1]
        action = "Strategy robust. Approved for deployment." if final_ret > 0 else "Strategy failing validation. Do not deploy."
        self._add_gist(f"ANALYSIS: 'Time Travel' Result: {final_ret:.1%} Return. ACTION: {action}")

        plt.show(block=False)
        plt.pause(0.1)

    def plot_cvar(self, portfolio_returns, alpha=0.05):
        if portfolio_returns is None or len(portfolio_returns) == 0:
            return
            
        vals = np.array(portfolio_returns)
        var = np.percentile(vals, alpha*100)
        cvar = vals[vals <= var].mean()

        plt.figure(figsize=(8,5))
        sns.histplot(vals, bins=50, kde=True, color='purple', alpha=0.4)
        plt.axvline(var, color="red", linestyle="--", label=f"VaR ({alpha:.0%}): {var:.2%}")
        plt.axvline(cvar, color="black", linestyle="-", linewidth=2, label=f"CVaR: {cvar:.2%}")
        plt.legend()

        
        plt.title(f"Tail Risk Analysis (VaR & CVaR)")
        
        action = "Extreme crash risk. Buy put protection." if cvar < -0.15 else "Tail risk managed."
        self._add_gist(f"ANALYSIS: CVaR (Avg Crash Loss): {cvar:.2%}. ACTION: {action}")

        plt.show(block=False)
        plt.pause(0.1)

    def plot_bayesian_fan(self, simulations):
        if simulations is None or len(simulations) == 0:
             return
             
        # simulations: list of arrays (cumulative paths)
        # Convert to 2D array: (Sims, Days)
        sim_array = np.array(simulations)
        
        if sim_array.ndim != 2:
             return

        percentiles = np.percentile(sim_array, [5, 25, 50, 75, 95], axis=0)

        plt.figure(figsize=(10,6))
        x = range(len(percentiles[0]))
        
        plt.fill_between(x, percentiles[0], percentiles[4], color='blue', alpha=0.1, label="5-95% CI")
        plt.fill_between(x, percentiles[1], percentiles[3], color='blue', alpha=0.2, label="25-75% CI")
        plt.plot(percentiles[2], color="black", linewidth=1.5, label="Median")
        
        plt.title("Bayesian Monte Carlo Fan Chart")
        plt.xlabel("Days")
        plt.ylabel("Cumulative Return")

        
        plt.legend(loc="upper left")
        
        low_bound = percentiles[0][-1] # 5th pct final
        high_bound = percentiles[4][-1] # 95th pct final
        width = high_bound - low_bound
        
        action = "Parameters uncertain. Use smaller size." if width > 0.5 else "Model confidence high."
        
        self._add_gist(f"ANALYSIS: 90% CI Width: {width:.1%}. ACTION: {action}")

        plt.show(block=False)
        plt.pause(0.1)
