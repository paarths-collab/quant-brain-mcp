import vectorbt as vbt


def run_backtest(df, length=20):
	"""Vectorized backtest for a Donchian-style volatility breakout."""
	close = df["Close"]
	high = df["High"]
	low = df["Low"]

	upper_band = high.rolling(window=length).max().shift(1)
	lower_exit = low.rolling(window=10).min().shift(1)

	entries = close > upper_band
	exits = close < lower_exit

	pf = vbt.Portfolio.from_signals(close, entries, exits, fees=0.001, freq="1D")
	stats = pf.stats()

	return {
		"strategy_name": "Volatility Breakout",
		"total_return": f"{stats['Total Return [%]']:.2f}%",
		"sharpe_ratio": round(stats['Sharpe Ratio'], 2),
		"win_rate": f"{stats['Win Rate [%]']:.2f}%",
		"max_drawdown": f"{stats['Max Drawdown [%]']:.2f}%",
		"profit_factor": round(stats['Profit Factor'], 2),
	}
