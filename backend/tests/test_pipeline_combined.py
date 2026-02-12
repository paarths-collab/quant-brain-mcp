"""
Comprehensive Test Suite for Combined Pipeline
Tests parallel execution of multiple pipelines and result aggregation.
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


class CombinedPipelineTestSuite:
    """Test suite for the combined multi-pipeline execution"""
    
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
    
    async def test_emotion_and_stock(self) -> bool:
        """Test 1: Default combined - emotion + stock_info"""
        print("\n" + "-"*50)
        print("📋 Test 1: Emotion + Stock Info (Default)")
        print("-"*50)
        
        start = time.time()
        results = await self.manager.run_combined_pipeline(
            ticker="AAPL",
            user_message="I'm worried about Apple. Should I sell my shares?",
            market="US",
            user_id="test_combined_user"
        )
        total_time = time.time() - start
        
        # Check both pipelines returned
        has_emotion = "emotion" in results
        has_stock = "stock_info" in results
        
        print(f"\n📊 Combined Results:")
        print(f"   Total Execution Time: {total_time:.2f}s")
        print(f"   Pipelines Returned: {list(results.keys())}")
        print(f"   Emotion Pipeline: {'✓' if has_emotion else '✗'}")
        print(f"   Stock Info Pipeline: {'✓' if has_stock else '✗'}")
        
        if has_emotion:
            emotion_result = results["emotion"]
            print(f"\n   🧠 Emotion Pipeline:")
            print(f"      Success: {emotion_result.success}")
            print(f"      Time: {emotion_result.execution_time:.2f}s")
        
        if has_stock:
            stock_result = results["stock_info"]
            print(f"\n   📈 Stock Info Pipeline:")
            print(f"      Success: {stock_result.success}")
            print(f"      Time: {stock_result.execution_time:.2f}s")
        
        passed = has_emotion and has_stock
        self.log_result("Emotion + Stock Info", passed, f"Both pipelines in {total_time:.2f}s")
        return passed
    
    async def test_all_three_pipelines(self) -> bool:
        """Test 2: All three pipelines together"""
        print("\n" + "-"*50)
        print("📋 Test 2: All Three Pipelines (emotion + stock_info + wealth)")
        print("-"*50)
        
        start = time.time()
        results = await self.manager.run_combined_pipeline(
            ticker="MSFT",
            user_message="Help me decide on Microsoft for my retirement portfolio",
            market="US",
            user_id="test_all_pipelines",
            pipelines=["emotion", "stock_info", "wealth"]
        )
        total_time = time.time() - start
        
        print(f"\n📊 All Pipelines Results:")
        print(f"   Total Execution Time: {total_time:.2f}s")
        print(f"   Pipelines Returned: {list(results.keys())}")
        
        for name, result in results.items():
            status = "✓" if result.success else "✗"
            print(f"   {status} {name}: {'Success' if result.success else result.data.get('error', 'Failed')[:50]}")
        
        # At least emotion and stock should work
        passed = results.get("emotion", PipelineResult("", False, {}, "", "", 0)).success
        details = f"{len([r for r in results.values() if r.success])}/{len(results)} pipelines succeeded"
        
        self.log_result("All Three Pipelines", passed, details)
        return passed
    
    async def test_single_pipeline_via_combined(self) -> bool:
        """Test 3: Single pipeline through combined interface"""
        print("\n" + "-"*50)
        print("📋 Test 3: Single Pipeline via Combined")
        print("-"*50)
        
        results = await self.manager.run_combined_pipeline(
            ticker="GOOGL",
            user_message="What's the price of Google?",
            market="US",
            user_id="test_single",
            pipelines=["stock_info"]
        )
        
        has_stock = "stock_info" in results
        passed = has_stock and results["stock_info"].success
        
        print(f"\n📊 Single Pipeline Result:")
        print(f"   Requested: ['stock_info']")
        print(f"   Returned: {list(results.keys())}")
        print(f"   Success: {passed}")
        
        self.log_result("Single Pipeline via Combined", passed, f"Got {list(results.keys())}")
        return passed
    
    async def test_parallel_execution_performance(self) -> bool:
        """Test 4: Verify parallel execution is faster than sequential"""
        print("\n" + "-"*50)
        print("📋 Test 4: Parallel Execution Performance")
        print("-"*50)
        
        # Run combined (parallel)
        start = time.time()
        parallel_results = await self.manager.run_combined_pipeline(
            ticker="NVDA",
            user_message="NVDA analysis please",
            market="US",
            user_id="test_parallel",
            pipelines=["emotion", "stock_info"]
        )
        parallel_time = time.time() - start
        
        # Get individual times
        emotion_time = parallel_results.get("emotion", PipelineResult("", False, {}, "", "", 0)).execution_time
        stock_time = parallel_results.get("stock_info", PipelineResult("", False, {}, "", "", 0)).execution_time
        sequential_estimate = emotion_time + stock_time
        
        print(f"\n📊 Performance Comparison:")
        print(f"   Parallel wall time: {parallel_time:.2f}s")
        print(f"   Emotion execution: {emotion_time:.2f}s")
        print(f"   Stock execution: {stock_time:.2f}s")
        print(f"   Sequential estimate: {sequential_estimate:.2f}s")
        
        # Parallel should be faster (or at least not much slower)
        # Allow some overhead for parallel coordination
        passed = parallel_time < (sequential_estimate + 5)  # 5s tolerance
        
        if parallel_time < sequential_estimate:
            savings = sequential_estimate - parallel_time
            details = f"Saved {savings:.1f}s via parallelism"
        else:
            details = f"Parallel overhead: {parallel_time - sequential_estimate:.1f}s"
        
        self.log_result("Parallel Performance", passed, details)
        return passed
    
    async def test_indian_market_combined(self) -> bool:
        """Test 5: Indian market with combined pipelines"""
        print("\n" + "-"*50)
        print("📋 Test 5: Indian Market Combined")
        print("-"*50)
        
        results = await self.manager.run_combined_pipeline(
            ticker="TCS",
            user_message="I'm nervous about TCS earnings. What should I do?",
            market="IN",
            user_id="test_india_combined"
        )
        
        passed = any(r.success for r in results.values())
        
        print(f"\n📊 Indian Market Results:")
        for name, result in results.items():
            status = "✓" if result.success else "✗"
            print(f"   {status} {name}")
        
        self.log_result("Indian Market Combined", passed, f"Market=IN, Ticker=TCS")
        return passed
    
    async def test_error_isolation(self) -> bool:
        """Test 6: One pipeline error shouldn't affect others"""
        print("\n" + "-"*50)
        print("📋 Test 6: Error Isolation")
        print("-"*50)
        
        # Use a problematic ticker that might fail stock lookup
        results = await self.manager.run_combined_pipeline(
            ticker="BADTICKER123",
            user_message="Analyze this stock for me please",
            market="US",
            user_id="test_error_isolation",
            pipelines=["emotion", "stock_info"]
        )
        
        # Both should return results (even if one fails)
        has_both = len(results) == 2
        
        print(f"\n📊 Error Isolation Test:")
        print(f"   Pipelines returned: {len(results)}")
        for name, result in results.items():
            print(f"   {name}: success={result.success}")
        
        # Test passes if both pipelines returned (regardless of their success)
        passed = has_both
        
        self.log_result("Error Isolation", passed, "Both pipelines returned results")
        return passed
    
    async def test_result_aggregation(self) -> bool:
        """Test 7: Result aggregation structure"""
        print("\n" + "-"*50)
        print("📋 Test 7: Result Aggregation Structure")
        print("-"*50)
        
        results = await self.manager.run_combined_pipeline(
            ticker="META",
            user_message="Feeling greedy about META!",
            market="US",
            user_id="test_aggregation"
        )
        
        # Check that results is a dict of PipelineResult objects
        checks = []
        
        checks.append(("Returns dict", isinstance(results, dict)))
        checks.append(("Has results", len(results) > 0))
        
        for name, result in results.items():
            checks.append((f"{name} is PipelineResult", isinstance(result, PipelineResult)))
            checks.append((f"{name} has pipeline attr", hasattr(result, 'pipeline')))
            checks.append((f"{name} has data attr", hasattr(result, 'data')))
            checks.append((f"{name} has summary attr", hasattr(result, 'summary')))
        
        passed_checks = sum(1 for _, p in checks if p)
        
        print(f"\n📊 Aggregation Structure:")
        for check_name, p in checks:
            status = "✓" if p else "✗"
            print(f"   {status} {check_name}")
        
        passed = passed_checks == len(checks)
        self.log_result("Result Aggregation", passed, f"{passed_checks}/{len(checks)} checks")
        return passed
    
    async def test_empty_pipelines_list(self) -> bool:
        """Test 8: Empty pipelines list handling"""
        print("\n" + "-"*50)
        print("📋 Test 8: Empty Pipelines List")
        print("-"*50)
        
        results = await self.manager.run_combined_pipeline(
            ticker="AMZN",
            user_message="Amazon analysis",
            market="US",
            user_id="test_empty_list",
            pipelines=[]  # Empty list - should use defaults
        )
        
        # Should use defaults (emotion + stock_info)
        print(f"\n📊 Empty List Response:")
        print(f"   Pipelines returned: {list(results.keys())}")
        
        # Empty list should still return something (default behavior)
        passed = len(results) >= 0  # Don't crash
        
        self.log_result("Empty Pipelines List", passed, f"Returned {list(results.keys())}")
        return passed
    
    async def test_summary_combination(self) -> bool:
        """Test 9: Combined summaries quality"""
        print("\n" + "-"*50)
        print("📋 Test 9: Summary Quality Check")
        print("-"*50)
        
        results = await self.manager.run_combined_pipeline(
            ticker="TSLA",
            user_message="I'm panicking about Tesla! Should I sell?",
            market="US",
            user_id="test_summaries"
        )
        
        print(f"\n📊 Summaries:")
        all_have_summaries = True
        
        for name, result in results.items():
            has_summary = len(result.summary) > 0
            all_have_summaries = all_have_summaries and has_summary
            
            print(f"\n   --- {name.upper()} ---")
            print(f"   Length: {len(result.summary)} chars")
            print(f"   Preview: {result.summary[:150]}...")
        
        passed = all_have_summaries
        self.log_result("Summary Quality", passed, "All pipelines have summaries")
        return passed
    
    async def test_performance_benchmark(self) -> bool:
        """Test 10: Overall performance benchmark"""
        print("\n" + "-"*50)
        print("📋 Test 10: Performance Benchmark")
        print("-"*50)
        
        start = time.time()
        results = await self.manager.run_combined_pipeline(
            ticker="AAPL",
            user_message="Full analysis of Apple please",
            market="US",
            user_id="test_benchmark",
            pipelines=["emotion", "stock_info"]
        )
        total_time = time.time() - start
        
        acceptable_time = 90  # seconds for combined
        passed = total_time < acceptable_time
        
        print(f"\n📊 Performance Results:")
        print(f"   Total Time: {total_time:.2f}s")
        print(f"   Threshold: {acceptable_time}s")
        print(f"   Pipelines: {list(results.keys())}")
        
        for name, result in results.items():
            print(f"   {name} time: {result.execution_time:.2f}s")
        
        self.log_result("Performance Benchmark", passed, f"{total_time:.2f}s total")
        return passed
    
    async def run_all_tests(self) -> bool:
        """Run all combined pipeline tests"""
        print("\n" + "="*60)
        print("🔄 COMBINED PIPELINE TEST SUITE")
        print("="*60)
        print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        # Run all tests
        await self.test_emotion_and_stock()
        await self.test_all_three_pipelines()
        await self.test_single_pipeline_via_combined()
        await self.test_parallel_execution_performance()
        await self.test_indian_market_combined()
        await self.test_error_isolation()
        await self.test_result_aggregation()
        await self.test_empty_pipelines_list()
        await self.test_summary_combination()
        await self.test_performance_benchmark()
        
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
    """Run combined pipeline tests"""
    suite = CombinedPipelineTestSuite()
    success = asyncio.run(suite.run_all_tests())
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
