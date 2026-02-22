import pytest
import numpy as np
import pandas as pd
from unittest.mock import MagicMock, patch
from backend.quant.risk_models import RiskModels
from backend.quant.stress_testing import StressTesting

# Mock Data
@pytest.fixture
def mock_ticker_data():
    dates = pd.date_range(start="2023-01-01", periods=100)
    # Generate random returns
    np.random.seed(42)
    prices = 100 * (1 + np.random.normal(0.001, 0.02, 100)).cumprod()
    df = pd.DataFrame({"Close": prices}, index=dates)
    return df

class TestRiskModels:
    
    @patch("yfinance.Ticker")
    def test_calculate_var(self, mock_ticker, mock_ticker_data):
        # Setup mock
        mock_instance = MagicMock()
        mock_instance.history.return_value = mock_ticker_data
        mock_ticker.return_value = mock_instance
        
        models = RiskModels()
        var = models.calculate_var("FAKE", confidence=0.95)
        
        # Check output type and logical range
        assert isinstance(var, float)
        assert var < 0 # VaR is typically negative logic (loss) or returns a negative number like -0.03
        
        # Verify calculation manually-ish (5th percentile)
        returns = mock_ticker_data["Close"].pct_change().dropna()
        expected = np.percentile(returns, 5) 
        assert abs(var - expected) < 1e-6

    @patch("yfinance.Ticker")
    def test_max_drawdown(self, mock_ticker, mock_ticker_data):
        mock_instance = MagicMock()
        mock_instance.history.return_value = mock_ticker_data
        mock_ticker.return_value = mock_instance
        
        models = RiskModels()
        mdd = models.max_drawdown("FAKE")
        
        assert isinstance(mdd, float)
        assert mdd <= 0

class TestStressTesting:
    
    def test_simulate_crash(self):
        stress = StressTesting()
        price = 100.0
        
        res = stress.simulate_crash(price, crash_percent=0.20)
        
        assert res["original_price"] == 100.0
        assert res["stressed_price"] == 80.0
        assert res["loss"] == 20.0
        assert res["crash_percent"] == 20.0
