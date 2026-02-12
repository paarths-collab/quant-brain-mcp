import asyncio
import pytest
import pandas as pd

from backend.finverse_integration.agents.wealth_orchestrator import WealthOrchestrator
from backend.finverse_integration.routes.wealth_routes import map_wealth_state_to_response
from backend.finverse_integration.utils import guardrails as guardrails_module


class _DummyResp:
    def __init__(self, content: str):
        self.content = content


@pytest.fixture(autouse=True)
def _patch_external_deps(monkeypatch):
    # Patch Guardrails to always allow (avoid LLM calls)
    async def _allow(_self, _raw_input: str):
        return {"valid": True, "reason": "valid"}

    monkeypatch.setattr(guardrails_module.WealthGuardrails, "validate_input", _allow, raising=True)

    # Patch LLMManager.invoke to avoid external API calls
    def _fake_invoke(self, messages):
        # Detect structurer prompt vs report prompt
        content = " ".join([getattr(m, "content", "") for m in messages])
        if "financial profile analyzer" in content.lower():
            return _DummyResp(
                """{
                  "market": "US",
                  "financial_snapshot": {
                    "monthly_income": 8000,
                    "income_type": "recurring",
                    "savings": 50000,
                    "loans": [],
                    "monthly_expenses": 3000,
                    "investable_surplus": 2000
                  },
                  "preferences": {
                    "horizon": "long",
                    "risk_tolerance": "moderate",
                    "goals": ["retirement"]
                  }
                }"""
            )
        return _DummyResp(
            """# Investment Strategy Report

## Executive Summary
Based on your financial profile and investment goals, we recommend a diversified portfolio 
focused on long-term growth with moderate risk tolerance. Your monthly investable surplus 
of $2,000 combined with existing savings of $50,000 provides a strong foundation for 
retirement planning.

## Portfolio Strategy
- Technology sector: 30% allocation for growth potential
- Financials sector: 25% allocation for stability
- Healthcare sector: 20% allocation for defensive positioning
- Cash reserves: 25% for liquidity and opportunities

## Risk Assessment
Your moderate risk tolerance aligns well with a balanced approach combining growth and 
stability. This strategy aims to maximize long-term returns while maintaining downside protection.

## Next Steps
1. Review individual stock recommendations
2. Consider dollar-cost averaging for gradual market entry
3. Maintain emergency fund before investing
4. Rebalance quarterly to maintain target allocations
"""
        )

    monkeypatch.setattr("backend.finverse_integration.utils.llm_manager.LLMManager.invoke", _fake_invoke, raising=True)

    # Patch DuckDuckGo tool to avoid network calls
    def _fake_news(self, query: str, num_results: int = 8):
        return "Dummy macro news"

    monkeypatch.setattr("backend.tools.duckduckgo_mcp.DuckDuckGoMCPTool.news", _fake_news, raising=True)

    # Patch NewsFetcher methods
    def _fake_fetch_news(self, ticker: str, limit: int = 10):
        return []

    def _fake_category_news(self, category_query: str, limit: int = 5):
        return []

    monkeypatch.setattr("backend.finverse_integration.utils.news_fetcher.NewsFetcher.fetch_news", _fake_fetch_news, raising=True)
    monkeypatch.setattr("backend.finverse_integration.utils.news_fetcher.NewsFetcher.get_category_news", _fake_category_news, raising=True)

    # Patch yfinance for deterministic data
    class _DummyTicker:
        def __init__(self, _):
            self.fast_info = {
                "last_price": 150.0,
                "previous_close": 148.0,
                "market_cap": 2_000_000_000_000,
            }

    def _fake_ticker(symbol: str):
        return _DummyTicker(symbol)

    def _fake_download(*_args, **_kwargs):
        return pd.DataFrame(
            {
                "Close": [100.0, 101.0, 103.0, 104.0, 105.0],
            }
        )

    monkeypatch.setattr("yfinance.Ticker", _fake_ticker, raising=True)
    monkeypatch.setattr("yfinance.download", _fake_download, raising=True)


def test_investment_ai_workflow_smoke():
    orchestrator = WealthOrchestrator()
    result = asyncio.run(
        orchestrator.run_workflow(
            user_input="I earn $8000/month and want long-term investing.",
            market="US",
        )
    )

    assert result is not None
    assert result.get("user_profile") is not None
    assert result.get("selected_stocks") is not None
    assert result.get("allocation_strategy") is not None
    assert result.get("investment_report") is not None
    assert result.get("errors") == [] or result.get("errors") is None


def test_state_to_response_adapter():
    state = {
        "investment_report": "Report text",
        "allocation_strategy": {"AAPL": 0.3, "CASH": 0.7, "stocks": 0.3},
        "selected_stocks": [{"Ticker": "AAPL"}],
        "execution_log": ["ok"],
        "errors": [],
    }
    response = map_wealth_state_to_response(state)
    assert response["success"] is True
    assert response["report"] == "Report text"
    assert response["selected_stock"]["Ticker"] == "AAPL"


def test_investment_ai_stock_recommendations():
    """
    Test that Finverse Investment AI provides specific stock recommendations.
    This test verifies the complete workflow and checks for actionable output.
    """
    orchestrator = WealthOrchestrator()
    
    # Test with a realistic user input
    result = asyncio.run(
        orchestrator.run_workflow(
            user_input="I have $50,000 to invest, earn $8,000/month, spend $3,000/month, "
                      "and want to build a retirement portfolio with moderate risk tolerance "
                      "for long-term growth over 10+ years.",
            market="US",
        )
    )
    
    # Verify the workflow completed successfully
    assert result is not None, "Workflow should return a result"
    assert result.get("errors") in [[], None], f"Should have no errors, got: {result.get('errors')}"
    
    # Verify user profile was created
    user_profile = result.get("user_profile")
    assert user_profile is not None, "User profile should be created"
    assert "financial_snapshot" in user_profile, "Should have financial snapshot"
    assert "preferences" in user_profile, "Should have preferences"
    
    # Verify stock selection happened
    selected_stocks = result.get("selected_stocks")
    assert selected_stocks is not None, "Should have selected stocks"
    assert len(selected_stocks) > 0, "Should select at least one stock"
    
    # Verify each stock has required fields
    for stock in selected_stocks:
        assert "Ticker" in stock, f"Stock should have Ticker field: {stock}"
        assert isinstance(stock["Ticker"], str), "Ticker should be a string"
        assert len(stock["Ticker"]) > 0, "Ticker should not be empty"
    
    # Verify allocation strategy was created
    allocation = result.get("allocation_strategy")
    assert allocation is not None, "Should have allocation strategy"
    assert isinstance(allocation, dict), "Allocation should be a dictionary"
    
    # Verify stocks allocation makes sense
    if "stocks" in allocation:
        stocks_allocation = allocation["stocks"]
        assert 0 <= stocks_allocation <= 1, f"Stock allocation should be between 0-1, got {stocks_allocation}"
    
    # Verify individual stock allocations sum correctly
    stock_tickers = [s["Ticker"] for s in selected_stocks]
    total_stock_allocation = sum(allocation.get(ticker, 0) for ticker in stock_tickers)
    if total_stock_allocation > 0:
        assert total_stock_allocation <= 1.0, "Total stock allocation should not exceed 100%"
    
    # Verify investment report was generated
    report = result.get("investment_report")
    assert report is not None, "Should have investment report"
    assert isinstance(report, str), "Report should be a string"
    assert len(report) > 50, "Report should have substantial content"
    
    # Verify sectors were discovered
    sectors = result.get("top_sectors")
    assert sectors is not None, "Should discover sectors"
    
    # Verify risk profile was assessed
    risk_profile = result.get("risk_profile")
    assert risk_profile is not None, "Should have risk profile"
    
    # Print results for manual verification
    print("\n" + "="*80)
    print("FINVERSE INVESTMENT AI - TEST RESULTS")
    print("="*80)
    print(f"\n📊 STOCK RECOMMENDATIONS:")
    for i, stock in enumerate(selected_stocks, 1):
        ticker = stock.get("Ticker", "N/A")
        allocation_pct = allocation.get(ticker, 0) * 100
        print(f"  {i}. {ticker} - {allocation_pct:.1f}% allocation")
    
    print(f"\n💼 ALLOCATION STRATEGY:")
    for key, value in allocation.items():
        if key != "stocks":
            print(f"  {key}: {value * 100:.1f}%")
    
    print(f"\n🎯 RISK PROFILE:")
    print(f"  Risk Tolerance: {user_profile.get('preferences', {}).get('risk_tolerance', 'N/A')}")
    print(f"  Investment Horizon: {user_profile.get('preferences', {}).get('horizon', 'N/A')}")
    
    print(f"\n📈 TOP SECTORS:")
    if isinstance(sectors, list):
        for sector in sectors[:3]:
            print(f"  • {sector}")
    
    print(f"\n📝 INVESTMENT REPORT PREVIEW:")
    print(f"  {report[:200]}..." if len(report) > 200 else f"  {report}")
    print("\n" + "="*80)
    
    return result
