import pandas_ta as ta


def get_pdist(df):
    """
    STRATEGY: Measures the distance price has moved.
    WHEN TO USE: Identifying price momentum via distance.
    MARKET CONDITION: High-intensity trending markets.
    """
    res = ta.pdist(df["Open"], df["High"], df["Low"], df["Close"])
    return res.tail(10).to_dict()
