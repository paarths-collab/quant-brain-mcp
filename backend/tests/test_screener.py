from backend.agents.screener_agent import ScreenerAgent
from backend.services.ticker_extractor import TickerExtractor
import pytest

def test_ticker_extractor():
    ext = TickerExtractor()
    text = "I like AAPL and MSFT but not THE or AND."
    tickers = ext.extract(text)
    
    assert "AAPL" in tickers
    assert "MSFT" in tickers
    assert "THE" not in tickers

# Integration test (requires internet)
def test_screener_agent():
    agent = ScreenerAgent()
    results = agent.discover_ai_stocks()
    
    assert isinstance(results, list)
    # Note: Results might be empty if search finding no tickers or market data fails, 
    # but the structure should be a list.
    if len(results) > 0:
        assert "ticker" in results[0]
        assert "score" in results[0]
