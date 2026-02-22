from backend.memory.vector_store import VectorStore
from backend.memory.session_memory import SessionMemory
from backend.memory.portfolio_memory import PortfolioMemory
from backend.agents.screener_agent import ScreenerAgent
from backend.engine.divergence_detector import detect_divergence
from backend.engine.confidence_engine import calculate_confidence
from backend.agents.institutional.macro_agent import MacroAgent
from backend.agents.institutional.insider_agent import InsiderAgent
from backend.agents.institutional.risk_agent import RiskAgent
from backend.models.response_model import SuperAgentResponse
# Core Agents
from backend.agents.emotion_agent import EmotionAnalysisAgent
from backend.agents.analyst_agent import AnalystAgent
from backend.agents.web_agent import WebAgent
from backend.agents.sector_agent import SectorAgent
from backend.agents.report_agent import ReportAgent
from backend.agents.stock_analyzer import detect_tickers_in_text
import asyncio
import uuid

class SuperAgent:


    def __init__(self):
        # Core Agents
        self.emotion = EmotionAnalysisAgent()
        self.analyst = AnalystAgent()
        self.web = WebAgent()
        self.sector = SectorAgent()
        self.report = ReportAgent()
        
        # Institutional Agents
        self.macro = MacroAgent()
        self.insider = InsiderAgent()
        self.risk = RiskAgent()
        
        # Memory & Discovery
        self.vector = VectorStore()
        self.session = SessionMemory()
        self.portfolio = PortfolioMemory()
        self.screener = ScreenerAgent()

    # The main entry point now supports session_id and orchestrates logic
    async def run_orchestrator(self, query: str, ticker: str = None, market: str = "us", session_id: str = "default", approved_plan: dict = None, portfolio: dict = None):
        
        # 0. Human-in-the-Loop: Planning Phase
        if not approved_plan and ("plan" in query.lower() or "deep" in query.lower() or "research" in query.lower()):
            # Simulate Plan Generation (in real implementation, use LLM)
            plan = {
                "thought": "This request requires multi-step deep research.",
                "steps": [
                    {"agent": "WebAgent", "tool": "search", "description": f"Deep dive research on {query}"},
                    {"agent": "AnalystAgent", "tool": "financials", "description": f"Analyze financial data for {ticker or 'relevant entities'}"},
                    {"agent": "ReportAgent", "tool": "compile", "description": "Synthesize comprehensive report"}
                ]
            }
            return {
                "status": "awaiting_confirmation",
                "plan": plan,
                "response": "I've drafted a research plan. Please review and approve."
            }

        # 1. Save query to semantic memory
        
        # 1. Save query to semantic memory
        mem_id = str(uuid.uuid4())
        self.vector.add(id=mem_id, text=query, metadata={"type": "query", "session_id": session_id})
        self.session.save(session_id, "last_query", query)

        # 2. Check for Discovery Intent (e.g. "Find AI stocks", "Give best performing stocks")
        # Keywords suggesting a list/discovery request
        discovery_keywords = ["find", "search", "list", "show", "give", "recommend", "best", "top"]
        target_keywords = ["stock", "stocks", "company", "companies", "ticker", "tickers", "sector"]
        
        query_lower = query.lower()
        is_discovery = any(k in query_lower for k in discovery_keywords) and any(t in query_lower for t in target_keywords)

        if is_discovery:
             discovery_results = await self.screener.discover_stocks(query)
             return {"discovery": discovery_results}

        # 3. Standard Analysis Flow
        if not ticker:
            # Best-effort extraction from the user query (fast path, no validation).
            candidates = detect_tickers_in_text(query or "", validate=False)
            if candidates:
                ticker = candidates[0]

        if not ticker:
            return {
                "status": "needs_ticker",
                "response": "Please provide a stock ticker (e.g., NVDA, AAPL, TSLA) so I can run a full analysis.",
            }

        emotion = self.emotion.analyze(query)

        # Run core analysis tasks in parallel threads (Institutional Scale)
        financial_task = asyncio.to_thread(self.analyst.analyze, ticker, market)
        web_task = asyncio.to_thread(self.web.research, query)
        sector_task = asyncio.to_thread(self.sector.analyze, market=market)
        macro_task = asyncio.to_thread(self.macro.analyze)
        insider_task = asyncio.to_thread(self.insider.analyze, ticker)

        financial, web, sector, macro, insider = await asyncio.gather(
            financial_task,
            web_task,
            sector_task,
            macro_task,
            insider_task
        )
        
        # Risk Evaluation
        portfolio_weights = self._portfolio_to_weights(portfolio)
        if portfolio_weights:
            self.portfolio.update("default_user", portfolio_weights)

        current_portfolio = self.portfolio.get("default_user") or {}
        risk = self.risk.evaluate(current_portfolio) if current_portfolio else {
            "concentration": None,
            "risk_score": None,
            "analysis": "No portfolio provided; concentration risk unavailable."
        }

        # Generate Report
        final_report = self.report.generate(financial, web, sector, emotion)
        
        # Append Institutional Insights (avoid static fallbacks; surface unavailable states)
        final_report += (
            "\n\n**Institutional Intelligence:**\n"
            f"- Macro Bias: {macro.get('market_bias', 'Unknown')}\n"
            f"- Insider Sentiment: {insider.get('summary', 'Unknown')}\n"
            f"- Portfolio Concentration Score: {risk.get('risk_score', 'N/A')}"
        )

        # Return Raw Data for Pipeline Processing
        return {
            "emotion": emotion,
            "financial": financial,
            "web": web,
            "sector": sector,
            "macro": macro,
            "insider": insider,
            "risk": risk,
            "report": final_report
        }

    # Backward compatibility wrapper if needed, or Main Entry
    async def run(self, query: str, ticker: str, market: str = "us"):
        return await self.run_orchestrator(query, ticker, market)
    def _portfolio_to_weights(self, portfolio):
        """
        Normalize various portfolio shapes to weights dict for RiskAgent.
        Accepts either:
        - weights: {"AAPL": 0.6, "MSFT": 0.4}
        - holdings: {"cash": 100000, "holdings": {"AAPL": 10, "MSFT": 5}}
        - positions: {"AAPL": 10, "MSFT": 5}
        """
        if not portfolio or not isinstance(portfolio, dict):
            return {}

        # holdings shape
        if isinstance(portfolio.get("holdings"), dict):
            holdings = portfolio.get("holdings") or {}
            numeric = {k: float(v) for k, v in holdings.items() if isinstance(v, (int, float))}
            total = sum(abs(v) for v in numeric.values())
            if total > 0:
                return {k: abs(v) / total for k, v in numeric.items()}
            return {}

        # direct dict; exclude known non-position keys
        numeric = {k: float(v) for k, v in portfolio.items() if k not in {"cash"} and isinstance(v, (int, float))}
        if not numeric:
            return {}

        total = sum(abs(v) for v in numeric.values())
        if total <= 0:
            return {}

        # If it already looks like weights (roughly sums to 1), keep proportions
        if 0.8 <= sum(numeric.values()) <= 1.2 and all(v >= 0 for v in numeric.values()):
            s = sum(numeric.values())
            return {k: (v / s if s else 0.0) for k, v in numeric.items()}

        # Otherwise treat as position sizes / amounts and normalize
        return {k: abs(v) / total for k, v in numeric.items()}
