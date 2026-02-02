"""
langgraph_orchestrator.py

A modern multi-agent orchestrator using LangGraph for sophisticated
workflow management. This enables:
- Parallel agent execution
- Conditional routing based on results
- State management across agent calls
- Error recovery and retries
- Observable agent graphs

This is the next evolution of the simple Orchestrator class.
"""

from __future__ import annotations
from typing import Dict, Any, List, Optional, TypedDict, Annotated
from dataclasses import dataclass, field
from enum import Enum
import operator
import json

# Try to import langgraph, provide fallback if not installed
try:
    from langgraph.graph import StateGraph, END
    from langgraph.checkpoint.memory import MemorySaver
    LANGGRAPH_AVAILABLE = True
except ImportError:
    LANGGRAPH_AVAILABLE = False
    print("[WARNING] langgraph not installed. Install with: pip install langgraph")


class AnalysisType(Enum):
    """Types of analysis that can be performed."""
    QUICK_SCAN = "quick_scan"
    DEEP_DIVE = "deep_dive"
    COMPARISON = "comparison"
    DISCOVERY = "discovery"
    BACKTEST = "backtest"


class AgentState(TypedDict):
    """
    The shared state passed between agents in the graph.
    
    This uses TypedDict for type safety and documentation.
    Using Annotated with operator.add allows message accumulation.
    """
    # Input parameters
    tickers: List[str]
    market: str
    start_date: str
    end_date: str
    analysis_type: str
    user_query: Optional[str]
    
    # Accumulated messages/logs from agents
    messages: Annotated[List[str], operator.add]
    
    # Results from each agent
    market_data: Optional[Dict[str, Any]]
    technical_analysis: Optional[Dict[str, Any]]
    fundamental_analysis: Optional[Dict[str, Any]]
    sentiment_analysis: Optional[Dict[str, Any]]
    insider_analysis: Optional[Dict[str, Any]]
    strategy_results: Optional[Dict[str, Any]]
    
    # Final synthesis
    synthesis: Optional[str]
    recommendation: Optional[str]
    
    # Control flow
    error: Optional[str]
    completed_agents: List[str]


class LangGraphOrchestrator:
    """
    A sophisticated multi-agent orchestrator using LangGraph.
    
    This orchestrator creates a directed acyclic graph (DAG) of agents
    that can execute in parallel where possible, with conditional
    routing based on intermediate results.
    
    Architecture:
    
    ┌─────────────┐
    │   Input     │
    └──────┬──────┘
           │
    ┌──────▼──────┐
    │  Classifier │  (Determines analysis type)
    └──────┬──────┘
           │
    ┌──────▼──────────────────────────┐
    │     Parallel Data Collection    │
    │  ┌─────┐ ┌─────┐ ┌──────────┐  │
    │  │Market│ │Tech │ │Sentiment │  │
    │  │ Data │ │ TA  │ │ Analysis │  │
    │  └─────┘ └─────┘ └──────────┘  │
    └──────┬──────────────────────────┘
           │
    ┌──────▼──────┐
    │ Synthesizer │  (Combines all results)
    └──────┬──────┘
           │
    ┌──────▼──────┐
    │   Output    │
    └─────────────┘
    """
    
    def __init__(self, base_orchestrator):
        """
        Initialize with the base orchestrator for agent access.
        
        Args:
            base_orchestrator: The original Orchestrator instance with all agents
        """
        self.base = base_orchestrator
        self.memory = MemorySaver() if LANGGRAPH_AVAILABLE else None
        
        if LANGGRAPH_AVAILABLE:
            self.graph = self._build_graph()
        else:
            self.graph = None
    
    def _build_graph(self) -> StateGraph:
        """Build the agent execution graph."""
        # Create the state graph
        workflow = StateGraph(AgentState)
        
        # Add all agent nodes
        workflow.add_node("classifier", self._classifier_node)
        workflow.add_node("market_data", self._market_data_node)
        workflow.add_node("technical_analysis", self._technical_analysis_node)
        workflow.add_node("sentiment_analysis", self._sentiment_analysis_node)
        workflow.add_node("fundamental_analysis", self._fundamental_analysis_node)
        workflow.add_node("synthesizer", self._synthesizer_node)
        
        # Set entry point
        workflow.set_entry_point("classifier")
        
        # Add conditional edges from classifier
        workflow.add_conditional_edges(
            "classifier",
            self._route_from_classifier,
            {
                "quick": "market_data",
                "deep": "market_data",
                "error": END
            }
        )
        
        # After market data, branch to parallel analysis
        workflow.add_edge("market_data", "technical_analysis")
        workflow.add_edge("market_data", "sentiment_analysis")
        
        # Deep analysis also includes fundamental
        workflow.add_conditional_edges(
            "technical_analysis",
            self._should_do_fundamental,
            {
                "yes": "fundamental_analysis",
                "no": "synthesizer"
            }
        )
        
        # Sentiment goes to synthesizer
        workflow.add_edge("sentiment_analysis", "synthesizer")
        
        # Fundamental goes to synthesizer
        workflow.add_edge("fundamental_analysis", "synthesizer")
        
        # Synthesizer is the end
        workflow.add_edge("synthesizer", END)
        
        # Compile with memory
        return workflow.compile(checkpointer=self.memory)
    
    # --- Node Functions ---
    
    def _classifier_node(self, state: AgentState) -> Dict[str, Any]:
        """Classify the analysis request and set up the workflow."""
        messages = [f"🔍 Classifier: Processing request for {state.get('tickers', [])}"]
        
        analysis_type = state.get("analysis_type", "quick_scan")
        
        return {
            "messages": messages,
            "analysis_type": analysis_type
        }
    
    def _market_data_node(self, state: AgentState) -> Dict[str, Any]:
        """Fetch market data for the requested tickers."""
        messages = ["📊 Market Data Agent: Fetching price and volume data..."]
        
        tickers = state.get("tickers", [])
        market = state.get("market", "us")
        
        try:
            # Use yfinance agent to get data for each ticker
            market_data = {}
            for ticker in tickers:
                data = self.base.yfinance_agent.get_full_analysis(ticker, market)
                market_data[ticker] = data
            
            messages.append(f"✅ Market Data Agent: Retrieved data for {len(tickers)} ticker(s)")
            
            return {
                "messages": messages,
                "market_data": market_data,
                "completed_agents": ["market_data"]
            }
        except Exception as e:
            return {
                "messages": [f"❌ Market Data Agent: Error - {str(e)}"],
                "error": str(e)
            }
    
    def _technical_analysis_node(self, state: AgentState) -> Dict[str, Any]:
        """Perform technical analysis."""
        messages = ["📈 Technical Analysis Agent: Computing indicators..."]
        
        market_data = state.get("market_data", {})
        technical_results = {}
        
        for ticker, data in market_data.items():
            hist = data.get("historical_data")
            if hist is not None and not hist.empty:
                # Extract key technical indicators
                latest = hist.iloc[-1] if len(hist) > 0 else {}
                technical_results[ticker] = {
                    "sma_fast": latest.get("trend_sma_fast"),
                    "sma_slow": latest.get("trend_sma_slow"),
                    "rsi": latest.get("momentum_rsi"),
                    "macd": latest.get("trend_macd"),
                    "bollinger_upper": latest.get("volatility_bbh"),
                    "bollinger_lower": latest.get("volatility_bbl"),
                }
        
        messages.append(f"✅ Technical Analysis Agent: Completed for {len(technical_results)} ticker(s)")
        
        return {
            "messages": messages,
            "technical_analysis": technical_results,
            "completed_agents": ["technical_analysis"]
        }
    
    def _sentiment_analysis_node(self, state: AgentState) -> Dict[str, Any]:
        """Analyze sentiment from social media and news."""
        messages = ["💬 Sentiment Agent: Analyzing social media and news..."]
        
        tickers = state.get("tickers", [])
        sentiment_results = {}
        
        for ticker in tickers:
            try:
                social = self.base.sentiment_agent.analyze(ticker)
                sentiment_results[ticker] = {
                    "social_sentiment": social,
                    "overall": social.get("Overall Social Sentiment", "Neutral")
                }
            except Exception as e:
                sentiment_results[ticker] = {"error": str(e)}
        
        messages.append(f"✅ Sentiment Agent: Completed for {len(sentiment_results)} ticker(s)")
        
        return {
            "messages": messages,
            "sentiment_analysis": sentiment_results,
            "completed_agents": ["sentiment_analysis"]
        }
    
    def _fundamental_analysis_node(self, state: AgentState) -> Dict[str, Any]:
        """Perform fundamental analysis for deep dives."""
        messages = ["📋 Fundamental Analysis Agent: Analyzing financials..."]
        
        market_data = state.get("market_data", {})
        fundamental_results = {}
        
        for ticker, data in market_data.items():
            snapshot = data.get("snapshot", {})
            fundamental_results[ticker] = {
                "pe_ratio": snapshot.get("trailingPE"),
                "pb_ratio": snapshot.get("priceToBook"),
                "dividend_yield": snapshot.get("dividendYield"),
                "market_cap": snapshot.get("marketCap"),
                "revenue_growth": snapshot.get("revenueGrowth"),
                "profit_margin": snapshot.get("profitMargins"),
                "sector": snapshot.get("sector"),
                "industry": snapshot.get("industry"),
            }
        
        messages.append(f"✅ Fundamental Analysis Agent: Completed for {len(fundamental_results)} ticker(s)")
        
        return {
            "messages": messages,
            "fundamental_analysis": fundamental_results,
            "completed_agents": ["fundamental_analysis"]
        }
    
    def _synthesizer_node(self, state: AgentState) -> Dict[str, Any]:
        """Synthesize all results into a final analysis."""
        messages = ["🧠 Synthesizer: Combining all analysis results..."]
        
        # Gather all results
        tickers = state.get("tickers", [])
        market_data = state.get("market_data", {})
        technical = state.get("technical_analysis", {})
        sentiment = state.get("sentiment_analysis", {})
        fundamental = state.get("fundamental_analysis", {})
        
        # Create synthesis for each ticker
        synthesis = {}
        for ticker in tickers:
            ticker_synthesis = {
                "ticker": ticker,
                "market_data": market_data.get(ticker, {}),
                "technical": technical.get(ticker, {}),
                "sentiment": sentiment.get(ticker, {}),
                "fundamental": fundamental.get(ticker, {}),
            }
            
            # Generate a simple recommendation based on signals
            signals = []
            
            # Technical signals
            tech = technical.get(ticker, {})
            if tech.get("sma_fast") and tech.get("sma_slow"):
                if tech["sma_fast"] > tech["sma_slow"]:
                    signals.append("Bullish: Price above long-term average")
                else:
                    signals.append("Bearish: Price below long-term average")
            
            # Sentiment signals
            sent = sentiment.get(ticker, {})
            overall_sent = sent.get("overall", "Neutral")
            if "Bullish" in overall_sent:
                signals.append("Bullish: Positive social sentiment")
            elif "Bearish" in overall_sent:
                signals.append("Bearish: Negative social sentiment")
            
            ticker_synthesis["signals"] = signals
            synthesis[ticker] = ticker_synthesis
        
        messages.append("✅ Synthesizer: Analysis complete!")
        
        return {
            "messages": messages,
            "synthesis": synthesis,
            "completed_agents": ["synthesizer"]
        }
    
    # --- Routing Functions ---
    
    def _route_from_classifier(self, state: AgentState) -> str:
        """Determine the next step based on analysis type."""
        if state.get("error"):
            return "error"
        
        analysis_type = state.get("analysis_type", "quick_scan")
        
        if analysis_type in ["deep_dive", "discovery"]:
            return "deep"
        return "quick"
    
    def _should_do_fundamental(self, state: AgentState) -> str:
        """Determine if fundamental analysis should be performed."""
        analysis_type = state.get("analysis_type", "quick_scan")
        
        if analysis_type in ["deep_dive", "discovery"]:
            return "yes"
        return "no"
    
    # --- Public API ---
    
    def run(
        self,
        tickers: List[str],
        market: str = "us",
        start_date: str = None,
        end_date: str = None,
        analysis_type: str = "quick_scan",
        user_query: str = None
    ) -> Dict[str, Any]:
        """
        Run the multi-agent analysis workflow.
        
        Args:
            tickers: List of stock tickers to analyze
            market: 'us' or 'india'
            start_date: Start date for historical data
            end_date: End date for historical data
            analysis_type: Type of analysis (quick_scan, deep_dive, etc.)
            user_query: Optional natural language query
            
        Returns:
            Dictionary containing all analysis results and synthesis
        """
        if not LANGGRAPH_AVAILABLE:
            # Fallback to simple sequential execution
            return self._run_fallback(tickers, market, start_date, end_date, analysis_type)
        
        import pandas as pd
        
        # Set default dates
        if not end_date:
            end_date = pd.Timestamp.now().strftime('%Y-%m-%d')
        if not start_date:
            start_date = (pd.Timestamp.now() - pd.DateOffset(years=1)).strftime('%Y-%m-%d')
        
        # Create initial state
        initial_state = {
            "tickers": tickers,
            "market": market,
            "start_date": start_date,
            "end_date": end_date,
            "analysis_type": analysis_type,
            "user_query": user_query,
            "messages": [],
            "market_data": None,
            "technical_analysis": None,
            "fundamental_analysis": None,
            "sentiment_analysis": None,
            "insider_analysis": None,
            "strategy_results": None,
            "synthesis": None,
            "recommendation": None,
            "error": None,
            "completed_agents": [],
        }
        
        # Run the graph
        config = {"configurable": {"thread_id": "analysis_1"}}
        
        try:
            final_state = self.graph.invoke(initial_state, config)
            return {
                "success": True,
                "tickers": tickers,
                "analysis_type": analysis_type,
                "messages": final_state.get("messages", []),
                "synthesis": final_state.get("synthesis", {}),
                "completed_agents": final_state.get("completed_agents", []),
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "tickers": tickers,
            }
    
    def _run_fallback(
        self,
        tickers: List[str],
        market: str,
        start_date: str,
        end_date: str,
        analysis_type: str
    ) -> Dict[str, Any]:
        """Fallback to sequential execution when langgraph is not available."""
        import pandas as pd
        
        if not end_date:
            end_date = pd.Timestamp.now().strftime('%Y-%m-%d')
        if not start_date:
            start_date = (pd.Timestamp.now() - pd.DateOffset(years=1)).strftime('%Y-%m-%d')
        
        results = {
            "success": True,
            "tickers": tickers,
            "analysis_type": analysis_type,
            "messages": ["Running in fallback mode (langgraph not installed)"],
            "synthesis": {},
        }
        
        for ticker in tickers:
            try:
                data = self.base.run_deep_dive_analysis(ticker, start_date, end_date, market)
                results["synthesis"][ticker] = data
            except Exception as e:
                results["synthesis"][ticker] = {"error": str(e)}
        
        return results
    
    def get_graph_visualization(self) -> Optional[str]:
        """Get a Mermaid diagram of the agent graph."""
        if not LANGGRAPH_AVAILABLE or not self.graph:
            return None
        
        try:
            return self.graph.get_graph().draw_mermaid()
        except:
            return None


# Convenience function to create the orchestrator
def create_langgraph_orchestrator(base_orchestrator) -> LangGraphOrchestrator:
    """Factory function to create a LangGraph orchestrator."""
    return LangGraphOrchestrator(base_orchestrator)
