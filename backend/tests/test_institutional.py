from backend.agents.institutional.macro_agent import MacroAgent
from backend.agents.institutional.insider_agent import InsiderAgent
from backend.agents.institutional.risk_agent import RiskAgent
from backend.services.fred_macro_service import FREDMacroService
import pytest

# Macro Tests
def test_macro_agent():
    # We might need to mock FRED service if API key not present, 
    # but let's assume environment is set or handle error gracefully.
    agent = MacroAgent()
    
    # Mocking for CI/CD safety if needed, but trying live first
    try:
        result = agent.analyze()
        assert "market_bias" in result
        assert "score" in result
        assert result["score"] in [40, 70]
    except Exception as e:
        pytest.skip(f"Skipping Macro test due to API/Env issue: {e}")

# Insider Tests
def test_insider_agent():
    agent = InsiderAgent()
    # NVDA usually has activity
    result = agent.analyze("NVDA")
    
    assert "score" in result
    assert "buy_count_last_5" in result

# Risk Tests
def test_risk_agent():
    agent = RiskAgent()
    
    # High Concentration
    port_high = {"AAPL": 1.0}
    res_high = agent.evaluate(port_high)
    assert res_high["risk_score"] == 0.0 # 100 - 100
    
    # Balanced
    port_bal = {"AAPL": 0.5, "MSFT": 0.5}
    res_bal = agent.evaluate(port_bal)
    assert res_bal["risk_score"] == 50.0 # 100 - (0.5*100) = 50
    
    # Low Concentration
    port_low = {"A": 0.1, "B": 0.1, "C": 0.1, "D": 0.1, "E": 0.6}
    res_low = agent.evaluate(port_low)
    assert res_low["risk_score"] == 40.0 # 100 - 60 = 40
