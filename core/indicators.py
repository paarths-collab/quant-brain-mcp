import pandas_ta as ta
import pandas as pd


def apply_indicators(df: pd.DataFrame, indicator_list: list):
	"""
	Applies specific pandas-ta indicators to the dataframe.
	indicator_list: e.g., [{"kind": "rsi", "length": 14}, {"kind": "sma", "length": 50}]
	"""
	if "error" in df:
		return df

	# Custom Strategy setup for pandas-ta
	try:
		strategy = ta.Strategy(name="Custom Agent Strategy", ta=indicator_list)
		df.ta.strategy(strategy)
		# Return only the last 100 rows to the agent to keep context window clean
		# but the calculation is done on the full history.
		return df.tail(100).to_dict(orient="records")
	except Exception as e:
		return {"error": f"Error applying pandas-ta: {str(e)}"}
