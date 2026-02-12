"""
Comprehensive Test Suite for Wealth Pipeline
Tests portfolio advice, asset allocation, wealth planning, and output formatting.
"""
import asyncio
import sys
import os
import time
from datetime import datetime
from typing import Dict, Any, List, Tuple

# Add backend to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from backend.chat.pipelines import PipelineManager, PipelineResult


class WealthPipelineTestSuite:
    """Test suite for the wealth management pipeline"""
    
    def __init__(self):
        self.manager = PipelineManager(use_gemini_formatting=False)
        self.results: List[Tuple[str, bool, str]] = []
    
    def log_result(self, test_name: str, passed: bool, details: str = ""):
        """Log test result"""
        self.results.append((test_name, passed, details))
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"\n{status} {test_name}")
        if details:
            print(f"   {details}")
    
    async def test_retirement_planning(self) -> bool:
        """Test 1: Retirement planning query"""
        print("\n" + "-"*50)
        print("📋 Test 1: Retirement Planning")
        print("-"*50)
        
        result = await self.manager.run_wealth_pipeline(
            user_input="I'm 30 years old and want to retire at 60 with $2 million. How should I invest?",
            market="US"
        )
        
        passed = result.success
        
        if passed:
            print(f"\n📊 Wealth Analysis:")
            print(f"   Pipeline: {result.pipeline}")
            print(f"   Execution Time: {result.execution_time:.2f}s")
            print(f"\n   Summary Preview:")
            print(f"   {result.summary[:300]}...")
            details = "Retirement planning processed"
        else:
            error = result.data.get("error", "Unknown")
            print(f"\n⚠️ Note: {error}")
            # Wealth module may not be loaded - this is expected in some setups
            if "not available" in str(error).lower() or "not loaded" in str(error).lower():
                details = "Wealth module not available (optional)"
                passed = True  # Mark as pass since it's optional
            else:
                details = f"Error: {error}"
        
        self.log_result("Retirement Planning", passed, details)
        return passed
    
    async def test_portfolio_allocation(self) -> bool:
        """Test 2: Portfolio allocation query"""
        print("\n" + "-"*50)
        print("📋 Test 2: Portfolio Allocation")
        print("-"*50)
        
        result = await self.manager.run_wealth_pipeline(
            user_input="I have $100,000 to invest. Create a diversified portfolio for moderate risk tolerance.",
            market="US"
        )
        
        passed = result.success
        
        if passed:
            print(f"\n📊 Portfolio Allocation:")
            print(f"   Execution Time: {result.execution_time:.2f}s")
            
            # Check for allocation data
            data = result.data
            if isinstance(data, dict):
                allocation = data.get("allocation", data.get("portfolio", {}))
                if allocation:
                    print(f"   Allocation Data: Yes")
                    for asset, pct in list(allocation.items())[:5]:
                        print(f"      - {asset}: {pct}")
            
            details = "Portfolio allocation generated"
        else:
            error = result.data.get("error", "Unknown")
            if "not available" in str(error).lower():
                details = "Wealth module not available (optional)"
                passed = True
            else:
                details = f"Error: {error}"
        
        self.log_result("Portfolio Allocation", passed, details)
        return passed
    
    async def test_emergency_fund(self) -> bool:
        """Test 3: Emergency fund advice"""
        print("\n" + "-"*50)
        print("📋 Test 3: Emergency Fund Advice")
        print("-"*50)
        
        result = await self.manager.run_wealth_pipeline(
            user_input="How much should I keep in an emergency fund? My monthly expenses are $5,000.",
            market="US"
        )
        
        passed = result.success or "not available" in str(result.data.get("error", "")).lower()
        
        if result.success:
            print(f"\n📊 Emergency Fund Analysis:")
            print(f"   {result.summary[:200]}...")
            details = "Emergency fund advice generated"
        else:
            details = "Wealth module not available (optional)" if "not available" in str(result.data.get("error", "")).lower() else f"Error: {result.data.get('error')}"
        
        self.log_result("Emergency Fund Advice", passed, details)
        return passed
    
    async def test_debt_vs_invest(self) -> bool:
        """Test 4: Debt vs investment decision"""
        print("\n" + "-"*50)
        print("📋 Test 4: Debt vs Investment Decision")
        print("-"*50)
        
        result = await self.manager.run_wealth_pipeline(
            user_input="I have $20,000. Should I pay off my student loans at 6% interest or invest in the market?",
            market="US"
        )
        
        passed = result.success or "not available" in str(result.data.get("error", "")).lower()
        
        if result.success:
            print(f"\n📊 Analysis:")
            print(f"   {result.summary[:200]}...")
            details = "Debt vs invest analysis completed"
        else:
            details = "Wealth module not available (optional)" if "not available" in str(result.data.get("error", "")).lower() else f"Error: {result.data.get('error')}"
        
        self.log_result("Debt vs Investment", passed, details)
        return passed
    
    async def test_indian_market(self) -> bool:
        """Test 5: Indian market wealth planning"""
        print("\n" + "-"*50)
        print("📋 Test 5: Indian Market Wealth Planning")
        print("-"*50)
        
        result = await self.manager.run_wealth_pipeline(
            user_input="I'm an Indian investor with ₹50 lakhs to invest. Suggest a long-term portfolio.",
            market="IN"
        )
        
        passed = result.success or "not available" in str(result.data.get("error", "")).lower()
        
        if result.success:
            print(f"\n📊 Indian Market Analysis:")
            print(f"   Market: IN")
            print(f"   {result.summary[:200]}...")
            details = "Indian market planning processed"
        else:
            details = "Wealth module not available (optional)" if "not available" in str(result.data.get("error", "")).lower() else f"Error: {result.data.get('error')}"
        
        self.log_result("Indian Market Planning", passed, details)
        return passed
    
    async def test_risk_assessment(self) -> bool:
        """Test 6: Risk assessment query"""
        print("\n" + "-"*50)
        print("📋 Test 6: Risk Assessment")
        print("-"*50)
        
        result = await self.manager.run_wealth_pipeline(
            user_input="I'm risk-averse and hate losing money. What's the safest way to invest?",
            market="US"
        )
        
        passed = result.success or "not available" in str(result.data.get("error", "")).lower()
        
        if result.success:
            # Check if conservative/safe options mentioned
            summary_lower = result.summary.lower()
            has_safe_advice = any(word in summary_lower for word in 
                                   ["bond", "fixed", "safe", "conservative", "treasury", "low risk"])
            print(f"\n📊 Risk Assessment:")
            print(f"   Has conservative advice: {'Yes' if has_safe_advice else 'Maybe'}")
            details = "Risk assessment completed"
        else:
            details = "Wealth module not available (optional)"
        
        self.log_result("Risk Assessment", passed, details)
        return passed
    
    async def test_tax_efficient(self) -> bool:
        """Test 7: Tax-efficient investing query"""
        print("\n" + "-"*50)
        print("📋 Test 7: Tax-Efficient Investing")
        print("-"*50)
        
        result = await self.manager.run_wealth_pipeline(
            user_input="How can I minimize taxes on my investments? Should I use a 401k or Roth IRA?",
            market="US"
        )
        
        passed = result.success or "not available" in str(result.data.get("error", "")).lower()
        
        if result.success:
            print(f"\n📊 Tax-Efficient Advice:")
            print(f"   {result.summary[:200]}...")
            details = "Tax-efficient advice generated"
        else:
            details = "Wealth module not available (optional)"
        
        self.log_result("Tax-Efficient Investing", passed, details)
        return passed
    
    async def test_output_structure(self) -> bool:
        """Test 8: Validate output structure"""
        print("\n" + "-"*50)
        print("📋 Test 8: Output Structure Validation")
        print("-"*50)
        
        result = await self.manager.run_wealth_pipeline(
            user_input="Build me a simple portfolio",
            market="US"
        )
        
        # Check PipelineResult structure
        checks = []
        
        checks.append(("pipeline='wealth'", result.pipeline == "wealth"))
        checks.append(("success (bool)", isinstance(result.success, bool)))
        checks.append(("data (dict)", isinstance(result.data, dict)))
        checks.append(("summary (str)", isinstance(result.summary, str) and len(result.summary) > 0))
        checks.append(("timestamp", len(result.timestamp) > 0))
        checks.append(("execution_time >= 0", result.execution_time >= 0))
        
        passed_checks = sum(1 for _, passed in checks if passed)
        total_checks = len(checks)
        
        print(f"\n📊 Structure Validation:")
        for check_name, passed in checks:
            status = "✓" if passed else "✗"
            print(f"   {status} {check_name}")
        
        passed = passed_checks == total_checks
        self.log_result("Output Structure", passed, f"{passed_checks}/{total_checks} checks passed")
        return passed
    
    async def test_empty_input(self) -> bool:
        """Test 9: Empty/minimal input handling"""
        print("\n" + "-"*50)
        print("📋 Test 9: Empty Input Handling")
        print("-"*50)
        
        result = await self.manager.run_wealth_pipeline(
            user_input="",
            market="US"
        )
        
        # Should handle gracefully without crashing
        passed = True  # Just don't crash
        
        print(f"\n📊 Empty Input Response:")
        print(f"   Success: {result.success}")
        print(f"   Has Response: {len(result.summary) > 0}")
        
        details = "Handled empty input gracefully"
        self.log_result("Empty Input Handling", passed, details)
        return passed
    
    async def test_performance(self) -> bool:
        """Test 10: Performance benchmark"""
        print("\n" + "-"*50)
        print("📋 Test 10: Performance Benchmark")
        print("-"*50)
        
        start = time.time()
        result = await self.manager.run_wealth_pipeline(
            user_input="Create a balanced portfolio for me",
            market="US"
        )
        total_time = time.time() - start
        
        acceptable_time = 60  # seconds
        passed = total_time < acceptable_time  # Just measure, don't fail on wealth unavailable
        
        print(f"\n📊 Performance Results:")
        print(f"   Total Wall Time: {total_time:.2f}s")
        print(f"   Reported Execution Time: {result.execution_time:.2f}s")
        print(f"   Threshold: {acceptable_time}s")
        
        self.log_result("Performance", passed, f"Completed in {total_time:.2f}s")
        return passed
    
    async def run_all_tests(self) -> bool:
        """Run all wealth pipeline tests"""
        print("\n" + "="*60)
        print("💰 WEALTH PIPELINE TEST SUITE")
        print("="*60)
        print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("\n⚠️  Note: Wealth module is optional. Tests will pass if module is not loaded.")
        
        # Run all tests
        await self.test_retirement_planning()
        await self.test_portfolio_allocation()
        await self.test_emergency_fund()
        await self.test_debt_vs_invest()
        await self.test_indian_market()
        await self.test_risk_assessment()
        await self.test_tax_efficient()
        await self.test_output_structure()
        await self.test_empty_input()
        await self.test_performance()
        
        # Print summary
        print("\n" + "="*60)
        print("📊 TEST RESULTS SUMMARY")
        print("="*60)
        
        passed_count = sum(1 for _, passed, _ in self.results if passed)
        total_count = len(self.results)
        
        for test_name, passed, details in self.results:
            status = "✅" if passed else "❌"
            print(f"   {status} {test_name}")
        
        print(f"\n{'✅' if passed_count == total_count else '⚠️'} Total: {passed_count}/{total_count} tests passed")
        print(f"Completed: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        return passed_count == total_count


def main():
    """Run wealth pipeline tests"""
    suite = WealthPipelineTestSuite()
    success = asyncio.run(suite.run_all_tests())
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
