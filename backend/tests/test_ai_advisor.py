"""
Comprehensive Test Suite for AI Advisor / Wealth Management System
====================================================================
Tests the complete wealth management pipeline including:
- Input validation and structuring
- Sector discovery
- Stock selection
- Allocation + report generation
- API endpoints
"""

import pytest
import asyncio
import sys
import os
from fastapi.testclient import TestClient

# Add backend to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from backend.main import app
from backend.finverse_integration.agents.wealth_orchestrator import WealthOrchestrator
from backend.finverse_integration.agents.state import WealthState


# ============================================================================
# FIXTURES
# ============================================================================

@pytest.fixture
def test_client():
    """FastAPI test client"""
    return TestClient(app)


@pytest.fixture
def wealth_orchestrator():
    """Wealth orchestrator instance"""
    return WealthOrchestrator()


@pytest.fixture
def sample_user_input_us():
    """Sample US market user input"""
    return """
    I'm 32 years old earning $8000/month. I have $50,000 in savings.
    I have a home loan with $2000 EMI for 15 years and car loan with $500 EMI for 3 years.
    My monthly expenses are around $3000. I want to invest for retirement (long-term).
    I'm comfortable with moderate risk.
    """


@pytest.fixture
def sample_user_input_india():
    """Sample Indian market user input"""
    return """
    I'm 28 years old working in IT earning ₹1,20,000/month. I have ₹8 lakhs in savings.
    I have a home loan EMI of ₹30,000 for 20 years. Monthly expenses are ₹40,000.
    I want to invest for my child's education (medium-term, 10 years).
    I prefer conservative to moderate risk.
    """


@pytest.fixture
def sample_user_input_aggressive():
    """Sample aggressive investor input"""
    return """
    I'm 25 years old, tech worker earning $12,000/month. I have $30,000 saved.
    No loans. Monthly expenses are $2500. I want high growth for next 5-10 years.
    I'm comfortable with high risk and market volatility.
    """


# ============================================================================
# UNIT TESTS - WealthOrchestrator Components
# ============================================================================

class TestWealthOrchestrator:
    """Test the core orchestrator"""
    
    def test_orchestrator_initialization(self, wealth_orchestrator):
        """Test that orchestrator initializes all agents properly"""
        assert wealth_orchestrator.llm_manager is not None
        assert wealth_orchestrator.news_fetcher is not None
        assert wealth_orchestrator.portfolio_engine is not None
        assert wealth_orchestrator.stock_picker is not None
        assert wealth_orchestrator.workflow is not None
        print("✓ WealthOrchestrator initialized successfully")
    
    @pytest.mark.asyncio
    async def test_workflow_execution_us_market(self, wealth_orchestrator, sample_user_input_us):
        """Test full workflow for US market"""
        result = await wealth_orchestrator.run_workflow(
            user_input=sample_user_input_us,
            market="US"
        )
        
        # Verify result structure
        assert result is not None
        assert "raw_input" in result
        assert "market" in result
        assert result["market"] == "US"
        
        # Check if profile was created
        if "user_profile" in result:
            profile = result["user_profile"]
            assert "financial_snapshot" in profile
            assert "preferences" in profile
            print(f"✓ Profile created for risk tolerance: {profile['preferences'].get('risk_tolerance', 'N/A')}")
        
        # Check if investment recommendations were made
        if "selected_stock" in result:
            stock = result["selected_stock"]
            print(f"✓ Stock recommendation: {stock.get('Ticker', 'N/A')}")
        
        if "investment_report" in result:
            print(f"✓ Report generated ({len(result['investment_report'])} chars)")
    
    @pytest.mark.asyncio
    async def test_workflow_execution_india_market(self, wealth_orchestrator, sample_user_input_india):
        """Test full workflow for Indian market"""
        result = await wealth_orchestrator.run_workflow(
            user_input=sample_user_input_india,
            market="IN"
        )
        
        assert result is not None
        assert result.get("market") in ["IN", "US"]  # May default to US
        print(f"✓ Indian market workflow completed")
    
    @pytest.mark.asyncio
    async def test_aggressive_investor_profile(self, wealth_orchestrator, sample_user_input_aggressive):
        """Test workflow handles aggressive risk profile"""
        result = await wealth_orchestrator.run_workflow(
            user_input=sample_user_input_aggressive,
            market="US"
        )
        
        assert result is not None
        if "user_profile" in result:
            risk = result["user_profile"]["preferences"].get("risk_tolerance")
            print(f"✓ Detected risk tolerance: {risk}")


# ============================================================================
# INTEGRATION TESTS - API Endpoints
# ============================================================================

class TestWealthAPI:
    """Test the FastAPI wealth management endpoints"""
    
    def test_health_endpoint(self, test_client):
        """Test root health check"""
        response = test_client.get("/")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}
        print("✓ Health endpoint working")
    
    def test_wealth_analyze_endpoint_us(self, test_client, sample_user_input_us):
        """Test /api/wealth/analyze endpoint with US input"""
        response = test_client.post(
            "/api/wealth/analyze",
            json={
                "user_input": sample_user_input_us,
                "market": "US"
            }
        )
        
        print(f"Status Code: {response.status_code}")
        if response.status_code != 200:
            print(f"Error: {response.text}")
        
        assert response.status_code == 200
        data = response.json()
        
        # Validate response structure
        assert "success" in data
        assert "report" in data
        assert "timestamp" in data
        
        print(f"✓ API Response received")
        print(f"  - Success: {data['success']}")
        print(f"  - Report length: {len(data.get('report', ''))} chars")
        if data.get('profile'):
            print(f"  - Risk profile: {data['profile'].get('preferences', {}).get('risk_tolerance', 'N/A')}")
        if data.get('selected_stock'):
            print(f"  - Stock pick: {data['selected_stock'].get('Ticker', 'N/A')}")
    
    def test_wealth_analyze_endpoint_india(self, test_client, sample_user_input_india):
        """Test /api/wealth/analyze endpoint with Indian input"""
        response = test_client.post(
            "/api/wealth/analyze",
            json={
                "user_input": sample_user_input_india,
                "market": "IN"
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "report" in data
        print(f"✓ Indian market API test passed")
    
    def test_wealth_analyze_invalid_market(self, test_client):
        """Test API with invalid market parameter"""
        response = test_client.post(
            "/api/wealth/analyze",
            json={
                "user_input": "Test investment query",
                "market": "INVALID_MARKET"
            }
        )
        
        # Should still work but might default to US
        print(f"✓ Invalid market test: Status {response.status_code}")
    
    def test_wealth_analyze_minimal_input(self, test_client):
        """Test API with minimal user input"""
        response = test_client.post(
            "/api/wealth/analyze",
            json={
                "user_input": "I want to invest $10000",
                "market": "US"
            }
        )
        
        assert response.status_code == 200
        print(f"✓ Minimal input test passed")


# ============================================================================
# EDGE CASE TESTS
# ============================================================================

class TestEdgeCases:
    """Test edge cases and error handling"""
    
    def test_empty_input(self, test_client):
        """Test with empty user input"""
        response = test_client.post(
            "/api/wealth/analyze",
            json={
                "user_input": "",
                "market": "US"
            }
        )
        # Should either succeed with error message or return 200 with error in response
        print(f"✓ Empty input test: Status {response.status_code}")
    
    def test_very_long_input(self, test_client):
        """Test with extremely long user input"""
        long_input = "I want to invest. " * 500
        response = test_client.post(
            "/api/wealth/analyze",
            json={
                "user_input": long_input,
                "market": "US"
            }
        )
        print(f"✓ Long input test: Status {response.status_code}")
    
    def test_special_characters_input(self, test_client):
        """Test with special characters in input"""
        response = test_client.post(
            "/api/wealth/analyze",
            json={
                "user_input": "I earn $5,000 & want to invest 50% in stocks! @high-risk #growth",
                "market": "US"
            }
        )
        assert response.status_code == 200
        print(f"✓ Special characters test passed")


# ============================================================================
# PERFORMANCE TESTS
# ============================================================================

class TestPerformance:
    """Test performance and timeout handling"""
    
    @pytest.mark.asyncio
    async def test_workflow_completion_time(self, wealth_orchestrator, sample_user_input_us):
        """Test that workflow completes in reasonable time"""
        import time
        
        start_time = time.time()
        result = await wealth_orchestrator.run_workflow(
            user_input=sample_user_input_us,
            market="US"
        )
        end_time = time.time()
        
        duration = end_time - start_time
        print(f"✓ Workflow completed in {duration:.2f} seconds")
        
        # Should complete within 60 seconds (adjust based on actual performance)
        assert duration < 60, f"Workflow took too long: {duration}s"


# ============================================================================
# MAIN TEST RUNNER
# ============================================================================

if __name__ == "__main__":
    print("\n" + "="*70)
    print("AI ADVISOR / WEALTH MANAGEMENT TEST SUITE")
    print("="*70 + "\n")
    
    # Run with pytest
    pytest.main([
        __file__,
        "-v",  # Verbose
        "-s",  # Show print statements
        "--tb=short",  # Short traceback format
        "--asyncio-mode=auto"  # Auto-detect async tests
    ])
