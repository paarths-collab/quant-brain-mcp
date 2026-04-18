import warnings

import yfinance as yf
import pandas as pd


warnings.filterwarnings(
	"ignore",
	message=r"YF\.download\(\) has changed argument auto_adjust default to True",
	category=UserWarning,
)


def fetch_stock_data(ticker: str, period: str = "2y", interval: str = "1d"):
	"""
	Fetches data from yfinance.
	Handles US stocks (AAPL) and Indian stocks (RELIANCE.NS).
	"""
	try:
		# Standardize ticker: if it's a common Indian name without suffix,
		# we can't guess .NS or .BO, so we rely on the Agent/User to provide it.
		# But we will strip whitespace and uppercase it.
		ticker = ticker.strip().upper()

		data = yf.download(
			ticker,
			period=period,
			interval=interval,
			progress=False,
			auto_adjust=False,
		)

		if data.empty:
			return {
				"error": f"No data found for ticker '{ticker}'. Check if the symbol is correct (e.g., .NS for Indian stocks)."
			}

		# Ensure column names are clean (yfinance sometimes returns MultiIndex)
		if isinstance(data.columns, pd.MultiIndex):
			data.columns = data.columns.get_level_values(0)

		return data
	except Exception as e:
		return {"error": f"Failed to fetch data for {ticker}: {str(e)}"}


def fetch_multi_data(tickers: list, period: str = "2y"):
	"""Fetches multiple tickers for portfolio optimization."""
	try:
		data = yf.download(tickers, period=period, progress=False, auto_adjust=False)["Close"]
		if data.empty:
			return {"error": "No data found for the provided list of tickers."}
		return data
	except Exception as e:
		return {"error": str(e)}


def fetch_data(ticker: str, period: str = "2y", interval: str = "1d"):
	"""Fetches data and auto-tries .NS for unsuffixed Indian tickers.

	Returns tuple: (dataframe_or_none, error_or_none)
	"""
	ticker = ticker.strip().upper()
	df = fetch_stock_data(ticker, period=period, interval=interval)
	if isinstance(df, dict) and "error" in df:
		if not ticker.endswith((".NS", ".BO")):
			indian_ticker = f"{ticker}.NS"
			df2 = fetch_stock_data(indian_ticker, period=period, interval=interval)
			if not isinstance(df2, dict):
				return df2, None
		return None, df["error"]
	return df, None
