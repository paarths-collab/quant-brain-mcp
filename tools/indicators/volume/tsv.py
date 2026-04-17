import pandas_ta as ta


def get_tsv(df, length=13):
    """
    STRATEGY: Segments price/volume into specific time blocks to find accumulation.
    WHEN TO USE: Identifying institutional block buying.
    MARKET CONDITION: Range-bound markets before a massive surge.
    """
    res = ta.tsv(df["Close"], df["Volume"], length=length)
    return res.tail(10).to_dict()
