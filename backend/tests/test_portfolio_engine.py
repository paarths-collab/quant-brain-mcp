import pandas as pd
from backend.services.portfolio_engine import combine_equity_curves

def test_portfolio_engine():
    dates = pd.date_range("2024-01-01", periods=5)

    ema_equity = pd.Series(
        [100000, 101000, 102000, 101500, 103000],
        index=dates
    )

    rsi_equity = pd.Series(
        [100000, 100500, 101200, 101800, 102500],
        index=dates
    )

    equity_curves = {
        "ema": ema_equity,
        "rsi": rsi_equity
    }

    weights = {
        "ema": 0.6,
        "rsi": 0.4
    }

    portfolio_df = combine_equity_curves(
        equity_curves=equity_curves,
        weights=weights,
        initial_capital=100000
    )

    print("\n✅ Portfolio Engine Output:")
    print(portfolio_df)

if __name__ == "__main__":
    test_portfolio_engine()
