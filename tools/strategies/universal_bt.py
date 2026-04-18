import vectorbt as vbt
import pandas_ta as ta


def run_universal_backtest(df, indicator_name: str, **params):
	"""
	Allows the Agent to perform a backtest on ANY indicator.
	Logic: Buys when the indicator crosses above a signal, sells when below.
	"""
	close = df["Close"]
	ind_func = getattr(ta, indicator_name)
	ind_data = ind_func(close, **params)

	entries = close > ind_data
	exits = close < ind_data

	pf = vbt.Portfolio.from_signals(close, entries, exits, fees=0.001, freq="1D")
	return pf.stats().to_dict()
