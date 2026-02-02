
import pytest
import pandas as pd
import numpy as np
from datetime import datetime
from backend.services.strategies.strategy_adapter import get_strategy, STRATEGY_REGISTRY

# --- Fixture for Basic OHLC Data ---
@pytest.fixture
def basic_ohlc_data():
    dates = pd.date_range(start="2023-01-01", periods=100, freq="D")
    data = pd.DataFrame({
        "Open": np.linspace(100, 200, 100),
        "High": np.linspace(105, 205, 100),
        "Low": np.linspace(95, 195, 100),
        "Close": np.linspace(102, 198, 100),  # General uptrend
        "Volume": np.random.randint(1000, 5000, 100)
    }, index=dates)
    return data

@pytest.fixture
def pairs_trading_data():
    dates = pd.date_range(start="2023-01-01", periods=100, freq="D")
    # Asset 1 and Asset 2 moving together
    asset1 = np.linspace(100, 110, 100) + np.random.normal(0, 1, 100)
    asset2 = asset1 * 0.5 + np.random.normal(0, 0.5, 100) + 10 # Correlated
    
    data = pd.DataFrame({
        "Asset1": asset1,
        "Asset2": asset2
    }, index=dates)
    return data

# --- Parametrized Test for Standard Single-Asset Strategies ---
@pytest.mark.parametrize("strategy_name", [
    "sma_crossover",
    "ema_crossover",
    "macd",
    "rsi_reversal",
    "rsi_momentum",
    "momentum",
    "mean_reversion",
    "breakout",
    "fibonacci_pullback",
    "support_resistance",
    "channel_trading"
])
def test_single_asset_strategies(strategy_name, basic_ohlc_data):
    """
    Test that all single-asset strategies can be instantiated and 
    generate signals with the correct returns structure.
    """
    try:
        strategy = get_strategy(strategy_name)
        result = strategy.generate_signals(basic_ohlc_data)
        
        # 1. Check return type
        assert isinstance(result, pd.DataFrame), f"{strategy_name} did not return a DataFrame"
        
        # 2. Check essential columns exist
        required_cols = ["signal", "entry_long", "entry_short"]
        for col in required_cols:
            assert col in result.columns, f"{strategy_name} is missing column: {col}"
            
        # 3. Check signal values are valid (-1, 0, 1)
        valid_signals = {-1, 0, 1}
        unique_signals = set(result["signal"].unique())
        assert unique_signals.issubset(valid_signals), f"{strategy_name} produced invalid signals: {unique_signals}"
        
        # 4. Check data integrity (length shouldn't change generally, unless specified)
        assert len(result) == len(basic_ohlc_data), f"{strategy_name} changed row count"

    except Exception as e:
        pytest.fail(f"Strategy '{strategy_name}' failed with error: {str(e)}")


def test_pairs_trading_strategy(pairs_trading_data):
    """
    Test the unique Pairs Trading strategy which requires 2 input columns.
    """
    strategy_name = "pairs_trading"
    try:
        strategy = get_strategy(strategy_name)
        result = strategy.generate_signals(pairs_trading_data)
        
        assert isinstance(result, pd.DataFrame)
        assert "signal" in result.columns
        assert "spread" in result.columns
        assert "zscore" in result.columns
        assert "beta" in result.attrs
        
        # Check signal generation logic
        unique_signals = set(result["signal"].unique())
        assert unique_signals.issubset({-1, 0, 1})

    except Exception as e:
        pytest.fail(f"Strategy '{strategy_name}' failed with error: {str(e)}")

def test_strategy_parameter_passing(basic_ohlc_data):
    """
    Verify that parameters passed to get_strategy are correctly set on the instance.
    """
    # Test SMA Crossover with custom windows
    strategy = get_strategy("sma_crossover", short_window=10, long_window=30)
    assert strategy.short_window == 10
    assert strategy.long_window == 30
    
    # Run to ensure custom params actually work in calculation
    result = strategy.generate_signals(basic_ohlc_data)
    assert "sma_short" in result.columns

def test_invalid_strategy_name():
    """
    Ensure the registry raises an error for unknown strategies.
    """
    with pytest.raises(ValueError, match="not registered"):
        get_strategy("non_existent_strategy")

