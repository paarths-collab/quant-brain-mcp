"""
langchain_tools.py

LangChain tools wrapper for the QuantInsights platform.
These tools allow LangChain agents to interact with the
existing analysis infrastructure.

This provides a clean interface between LangChain/LangGraph
and our custom agents.
"""

from typing import Dict, Any, List, Optional
from dataclasses import dataclass

# Import our stock analyzer module
from backend.agents.stock_analyzer import (
    analyze_stock as yf_analyze_stock,
    detect_tickers_in_text,
    format_analysis_for_display,
    search_and_analyze,
    search_stock as search_stock_db
)

# Try to import langchain, provide fallback
try:
    from langchain_core.tools import tool, BaseTool
    from langchain_core.pydantic_v1 import BaseModel, Field
    LANGCHAIN_AVAILABLE = True
except ImportError:
    LANGCHAIN_AVAILABLE = False
    print("[INFO] langchain not installed. Tools will work in standalone mode.")
    
    # Provide simple fallback decorators/classes
    def tool(func):
        """Fallback tool decorator"""
        func.is_tool = True
        return func
    
    class BaseModel:
        pass
    
    class Field:
        def __init__(self, *args, **kwargs):
            pass


class StockAnalysisInput(BaseModel):
    """Input schema for stock analysis tool."""
    ticker: str = Field(description="The stock ticker symbol (e.g., AAPL, MSFT)")
    market: str = Field(default="us", description="Market: 'us' or 'india'")


class CompareStocksInput(BaseModel):
    """Input schema for stock comparison tool."""
    ticker1: str = Field(description="First stock ticker")
    ticker2: str = Field(description="Second stock ticker")
    market: str = Field(default="us", description="Market: 'us' or 'india'")


class LangChainTools:
    """
    A collection of LangChain-compatible tools for financial analysis.
    
    These tools wrap the existing QuantInsights agents and make them
    accessible to LangChain/LangGraph workflows.
    """
    
    def __init__(self, orchestrator):
        """
        Initialize with the orchestrator for agent access.
        
        Args:
            orchestrator: The main Orchestrator instance
        """
        self.orchestrator = orchestrator
        self._setup_tools()
    
    def _setup_tools(self):
        """Set up all available tools."""
        self.tools_list = [
            self.get_stock_price,
            self.analyze_stock,
            self.search_stock,  # Search for stocks by company name
            self.search_analyze_stocks,  # Auto-detect & analyze stocks
            self.get_market_overview,
            self.get_sentiment,
            self.backtest_strategy,
            self.get_portfolio,
        ]
    
    @tool
    def get_stock_price(self, ticker: str, market: str = "us") -> Dict[str, Any]:
        """
        Get the current price and basic info for a stock.
        
        Args:
            ticker: Stock ticker symbol (e.g., AAPL, MSFT)
            market: 'us' or 'india'
            
        Returns:
            Dictionary with current price, change, and basic metrics
        """
        try:
            data = self.orchestrator.yfinance_agent.get_full_analysis(ticker, market)
            quote = data.get("live_quote", {})
            snapshot = data.get("snapshot", {})
            
            return {
                "ticker": ticker,
                "price": quote.get("c", "N/A"),
                "change_percent": quote.get("dp", 0),
                "market_cap": snapshot.get("marketCap", "N/A"),
                "pe_ratio": snapshot.get("trailingPE", "N/A"),
                "sector": snapshot.get("sector", "N/A"),
            }
        except Exception as e:
            return {"error": str(e)}
    
    @tool
    def analyze_stock(self, ticker: str, market: str = "us") -> Dict[str, Any]:
        """
        Perform a comprehensive analysis on a stock including technicals,
        fundamentals, and sentiment.
        
        Args:
            ticker: Stock ticker symbol
            market: 'us' or 'india'
            
        Returns:
            Comprehensive analysis results
        """
        import pandas as pd
        
        try:
            end_date = pd.Timestamp.now().strftime('%Y-%m-%d')
            start_date = (pd.Timestamp.now() - pd.DateOffset(years=1)).strftime('%Y-%m-%d')
            
            results = self.orchestrator.run_deep_dive_analysis(
                ticker=ticker,
                start_date=start_date,
                end_date=end_date,
                market=market
            )
            
            # Summarize for agent consumption
            snapshot = results.get("snapshot", {})
            sentiment = results.get("social_sentiment", {})
            news = results.get("news_sentiment", {})
            
            return {
                "ticker": ticker,
                "company_name": snapshot.get("longName", ticker),
                "sector": snapshot.get("sector", "N/A"),
                "industry": snapshot.get("industry", "N/A"),
                "market_cap": snapshot.get("marketCap", "N/A"),
                "pe_ratio": snapshot.get("trailingPE", "N/A"),
                "dividend_yield": snapshot.get("dividendYield", 0),
                "social_sentiment": sentiment.get("Overall Social Sentiment", "Neutral"),
                "news_sentiment_score": news.get("avg_score", 0),
                "summary": snapshot.get("longBusinessSummary", "")[:500],
            }
        except Exception as e:
            return {"error": str(e), "ticker": ticker}
    
    @tool
    def search_stock(self, query: str) -> Dict[str, Any]:
        """
        Search for stocks by company name, symbol, or industry.
        Works for both US and Indian (NSE/BSE) markets.
        
        Use this tool when you need to find the ticker symbol for a company
        or when the user mentions a company name instead of a ticker.
        
        Args:
            query: Search query (company name, partial name, or symbol)
            
        Returns:
            List of matching stocks with Symbol, Company Name, Industry, Market
            
        Examples:
            - "idfc bank" -> finds IDFCFIRSTB
            - "reliance" -> finds RELIANCE
            - "apple" -> finds AAPL
            - "tata motors" -> finds TATAMOTORS
        """
        try:
            results = search_stock_db(query, limit=5)
            
            if not results:
                return {
                    "message": f"No stocks found matching '{query}'",
                    "results": [],
                    "suggestion": "Try searching with a different company name or use the exact ticker symbol"
                }
            
            return {
                "query": query,
                "results": results,
                "top_match": results[0] if results else None,
                "message": f"Found {len(results)} stocks matching '{query}'"
            }
        except Exception as e:
            return {"error": str(e), "query": query}
    
    @tool
    def search_analyze_stocks(self, query: str) -> Dict[str, Any]:
        """
        Automatically detect stock tickers in a user's query and run
        comprehensive analysis on them. Works for both US and Indian stocks.
        
        This is the primary tool for answering user questions about stocks.
        It will:
        1. Detect stock tickers mentioned in the query
        2. Run full analysis on each detected stock
        3. Return formatted analysis with insights
        
        Args:
            query: The user's question or text containing stock ticker(s)
            
        Returns:
            Comprehensive analysis for all detected stocks
            
        Examples:
            - "Why is TARIL stock falling?" -> Analyzes TARIL
            - "Compare AAPL and MSFT" -> Analyzes both stocks
            - "Should I buy RELIANCE?" -> Analyzes RELIANCE
        """
        try:
            # Use the stock analyzer to detect and analyze
            result = search_and_analyze(query)
            
            if not result.get("tickers_found"):
                return {
                    "message": "No stock tickers detected. Please mention specific symbols like AAPL, TSLA, TARIL, RELIANCE, etc.",
                    "tickers_found": [],
                    "analyses": []
                }
            
            # Build summary for each stock
            summaries = []
            for analysis in result.get("analyses", []):
                if analysis.get("success"):
                    price = analysis.get("price", {})
                    valuation = analysis.get("valuation", {})
                    perf = analysis.get("performance", {})
                    
                    summary = {
                        "ticker": analysis["ticker"],
                        "company": analysis["company"]["name"],
                        "market": analysis["market"],
                        "current_price": price.get("current", 0),
                        "change_percent": price.get("change_percent", 0),
                        "pe_ratio": valuation.get("pe_ratio", "N/A"),
                        "market_cap": valuation.get("market_cap_formatted", "N/A"),
                        "1_year_return": perf.get("1_year_return", "N/A"),
                        "1_week_return": perf.get("1_week_return", "N/A"),
                        "volatility": perf.get("volatility", "N/A"),
                        "signals": analysis.get("signals", []),
                        "insights": analysis.get("insights", []),
                        "risks": analysis.get("risks", [])
                    }
                    summaries.append(summary)
                else:
                    summaries.append({
                        "ticker": analysis["ticker"],
                        "error": analysis.get("error", "Analysis failed")
                    })
            
            return {
                "tickers_found": result["tickers_found"],
                "stock_analyses": summaries,
                "formatted_reports": result.get("formatted_reports", [])
            }
            
        except Exception as e:
            return {"error": str(e), "query": query}
    
    @tool
    def get_market_overview(self) -> Dict[str, Any]:
        """
        Get an overview of current market conditions including
        US and India markets.
        
        Returns:
            Market overview with key indicators
        """
        try:
            overview = self.orchestrator.run_market_overview()
            return {
                "us_market": overview.get("us_indicators", {}),
                "india_market": overview.get("india_indicators", {}),
                "global": overview.get("global_indicators", {}),
            }
        except Exception as e:
            return {"error": str(e)}
    
    @tool
    def get_sentiment(self, ticker: str) -> Dict[str, Any]:
        """
        Get social media and news sentiment for a stock.
        
        Args:
            ticker: Stock ticker symbol
            
        Returns:
            Sentiment analysis results
        """
        try:
            social = self.orchestrator.sentiment_agent.analyze(ticker)
            return {
                "ticker": ticker,
                "social_sentiment": social,
            }
        except Exception as e:
            return {"error": str(e), "ticker": ticker}
    
    @tool
    def backtest_strategy(
        self, 
        ticker: str, 
        strategy: str = "momentum",
        market: str = "us"
    ) -> Dict[str, Any]:
        """
        Backtest a trading strategy on a stock.
        
        Args:
            ticker: Stock ticker symbol
            strategy: Strategy name (momentum, sma_crossover, rsi, etc.)
            market: 'us' or 'india'
            
        Returns:
            Backtest results with performance metrics
        """
        import pandas as pd
        
        try:
            from backend.services.backtest_service import run_backtest_service
            
            # Default parameters
            initial_capital = 10000.0
            
            # Run backtest
            results = run_backtest_service(
                symbol=ticker,
                strategy_name=strategy,
                range_period="1y",
                interval="1d",
                initial_capital=initial_capital,
                market=market
            )
            
            if "error" in results:
                return results
                
            # Summarize for the agent (it can't handle the full equity curve JSON easily)
            metrics = results.get("metrics", {})
            
            return {
                "ticker": ticker,
                "strategy": strategy,
                "total_return": f"{metrics.get('totalReturn', 0)}%",
                "max_drawdown": f"{metrics.get('maxDrawdown', 0)}%",
                "sharpe_ratio": metrics.get("sharpeRatio", 0),
                "win_rate": f"{metrics.get('winRate', 0)}%",
                "total_trades": metrics.get("totalTrades", 0),
                "final_equity": metrics.get("finalEquity", 0),
                "summary": f"Backtest of {strategy} on {ticker} returned {metrics.get('totalReturn', 0)}% over the last year with a max drawdown of {metrics.get('maxDrawdown', 0)}%."
            }
                
        except Exception as e:
            return {"error": str(e), "ticker": ticker}
    
    @tool
    def get_portfolio(self) -> Dict[str, Any]:
        """
        Get the current portfolio positions and account info.
        
        Returns:
            Portfolio positions and account balance
        """
        try:
            account = self.orchestrator.execution_agent.get_account_info()
            positions = self.orchestrator.execution_agent.get_open_positions()
            
            return {
                "account": account,
                "positions": positions,
            }
        except Exception as e:
            return {"error": str(e)}
    
    def get_tools(self) -> List:
        """Get list of all available tools."""
        return self.tools_list


# ReAct Agent for autonomous research with web search capabilities
class ResearchAgent:
    """
    A ReAct-style agent that can autonomously research stocks and topics
    using web search (Tavily), web scraping (FireCrawl), and stock analysis tools.
    
    Flow:
    1. AI analyzes query to understand intent
    2. Gathers web research data (Tavily search + optional FireCrawl scraping)
    3. Gathers stock data if relevant
    4. AI synthesizes all data into comprehensive response
    """
    
    SYSTEM_PROMPT = """You are a senior financial research analyst with access to:
- Real-time web search results and news
- Comprehensive stock data (prices, metrics, technicals)
- Company information and market analysis

When answering questions:
1. Synthesize information from ALL provided sources (web + stock data)
2. Cite specific facts and numbers from the data
3. Provide balanced analysis with both positives and risks
4. Use clear markdown formatting with headers and bullet points
5. Include relevant disclaimers for investment advice

Be thorough but concise. Focus on what's most relevant to the user's question."""

    def __init__(self, orchestrator, llm_agent):
        self.orchestrator = orchestrator
        self.llm = llm_agent
        self.tools = LangChainTools(orchestrator)
        
        # Initialize web researcher
        try:
            from backend.agents.web_research import create_web_researcher
            self.web_researcher = create_web_researcher(llm_agent=llm_agent)
            self.web_research_available = True
            print("[SUCCESS] Web research (Tavily + FireCrawl) initialized")
        except Exception as e:
            print(f"[WARNING] Web research not available: {e}")
            self.web_researcher = None
            self.web_research_available = False
    
    def research(self, query: str) -> str:
        """
        Research a topic using web search and stock analysis.
        
        Args:
            query: The user's research question
            
        Returns:
            Comprehensive research findings
        """
        # Step 1: Use AI to analyze query and understand intent
        try:
            from backend.agents.stock_analyzer import ai_analyze_query
            query_analysis = ai_analyze_query(query, self.llm)
            detected_tickers = query_analysis.get("tickers", [])
            intent = query_analysis.get("intent", "general_question")
            is_stock_question = query_analysis.get("is_stock_question", False)
        except Exception as e:
            print(f"Query analysis failed: {e}")
            detected_tickers = []
            intent = "general_question"
            is_stock_question = False
        
        context_parts = []
        
        # Step 2: Gather web research data
        if self.web_research_available and self.web_researcher:
            try:
                print(f"[RESEARCH] Searching web for: {query}")
                web_data = self.web_researcher.research(query)
                web_context = self.web_researcher.format_for_llm(web_data)
                if web_context and web_context != "No web research data available.":
                    context_parts.append("# Web Research Results\n" + web_context)
            except Exception as e:
                print(f"Web research error: {e}")
                context_parts.append(f"*Web research unavailable: {str(e)}*")
        
        # Step 3: Gather stock data if relevant
        if is_stock_question and detected_tickers:
            try:
                stock_context = self._gather_stock_context(detected_tickers)
                if stock_context:
                    context_parts.append("\n# Stock Analysis Data\n" + stock_context)
            except Exception as e:
                print(f"Stock analysis error: {e}")
        elif is_stock_question:
            # Try traditional detection
            stock_context = self._gather_context(query)
            if stock_context and stock_context != "No stock tickers detected.":
                context_parts.append("\n# Stock Analysis Data\n" + stock_context)
        
        # If no context gathered, provide a helpful message
        if not context_parts:
            return """I couldn't find specific information for your query.

**Tips:**
- For stock analysis, mention the ticker symbol (e.g., "AAPL", "RELIANCE")
- For market research, try more specific terms
- I can help with company analysis, market trends, and financial concepts

What would you like me to research?"""
        
        # Step 4: Synthesize with AI
        combined_context = "\n\n".join(context_parts)
        
        prompt = f"""{self.SYSTEM_PROMPT}

## User Query
{query}

## Available Research Data
{combined_context}

## Task
Based on ALL the above data, provide a comprehensive answer to the user's question.
Synthesize information from both web and stock sources where available.
Be specific and cite the data. Format your response clearly in markdown."""

        try:
            response = self.llm.run(
                prompt=prompt, 
                model_name="llama-3.3-70b-versatile"
            )
            return response
        except Exception as e:
            # Return raw context if LLM fails
            return f"**Research Data (AI synthesis failed)**\n\n{combined_context}"
    
    def _gather_stock_context(self, tickers: List[str]) -> str:
        """Gather stock analysis for specific tickers."""
        context_parts = []
        
        for ticker in tickers[:3]:  # Limit to 3 tickers
            try:
                analysis = yf_analyze_stock(ticker)
                if analysis.get("success"):
                    formatted = format_analysis_for_display(analysis)
                    context_parts.append(formatted)
            except Exception as e:
                context_parts.append(f"Error analyzing {ticker}: {str(e)}")
        
        return "\n\n".join(context_parts)
    
    def _gather_context(self, query: str) -> str:
        """Gather relevant context based on the query using stock_analyzer (legacy)."""
        import json
        
        context_parts = []
        
        try:
            result = search_and_analyze(query)
            
            if not result.get("tickers_found"):
                tickers = detect_tickers_in_text(query)
                if not tickers:
                    return "No stock tickers detected."
                
                for ticker in tickers[:2]:
                    analysis = yf_analyze_stock(ticker)
                    if analysis.get("success"):
                        formatted = format_analysis_for_display(analysis)
                        context_parts.append(formatted)
            else:
                for report in result.get("formatted_reports", []):
                    context_parts.append(report)
        
        except Exception as e:
            context_parts.append(f"Error gathering stock data: {str(e)}")
        
        # Check for market overview keywords
        if any(word in query.lower() for word in ['market', 'economy', 'overview', 'outlook']):
            try:
                overview = self.tools.get_market_overview()
                context_parts.append(f"\n### Market Overview\n{json.dumps(overview, indent=2, default=str)}")
            except:
                pass
        
        return "\n\n".join(context_parts) if context_parts else "No specific data gathered."


def create_tools(orchestrator) -> LangChainTools:
    """Factory function to create LangChain tools."""
    return LangChainTools(orchestrator)


def create_research_agent(orchestrator, llm_agent) -> ResearchAgent:
    """Factory function to create the research agent with web research capabilities."""
    return ResearchAgent(orchestrator, llm_agent)

