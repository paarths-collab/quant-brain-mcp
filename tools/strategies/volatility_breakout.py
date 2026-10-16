import vectorbt as vbt

from tools.strategies._common import history_error, pct, positive_int, ratio


def run_backtest(df, length=20):
	"""Vectorized backtest for a Donchian-style volatility breakout."""
	length = positive_int("length", length)
	close = df["Close"]
	error = history_error(close, max(length, 10) + 1, "Volatility Breakout")
	if error:
		return error
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
		"total_return": pct(stats['Total Return [%]']),
		"sharpe_ratio": ratio(stats['Sharpe Ratio']),
		"win_rate": pct(stats['Win Rate [%]']),
		"max_drawdown": pct(stats['Max Drawdown [%]']),
		"profit_factor": ratio(stats['Profit Factor']),
	}
