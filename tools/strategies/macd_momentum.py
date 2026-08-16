import vectorbt as vbt
import pandas_ta as ta


def run_strategy(df):
    """
    STRATEGY: Uses MACD crossovers supported by EMA 200.
    WHEN TO USE: To ensure you are trading in the direction of the big trend.
    MARKET CONDITION: Sustained bull or bear markets.
    RISK: Late entries near cycle ends.
    """
    close = df["Close"]
    macd = ta.macd(close)
    ema200 = ta.ema(close, length=200)

    # ta.ema returns None (not NaN) when the series is shorter than the
    # lookback. `close > None` does not raise -- pandas silently broadcasts
    # it to all-False -- so entries would be unconditionally empty and the
    # backtest would report a confident-looking "0.00% return, 0 trades"
    # instead of surfacing that the strategy could not run at all.
    if ema200 is None or ema200.dropna().empty:
        return {
            "error": (
                f"Insufficient history for MACD Momentum: need at least 200 bars "
                f"for the EMA-200 trend filter, got {len(close)}."
            )
        }

    entries = (macd.iloc[:, 0] > macd.iloc[:, 2]) & (close > ema200)
    exits = macd.iloc[:, 0] < macd.iloc[:, 2]

    pf = vbt.Portfolio.from_signals(close, entries, exits, fees=0.001, freq="1D")
    stats = pf.stats()

    return {
        "strategy_name": "MACD Momentum",
        "win_rate": f"{stats['Win Rate [%]']:.2f}%",
        "total_return": f"{stats['Total Return [%]']:.2f}%",
        "sharpe_ratio": round(stats['Sharpe Ratio'], 2),
        "max_drawdown": f"{stats['Max Drawdown [%]']:.2f}%",
        "total_trades": stats['Total Trades'],
    }
