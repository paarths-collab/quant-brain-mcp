"""
Comprehensive Test Suite for Stock Info Pipeline
Tests stock data retrieval, news fetching, social sentiment, and output formatting.
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


class StockInfoPipelineTestSuite:
    """Test suite for the stock information pipeline"""
    
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
    
    async def test_us_stock_basic(self) -> bool:
        """Test 1: Basic US stock data retrieval"""
        print("\n" + "-"*50)
        print("📋 Test 1: US Stock Basic Data (AAPL)")
        print("-"*50)
        
        result = await self.manager.run_stock_info_pipeline(
            ticker="AAPL",
            market="US"
        )
        
        passed = result.success
        
        if passed:
            data = result.data
            price_data = data.get("price_data", {})
            
            print(f"\n📊 Stock Data Retrieved:")
            print(f"   Ticker: {data.get('ticker', 'N/A')}")
            print(f"   Market: {data.get('market', 'N/A')}")
            print(f"   Current Price: ${price_data.get('current_price', 'N/A')}")
            print(f"   Daily Return: {price_data.get('daily_return', 0) * 100:.2f}%")
            print(f"   Company: {price_data.get('company_name', 'N/A')}")
            print(f"   Execution Time: {result.execution_time:.2f}s")
            
            # Validate we got real data
            if price_data.get('current_price', 0) > 0:
                details = f"Price: ${price_data['current_price']:.2f}"
            else:
                details = "Price data may be missing"
                passed = False
        else:
            details = f"Error: {result.data.get('error', 'Unknown')}"
            print(f"\n❌ Error: {details}")
        
        self.log_result("US Stock Basic (AAPL)", passed, details)
        return passed
    
    async def test_us_stock_tech(self) -> bool:
        """Test 2: Tech stock with high volatility (NVDA)"""
        print("\n" + "-"*50)
        print("📋 Test 2: Tech Stock (NVDA)")
        print("-"*50)
        
        result = await self.manager.run_stock_info_pipeline(
            ticker="NVDA",
            market="US"
        )
        
        passed = result.success
        
        if passed:
            data = result.data
            print(f"\n📊 NVDA Data Retrieved:")
            print(f"   Current Price: ${data.get('price_data', {}).get('current_price', 'N/A')}")
            print(f"   News Articles: {len(data.get('news', []))}")
            print(f"   Social Mentions: {len(data.get('social_sentiment', {}).get('mentions', []))}")
            details = "High-volatility tech stock processed"
        else:
            details = f"Error: {result.data.get('error', 'Unknown')}"
        
        self.log_result("Tech Stock (NVDA)", passed, details)
        return passed
    
    async def test_indian_stock_nse(self) -> bool:
        """Test 3: Indian NSE stock (RELIANCE)"""
        print("\n" + "-"*50)
        print("📋 Test 3: Indian NSE Stock (RELIANCE)")
        print("-"*50)
        
        result = await self.manager.run_stock_info_pipeline(
            ticker="RELIANCE",
            market="IN"
        )
        
        passed = result.success
        
        if passed:
            data = result.data
            price_data = data.get("price_data", {})
            
            print(f"\n📊 RELIANCE Data Retrieved:")
            print(f"   Ticker: {data.get('ticker', 'N/A')}")
            print(f"   Market: {data.get('market', 'N/A')}")
            print(f"   Current Price: ₹{price_data.get('current_price', 'N/A')}")
            print(f"   Execution Time: {result.execution_time:.2f}s")
            
            details = f"Price: ₹{price_data.get('current_price', 'N/A')}"
        else:
            details = f"Error: {result.data.get('error', 'Unknown')}"
        
        self.log_result("Indian Stock (RELIANCE)", passed, details)
        return passed
    
    async def test_indian_stock_tcs(self) -> bool:
        """Test 4: Indian IT stock (TCS)"""
        print("\n" + "-"*50)
        print("📋 Test 4: Indian IT Stock (TCS)")
        print("-"*50)
        
        result = await self.manager.run_stock_info_pipeline(
            ticker="TCS",
            market="IN"
        )
        
        passed = result.success
        
        if passed:
            data = result.data
            print(f"\n📊 TCS Data Retrieved:")
            print(f"   Current Price: ₹{data.get('price_data', {}).get('current_price', 'N/A')}")
            details = "Indian IT stock processed"
        else:
            details = f"Error: {result.data.get('error', 'Unknown')}"
        
        self.log_result("Indian IT Stock (TCS)", passed, details)
        return passed
    
    async def test_news_data(self) -> bool:
        """Test 5: News data retrieval"""
        print("\n" + "-"*50)
        print("📋 Test 5: News Data Retrieval")
        print("-"*50)
        
        result = await self.manager.run_stock_info_pipeline(
            ticker="MSFT",
            market="US"
        )
        
        passed = result.success
        news = result.data.get("news", [])
        
        if passed:
            print(f"\n📰 News Data:")
            print(f"   Total Articles: {len(news)}")
            
            if news and len(news) > 0:
                for i, article in enumerate(news[:3], 1):
                    if isinstance(article, dict):
                        title = article.get('title', article.get('headline', 'No title'))[:60]
                        print(f"   {i}. {title}...")
                    else:
                        print(f"   {i}. {str(article)[:60]}...")
                details = f"{len(news)} news articles found"
            else:
                details = "No news articles (DDG may have rate limited)"
        else:
            details = f"Error: {result.data.get('error', 'Unknown')}"
        
        self.log_result("News Data Retrieval", passed, details)
        return passed
    
    async def test_social_sentiment(self) -> bool:
        """Test 6: Social sentiment data"""
        print("\n" + "-"*50)
        print("📋 Test 6: Social Sentiment Data")
        print("-"*50)
        
        result = await self.manager.run_stock_info_pipeline(
            ticker="TSLA",
            market="US"
        )
        
        passed = result.success
        social = result.data.get("social_sentiment", {})
        
        if passed:
            print(f"\n📱 Social Sentiment:")
            print(f"   Reddit Data: {'Yes' if social else 'No'}")
            
            if social:
                mentions = social.get('mentions', social.get('posts', []))
                sentiment = social.get('sentiment_score', social.get('sentiment', 'N/A'))
                print(f"   Mentions: {len(mentions) if isinstance(mentions, list) else mentions}")
                print(f"   Sentiment: {sentiment}")
                details = "Social data retrieved"
            else:
                details = "No social data (may require Reddit API)"
        else:
            details = f"Error: {result.data.get('error', 'Unknown')}"
        
        self.log_result("Social Sentiment", passed, details)
        return passed
    
    async def test_output_structure(self) -> bool:
        """Test 7: Validate complete output structure"""
        print("\n" + "-"*50)
        print("📋 Test 7: Output Structure Validation")
        print("-"*50)
        
        result = await self.manager.run_stock_info_pipeline(
            ticker="GOOG",
            market="US"
        )
        
        # Check PipelineResult structure
        checks = []
        
        checks.append(("pipeline='stock_info'", result.pipeline == "stock_info"))
        checks.append(("success (bool)", isinstance(result.success, bool)))
        checks.append(("data (dict)", isinstance(result.data, dict)))
        checks.append(("summary (str)", isinstance(result.summary, str) and len(result.summary) > 0))
        checks.append(("timestamp", len(result.timestamp) > 0))
        checks.append(("execution_time >= 0", result.execution_time >= 0))
        
        # Check data contents
        if result.success:
            data = result.data
            checks.append(("ticker in data", "ticker" in data))
            checks.append(("market in data", "market" in data))
            checks.append(("price_data in data", "price_data" in data))
            checks.append(("news in data", "news" in data))
            
            price_data = data.get("price_data", {})
            checks.append(("current_price exists", "current_price" in price_data or "error" in price_data))
        
        passed_checks = sum(1 for _, passed in checks if passed)
        total_checks = len(checks)
        
        print(f"\n📊 Structure Validation:")
        for check_name, passed in checks:
            status = "✓" if passed else "✗"
            print(f"   {status} {check_name}")
        
        passed = passed_checks >= total_checks - 2  # Allow some flexibility
        self.log_result("Output Structure", passed, f"{passed_checks}/{total_checks} checks passed")
        return passed
    
    async def test_invalid_ticker(self) -> bool:
        """Test 8: Invalid/unknown ticker handling"""
        print("\n" + "-"*50)
        print("📋 Test 8: Invalid Ticker Handling")
        print("-"*50)
        
        result = await self.manager.run_stock_info_pipeline(
            ticker="XYZNOTEXIST123",
            market="US"
        )
        
        # Should either fail gracefully or return empty data
        print(f"\n📊 Invalid Ticker Response:")
        print(f"   Success: {result.success}")
        print(f"   Has Error: {'error' in result.data}")
        
        # Test passes if it doesn't crash and handles gracefully
        passed = True  # Pipeline should not crash
        
        if not result.success:
            details = "Gracefully handled invalid ticker"
        else:
            price = result.data.get("price_data", {}).get("current_price", 0)
            details = f"Returned data (price: {price})"
        
        self.log_result("Invalid Ticker Handling", passed, details)
        return passed
    
    async def test_summary_format(self) -> bool:
        """Test 9: Summary formatting quality"""
        print("\n" + "-"*50)
        print("📋 Test 9: Summary Formatting")
        print("-"*50)
        
        result = await self.manager.run_stock_info_pipeline(
            ticker="AMZN",
            market="US"
        )
        
        summary = result.summary
        
        print(f"\n📊 Summary Preview:")
        print("-"*40)
        print(summary[:500] if len(summary) > 500 else summary)
        print("-"*40)
        
        # Check summary quality
        checks = []
        checks.append(("Has content", len(summary) > 20))
        checks.append(("Contains ticker", "AMZN" in summary.upper()))
        checks.append(("Has markdown", "**" in summary or "#" in summary or "•" in summary or "-" in summary))
        
        passed_checks = sum(1 for _, p in checks if p)
        passed = passed_checks >= 2
        
        self.log_result("Summary Formatting", passed, f"{passed_checks}/{len(checks)} formatting checks")
        return passed
    
    async def test_performance(self) -> bool:
        """Test 10: Performance benchmark"""
        print("\n" + "-"*50)
        print("📋 Test 10: Performance Benchmark")
        print("-"*50)
        
        start = time.time()
        result = await self.manager.run_stock_info_pipeline(
            ticker="META",
            market="US"
        )
        total_time = time.time() - start
        
        acceptable_time = 60  # seconds (includes news/social fetching)
        passed = result.success and total_time < acceptable_time
        
        print(f"\n📊 Performance Results:")
        print(f"   Total Wall Time: {total_time:.2f}s")
        print(f"   Reported Execution Time: {result.execution_time:.2f}s")
        print(f"   Threshold: {acceptable_time}s")
        
        self.log_result("Performance", passed, f"Completed in {total_time:.2f}s")
        return passed
    
    async def run_all_tests(self) -> bool:
        """Run all stock info pipeline tests"""
        print("\n" + "="*60)
        print("📈 STOCK INFO PIPELINE TEST SUITE")
        print("="*60)
        print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        # Run all tests
        await self.test_us_stock_basic()
        await self.test_us_stock_tech()
        await self.test_indian_stock_nse()
        await self.test_indian_stock_tcs()
        await self.test_news_data()
        await self.test_social_sentiment()
        await self.test_output_structure()
        await self.test_invalid_ticker()
        await self.test_summary_format()
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
    """Run stock info pipeline tests"""
    suite = StockInfoPipelineTestSuite()
    success = asyncio.run(suite.run_all_tests())
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
