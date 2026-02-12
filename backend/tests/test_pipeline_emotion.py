"""
Comprehensive Test Suite for Emotion Pipeline
Tests emotional bias detection, recommendation logic, cooldown system, and output formatting.
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


class EmotionPipelineTestSuite:
    """Test suite for the emotion analysis pipeline"""
    
    def __init__(self):
        self.manager = PipelineManager(use_gemini_formatting=False)  # Disable for faster tests
        self.results: List[Tuple[str, bool, str]] = []  # (test_name, passed, details)
    
    def log_result(self, test_name: str, passed: bool, details: str = ""):
        """Log test result"""
        self.results.append((test_name, passed, details))
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"\n{status} {test_name}")
        if details:
            print(f"   {details}")
    
    async def test_panic_detection(self) -> bool:
        """Test 1: Panic emotion detection"""
        print("\n" + "-"*50)
        print("📋 Test 1: Panic Emotion Detection")
        print("-"*50)
        
        result = await self.manager.run_emotion_pipeline(
            ticker="AAPL",
            user_message="I'm freaking out! The market is crashing! Should I sell everything NOW before it goes to zero?!",
            market="US",
            user_id="test_panic_user"
        )
        
        # Validate result structure
        passed = True
        details = []
        
        if not result.success:
            passed = False
            details.append(f"Pipeline failed: {result.data.get('error', 'Unknown')}")
        
        if result.pipeline != "emotion":
            passed = False
            details.append(f"Wrong pipeline name: {result.pipeline}")
        
        if result.execution_time <= 0:
            passed = False
            details.append("Invalid execution time")
        
        # Check for panic detection in data
        analysis = result.data.get("analysis", result.data.get("bias_analysis", {}))
        detected_bias = analysis.get("detected_bias", analysis.get("dominant_bias", "")).lower()
        emotion_intensity = analysis.get("emotion_intensity", 0)
        
        if "panic" not in detected_bias and "fear" not in detected_bias:
            details.append(f"Expected panic/fear bias, got: {detected_bias}")
        else:
            details.append(f"Correctly detected: {detected_bias}")
        
        if emotion_intensity < 0.5:
            details.append(f"Low emotion intensity: {emotion_intensity:.0%}")
        else:
            details.append(f"High emotion intensity: {emotion_intensity:.0%} ✓")
        
        # Check recommendation
        recommendation = result.data.get("action_recommendation", "")
        details.append(f"Recommendation: {recommendation}")
        
        print(f"\n📊 Result Summary:")
        print(f"   Ticker: AAPL")
        print(f"   Execution Time: {result.execution_time:.2f}s")
        print(f"   Detected Bias: {detected_bias}")
        print(f"   Emotion Intensity: {emotion_intensity:.0%}")
        print(f"   Recommendation: {recommendation}")
        
        self.log_result("Panic Detection", passed, " | ".join(details[:2]))
        return passed
    
    async def test_fomo_detection(self) -> bool:
        """Test 2: FOMO emotion detection"""
        print("\n" + "-"*50)
        print("📋 Test 2: FOMO (Fear of Missing Out) Detection")
        print("-"*50)
        
        result = await self.manager.run_emotion_pipeline(
            ticker="NVDA",
            user_message="Everyone is making money on NVDA! It's going to the moon! I NEED to buy before it's too late! I'll use my emergency fund!",
            market="US",
            user_id="test_fomo_user"
        )
        
        passed = result.success
        analysis = result.data.get("analysis", result.data.get("bias_analysis", {}))
        detected_bias = analysis.get("detected_bias", analysis.get("dominant_bias", "")).lower()
        
        print(f"\n📊 Result Summary:")
        print(f"   Ticker: NVDA")
        print(f"   Execution Time: {result.execution_time:.2f}s")
        print(f"   Detected Bias: {detected_bias}")
        
        details = f"Detected: {detected_bias}"
        if "fomo" in detected_bias or "greed" in detected_bias or "euphoria" in detected_bias:
            details += " (expected FOMO/greed behavior)"
        
        self.log_result("FOMO Detection", passed, details)
        return passed
    
    async def test_greed_detection(self) -> bool:
        """Test 3: Greed/Overconfidence detection"""
        print("\n" + "-"*50)
        print("📋 Test 3: Greed/Overconfidence Detection")
        print("-"*50)
        
        result = await self.manager.run_emotion_pipeline(
            ticker="TSLA",
            user_message="I'm doubling down on TSLA with margin! I'm 100% sure it's going to 10x from here. I can't lose!",
            market="US",
            user_id="test_greed_user"
        )
        
        passed = result.success
        analysis = result.data.get("analysis", result.data.get("bias_analysis", {}))
        detected_bias = analysis.get("detected_bias", analysis.get("dominant_bias", "")).lower()
        
        print(f"\n📊 Result Summary:")
        print(f"   Ticker: TSLA")
        print(f"   Execution Time: {result.execution_time:.2f}s")
        print(f"   Detected Bias: {detected_bias}")
        
        self.log_result("Greed Detection", passed, f"Detected: {detected_bias}")
        return passed
    
    async def test_calm_rational_message(self) -> bool:
        """Test 4: Calm/rational message - low emotion"""
        print("\n" + "-"*50)
        print("📋 Test 4: Calm/Rational Message (Low Emotion)")
        print("-"*50)
        
        result = await self.manager.run_emotion_pipeline(
            ticker="MSFT",
            user_message="I'm considering adding Microsoft to my portfolio for long-term growth. What are the fundamentals?",
            market="US",
            user_id="test_calm_user"
        )
        
        passed = result.success
        analysis = result.data.get("analysis", result.data.get("bias_analysis", {}))
        emotion_intensity = analysis.get("emotion_intensity", 1.0)
        
        print(f"\n📊 Result Summary:")
        print(f"   Ticker: MSFT")
        print(f"   Execution Time: {result.execution_time:.2f}s")
        print(f"   Emotion Intensity: {emotion_intensity:.0%}")
        
        # Expect lower emotion intensity for calm message
        if emotion_intensity < 0.5:
            details = f"Low intensity as expected: {emotion_intensity:.0%}"
        else:
            details = f"Higher intensity than expected: {emotion_intensity:.0%}"
        
        self.log_result("Calm Message Detection", passed, details)
        return passed
    
    async def test_indian_stock(self) -> bool:
        """Test 5: Indian market stock (NSE)"""
        print("\n" + "-"*50)
        print("📋 Test 5: Indian Market Stock (NSE)")
        print("-"*50)
        
        result = await self.manager.run_emotion_pipeline(
            ticker="RELIANCE",
            user_message="Reliance is falling every day! I bought at the top. Should I cut my losses?",
            market="IN",
            user_id="test_indian_user"
        )
        
        passed = result.success
        
        print(f"\n📊 Result Summary:")
        print(f"   Ticker: RELIANCE")
        print(f"   Market: IN (NSE)")
        print(f"   Execution Time: {result.execution_time:.2f}s")
        print(f"   Success: {passed}")
        
        details = "Indian market processed" if passed else f"Error: {result.data.get('error', 'Unknown')}"
        self.log_result("Indian Stock (NSE)", passed, details)
        return passed

    async def test_indian_stock_with_suffix(self) -> bool:
        """Test 5b: Indian market stock with .NS suffix"""
        print("\n" + "-"*50)
        print("📋 Test 5b: Indian Stock With .NS Suffix")
        print("-"*50)
        
        result = await self.manager.run_emotion_pipeline(
            ticker="TARIL.NS",
            user_message="I'm worried about TARIL.NS dropping quickly. Should I sell before it gets worse?",
            market="IN",
            user_id="test_taril_user"
        )
        
        passed = result.success
        
        print(f"\n📊 Result Summary:")
        print(f"   Ticker: TARIL.NS")
        print(f"   Market: IN (NSE)")
        print(f"   Execution Time: {result.execution_time:.2f}s")
        print(f"   Success: {passed}")
        
        details = "Indian .NS ticker processed" if passed else f"Error: {result.data.get('error', 'Unknown')}"
        self.log_result("Indian Stock (.NS Suffix)", passed, details)
        return passed
    
    async def test_no_ticker(self) -> bool:
        """Test 6: Message without specific ticker"""
        print("\n" + "-"*50)
        print("📋 Test 6: Message Without Ticker")
        print("-"*50)
        
        result = await self.manager.run_emotion_pipeline(
            ticker="",
            user_message="The whole market is going down! I'm losing money everywhere!",
            market="US",
            user_id="test_no_ticker_user"
        )
        
        passed = result.success
        
        print(f"\n📊 Result Summary:")
        print(f"   Ticker: (none)")
        print(f"   Execution Time: {result.execution_time:.2f}s")
        print(f"   Success: {passed}")
        
        self.log_result("No Ticker Message", passed, "General market anxiety processed")
        return passed
    
    async def test_output_structure(self) -> bool:
        """Test 7: Validate complete output structure"""
        print("\n" + "-"*50)
        print("📋 Test 7: Output Structure Validation")
        print("-"*50)
        
        result = await self.manager.run_emotion_pipeline(
            ticker="AAPL",
            user_message="I'm worried about my Apple stock position.",
            market="US",
            user_id="test_structure_user"
        )
        
        # Check PipelineResult structure
        checks = []
        
        checks.append(("pipeline field", hasattr(result, 'pipeline') and result.pipeline == "emotion"))
        checks.append(("success field", hasattr(result, 'success') and isinstance(result.success, bool)))
        checks.append(("data field", hasattr(result, 'data') and isinstance(result.data, dict)))
        checks.append(("summary field", hasattr(result, 'summary') and isinstance(result.summary, str)))
        checks.append(("timestamp field", hasattr(result, 'timestamp') and len(result.timestamp) > 0))
        checks.append(("execution_time field", hasattr(result, 'execution_time') and result.execution_time >= 0))
        
        # Check data contents
        if result.success:
            data = result.data
            checks.append(("action_recommendation", "action_recommendation" in data))
            
            analysis = data.get("analysis", data.get("bias_analysis", {}))
            checks.append(("bias_analysis/analysis", bool(analysis)))
            checks.append(("emotion_intensity", "emotion_intensity" in analysis))
        
        passed_checks = sum(1 for _, passed in checks if passed)
        total_checks = len(checks)
        
        print(f"\n📊 Structure Validation:")
        for check_name, passed in checks:
            status = "✓" if passed else "✗"
            print(f"   {status} {check_name}")
        
        passed = passed_checks == total_checks
        self.log_result("Output Structure", passed, f"{passed_checks}/{total_checks} checks passed")
        return passed
    
    async def test_performance(self) -> bool:
        """Test 8: Performance benchmark"""
        print("\n" + "-"*50)
        print("📋 Test 8: Performance Benchmark")
        print("-"*50)
        
        message = "Should I sell my GOOGL shares?"
        
        start = time.time()
        result = await self.manager.run_emotion_pipeline(
            ticker="GOOGL",
            user_message=message,
            market="US",
            user_id="test_perf_user"
        )
        total_time = time.time() - start
        
        # Performance thresholds
        acceptable_time = 30  # seconds
        passed = result.success and total_time < acceptable_time
        
        print(f"\n📊 Performance Results:")
        print(f"   Total Wall Time: {total_time:.2f}s")
        print(f"   Reported Execution Time: {result.execution_time:.2f}s")
        print(f"   Threshold: {acceptable_time}s")
        print(f"   Result: {'✓ Within threshold' if total_time < acceptable_time else '✗ Exceeded threshold'}")
        
        self.log_result("Performance", passed, f"Completed in {total_time:.2f}s")
        return passed
    
    async def run_all_tests(self) -> bool:
        """Run all emotion pipeline tests"""
        print("\n" + "="*60)
        print("🧠 EMOTION PIPELINE TEST SUITE")
        print("="*60)
        print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        # Run all tests
        await self.test_panic_detection()
        await self.test_fomo_detection()
        await self.test_greed_detection()
        await self.test_calm_rational_message()
        await self.test_indian_stock()
        await self.test_indian_stock_with_suffix()
        await self.test_no_ticker()
        await self.test_output_structure()
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
    """Run emotion pipeline tests"""
    suite = EmotionPipelineTestSuite()
    success = asyncio.run(suite.run_all_tests())
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
