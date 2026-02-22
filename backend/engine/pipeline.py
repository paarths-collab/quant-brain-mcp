import asyncio
from backend.agents.super_agent import SuperAgent
from backend.memory.vector_store import VectorStore
from backend.engine.divergence_detector import detect_divergence
from backend.engine.confidence_engine import calculate_confidence
from backend.models.response_model import SuperAgentResponse
import uuid
import re
from typing import Optional, Tuple

# Strategy Lab
from backend.strategies.strategy_selector import StrategySelector
from backend.services.position_sizing_service import PositionSizingService
from backend.services.monte_carlo_service import MonteCarloService
from backend.services.trade_levels_service import TradeLevelsService

# Quant Engine
from backend.quant.mean_variance_optimizer import MeanVarianceOptimizer
from backend.quant.rl_strategy_selector import RLStrategySelector
# from backend.quant.trade_execution_simulator import TradeExecutionSimulator 
from backend.quant.risk_models import RiskModels
from backend.quant.stress_testing import StressTesting

# AI Strategy System
from backend.quant.regime_detector import RegimeDetector
from backend.quant.ai_strategy_selector import AIStrategySelector

from backend.agents.stock_analyzer import detect_tickers_in_text, detect_market_from_ticker


def normalize_market(market: Optional[str]) -> str:
    m = (market or "us").strip().lower()
    if m in {"in", "india", "nse", "bse"}:
        return "india"
    return "us"


def resolve_ticker_and_market(
    query: str,
    ticker: Optional[str],
    market: Optional[str],
) -> Tuple[Optional[str], str]:
    """
    Resolve a best-effort ticker from explicit input or from the query string.
    Returns (ticker|None, normalized_market).
    """
    normalized_market = normalize_market(market)

    # If this is a discovery/listing request, do NOT infer a ticker.
    query_lower = (query or "").lower()
    discovery_keywords = ["find", "search", "list", "show", "give", "recommend", "best", "top"]
    target_keywords = ["stock", "stocks", "company", "companies", "ticker", "tickers", "sector"]
    is_discovery = any(k in query_lower for k in discovery_keywords) and any(t in query_lower for t in target_keywords)
    if is_discovery:
        return None, normalized_market

    if ticker and str(ticker).strip():
        t = str(ticker).strip().upper()
        # If market wasn't explicitly set, infer from ticker.
        if not market:
            normalized_market = normalize_market(detect_market_from_ticker(t))
        return t, normalized_market

    # Infer from query (fast, no yfinance validation).
    candidates = detect_tickers_in_text(query or "", validate=False)
    if candidates:
        t = candidates[0].strip().upper()
        if not market:
            normalized_market = normalize_market(detect_market_from_ticker(t))
        return t, normalized_market

    return None, normalized_market


def format_ticker_for_yfinance(ticker: str, market: str) -> str:
    if not ticker:
        return ticker
    t = ticker.strip().upper()
    if market == "india" and not re.search(r"\.(NS|BO)$", t, flags=re.IGNORECASE):
        return f"{t}.NS"
    return t


class InvestmentPipeline:

    def __init__(self):
        self.agent = SuperAgent()
        self.memory = VectorStore()
        
        # Strategy Lab
        self.strategy_selector = StrategySelector() # Keep for access to strategies list
        self.sizing = PositionSizingService()
        self.monte_carlo = MonteCarloService()
        self.trade_levels = TradeLevelsService()
        
        # Quant Engine & AI Controller
        self.regime_detector = RegimeDetector()
        self.ai_selector = AIStrategySelector()
        self.rl_selector = self.ai_selector.rl # Expose RL if needed (or just use via ai_selector)
        
        # self.execution_sim = TradeExecutionSimulator() # Removed
        self.risk_models = RiskModels()
        self.stress_testing = StressTesting()

    async def run(self, query: str, ticker: str = None, market: str = "us", portfolio=None, session_id="default", approved_plan=None):
        resolved_ticker, resolved_market = resolve_ticker_and_market(query, ticker, market)
        yf_ticker = format_ticker_for_yfinance(resolved_ticker, resolved_market) if resolved_ticker else None
        
        # 1. Orchestrate SuperAgent Execution (Gather Intelligence)
        agent_result = await self.agent.run_orchestrator(query, yf_ticker, resolved_market, session_id, approved_plan, portfolio=portfolio)

        # Handle "Awaiting Confirmation"
        if agent_result.get("status") == "awaiting_confirmation":
            return agent_result

        # Handle "Needs Ticker"
        if agent_result.get("status") == "needs_ticker":
            return agent_result

        # Handle "Discovery Mode" fast-exit
        if "discovery" in agent_result:
             return {
                 "discovery": agent_result["discovery"],
                 "report": "Discovery complete."
             }

        # 2. Advanced Engine Logic
        divergence = detect_divergence(agent_result["financial"], agent_result["web"])
        confidence = calculate_confidence(
            agent_result["financial"].get("score", 0),
            agent_result["web"].get("score", 50),
            agent_result["sector"].get("score", 50),
            agent_result["emotion"].get("penalty", 0)
        )

        # 3. Institutional Strategy Lab Execution
        strategy_data = {}
        quant_data = {}
        risk_data_out = {}
        execution_data = {}
        rl_data = {}
        opt_data = {}

        if yf_ticker:
            # ---------------------------------------------------------
            # AI STRATEGY META-CONTROLLER
            # ---------------------------------------------------------
            
            # 1. Detect Market Regime (Trending, Chop, Volatility)
            regime = self.regime_detector.detect(yf_ticker)
            
            # 2. Run All Strategies
            # We use the raw list from selector to run them
            strategy_results = [s.run(yf_ticker) for s in self.strategy_selector.strategies]
            valid_results = [r for r in strategy_results if "error" not in r and "return" in r]

            if not valid_results:
                 # Fallback
                 valid_results = [{
                     "strategy": "None", "return": 0.0, "win_rate": 0.0, "last_signal": 0
                 }]

            # 3. AI Selection (LLM + RL + Macro Context)
            ai_decision = self.ai_selector.select(
                strategy_results=valid_results,
                regime=regime,
                macro_data=agent_result.get("macro", {})
            )
            
            # 4. Resolve Final Strategy
            final_strategy_name = ai_decision["selected_strategy"]
            best_strategy = next(
                (s for s in valid_results if s["strategy"] == final_strategy_name), 
                valid_results[0]
            )
            
            all_strategies = valid_results # For frontend display

            rl_data = {
                "chosen": final_strategy_name,
                "reasoning": ai_decision.get("reasoning"),
                "rl_suggestion": ai_decision.get("rl_suggestion"),
                "q_table": ai_decision.get("q_table")
            }

            # ---------------------------------------------------------
            # EXECUTION LOGIC
            # ---------------------------------------------------------

            # C. Trade Levels & Sizing
            action = "HOLD"
            if best_strategy.get("last_signal") == 1: action = "BUY"
            elif best_strategy.get("last_signal") == -1: action = "SELL"
            
            levels = self.trade_levels.calculate(yf_ticker, action)
            
            capital = 100000.0
            if portfolio and isinstance(portfolio, dict) and "cash" in portfolio:
                capital = float(portfolio["cash"])
            
            sizing_res = self.sizing.calculate(capital, levels["entry_price"], levels["stop_loss"])
            
            monte_res = self.monte_carlo.simulate(yf_ticker)
            
            strategy_data = {
                "regime": regime, # Added this!
                "best_strategy": best_strategy,
                "all_strategies": all_strategies,
                "ai_reasoning": ai_decision.get("reasoning"),
                "trade_levels": levels,
                "position_sizing": sizing_res,
                "monte_carlo": monte_res
            }

            # E. Risk Engine
            var = self.risk_models.calculate_var(yf_ticker)
            cvar = self.risk_models.calculate_cvar(yf_ticker)
            drawdown = self.risk_models.max_drawdown(yf_ticker)
            stress_res = self.stress_testing.simulate_crash(levels["entry_price"])
            
            risk_data_out = {
                "VaR": var,
                "CVaR": cvar,
                "Max_Drawdown": drawdown,
                "Stress_Test": stress_res
            }

        # 4. Portfolio Optimization
        tickers_to_optimize = [yf_ticker] if yf_ticker else []
        if portfolio and isinstance(portfolio, dict) and "holdings" in portfolio:
             # Add existing holdings to optimization
             tickers_to_optimize.extend(list(portfolio["holdings"].keys()))
             tickers_to_optimize = list(set(tickers_to_optimize)) # Unique
        
        if len(tickers_to_optimize) > 1:
            optimizer = MeanVarianceOptimizer(tickers_to_optimize)
            opt_data = optimizer.optimize()

        # 5. Add ticker-specific, non-static insights to the report (for UI display)
        report_text = agent_result.get("report", "") or ""
        ticker_lines = []
        if yf_ticker and strategy_data:
            regime = (strategy_data or {}).get("regime") or {}
            if isinstance(regime, dict) and regime.get("regime"):
                ticker_lines.append(f"- Ticker Regime: {regime.get('regime')} ({regime.get('trend_signal', 'n/a')}, vol {regime.get('volatility', 0.0):.1%})")

            if isinstance(risk_data_out, dict) and "Max_Drawdown" in risk_data_out:
                max_dd = risk_data_out.get("Max_Drawdown")
                if isinstance(max_dd, (int, float)):
                    ticker_lines.append(f"- 1Y Max Drawdown: {max_dd:.1%}")
            if isinstance(risk_data_out, dict) and "VaR" in risk_data_out:
                var = risk_data_out.get("VaR")
                if isinstance(var, (int, float)):
                    ticker_lines.append(f"- 1D VaR(95%): {var:.2%}")

        if ticker_lines:
            report_text = report_text + "\n\n**Ticker Intelligence:**\n" + "\n".join(ticker_lines)
            agent_result["report"] = report_text

        # 5. Persistent Memory Step
        self.memory.add(
            id=f"{session_id}_{uuid.uuid4()}", 
            text=f"Query: {query}\nTicker: {yf_ticker or ''}\nReport: {agent_result.get('report', '')}",
            metadata={"type": "report", "session_id": session_id}
        )

        # 6. Enforce Strict Output Contract
        response = SuperAgentResponse(
            emotion=agent_result["emotion"],
            financial=agent_result["financial"],
            web=agent_result["web"],
            sector=agent_result["sector"],
            macro=agent_result["macro"],
            insider=agent_result["insider"],
            risk=agent_result["risk"],
            divergence=divergence,
            confidence=confidence,
            report=agent_result.get("report", ""),
            strategy=strategy_data,
            portfolio_optimization=opt_data,
            rl_strategy=rl_data,
            # trade_execution=execution_data, # Removed
            risk_engine=risk_data_out
        )

        return response.model_dump()
