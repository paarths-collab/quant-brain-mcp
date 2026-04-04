import os
import json
from typing import Dict, Any
from langchain_core.messages import HumanMessage
from .fundamentals_service import get_fundamentals_summary
from backend.services.market_data import market_service
from backend.finverse_integration.agents.stock_agent import StockSelectionAgent
from backend.finverse_integration.utils.llm_manager import LLMManager

# Initialize Finverse Components
# We initialize them globally to reuse clients/connections
try:
    llm_manager = LLMManager()
    stock_agent = StockSelectionAgent(llm_manager)
except Exception as e:
    print(f"Warning: Failed to init Finverse Agents: {e}")
    llm_manager = None
    stock_agent = None

def generate_research_report(symbol: str) -> Dict[str, Any]:
    """
    Generates an AI-powered research report for a stock using Finverse Pipeline.
    Integrates: Fundamentals + Technicals + Reddit Sentiment + Deep Web Research.
    """
    symbol = symbol.upper()
    
    # 1. Gather Data (Fundamentals & Technicals)
    try:
        fundamentals = get_fundamentals_summary(symbol)
        candles = market_service.fetch_candles(symbol, interval="1wk", period="3mo")
    except Exception as e:
        return {"error": f"Data fetch failed: {e}"}

    if not fundamentals:
        return {"error": "Stock not found"}

    # Calculate Trend
    trend = "Unknown"
    if candles and len(candles) >= 2:
        start_p = candles[0]['close']
        end_p = candles[-1]['close']
        pct = ((end_p - start_p) / start_p) * 100
        trend = f"{pct:.2f}% over last 3 months"

    # 2. Finverse Research (Deep Web & Sentiment)
    research_summary = "No web research available."
    sentiment_score = 0
    research_source = "None"
    
    if stock_agent:
        try:
            # Deep Web Research (Tavily/NewsDataIO/Finnhub)
            research_data = stock_agent._deep_research_robust(symbol)
            if research_data.get('summary'):
                research_summary = "\n- ".join(research_data['summary'])
                research_source = research_data.get('source', 'Unknown')
            
            # Reddit Sentiment
            sent_map = stock_agent._analyze_reddit_sentiment([symbol])
            sentiment_score = sent_map.get(symbol, 0)
        except Exception as e:
            print(f"Finverse Research Error: {e}")

    # 3. Construct Rich Prompt
    prompt = f"""
    You are a Strategic Investment Analyst. Analyze {symbol} ({fundamentals.get('name')}).

    **Quantitative Data:**
    - Price: {fundamentals.get('price')} {fundamentals.get('currency')}
    - P/E Ratio: {fundamentals.get('metrics', {}).get('peRatio')}
    - Market Cap: {fundamentals.get('marketCap')}
    - 3-Month Trend: {trend}

    **Qualitative Intelligence (Source: {research_source}):**
    {research_summary}

    **Market Sentiment (Reddit Score):**
    {sentiment_score} (Scale: Higher is better/more active)

    **Task:**
    Write a comprehensive Investment Memo in Markdown.
    
    Structure:
    1. **Executive Thesis**: The "Bottom Line" verdict (Buy/Sell/Hold) with primary reason.
    2. **Catalysts & Strengths**: Synthesize fundamentals with the web research (e.g., new contracts, earnings growth).
    3. **Risks & Headwinds**: Highlight valuations, debt, or supply chain issues found in search.
    4. **Sentiment Check**: Interpret the Reddit score (High=Hype, Low=Ignored).
    
    Style: Institutional, Data-Driven, Forward-Looking.
    """

    # 4. Generate Report via LLM Manager
    report_content = "AI Generation Failed."
    if llm_manager:
        try:
            # invoke returns AIMessage, .content extracts string
            response = llm_manager.invoke([HumanMessage(content=prompt)])
            report_content = response.content
        except Exception as e:
            report_content = f"LLM Error: {str(e)}"
    else:
        report_content = "Finverse LLM Manager not initialized (Missing Keys?)."

    return {
        "symbol": symbol,
        "companyName": fundamentals.get("name"),
        "report": report_content,
        "meta": {
             "sentiment": sentiment_score,
             "research_source": research_source
        }
    }
