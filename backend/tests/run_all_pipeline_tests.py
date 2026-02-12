"""
Master Test Runner for All Pipeline Tests
Runs all 4 pipeline test suites and provides comprehensive output.
"""
import asyncio
import sys
import os
import time
from datetime import datetime

# Add backend to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

# Import test suites
from backend.tests.test_pipeline_emotion import EmotionPipelineTestSuite
from backend.tests.test_pipeline_stock import StockInfoPipelineTestSuite
from backend.tests.test_pipeline_wealth import WealthPipelineTestSuite
from backend.tests.test_pipeline_combined import CombinedPipelineTestSuite


async def run_all_pipeline_tests():
    """Run all pipeline test suites"""
    print("\n" + "🚀"*30)
    print("   COMPREHENSIVE PIPELINE TEST RUNNER")
    print("🚀"*30)
    print(f"\nStarted: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    start_time = time.time()
    suite_results = []
    
    # Test Suite 1: Emotion Pipeline
    print("\n" + "="*70)
    print("📦 SUITE 1/4: EMOTION PIPELINE")
    print("="*70)
    emotion_suite = EmotionPipelineTestSuite()
    emotion_passed = await emotion_suite.run_all_tests()
    emotion_count = sum(1 for _, p, _ in emotion_suite.results if p)
    emotion_total = len(emotion_suite.results)
    suite_results.append(("Emotion Pipeline", emotion_passed, emotion_count, emotion_total))
    
    # Test Suite 2: Stock Info Pipeline
    print("\n" + "="*70)
    print("📦 SUITE 2/4: STOCK INFO PIPELINE")
    print("="*70)
    stock_suite = StockInfoPipelineTestSuite()
    stock_passed = await stock_suite.run_all_tests()
    stock_count = sum(1 for _, p, _ in stock_suite.results if p)
    stock_total = len(stock_suite.results)
    suite_results.append(("Stock Info Pipeline", stock_passed, stock_count, stock_total))
    
    # Test Suite 3: Wealth Pipeline
    print("\n" + "="*70)
    print("📦 SUITE 3/4: WEALTH PIPELINE")
    print("="*70)
    wealth_suite = WealthPipelineTestSuite()
    wealth_passed = await wealth_suite.run_all_tests()
    wealth_count = sum(1 for _, p, _ in wealth_suite.results if p)
    wealth_total = len(wealth_suite.results)
    suite_results.append(("Wealth Pipeline", wealth_passed, wealth_count, wealth_total))
    
    # Test Suite 4: Combined Pipeline
    print("\n" + "="*70)
    print("📦 SUITE 4/4: COMBINED PIPELINE")
    print("="*70)
    combined_suite = CombinedPipelineTestSuite()
    combined_passed = await combined_suite.run_all_tests()
    combined_count = sum(1 for _, p, _ in combined_suite.results if p)
    combined_total = len(combined_suite.results)
    suite_results.append(("Combined Pipeline", combined_passed, combined_count, combined_total))
    
    total_time = time.time() - start_time
    
    # Print comprehensive summary
    print("\n" + "="*70)
    print("📊 COMPREHENSIVE TEST RESULTS")
    print("="*70)
    
    total_tests = 0
    total_passed = 0
    
    for suite_name, passed, count, total in suite_results:
        status = "✅" if passed else "❌"
        print(f"\n{status} {suite_name}")
        print(f"   Tests: {count}/{total} passed")
        total_tests += total
        total_passed += count
    
    # Detailed breakdown
    print("\n" + "-"*70)
    print("DETAILED BREAKDOWN")
    print("-"*70)
    
    all_results = [
        ("Emotion", emotion_suite.results),
        ("Stock", stock_suite.results),  
        ("Wealth", wealth_suite.results),
        ("Combined", combined_suite.results)
    ]
    
    for suite_name, results in all_results:
        print(f"\n{suite_name} Pipeline Tests:")
        for test_name, passed, details in results:
            status = "✅" if passed else "❌"
            print(f"   {status} {test_name}")
    
    # Final summary
    print("\n" + "="*70)
    print("FINAL SUMMARY")
    print("="*70)
    
    suites_passed = sum(1 for _, passed, _, _ in suite_results if passed)
    
    print(f"""
   📦 Test Suites:  {suites_passed}/4 passed
   🧪 Total Tests:  {total_passed}/{total_tests} passed
   ⏱️  Total Time:   {total_time:.1f} seconds
   📅 Completed:    {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
""")
    
    overall_success = suites_passed == 4
    
    if overall_success:
        print("🎉 ALL PIPELINE TESTS PASSED! 🎉")
    else:
        print("⚠️  SOME TESTS FAILED - Review output above")
    
    print("="*70 + "\n")
    
    return overall_success


def main():
    """Main entry point"""
    success = asyncio.run(run_all_pipeline_tests())
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
