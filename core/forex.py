import yfinance as yf
import pandas as pd


def get_conversion_rate():
	"""Fetches current USD/INR rate to normalize portfolios."""
	ticker = "USDINR=X"
	data = yf.download(ticker, period="1d", progress=False)
	rate = data["Close"].iloc[-1]
	# Fix if it's a pandas Series
	if isinstance(rate, pd.Series):
		rate = rate.iloc[0]
	return float(rate)


def normalize_prices(price_df):
	"""Converts all Indian stock prices (.NS) into USD equivalents."""
	rate = get_conversion_rate()
	for col in price_df.columns:
		if ".NS" in col or ".BO" in col:
			price_df[col] = price_df[col] / rate
	return price_df
