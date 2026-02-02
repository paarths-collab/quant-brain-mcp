"""
Master integration test for long-term investment strategies.

Run with:
    python -m backend.tests.test_long_term_strategies
"""

from pprint import pprint

from backend.services.data_loader import get_history
from backend.services.long_term_strategy import (
    run_long_term_dca,
    run_dividend_strategy,
    run_growth_strategy,
    run_value_strategy,
    run_index_strategy,
    run_long_term_strategy,
)

# ------------------------------------------------
# CONFIG
# ------------------------------------------------
START = "2015-01-01"
END = "2024-01-01"

US_STOCK = "AAPL"
US_DIVIDEND = "KO"
US_GROWTH = "NVDA"
US_VALUE = "MSFT"
US_ETF = "SPY"

IN_STOCK = "TCS"

# ------------------------------------------------
# HELPERS
# ------------------------------------------------

def print_section(title: str):
    print("\n" + "=" * 60)
    print(f"✅ {title}")
    print("=" * 60)


# ------------------------------------------------
# TESTS
# ------------------------------------------------

def test_data_loader():
    print_section("DATA LOADER")

    df_us = get_history(US_STOCK, START, END, market="US")
    assert not df_us.empty, "US data loader failed"
    print("US data OK")

    df_in = get_history(IN_STOCK, START, END, market="IN")
    assert not df_in.empty, "IN data loader failed"
    print("IN data OK")


def test_dca():
    print_section("DCA STRATEGY")

    result = run_long_term_dca(
        ticker="VOO",
        start_date=START,
        end_date=END,
        market="US",
        monthly_investment=1000,
    )

    assert isinstance(result, dict), "DCA did not return dict"
    pprint(result)


def test_dividend():
    print_section("DIVIDEND STRATEGY")

    result = run_dividend_strategy(
        ticker=US_DIVIDEND,
        start=START,
        end=END,
        market="US",
    )

    assert isinstance(result, dict), "Dividend strategy failed"
    pprint(result)


def test_growth():
    print_section("GROWTH STRATEGY")

    result = run_growth_strategy(
        ticker=US_GROWTH,
        start=START,
        end=END,
        market="US",
    )

    assert isinstance(result, dict), "Growth strategy failed"
    pprint(result)


def test_value():
    print_section("VALUE STRATEGY")

    result = run_value_strategy(
        ticker=US_VALUE,
        start=START,
        end=END,
        market="US",
    )

    assert isinstance(result, dict), "Value strategy failed"
    pprint(result)


def test_index_etf():
    print_section("INDEX / ETF STRATEGY")

    result = run_index_strategy(
        ticker=US_ETF,
        start=START,
        end=END,
        market="US",
    )

    assert isinstance(result, dict), "Index strategy failed"
    pprint(result)


def test_capital_preservation_profile():
    print_section("CAPITAL PRESERVATION PROFILE")

    result = run_long_term_strategy(
        ticker="SPY",
        start="2018-01-01",
        end="2024-01-01",
        market="US",
        capital=100000,
        risk_profile="capital_preservation",
        monthly_investment=1000
    )

    strategies = result["metadata"]["strategy_weights"]
    
    # Assertions based on "capital_preservation" profile in risk_profiles.py
    # NOTE: The user provided code assumes specific allocations.
    # checking risk_profiles.py again to ensure values match assertions.
    # "capital_preservation": strategy_allocation={ "dca": 0.40, "dividend": 0.35, "index": 0.25, ... }
    
    print("Strategy Weights:", strategies)

    assert "growth" not in strategies
    assert "value" not in strategies
    assert "dca" in strategies
    assert abs(sum(strategies.values()) - 1.0) < 0.0001


# ------------------------------------------------
# RUNNER
# ------------------------------------------------

if __name__ == "__main__":
    test_data_loader()
    test_dca()
    test_dividend()
    test_growth()
    test_value()
    test_index_etf()
    test_capital_preservation_profile()

    print("\n🎯 ALL LONG-TERM STRATEGY TESTS PASSED")
