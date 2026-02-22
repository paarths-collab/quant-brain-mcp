import asyncio
import time
from backend.services.sector_resolver import SectorResolver
from backend.backend1.orchestrator.summary_builder import SummaryBuilder
from backend.backend1.agents.deciding_agent import DecidingAgent
from backend.backend1.utils.cache_manager import CacheManager
from backend.backend1.agents.financial_agent import FinancialAnalystAgent
from backend.backend1.agents.technical_agent import TechnicalAnalystAgent
from backend.backend1.agents.gnews_intelligence import GNewsIntelligenceAgent

from backend.backend1.utils.market_data import MarketData
from backend.utils.throttle import Throttle
from backend.utils.llm_rate_limiter import LLMRateLimiter
from backend.utils.llm_cooldown import LLMCooldownManager

from backend.analytics.backtester import Backtester
from backend.analytics.monte_carlo import MonteCarloSimulator

# Quant Engine Modules
from backend.analytics.mean_variance import MeanVarianceOptimizer
from backend.analytics.black_litterman import BlackLitterman
from backend.analytics.cvar_optimizer import CVaROptimizer
from backend.analytics.bayesian_mc import BayesianMonteCarlo
from backend.analytics.hmm_regime import HMMRegimeDetector
from backend.analytics.walk_forward import WalkForwardBacktest
from backend.analytics.utils import get_risk_free_rate
from backend.analytics.visualization import PortfolioVisualizer
from backend.backend1.utils.market_context import get_market_context
import yfinance as yf
import pandas as pd
import numpy as np

class SectorDecisionOrchestrator:

    def __init__(self):
        self.sector_resolver = SectorResolver()
        self.financial_agent = FinancialAnalystAgent()
        self.technical_agent = TechnicalAnalystAgent() 
        self.news_agent = GNewsIntelligenceAgent()
        self.summary_builder = SummaryBuilder()
        self.deciding_agent = DecidingAgent()
        self.market_data = MarketData()
        self.cache = CacheManager()
        
        # Flow Control
        self.llm_semaphore = asyncio.Semaphore(2)  # Reduced to 2 for extra safety
        self.throttle = Throttle(0.5, 1.5)  # jitter delay
        self.llm_rate_limiter = LLMRateLimiter(min_interval=5.0)  # Global 5s spacing
        self.llm_cooldown = LLMCooldownManager() # Global TPM Lock

        # Strategy Engine
        self.backtester = Backtester(lookback_years=3)
        self.monte_carlo = MonteCarloSimulator(simulations=500)
        
        # Quant Portfolio Lab
        self.mvo = MeanVarianceOptimizer(lookback_years=3)
        self.bl = BlackLitterman()
        self.cvar = CVaROptimizer()
        self.bayesian = BayesianMonteCarlo()
        self.hmm = HMMRegimeDetector()
        self.walk_forward = WalkForwardBacktest()
        
        # Visualization
        self.visualizer = PortfolioVisualizer()

    async def analyze_stock(self, ticker, risk_profile, market_pe=None, region="US"):
        cache_key = f"{ticker}_{risk_profile}_analysis_v4" 

        cached = self.cache.get(cache_key)
        # Note: If market_pe changes, cached result might define old relative score?
        # Ideally, relative scoring should happen outside cache or cache key includes market_pe.
        # For MVP: Accept cache might have slight drift on relative PE.
        if cached:
            return cached

        # Run analysis in parallel
        # 1. Fundamental & Technical First (Fast, Parallel, Local)
        # We run these first as requested by user ("first go for fundamental and technical")
        financial_task = asyncio.to_thread(self.financial_agent.run, ticker)
        technical_task = asyncio.to_thread(self.technical_agent.run, ticker) 

        financial, technical = await asyncio.gather(financial_task, technical_task)
        
        # 2. News (Slow, Rate Limited, External)
        # Only run news after fin/tech is done.
        # Throttled News/LLM call
        async def run_news_throttled():
             # Check for 429 global cooldown first
             await self.llm_cooldown.wait_if_needed()

             async with self.llm_semaphore:
                 # Still enforce 5s spacing between calls
                 await self.llm_rate_limiter.wait()
                 
                 try:
                     return await asyncio.to_thread(self.news_agent.run, ticker, region=region)
                 except Exception as e:
                     if "429" in str(e) or "rate_limit" in str(e):
                         await self.llm_cooldown.trigger_cooldown(60)
                         print(f"🔁 TPM Limit hit for {ticker}. Retrying after global cooldown...")
                         # Wait for the cooldown we just set (or allow wait_if_needed to handle it in next loop? 
                         # No, we must wait here to retry this specific item)
                         await asyncio.sleep(60)
                         
                         # Retry once
                         try:
                             return await asyncio.to_thread(self.news_agent.run, ticker, region=region)
                         except Exception as retry_e:
                             print(f"❌ Retry failed for {ticker}: {retry_e}")
                             # Return safe fallback
                             return {
                                "ticker": ticker,
                                "sentiment_score": 0.5,
                                "bullish_signals": [],
                                "bearish_signals": [],
                                "risk_flags": ["News unavailable due to rate limit"],
                                "catalysts": []
                             }
                     
                     # Check for other errors or re-raise
                     print(f"❌ News Error {ticker}: {e}")
                     return {
                        "ticker": ticker,
                        "sentiment_score": 0.5,
                        "bullish_signals": [],
                        "bearish_signals": [],
                        "risk_flags": [f"Error: {str(e)}"],
                        "catalysts": []
                     }

        news = await run_news_throttled()
        
        summary = self.summary_builder.build_summary(
            ticker,
            financial,
            technical,
            news,
            risk_profile=risk_profile,
            market_pe=market_pe
        )
        
        # Cache the specific analysis result
        self.cache.set(cache_key, summary)
        
        return summary

    async def run_custom_universe(self, tickers, risk_profile="balanced", region="US", market_context=None, analyze_limit=None, strategy_limit=None, horizon="long", **kwargs):
        """
        Runs the full pipeline on a specific list of tickers (Custom Universe).
        """
        print(f"Running Custom Universe Analysis on {len(tickers)} stocks ({region}) | Horizon: {horizon}")
        return await self._process_tickers(tickers, risk_profile, region, market_context, analyze_limit, strategy_limit, horizon)

    async def run(self, sector_name: str, risk_profile="balanced", region="US", market_context=None, analyze_limit=None, strategy_limit=None, horizon="long", **kwargs):
        """
        Resolves tickers from a sector/theme and runs the pipeline.
        """
        print(f"Resolving sector: {sector_name} ({region}) | Horizon: {horizon}")
        
        # Use new SectorResolver service
        tickers = self.sector_resolver.resolve_sector(sector_name, region)
        
        if not tickers:
            return {"error": f"Could not find tickers for sector {sector_name}"}

        return await self._process_tickers(tickers, risk_profile, region, market_context, analyze_limit, strategy_limit, horizon)

    async def _process_tickers(self, tickers, risk_profile, region, market_context, analyze_limit=None, strategy_limit=None, horizon="long"):
        print(f"DEBUG: _process_tickers received tickers ({type(tickers)}): {tickers}")
        print(f"Analyzing {len(tickers)} stocks: {tickers}")
        print(f"Running analysis for region: {region}")
        
        # 1. Market Context
        if not market_context:
             print(f"Fetching Market Context for {region}...")
             market_context = get_market_context(region)
             
        # Fallback values if fetch failed
        market_pe = market_context.get("trailing_pe", 25.0) if market_context else 25.0
        rf_rate = market_context.get("risk_free_rate", 0.045) if market_context else 0.045
        
        print(f"Market Context ({region}): P/E={market_pe}, Risk-Free Rate={rf_rate:.1%}")

        # 2. Analyze Stocks (Parallel)
        # Apply analysis limit if provided, else analyze all
        target_tickers = tickers[:analyze_limit] if analyze_limit else tickers
        
        tasks = [self.analyze_stock(t, risk_profile, market_pe, region) for t in target_tickers]
        stock_summaries = await asyncio.gather(*tasks)

        print("Deciding best stock...")
        decision = self.deciding_agent.decide(stock_summaries, horizon=horizon)

        # 3. Strategy Engine & Quant Lab
        ranked_stocks = decision.get("ranked", [])
        if ranked_stocks:
             # Apply strategy limit if provided, else take all that were ranked
             limit = strategy_limit if strategy_limit else len(ranked_stocks)
             top_stocks = ranked_stocks[:limit]
             top_tickers = [s["ticker"] for s in top_stocks]
             
             if top_tickers:
                 await self._run_quant_lab(top_tickers, decision, rf_rate, horizon)

        return decision

    async def _run_quant_lab(self, top_tickers, decision, rf_rate, horizon="long"):
         print(f"Generating Strategy Report for: {top_tickers}")
         
         strategy_analysis = {}
         
         # Analyze each stock individually
         for ticker in top_tickers:
             print(f"   -> Analyzing strategy for {ticker}...")
             
             # 1. Backtest (Multi-Timeframe) -> now Horizon-Aware
             backtest_results = self.backtester.backtest([ticker], horizon=horizon)
             
             if not backtest_results:
                 print(f"      Running strategy failed for {ticker} (No backtest data)")
                 continue
                 
             stock_results = {}
             
             for period, bt_res in backtest_results.items():
                 if not bt_res or bt_res.get("cumulative_return") == 0: 
                     continue
                 
                 # 2. Monte Carlo
                 mc_res = self.monte_carlo.simulate(bt_res["daily_returns"], days=252)
                 
                 if "daily_returns" in bt_res:
                    del bt_res["daily_returns"]
                 
                 stock_results[period] = {
                     "backtest": bt_res,
                     "monte_carlo": mc_res
                 }
                 print(f"      [{period.upper()}] Backtest: Return {bt_res['cumulative_return']:.1%}, MaxDD {bt_res['max_drawdown']:.1%}")
             
             strategy_analysis[ticker] = stock_results
         
         # --- Quant Portfolio Lab ---
         print(f"\nQuant Portfolio Lab (Top 5: {top_tickers})")
         
         try:
             # 1. Fetch Consolidated Data (3 Years)
             # Note: yfinance might fail for mixed regions if not careful, but top_tickers should be consistent region
             data_flat = yf.download(top_tickers, period="3y", interval="1d", auto_adjust=True, progress=False)["Close"]
             
             if isinstance(data_flat, pd.Series):
                 data_flat = data_flat.to_frame(name=top_tickers[0])
             
             returns = data_flat.pct_change().dropna()
             
             if not returns.empty:
                 
                 # Data Collection for Viz
                 viz_data = {
                     "returns": returns,
                     "mc_results": None,
                     "mc_paths": None,
                     "regimes": None,
                     "walk_forward": None,
                     "bayesian_paths": None
                 }

                 # 2. Mean-Variance Optimization (MVO)
                 mvo_res = self.mvo.optimize(top_tickers)
                 opt_weights = mvo_res.get("weights", [])
                 
                 if opt_weights:
                    print(f"   [MVO] Optimized Weights: {[round(w, 2) for w in opt_weights]}")
                    print(f"   [MVO] Exp Ret: {mvo_res['expected_return']:.1%}, Vol: {mvo_res['volatility']:.1%}")
                    
                    # 3. Monthly Rebalance Backtest
                    rebalance_res = self.backtester.backtest_monthly_rebalance(
                        top_tickers, 
                        weights=opt_weights
                    )
                    if rebalance_res:
                        print(f"   [Backtest MVO] Monthly Rebalance: Return {rebalance_res['cumulative_return']:.1%}, Sharpe {rebalance_res['sharpe_ratio']:.2f}")

                 # 4. Black-Litterman
                 market_weights = np.ones(len(top_tickers)) / len(top_tickers)
                 views = [0.15] * len(top_tickers) 
                 confidences = [0.05] * len(top_tickers)
                 bl_weights = self.bl.optimize(returns, market_weights, views, confidences)
                 print(f"   [Black-Litterman] Weights: {[round(w, 2) for w in bl_weights]}")

                 # 5. CVaR
                 cvar_weights = self.cvar.optimize(returns)
                 print(f"   [CVaR] Min-Tail-Risk Weights: {[round(w, 2) for w in cvar_weights]}")

                 # 6. Regime Detection
                 regimes = self.hmm.fit_predict(returns)
                 if regimes:
                     current_regime = regimes[-1]
                     print(f"   [Regime HMM] Current Market State: {current_regime} (0=LowVol/Bull, 1=HighVol/Bear likely)")
                     viz_data["regimes"] = regimes
                     
                 # 7. Walk-Forward
                 def optimize_wrapper(train_rets):
                     try:
                         mu = train_rets.mean() * 252
                         cov = train_rets.cov() * 252
                         inv_cov = np.linalg.inv(cov)
                         w = inv_cov @ mu
                         return w / w.sum()
                     except:
                         return np.ones(len(train_rets.columns))/len(train_rets.columns)

                 wf_res = self.walk_forward.run(returns, optimize_wrapper)
                 if wf_res:
                     print(f"   [Walk-Forward] Avg Test Return: {wf_res['average_test_return']:.1%}")
                     viz_data["walk_forward"] = wf_res

                 # 8. Bayesian MC
                 bayesian_res = self.bayesian.simulate(returns.mean(axis=1))
                 print(f"   [Bayesian MC] Exp Return {bayesian_res['expected']:.1%}, 5% Worst Case {bayesian_res['worst_5pct']:.1%}")
                 if "paths" in bayesian_res:
                    viz_data["bayesian_paths"] = bayesian_res["paths"]
                 
                 # Standard MC for Viz
                 mc_stats = self.monte_carlo.simulate(returns.mean(axis=1), days=252)
                 if "paths" in mc_stats:
                     viz_data["mc_paths"] = mc_stats["paths"]
                     viz_data["mc_results"] = mc_stats["distribution"]

                 # --- EXECUTE VISUALIZATION ---
                 print("Launching Quant Research Terminal Charts...")
                 try:
                     self.visualizer.plot_rolling_sharpe(returns, rf=rf_rate)
                     self.visualizer.plot_efficient_frontier(returns)
                     
                     if viz_data["mc_results"]:
                        self.visualizer.plot_monte_carlo_distribution(viz_data["mc_results"])
                     if viz_data["mc_paths"]:
                        self.visualizer.plot_monte_carlo_paths(viz_data["mc_paths"])
                     if viz_data["regimes"]:
                        self.visualizer.plot_regimes(returns, viz_data["regimes"])
                     if viz_data["walk_forward"]:
                        self.visualizer.plot_walk_forward(viz_data["walk_forward"])
                        
                     self.visualizer.plot_cvar(returns.mean(axis=1))
                     
                     if viz_data["bayesian_paths"]:
                        self.visualizer.plot_bayesian_fan(viz_data["bayesian_paths"])
                        
                 except Exception as v_err:
                     print(f"⚠️ Visualization Error: {v_err}")

         except Exception as q_err:
             print(f"⚠️ Quant Lab Error: {q_err}")

         decision["strategy_analysis"] = strategy_analysis
         decision["strategy_tickers"] = top_tickers
