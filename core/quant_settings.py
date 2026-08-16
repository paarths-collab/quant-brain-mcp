"""Global quant conventions applied once at process start.

Importing this module configures vectorbt to annualize with 252 trading days
rather than its 365-calendar-day default. With daily equity bars there are
~252 observations per year, so the default inflates every annualized figure
(Sharpe, Calmar, volatility) by sqrt(365/252) = 1.2035x.

That matters beyond cosmetics: `run_generate_optimized_verdict` gates its
verdict on `actual_sharpe > 1.2` / `> 0.7`, so an inflated Sharpe silently
promotes portfolios into stronger verdicts than the data supports.
"""

from __future__ import annotations

TRADING_DAYS_PER_YEAR = 252


def apply() -> None:
    """Set annualization to a 252-day trading year. Safe to call repeatedly."""
    try:
        import vectorbt as vbt

        vbt.settings["returns"]["year_freq"] = f"{TRADING_DAYS_PER_YEAR} days"
    except Exception:
        # Never let a settings tweak break server startup.
        pass


apply()
