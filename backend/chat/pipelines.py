"""
Pipeline Manager - CrewAI Crews for each analysis pipeline
Integrates with existing services for actual execution.
"""
# Suppress warnings before any imports
import warnings
warnings.filterwarnings("ignore", category=FutureWarning)
warnings.filterwarnings("ignore", category=DeprecationWarning, module="google")

import os
import asyncio
import json
import pandas as pd
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

# Optional: structured DDG news for relevance filtering
try:
    from duckduckgo_search import DDGS
    DDGS_AVAILABLE = True
except Exception:
    DDGS_AVAILABLE = False

# Load environment variables
try:
    from dotenv import load_dotenv
    env_path = Path(__file__).parent.parent / ".env"
    load_dotenv(env_path)
except ImportError:
    pass

# Try to import Gemini for structured output formatting
try:
    import google.generativeai as genai
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
    if GEMINI_API_KEY:
        genai.configure(api_key=GEMINI_API_KEY)
        GEMINI_AVAILABLE = True
    else:
        GEMINI_AVAILABLE = False
except ImportError:
    GEMINI_AVAILABLE = False
    genai = None

# Try Groq as fallback for formatting
try:
    from groq import Groq
    GROQ_API_KEY = os.getenv("GROQ_API_KEY")
    GROQ_AVAILABLE = bool(GROQ_API_KEY)
except ImportError:
    GROQ_AVAILABLE = False
    Groq = None

# Try to import CrewAI (optional - fallback to direct service calls)
try:
    from crewai import Agent, Task, Crew, Process
    CREWAI_AVAILABLE = True
except ImportError:
    CREWAI_AVAILABLE = False
    print("⚠️ CrewAI not installed - using direct service calls")

# Import existing services (Unified Architecture)
try:
    from backend.services.emotion_advisor_service import analyze_emotion_safe_advice
    from backend.services.market_data import market_service
    # Keep function names if used in localized code
    get_history = market_service.get_history
    get_company_snapshot = market_service.get_fundamentals
    format_ticker = market_service.normalize_ticker
    get_comprehensive_stock_data = market_service.get_fundamentals # Wait, check if this is correct
    
    from backend.services.backtest_service import run_backtest_service
    from backend.services.emotion_data_scraper import EmotionDataScraper
    from backend.services.company_resolver import resolve_company_identity
    from backend.tools.duckduckgo_mcp import DuckDuckGoMCPTool
except ImportError:
    # Fallback for localized testing (To be retired)
    from services.emotion_advisor_service import analyze_emotion_safe_advice
    from backend.services.market_data import market_service as ms
    get_history = ms.get_history
    get_company_snapshot = ms.get_fundamentals
    format_ticker = ms.normalize_ticker
    get_comprehensive_stock_data = ms.get_fundamentals
    
    from services.backtest_service import run_backtest_service
    from services.emotion_data_scraper import EmotionDataScraper
    from services.company_resolver import resolve_company_identity
    from tools.duckduckgo_mcp import DuckDuckGoMCPTool

# Try to import wealth orchestrator
try:
    from backend.finverse_integration.agents.wealth_orchestrator import WealthOrchestrator
    WEALTH_AVAILABLE = True
except ImportError:
    try:
        from finverse_integration.agents.wealth_orchestrator import WealthOrchestrator
        WEALTH_AVAILABLE = True
    except ImportError:
        WEALTH_AVAILABLE = False


@dataclass
class PipelineResult:
    """Result from a pipeline execution"""
    pipeline: str
    success: bool
    data: Dict[str, Any]
    summary: str
    timestamp: str
    execution_time: float


class PipelineManager:
    """
    Manages and executes analysis pipelines.
    Uses CrewAI when available, falls back to direct service calls.
    Uses Gemini for structured output formatting when available.
    """
    
    def __init__(self, groq_api_key: Optional[str] = None, use_gemini_formatting: bool = True):
        self.groq_api_key = groq_api_key or os.getenv("GROQ_API_KEY")
        self.use_gemini_formatting = use_gemini_formatting and GEMINI_AVAILABLE
        # self.emotion_service - using function directly
        # self.data_loader - using functions directly
        self.data_scraper = EmotionDataScraper()
        self.ddg_tool = DuckDuckGoMCPTool()
        
        # Initialize Gemini model for formatting
        if self.use_gemini_formatting:
            try:
                model_name = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")
                self.gemini_model = genai.GenerativeModel(model_name)
            except Exception:
                self.gemini_model = None
                self.use_gemini_formatting = False
        else:
            self.gemini_model = None
        
        # Initialize wealth orchestrator if available
        self.wealth_orchestrator = WealthOrchestrator() if WEALTH_AVAILABLE else None
        
        # CrewAI agents (lazy init)
        self._crews_initialized = False
        self._agents = {}
        self._crews = {}
    
    def _init_crews(self):
        """Initialize CrewAI agents and crews"""
        if not CREWAI_AVAILABLE or self._crews_initialized:
            return
            
        # LLM config for Groq
        llm_config = {
            "model": "groq/llama-3.1-70b-versatile",
            "api_key": self.groq_api_key,
        }
        
        # Define agents
        self._agents["emotional_analyst"] = Agent(
            role="Emotional Trading Analyst",
            goal="Analyze user emotions and detect behavioral biases in trading decisions",
            backstory="""You are an expert in behavioral finance and trading psychology.
            You help retail investors avoid emotional trading mistakes like panic selling,
            FOMO buying, and revenge trading. You provide calm, rational advice.""",
            verbose=True,
            llm=llm_config
        )
        
        self._agents["stock_analyst"] = Agent(
            role="Stock Research Analyst",
            goal="Provide comprehensive stock analysis including fundamentals, technicals, and news",
            backstory="""You are a seasoned equity research analyst with deep knowledge
            of financial markets. You analyze stocks objectively based on data, not hype.""",
            verbose=True,
            llm=llm_config
        )
        
        self._agents["wealth_advisor"] = Agent(
            role="Wealth Management Advisor",
            goal="Help users build long-term wealth through proper asset allocation",
            backstory="""You are a certified financial planner focused on helping
            retail investors build wealth. You emphasize diversification, low costs,
            and long-term thinking over market timing.""",
            verbose=True,
            llm=llm_config
        )
        
        self._crews_initialized = True
    
    async def run_emotion_pipeline(
        self,
        ticker: str,
        user_message: str,
        market: str = "US",
        user_id: str = "default"
    ) -> PipelineResult:
        """Run the emotional advisor pipeline"""
        start_time = datetime.now()
        
        try:
            # Use existing emotion advisor service function
            # analyze_emotion_safe_advice is synchronous, so we run it in a thread
            result = await asyncio.to_thread(
                analyze_emotion_safe_advice,
                message=user_message,
                tickers=[ticker] if ticker else None,
                market=market,
                user_id=user_id,
                check_cooldown=True,
                auto_create_cooldown=True,
                include_comprehensive_scrape=True
            )
            
            # Create summary
            summary = await self._create_emotion_summary_professional(result)
            
            return PipelineResult(
                pipeline="emotion",
                success=True,
                data=result,
                summary=summary,
                timestamp=datetime.now().isoformat(),
                execution_time=(datetime.now() - start_time).total_seconds()
            )
            
        except Exception as e:
            return PipelineResult(
                pipeline="emotion",
                success=False,
                data={"error": str(e)},
                summary=f"❌ Emotion analysis failed: {str(e)}",
                timestamp=datetime.now().isoformat(),
                execution_time=(datetime.now() - start_time).total_seconds()
            )
    
    async def run_stock_info_pipeline(
        self,
        ticker: str,
        market: str = "US",
        include_technicals: bool = True,
        include_web_search: bool = True,
        include_backtest: bool = True,
        user_message: str = ""
    ) -> PipelineResult:
        """Run the enhanced stock information pipeline with comprehensive data, technical indicators, and web search"""
        start_time = datetime.now()
        
        try:
            # Get comprehensive stock data (includes ALL yfinance data + news)
            stock_data = await asyncio.to_thread(
                get_comprehensive_stock_data,
                ticker=ticker,
                market=market
            )
            
            # Get company name for better search
            company_name = stock_data.get("company_name", ticker)
            
            # Enhanced web search for better news relevance
            if include_web_search:
                web_news = await self._search_stock_news(ticker, company_name, market)
                stock_data["web_news"] = web_news

                ddg_queries = await self._generate_ddg_queries(ticker, company_name, market, user_message)
                ddg_results = await self._run_ddg_queries(ddg_queries)
                stock_data["ddg_research"] = {
                    "queries": ddg_queries,
                    "results": ddg_results
                }
            
            # Calculate technical indicators
            if include_technicals:
                technical_data = await self._calculate_technicals(ticker, market)
                stock_data["technical_indicators"] = technical_data

            # Risk metrics (Sharpe) from price history
            sharpe = await self._calculate_sharpe_ratio(ticker, market)
            stock_data["risk_metrics"] = {"sharpe_ratio": sharpe}

            # Backtest pipeline (single strategy baseline)
            if include_backtest:
                backtest = await asyncio.to_thread(
                    run_backtest_service,
                    symbol=ticker,
                    strategy_name="momentum",
                    range_period="1y",
                    interval="1d",
                    initial_capital=100000
                )
                stock_data["backtest"] = {
                    "strategy": "momentum",
                    "metrics": backtest.get("metrics"),
                    "error": backtest.get("error")
                }
            
            # Also try to get additional social sentiment
            social_data = self.data_scraper.scrape_social_sentiment(ticker)
            
            # Merge social data into result
            stock_data["social_sentiment"] = social_data.get("reddit", {})
            stock_data["user_question"] = user_message
            
            summary = await self._create_stock_summary_enhanced(stock_data)
            
            return PipelineResult(
                pipeline="stock_info",
                success=True,
                data=stock_data,
                summary=summary,
                timestamp=datetime.now().isoformat(),
                execution_time=(datetime.now() - start_time).total_seconds()
            )
            
        except Exception as e:
            return PipelineResult(
                pipeline="stock_info",
                success=False,
                data={"error": str(e)},
                summary=f"❌ Stock analysis failed: {str(e)}",
                timestamp=datetime.now().isoformat(),
                execution_time=(datetime.now() - start_time).total_seconds()
            )
    
    async def run_wealth_pipeline(
        self,
        user_input: str,
        market: str = "US"
    ) -> PipelineResult:
        """Run the wealth management pipeline"""
        start_time = datetime.now()
        
        try:
            if not WEALTH_AVAILABLE or not self.wealth_orchestrator:
                return PipelineResult(
                    pipeline="wealth",
                    success=False,
                    data={"error": "Wealth advisor not available"},
                    summary="❌ Wealth advisor module not loaded",
                    timestamp=datetime.now().isoformat(),
                    execution_time=0
                )
            
            # Run wealth analysis
            result = await asyncio.to_thread(
                self.wealth_orchestrator.analyze,
                user_input=user_input,
                market=market
            )
            
            summary = self._create_wealth_summary(result)
            
            return PipelineResult(
                pipeline="wealth",
                success=True,
                data=result,
                summary=summary,
                timestamp=datetime.now().isoformat(),
                execution_time=(datetime.now() - start_time).total_seconds()
            )
            
        except Exception as e:
            return PipelineResult(
                pipeline="wealth",
                success=False,
                data={"error": str(e)},
                summary=f"❌ Wealth analysis failed: {str(e)}",
                timestamp=datetime.now().isoformat(),
                execution_time=(datetime.now() - start_time).total_seconds()
            )
    
    async def run_combined_pipeline(
        self,
        ticker: str,
        user_message: str,
        market: str = "US",
        user_id: str = "default",
        pipelines: List[str] = None
    ) -> Dict[str, PipelineResult]:
        """Run multiple pipelines in parallel"""
        pipelines = pipelines or ["emotion", "stock_info"]
        results = {}
        
        tasks = []
        if "emotion" in pipelines:
            tasks.append(("emotion", self.run_emotion_pipeline(ticker, user_message, market, user_id)))
        if "stock_info" in pipelines:
            tasks.append(("stock_info", self.run_stock_info_pipeline(ticker, market, user_message=user_message)))
        if "wealth" in pipelines:
            tasks.append(("wealth", self.run_wealth_pipeline(user_message, market)))
        
        # Run in parallel
        task_results = await asyncio.gather(*[t[1] for t in tasks], return_exceptions=True)
        
        for (name, _), result in zip(tasks, task_results):
            if isinstance(result, Exception):
                results[name] = PipelineResult(
                    pipeline=name,
                    success=False,
                    data={"error": str(result)},
                    summary=f"❌ {name} pipeline failed: {str(result)}",
                    timestamp=datetime.now().isoformat(),
                    execution_time=0
                )
            else:
                results[name] = result
        
        return results
    
    def _create_emotion_summary(self, result: Dict) -> str:
        """Create human-readable emotion analysis summary"""
        try:
            if not isinstance(result, dict):
                return "Emotion analysis completed. Raw data unavailable."
            
            # Get bias analysis from correct key with None safety
            bias_analysis = result.get("bias_analysis")
            if not isinstance(bias_analysis, dict):
                bias_analysis = {}
            
            bias = bias_analysis.get("dominant_bias") or "calm"
            intensity = bias_analysis.get("emotion_intensity") or 0
            emotion_label = bias_analysis.get("emotion_label") or "calm"
            biases = bias_analysis.get("biases") or []
            
            # Get action recommendation from correct key
            recommendation = result.get("action_recommendation") or "HOLD"
            
            # Emoji based on recommendation
            emoji = "🟢" if recommendation == "BUY" else "🔴" if recommendation == "SELL" else "🟡"
            
            # Format bias display
            bias_display = bias.replace('_', ' ').title() if bias else emotion_label.title()
            
            summary = f"""# 🧠 Emotional Analysis Complete

## Emotion Profile
| Metric | Value |
|--------|-------|
| **Detected Emotion** | {emotion_label.title()} |
| **Dominant Bias** | {bias_display} |
| **Intensity** | {intensity:.0%} |
| **Recommendation** | {emoji} {recommendation} |

"""
            # Add all detected biases
            if biases and isinstance(biases, list):
                summary += "## 🎯 Biases Detected\n"
                for b in biases:
                    if isinstance(b, dict):
                        bias_name = (b.get('bias') or 'Unknown').replace('_', ' ').title()
                        tone = b.get('tone') or 'unknown'
                        score = b.get('score') or b.get('weight') or 0
                        summary += f"- **{bias_name}** (tone: {tone}, score: {score:.2f})\n"
                summary += "\n"
            
            # Add guidance from advisor
            guidance = result.get("guidance") or ""
            if guidance:
                if isinstance(guidance, list):
                    summary += "## 💡 Guidance\n"
                    for item in guidance:
                        if isinstance(item, dict):
                            title = item.get("title") or "Guidance"
                            message = item.get("message") or ""
                            summary += f"- **{title}**: {message}\n"
                        else:
                            summary += f"- {item}\n"
                    summary += "\n"
                else:
                    summary += f"## 💡 Guidance\n{guidance}\n\n"
            
            # Add nudge
            nudge = result.get("nudge") or ""
            if nudge:
                summary += f"## 🔔 Nudge\n{nudge}\n\n"
            
            # Add market context
            market_context = result.get("market_context")
            if market_context and isinstance(market_context, dict):
                summary += "## 📊 Market Context\n"
                summary += "| Ticker | Price | 1M Return | Volatility | Drawdown |\n"
                summary += "|--------|-------|-----------|------------|----------|\n"
                for ticker, metrics in market_context.items():
                    if isinstance(metrics, dict):
                        price = metrics.get("last_price") or 0
                        ret_1m = metrics.get("return_1m_pct") or 0
                        vol = metrics.get("volatility_30d_pct") or 0
                        dd = metrics.get("current_drawdown_pct") or 0
                        ret_emoji = "🟢" if ret_1m >= 0 else "🔴"
                        summary += f"| **{ticker}** | ${price:,.2f} | {ret_emoji} {ret_1m:+.2f}% | {vol:.1f}% | {dd:.2f}% |\n"
                summary += "\n"
            
            # Add historical context
            historical = result.get("historical_context")
            if historical and isinstance(historical, list):
                summary += "## 📜 Historical Context\n"
                for note in historical:
                    if note:  # Skip None or empty strings
                        summary += f"- {note}\n"
                summary += "\n"
            
            # Add news context
            news_context = result.get("news_context")
            if news_context and isinstance(news_context, dict):
                summary += "## 📰 Recent News\n"
                for ticker, news_data in news_context.items():
                    if isinstance(news_data, dict):
                        headlines = news_data.get("headlines") or []
                        for h in headlines[:3]:  # Limit to 3
                            if isinstance(h, dict):
                                title = h.get('title') or 'No title'
                                summary += f"- {title}\n"
                            elif h:  # String
                                summary += f"- {h}\n"
                summary += "\n"
            
            # Add cooldown warning if locked
            cooldown = result.get("cooldown_lock")
            if cooldown and isinstance(cooldown, dict):
                status = cooldown.get("status")
                if status and isinstance(status, dict) and status.get("active"):
                    remaining = status.get('time_remaining_hours') or 24
                    summary += f"\n⚠️ **24-Hour Cooldown Active** ({remaining:.1f}h remaining) - Consider sleeping on this decision.\n"
            
            return summary
            
        except Exception as e:
            return f"Emotion analysis completed. Error formatting: {str(e)}"
    
    async def _create_emotion_summary_professional(self, result: Dict) -> str:
        """Create professional emotion analysis summary without emojis"""
        try:
            if not isinstance(result, dict):
                return "Emotion analysis completed. Raw data unavailable."
            
            # Get bias analysis from correct key with None safety
            bias_analysis = result.get("bias_analysis")
            if not isinstance(bias_analysis, dict):
                bias_analysis = {}
            
            bias = bias_analysis.get("dominant_bias") or "calm"
            intensity = bias_analysis.get("emotion_intensity") or 0
            emotion_label = bias_analysis.get("emotion_label") or "calm"
            biases = bias_analysis.get("biases") or []
            
            # Get action recommendation from correct key
            recommendation = result.get("action_recommendation") or "HOLD"
            
            # Format bias display
            bias_display = bias.replace('_', ' ').title() if bias else emotion_label.title()
            
            summary = f"""EMOTIONAL TRADING ANALYSIS

EMOTION PROFILE
Detected Emotion: {emotion_label.title()}
Dominant Bias: {bias_display}
Intensity Level: {intensity:.0%}
Recommendation: {recommendation}

"""
            
            # Add all detected biases
            if biases and isinstance(biases, list):
                summary += "DETECTED BIASES\n"
                for b in biases:
                    if isinstance(b, dict):
                        bias_name = (b.get('bias') or 'Unknown').replace('_', ' ').title()
                        tone = b.get('tone') or 'unknown'
                        score = b.get('score') or b.get('weight') or 0
                        summary += f"{bias_name} (Tone: {tone}, Score: {score:.2f})\n"
                summary += "\n"
            
            # Add guidance from advisor
            guidance = result.get("guidance") or ""
            if guidance:
                if isinstance(guidance, list):
                    summary += "BEHAVIORAL GUIDANCE\n"
                    for item in guidance:
                        if isinstance(item, dict):
                            title = item.get("title") or "Guidance"
                            message = item.get("message") or ""
                            summary += f"{title}: {message}\n"
                        else:
                            summary += f"{item}\n"
                    summary += "\n"
                else:
                    summary += f"BEHAVIORAL GUIDANCE\n{guidance}\n\n"
            
            # Add nudge
            nudge = result.get("nudge") or ""
            if nudge:
                summary += f"ADVISORY NOTE\n{nudge}\n\n"
            
            # Add market context
            market_context = result.get("market_context")
            if market_context and isinstance(market_context, dict):
                summary += "MARKET CONTEXT\n"
                for ticker, metrics in market_context.items():
                    if isinstance(metrics, dict):
                        price = metrics.get("last_price") or 0
                        ret_1m = metrics.get("return_1m_pct") or 0
                        vol = metrics.get("volatility_30d_pct") or 0
                        dd = metrics.get("current_drawdown_pct") or 0
                        summary += f"{ticker}: Price=${price:,.2f}, 1M Return={ret_1m:+.2f}%, Volatility={vol:.1f}%, Drawdown={dd:.2f}%\n"
                summary += "\n"
            
            # Add historical context
            historical = result.get("historical_context")
            if historical and isinstance(historical, list):
                summary += "HISTORICAL CONTEXT\n"
                for note in historical:
                    if note:  # Skip None or empty strings
                        summary += f"- {note}\n"
                summary += "\n"
            
            # Add news context
            news_context = result.get("news_context")
            if news_context and isinstance(news_context, dict):
                summary += "RECENT NEWS\n"
                for ticker, news_data in news_context.items():
                    if isinstance(news_data, dict):
                        headlines = news_data.get("headlines") or []
                        for h in headlines[:3]:  # Limit to 3
                            if isinstance(h, dict):
                                title = h.get('title') or 'No title'
                                summary += f"- {title}\n"
                            elif h:  # String
                                summary += f"- {h}\n"
                summary += "\n"
            
            # Add cooldown warning if locked
            cooldown = result.get("cooldown_lock")
            if cooldown and isinstance(cooldown, dict):
                status = cooldown.get("status")
                if status and isinstance(status, dict) and status.get("active"):
                    remaining = status.get('time_remaining_hours') or 24
                    summary += f"\nCOOLDOWN ACTIVE: {remaining:.1f} hours remaining. Consider waiting before making decisions.\n"
            
            # Normalize to remove any formatting
            summary = await self._normalize_text(summary)
            
            return summary
            
        except Exception as e:
            return f"Emotion analysis completed. Error formatting: {str(e)}"
    
    def _create_stock_summary(self, data: Dict) -> str:
        """Create comprehensive human-readable stock info summary"""
        try:
            ticker = data.get("symbol", data.get("ticker", "Unknown"))
            company = data.get("company_name", ticker)
            
            # Price Data
            current_price = data.get("current_price", 0)
            daily_change = data.get("daily_change", 0)
            daily_change_pct = data.get("daily_change_pct", 0)
            
            # Currency symbol
            currency = data.get("currency", "$")
            
            # Price direction emoji
            change_emoji = "📈" if daily_change_pct > 0 else "📉" if daily_change_pct < 0 else "➡️"
            
            summary = f"""# 📊 {company} ({ticker})

## 💰 Price Data
| Metric | Value |
|--------|-------|
| **Current Price** | {currency}{current_price:,.2f} |
| **Daily Change** | {change_emoji} {currency}{daily_change:+,.2f} ({daily_change_pct:+.2f}%) |
| **Previous Close** | {currency}{data.get('previous_close', 0):,.2f} |
| **Open** | {currency}{data.get('open', 0):,.2f} |
| **Day High** | {currency}{data.get('day_high', 0):,.2f} |
| **Day Low** | {currency}{data.get('day_low', 0):,.2f} |
| **52-Week High** | {currency}{data.get('week_52_high', 0):,.2f} |
| **52-Week Low** | {currency}{data.get('week_52_low', 0):,.2f} |
| **Volume** | {data.get('volume', 0):,} |
| **Avg Volume** | {data.get('avg_volume', 0):,} |

## 📈 Returns
"""
            # Add returns
            returns = data.get("returns", {})
            if returns:
                for period, value in returns.items():
                    period_name = period.replace("_", " ").title()
                    ret_emoji = "🟢" if value > 0 else "🔴" if value < 0 else "⚪"
                    summary += f"- {ret_emoji} **{period_name}:** {value:+.2f}%\n"
            
            summary += f"""
## 🏢 Company Info
- **Sector:** {data.get('sector', 'N/A')}
- **Industry:** {data.get('industry', 'N/A')}
- **Exchange:** {data.get('exchange', 'N/A')}
- **Employees:** {data.get('employees', 0):,}
- **Country:** {data.get('country', 'N/A')}

## 📊 Valuation
| Metric | Value |
|--------|-------|
| **Market Cap** | {currency}{data.get('market_cap', 0) / 1e9:.2f}B |
| **P/E (Trailing)** | {data.get('trailing_pe', 0):.2f} |
| **P/E (Forward)** | {data.get('forward_pe', 0):.2f} |
| **PEG Ratio** | {data.get('peg_ratio', 0):.2f} |
| **Price/Book** | {data.get('price_to_book', 0):.2f} |
| **Price/Sales** | {data.get('price_to_sales', 0):.2f} |
| **EV/Revenue** | {data.get('ev_to_revenue', 0):.2f} |
| **EV/EBITDA** | {data.get('ev_to_ebitda', 0):.2f} |

## 💵 Profitability & Growth
| Metric | Value |
|--------|-------|
| **Profit Margin** | {data.get('profit_margin', 0) * 100:.1f}% |
| **Operating Margin** | {data.get('operating_margin', 0) * 100:.1f}% |
| **ROE** | {data.get('return_on_equity', 0) * 100:.1f}% |
| **ROA** | {data.get('return_on_assets', 0) * 100:.1f}% |
| **Revenue Growth** | {data.get('revenue_growth', 0) * 100:.1f}% |
| **Earnings Growth** | {data.get('earnings_growth', 0) * 100:.1f}% |

## 💳 Financial Health
| Metric | Value |
|--------|-------|
| **Total Cash** | {currency}{data.get('total_cash', 0) / 1e9:.2f}B |
| **Total Debt** | {currency}{data.get('total_debt', 0) / 1e9:.2f}B |
| **Debt/Equity** | {data.get('debt_to_equity', 0):.2f} |
| **Current Ratio** | {data.get('current_ratio', 0):.2f} |
| **Free Cash Flow** | {currency}{data.get('free_cash_flow', 0) / 1e9:.2f}B |

## 📈 Per Share Data
| Metric | Value |
|--------|-------|
| **EPS (Trailing)** | {currency}{data.get('eps_trailing', 0):.2f} |
| **EPS (Forward)** | {currency}{data.get('eps_forward', 0):.2f} |
| **Book Value** | {currency}{data.get('book_value', 0):.2f} |

## 💸 Dividends
| Metric | Value |
|--------|-------|
| **Dividend Rate** | {currency}{data.get('dividend_rate', 0):.2f} |
| **Dividend Yield** | {data.get('dividend_yield', 0) * 100 if data.get('dividend_yield') else 0:.2f}% |
| **Payout Ratio** | {data.get('payout_ratio', 0) * 100 if data.get('payout_ratio') else 0:.1f}% |

## 🎯 Analyst Ratings
| Metric | Value |
|--------|-------|
| **Rating** | {data.get('analyst_rating', 'N/A').upper()} |
| **Rating Score** | {data.get('analyst_rating_score', 0):.1f}/5 |
| **Target High** | {currency}{data.get('target_high', 0):,.2f} |
| **Target Mean** | {currency}{data.get('target_mean', 0):,.2f} |
| **Target Low** | {currency}{data.get('target_low', 0):,.2f} |
| **# of Analysts** | {data.get('num_analysts', 0)} |

## ⚠️ Risk Metrics
| Metric | Value |
|--------|-------|
| **Beta** | {data.get('beta', 0):.2f} |
| **Short Ratio** | {data.get('short_ratio', 0):.2f} |
| **Short % of Float** | {data.get('short_pct_of_float', 0) * 100 if data.get('short_pct_of_float') else 0:.2f}% |
| **Institutional Ownership** | {data.get('institution_ownership', 0) * 100 if data.get('institution_ownership') else 0:.1f}% |
| **Insider Ownership** | {data.get('insider_ownership', 0) * 100 if data.get('insider_ownership') else 0:.1f}% |

"""
            # Add news section
            news = data.get("news", [])
            if news:
                summary += "## 📰 Recent News\n"
                for item in news[:5]:
                    title = item.get('title', 'No title')
                    publisher = item.get('publisher', '')
                    link = item.get('link', '')
                    if link:
                        summary += f"- [{title}]({link}) - *{publisher}*\n"
                    else:
                        summary += f"- {title} - *{publisher}*\n"
            
            # Add description snippet
            description = data.get("description", "")
            if description:
                summary += f"\n## 📝 About\n{description}\n"
            
            return summary
            
        except Exception as e:
            return f"Stock analysis completed. Error formatting: {str(e)}. Check data for details."
    
    def _create_wealth_summary(self, result: Dict) -> str:
        """Create human-readable wealth advice summary"""
        try:
            allocation = result.get("allocation", {}) or result.get("allocation_strategy", {})
            report_text = result.get("report") or result.get("investment_report") or ""
            selected_stocks = result.get("selected_stocks") or []
            primary_stock = result.get("selected_stock") or (selected_stocks[0] if selected_stocks else None)
            
            summary = "**💰 Wealth Management Advice**\n\n"
            
            if allocation:
                summary += "**Recommended Allocation:**\n"
                for asset, pct in allocation.items():
                    summary += f"• {asset}: {pct:.0%}\n"

            if primary_stock:
                ticker = primary_stock.get("Ticker") or primary_stock.get("ticker")
                if ticker:
                    summary += f"\n**Top Pick:** {ticker}\n"
            
            if report_text:
                summary += f"\n{report_text[:500]}..."
            
            return summary
            
        except Exception:
            return "Wealth analysis completed. Check data for details."
    
    async def format_with_gemini(
        self, 
        pipeline_type: str,
        raw_data: Dict[str, Any],
        user_message: str = ""
    ) -> str:
        """
        Use Gemini to create a beautifully structured response from raw pipeline data.
        
        Args:
            pipeline_type: Type of analysis (emotion, stock_info, wealth)
            raw_data: Raw data from the pipeline
            user_message: Original user question for context
            
        Returns:
            Gemini-formatted markdown response
        """
        if not self.use_gemini_formatting or not self.gemini_model:
            # Fallback to basic formatting
            if pipeline_type == "emotion":
                return self._create_emotion_summary(raw_data)
            elif pipeline_type == "stock_info":
                return self._create_stock_summary(raw_data)
            elif pipeline_type == "wealth":
                return self._create_wealth_summary(raw_data)
            return json.dumps(raw_data, indent=2)
        
        # Build prompt based on pipeline type
        prompts = {
            "emotion": """You are a financial advisor assistant. Format this emotional trading analysis into a clear, helpful response.

User asked: "{user_message}"

Raw Analysis Data:
{data}

Create a response that:
1. Acknowledges their emotional state empathetically
2. Shows the detected bias and intensity clearly
3. Provides the recommendation with context
4. Gives 2-3 actionable next steps
5. Uses emojis sparingly but effectively
6. Keeps the tone calm and supportive

Format as clean markdown. Be concise but thorough.""",


            "stock_info": """You are a stock analyst assistant. Format this stock analysis into a clear investor-friendly response.

User asked: "{user_message}"

Raw Stock Data:
{data}

Create a response that:
1. Shows current price and daily change prominently
2. Summarizes key metrics (if available)
3. Lists 2-3 recent news headlines (if available)
4. Highlights any user-specific constraints or details mentioned in the question
5. Provides a brief technical outlook
6. Incorporates Sharpe ratio and backtest summary (if available)
7. Gives a justified action recommendation (Buy/Hold/Sell) with reasoning
8. Ends with "Key Considerations" bullet points

Format as clean markdown. Be data-driven and objective.""",


            "wealth": """You are a wealth management advisor. Format this portfolio analysis into clear actionable advice.

User asked: "{user_message}"

Raw Wealth Data:
{data}

Create a response that:
1. Shows recommended asset allocation clearly
2. Explains the rationale briefly
3. Lists 2-3 specific action items
4. Notes any risks or caveats
5. Uses emojis for key sections
6. Maintains a long-term perspective

Format as clean markdown. Be prudent and educational.""",


            "combined": """You are a comprehensive financial advisor. Format this multi-dimensional analysis into a unified response.

User asked: "{user_message}"

Raw Analysis Data:
{data}

Create a response that:
1. Synthesizes emotional, technical, and strategic insights
2. Shows the key data points prominently
3. Provides a clear recommendation with confidence level
4. Lists specific action items
5. Addresses any emotional concerns detected
6. Uses clear section headers with emojis

Format as clean markdown. Be thorough but scannable."""
        }
        
        prompt_template = prompts.get(pipeline_type, prompts["combined"])
        
        # Prepare data for prompt (limit size)
        data_str = json.dumps(raw_data, indent=2, default=str)
        if len(data_str) > 4000:
            # Truncate large data
            data_str = data_str[:4000] + "\n... (truncated)"
        
        prompt = prompt_template.format(
            user_message=user_message[:500] if user_message else "Analyze this stock",
            data=data_str
        )
        
        try:
            response = await asyncio.to_thread(
                self.gemini_model.generate_content,
                prompt
            )
            return response.text
        except Exception as e:
            # Fallback to basic formatting
            print(f"⚠️ Gemini formatting failed: {e}")
            if pipeline_type == "emotion":
                return self._create_emotion_summary(raw_data)
            elif pipeline_type == "stock_info":
                return self._create_stock_summary(raw_data)
            elif pipeline_type == "wealth":
                return self._create_wealth_summary(raw_data)
            return f"Analysis complete. Raw data available.\n\n```json\n{data_str[:1000]}\n```"
    
    async def _search_stock_news(self, ticker: str, company_name: str, market: str) -> Dict[str, Any]:
        """Search for relevant stock news using DuckDuckGo"""
        try:
            identity = resolve_company_identity(ticker, market)
            company = identity.get("company") or company_name or ticker
            
            if market.upper() in {"IN", "INDIA"}:
                preferred_sites = [
                    "economictimes.indiatimes.com",
                    "livemint.com",
                    "moneycontrol.com",
                    "reuters.com",
                    "bloomberg.com",
                ]
            else:
                preferred_sites = [
                    "reuters.com",
                    "bloomberg.com",
                    "wsj.com",
                    "marketwatch.com",
                    "finance.yahoo.com",
                ]
            
            site_filter = " OR ".join([f"site:{d}" for d in preferred_sites])
            queries = [
                f"\"{company}\" {ticker} {site_filter}",
                f"\"{company}\" earnings {site_filter}",
            ]
            
            def score_news_relevance(article: Dict[str, Any], company_name: str, symbol: str) -> int:
                text = f"{article.get('title','')} {article.get('body','')} {article.get('snippet','')}".lower()
                score = 0
                if company_name.lower() in text:
                    score += 2
                if symbol.lower() in text:
                    score += 1
                if "earnings" in text or "results" in text or "guidance" in text:
                    score += 1
                return score
            
            all_results = []
            for query in queries:
                if not DDGS_AVAILABLE:
                    break
                try:
                    def _ddg_news(q: str):
                        with DDGS() as ddgs:
                            return list(ddgs.news(keywords=q, max_results=6))

                    results = await asyncio.to_thread(_ddg_news, query)
                    if results:
                        all_results.extend(results)
                except Exception as e:
                    print(f"DDG news search error for {query}: {e}")
            
            if not all_results:
                return {
                    "available": False,
                    "reason": "No structured news results available",
                    "ticker": ticker,
                    "company": company,
                }
            
            filtered = []
            for item in all_results:
                score = score_news_relevance(item, company, ticker)
                if score >= 2:
                    filtered.append({
                        "title": item.get("title", ""),
                        "url": item.get("url", ""),
                        "source": item.get("source", ""),
                        "date": item.get("date", ""),
                        "snippet": item.get("body", ""),
                        "score": score,
                    })
            
            filtered.sort(key=lambda x: x.get("score", 0), reverse=True)
            
            return {
                "available": len(filtered) > 0,
                "ticker": ticker,
                "company": company,
                "query_sites": preferred_sites,
                "results": filtered[:8],
                "total_found": len(all_results),
                "total_filtered": len(filtered),
                "note": "No high-confidence stock-specific news found" if not filtered else "",
            }
        except Exception as e:
            return {"available": False, "error": str(e)}
    
    async def _calculate_technicals(self, ticker: str, market: str) -> Dict[str, Any]:
        """Calculate technical indicators for the stock"""
        try:
            # Get historical data (last 6 months for calculations)
            end_date = datetime.now()
            start_date = end_date - pd.Timedelta(days=180)
            
            df = await asyncio.to_thread(
                get_history,
                ticker=ticker,
                start=start_date.strftime("%Y-%m-%d"),
                end=end_date.strftime("%Y-%m-%d"),
                market=market,
                interval="1d"
            )
            
            if df.empty or len(df) < 20:
                return {"available": False, "reason": "Insufficient data"}
            
            # Calculate RSI
            delta = df['Close'].diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
            rs = gain / loss
            rsi = 100 - (100 / (1 + rs))
            current_rsi = rsi.iloc[-1] if not rsi.empty else None
            
            # Calculate MACD
            exp1 = df['Close'].ewm(span=12, adjust=False).mean()
            exp2 = df['Close'].ewm(span=26, adjust=False).mean()
            macd = exp1 - exp2
            signal = macd.ewm(span=9, adjust=False).mean()
            macd_current = macd.iloc[-1] if not macd.empty else None
            signal_current = signal.iloc[-1] if not signal.empty else None
            
            # Calculate Bollinger Bands
            sma_20 = df['Close'].rolling(window=20).mean()
            std_20 = df['Close'].rolling(window=20).std()
            upper_band = sma_20 + (std_20 * 2)
            lower_band = sma_20 - (std_20 * 2)
            current_price = df['Close'].iloc[-1]
            
            # Calculate support/resistance levels
            recent_high = df['High'].rolling(window=20).max().iloc[-1]
            recent_low = df['Low'].rolling(window=20).min().iloc[-1]
            
            # Moving averages
            sma_50 = df['Close'].rolling(window=50).mean().iloc[-1] if len(df) >= 50 else None
            sma_200 = df['Close'].rolling(window=200).mean().iloc[-1] if len(df) >= 200 else None
            
            return {
                "available": True,
                "rsi": {
                    "value": float(current_rsi) if current_rsi else None,
                    "signal": "oversold" if current_rsi and current_rsi < 30 else ("overbought" if current_rsi and current_rsi > 70 else "neutral")
                },
                "macd": {
                    "macd": float(macd_current) if macd_current else None,
                    "signal": float(signal_current) if signal_current else None,
                    "divergence": float(macd_current - signal_current) if (macd_current and signal_current) else None
                },
                "bollinger_bands": {
                    "upper": float(upper_band.iloc[-1]) if not upper_band.empty else None,
                    "middle": float(sma_20.iloc[-1]) if not sma_20.empty else None,
                    "lower": float(lower_band.iloc[-1]) if not lower_band.empty else None,
                    "current_price": float(current_price),
                    "position": "above_upper"
                    if current_price > upper_band.iloc[-1]
                    else ("below_lower" if current_price < lower_band.iloc[-1] else "within_bands")
                },
                "moving_averages": {
                    "sma_20": float(sma_20.iloc[-1]) if not sma_20.empty else None,
                    "sma_50": float(sma_50) if sma_50 else None,
                    "sma_200": float(sma_200) if sma_200 else None
                },
                "support_resistance": {
                    "resistance": float(recent_high),
                    "support": float(recent_low)
                }
            }
        except Exception as e:
            return {"available": False, "error": str(e)}

    async def _calculate_sharpe_ratio(self, ticker: str, market: str) -> Optional[float]:
        """Compute annualized Sharpe ratio from daily returns."""
        try:
            end_date = datetime.now()
            start_date = end_date - pd.Timedelta(days=365)
            df = await asyncio.to_thread(
                get_history,
                ticker=ticker,
                start=start_date.strftime("%Y-%m-%d"),
                end=end_date.strftime("%Y-%m-%d"),
                market=market,
                interval="1d"
            )
            if df.empty or "Close" not in df.columns:
                return None
            returns = df["Close"].pct_change().dropna()
            if returns.empty or returns.std() == 0:
                return 0.0
            sharpe = (returns.mean() / returns.std()) * (252 ** 0.5)
            return float(sharpe)
        except Exception:
            return None

    async def _generate_ddg_queries(
        self,
        ticker: str,
        company: str,
        market: str,
        user_message: str
    ) -> List[str]:
        """Generate 10 targeted DuckDuckGo queries for stock research."""
        # If Gemini/Groq formatting is available, try LLM for tailored queries
        if self.use_gemini_formatting and self.gemini_model:
            prompt = (
                "Generate 10 concise search queries for DuckDuckGo to research this stock. "
                "Focus on earnings, guidance, risks, lawsuits, supply chain, downgrades, "
                "competitors, valuation, insider activity, and recent losses. "
                "Return ONLY a JSON list of strings.\n\n"
                f"Company: {company}\nTicker: {ticker}\nMarket: {market}\n"
                f"User question: {user_message}\n"
            )
            try:
                response = await asyncio.to_thread(self.gemini_model.generate_content, prompt)
                text = response.text.strip().replace("```json", "").replace("```", "")
                queries = json.loads(text)
                if isinstance(queries, list) and queries:
                    return queries[:10]
            except Exception:
                pass

        base = company or ticker
        return [
            f"{base} {ticker} latest earnings results",
            f"{base} {ticker} guidance update",
            f"{base} {ticker} revenue decline or loss",
            f"{base} {ticker} lawsuit regulatory investigation",
            f"{base} {ticker} insider selling",
            f"{base} {ticker} analyst downgrade upgrade",
            f"{base} {ticker} supply chain risks",
            f"{base} {ticker} key competitors market share",
            f"{base} {ticker} valuation concerns P/E",
            f"{base} {ticker} major contracts partnerships",
        ]

    async def _run_ddg_queries(self, queries: List[str]) -> List[Dict[str, Any]]:
        """Run DuckDuckGo queries and return formatted results."""
        results = []
        for q in queries[:10]:
            try:
                text = await asyncio.to_thread(self.ddg_tool.search, q, 6)
                results.append({"query": q, "results": text})
            except Exception as e:
                results.append({"query": q, "error": str(e)})
        return results
    
    async def _normalize_text(self, text: str) -> str:
        """Use Gemini to normalize text - remove emojis, markdown, clean formatting"""
        if not self.use_gemini_formatting or not self.gemini_model:
            # Simple regex-based cleanup
            import re
            # Remove emojis
            text = re.sub(r'[^\x00-\x7F₹$€£¥]+', '', text)
            # Remove markdown bold/italic
            text = re.sub(r'\*\*?', '', text)
            # Remove headers
            text = re.sub(r'^#{1,6}\s', '', text, flags=re.MULTILINE)
            return text.strip()
        
        try:
            prompt = f'''Convert this text to plain professional format:
- Remove ALL emojis
- Remove markdown formatting (* ** # | -)
- Keep only essential punctuation
- Maintain paragraph structure
- Use proper spacing
- Professional tone only

Text:
{text}

Output only the cleaned text, nothing else.'''
            
            response = await asyncio.to_thread(
                self.gemini_model.generate_content,
                prompt
            )
            return response.text.strip()
        except Exception as e:
            print(f"Gemini normalization failed: {e}")
            import re
            text = re.sub(r'[^\x00-\x7F₹$€£¥]+', '', text)
            text = re.sub(r'\*\*?', '', text)
            text = re.sub(r'^#{1,6}\s', '', text, flags=re.MULTILINE)
            return text.strip()
    
    async def _create_stock_summary_enhanced(self, data: Dict) -> str:
        """Create comprehensive professional stock summary without emojis"""
        try:
            ticker = data.get("symbol", data.get("ticker", "Unknown"))
            company = data.get("company_name", ticker)
            current_price = data.get("current_price", 0)
            daily_change_pct = data.get("daily_change_pct", 0)
            currency = data.get("currency", "$")
            
            # Start with basic info
            summary = f"""COMPREHENSIVE STOCK ANALYSIS: {company} ({ticker})

PRICE INFORMATION
Current Price: {currency}{current_price:,.2f}
Daily Change: {daily_change_pct:+.2f}%
Previous Close: {currency}{data.get('previous_close', 0):,.2f}
52-Week Range: {currency}{data.get('week_52_low', 0):,.2f} - {currency}{data.get('week_52_high', 0):,.2f}

"""
            
            # Technical Indicators
            technicals = data.get("technical_indicators", {})
            if technicals.get("available"):
                summary += "TECHNICAL ANALYSIS\n"
                
                rsi = technicals.get("rsi", {})
                if rsi.get("value"):
                    summary += f"RSI (14): {rsi['value']:.2f} - {rsi.get('signal', 'neutral').upper()}\n"
                
                macd = technicals.get("macd", {})
                if macd.get("macd") is not None:
                    summary += f"MACD: {macd['macd']:.4f}, Signal: {macd['signal']:.4f}\n"
                
                bb = technicals.get("bollinger_bands", {})
                if bb.get("upper"):
                    summary += f"Bollinger Bands: {currency}{bb['lower']:.2f} - {currency}{bb['upper']:.2f}\n"
                    summary += f"Position: {bb.get('position', 'within_bands').replace('_', ' ').title()}\n"
                
                ma = technicals.get("moving_averages", {})
                if ma.get("sma_200"):
                    summary += f"Moving Averages: SMA20={currency}{ma.get('sma_20', 0):.2f}, "
                    summary += f"SMA50={currency}{ma.get('sma_50', 0):.2f}, "
                    summary += f"SMA200={currency}{ma.get('sma_200', 0):.2f}\n"
                
                sr = technicals.get("support_resistance", {})
                if sr.get("support"):
                    summary += f"Support/Resistance: {currency}{sr['support']:.2f} / {currency}{sr['resistance']:.2f}\n"
                
                summary += "\n"
            
            # Company fundamentals
            summary += "FUNDAMENTAL METRICS\n"
            if data.get("market_cap"):
                summary += f"Market Cap: {currency}{data['market_cap']:,.0f}\n"
            if data.get("pe_ratio"):
                summary += f"P/E Ratio: {data['pe_ratio']:.2f}\n"
            if data.get("eps"):
                summary += f"EPS: {currency}{data['eps']:.2f}\n"
            if data.get("dividend_yield"):
                summary += f"Dividend Yield: {data['dividend_yield']:.2f}%\n"
            if data.get("beta"):
                summary += f"Beta: {data['beta']:.2f}\n"
            
            summary += "\n"
            
            # Returns
            returns = data.get("returns", {})
            if returns:
                summary += "PERFORMANCE RETURNS\n"
                for period, value in returns.items():
                    period_name = period.replace("_", " ").title()
                    summary += f"{period_name}: {value:+.2f}%\n"
                summary += "\n"
            
            # Web news (more relevant than yfinance news)
            web_news = data.get("web_news", {})
            if web_news.get("available"):
                summary += "RECENT NEWS AND DEVELOPMENTS\n"
                results = web_news.get("results") or []
                if results:
                    for item in results[:3]:
                        title = item.get("title", "No title")
                        source = item.get("source", "")
                        date = item.get("date", "")
                        summary += f"- {title} ({source} {date})\n"
                else:
                    note = web_news.get("note") or "No high-confidence stock-specific news found."
                    summary += f"- {note}\n"
                summary += "\n"

            # DuckDuckGo research queries
            ddg_research = data.get("ddg_research", {})
            if ddg_research.get("queries"):
                summary += "RESEARCH QUERIES (DUCKDUCKGO)\n"
                for q in ddg_research.get("queries", [])[:10]:
                    summary += f"- {q}\n"
                summary += "\n"

            # Risk metrics
            risk_metrics = data.get("risk_metrics", {})
            if risk_metrics:
                sharpe = risk_metrics.get("sharpe_ratio")
                if sharpe is not None:
                    summary += f"RISK METRICS\nSharpe Ratio (1Y): {sharpe:.2f}\n\n"

            # Backtest metrics
            backtest = data.get("backtest", {})
            if backtest:
                metrics = backtest.get("metrics") or {}
                if metrics:
                    summary += "BACKTEST SUMMARY (Momentum, 1Y)\n"
                    summary += f"Total Return: {metrics.get('totalReturn', 'N/A')}%\n"
                    summary += f"Max Drawdown: {metrics.get('maxDrawdown', 'N/A')}%\n"
                    summary += f"Sharpe Ratio: {metrics.get('sharpeRatio', 'N/A')}\n"
                    summary += f"Win Rate: {metrics.get('winRate', 'N/A')}%\n"
                    summary += "\n"
            
            # Analyst rating
            if data.get("analyst_rating"):
                summary += f"\nANALYST CONSENSUS: {data['analyst_rating'].upper()}\n"
                if data.get("target_price"):
                    summary += f"Target Price: {currency}{data['target_price']:.2f}\n"
            
            # Normalize to remove any remaining formatting
            summary = await self._normalize_text(summary)
            
            return summary
            
        except Exception as e:
            return f"Stock analysis completed. Error formatting: {str(e)}"


# Singleton instance
_manager: Optional[PipelineManager] = None

def get_pipeline_manager() -> PipelineManager:
    """Get singleton PipelineManager instance"""
    global _manager
    if _manager is None:
        _manager = PipelineManager()
    return _manager
