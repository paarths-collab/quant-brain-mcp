from __future__ import annotations
import yaml
import pandas as pd
from pathlib import Path
from typing import Dict, Any, List, Optional
import importlib.util
import json

# --- Agents (with graceful fallbacks for missing packages) ---
from backend.agents.screener_agent import ScreenerAgent
from backend.agents.macro_agent import MacroAgent
from backend.agents.insider_agent import InsiderAgent
from backend.agents.yfinance_agent import YFinanceAgent
from backend.agents.sector_agent import SectorAgent
from backend.agents.stock_picker_agent import StockPickerAgent

# Optional: ExecutionAgent requires alpaca package
try:
    from backend.agents.execution_agent import ExecutionAgent
except ImportError:
    ExecutionAgent = None
    print("⚠️ ExecutionAgent not available (missing alpaca package)")

# Optional agents - may not exist
try:
    from backend.finverse_integration.agents.sentiment_agent import SentimentAgent
except ImportError:
    SentimentAgent = None
    print("⚠️ SentimentAgent not available")

# LLMAgent stub (module doesn't exist)
class LLMAgent:
    """Stub for LLMAnalystAgent - implement or connect to real LLM service"""
    def __init__(self, *args, **kwargs):
        pass
    def analyze(self, *args, **kwargs):
        return {"analysis": "LLM analysis not configured"}

# --- Utilities (with graceful fallbacks) ---
try:
    from backend.finverse_integration.utils import portfolio_engine
except ImportError:
    portfolio_engine = None
    print("⚠️ portfolio_engine not available")

try:
    from backend.finverse_integration.utils.news_fetcher import NewsFetcher
    # Create helper functions to match expected API
    _news_fetcher = NewsFetcher()
    def get_company_news(ticker: str, limit: int = 5):
        return _news_fetcher.get_stock_news(ticker, limit)
    def calculate_headline_sentiment(headlines: list):
        # Simple sentiment stub
        return {"sentiment": "neutral", "score": 0.0}
except ImportError:
    get_company_news = lambda *args, **kwargs: []
    calculate_headline_sentiment = lambda *args, **kwargs: {"sentiment": "neutral", "score": 0.0}
    print("⚠️ news_fetcher not available")

from backend.services.data_loader import format_ticker

def _load_modules_from_path(path: Path, module_prefix: str):
    modules = {}
    non_strategy_files = {"strategy_adapter", "custom_strategy", "__init__"}
    
    for file_path in path.glob("*.py"):
        if file_path.stem in non_strategy_files or file_path.stem == "__init__":
            continue
        
        module_name = f"{module_prefix}.{file_path.stem}"
        spec = importlib.util.spec_from_file_location(module_name, file_path)
        if spec and spec.loader:
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            strategy_name = file_path.stem.replace('_', ' ').title()
            modules[strategy_name] = module
    return modules

class Orchestrator:
    def __init__(self, config: Dict[str, Any]):
        self.cfg = config
        self.keys = self.cfg.get("api_keys", {})
        self.sets = self.cfg.get("agent_settings", {})
        self.rapidapi_cfg = self.cfg.get("rapidapi", {})
        print("Orchestrator: Initializing all agents...")
        self._initialize_agents()
        self._register_strategies()
        print("Orchestrator: Initialization complete.")

    def _initialize_agents(self):
        self.yfinance_agent = YFinanceAgent()
        
        # --- INITIALIZATION FOR OPENROUTER (prefer openrouter1 for Qwen, fallback to openrouter) ---
        openrouter_key = self.keys.get("openrouter1") or self.keys.get("openrouter")
        self.llm_agent = LLMAgent(openrouter_api_key=openrouter_key)
        
        self.macro_agent = MacroAgent(fred_api_key=self.keys.get("fred"))
        self.stock_picker_agent = StockPickerAgent()
        self.sector_agent = SectorAgent(
            news_api_key=self.keys.get("newsapi"),
            us_universe=self.stock_picker_agent.us_stock_universe,
            indian_universe=self.stock_picker_agent.indian_stock_universe
        )
        self.screener_agent = ScreenerAgent(rapidapi_config=self.rapidapi_cfg)
        self.execution_agent = ExecutionAgent(api_key=self.keys.get("alpaca_key_id"), api_secret=self.keys.get("alpaca_secret_key"), paper=self.sets.get("paper_trading", True))
        self.insider_agent = InsiderAgent(finnhub_key=self.keys.get("finnhub"), rapidapi_config=self.rapidapi_cfg)
        self.sentiment_agent = SentimentAgent(llm_agent=self.llm_agent)

    def _register_strategies(self):
        print("Orchestrator: Discovering and registering strategies...")
        long_term_path, short_term_path = Path("Long_Term_Strategy"), Path("strategies")
        self.long_term_modules = _load_modules_from_path(long_term_path, "Long_Term_Strategy")
        self.short_term_modules = _load_modules_from_path(short_term_path, "strategies")
        print(f"Registered {len(self.long_term_modules)} long-term strategies.")
        print(f"Registered {len(self.short_term_modules)} short-term strategies.")

    def _format_tickers_for_market(self, tickers: List[str], market: str) -> List[str]:
        return [format_ticker(t, market) for t in tickers]

    def run_deep_dive_analysis(self, ticker: str, start_date: str, end_date: str, market: str) -> Dict[str, Any]:
        analysis_data = self.yfinance_agent.get_full_analysis(ticker, market)
        if "error" in analysis_data: return analysis_data
        
        # Get company name for sentiment context
        company_name = analysis_data.get("snapshot", {}).get("longName", ticker)
        
        # Skip Finnhub news for Indian stocks (not supported on free tier)
        if market.lower() == "india":
            analysis_data["news_sentiment"] = {"avg_score": 0, "headlines": [], "note": "News sentiment not available for India market"}
            insider_analysis = {"summary": "N/A for this region", "transactions": pd.DataFrame()}
            headlines = []
        else:
            news = get_company_news(ticker, self.keys.get("finnhub"), start_date, end_date)
            headlines = [item.get("headline", "") for item in news]
            analysis_data["news_sentiment"] = {"avg_score": calculate_headline_sentiment(headlines), "headlines": headlines[:10]}
            insider_analysis = self.insider_agent.analyze(ticker)
        
        # Fast AI-powered sentiment analysis (uses LLM instead of slow Reddit)
        analysis_data["social_sentiment"] = self.sentiment_agent.analyze(
            ticker, 
            company_name=company_name,
            news_headlines=headlines[:5] if headlines else None
        )
        
        analysis_data["insider_analysis"] = insider_analysis
        return analysis_data

    def run_market_overview(self) -> Dict[str, Any]:
        return {
            "us_indicators": self.macro_agent.analyze_us_market(),
            "india_indicators": self.macro_agent.analyze_indian_market(),
            "global_indicators": self.macro_agent.get_global_indicators()
        }

    def run_short_term_analysis(self, tickers: List[str], start_date: str, end_date: str, market: str) -> pd.DataFrame:
        formatted_tickers = self._format_tickers_for_market(tickers, market)
        if not formatted_tickers: return pd.DataFrame()
        all_summaries = []
        for ticker in formatted_tickers:
            for name, module in self.short_term_modules.items():
                if name == "Pairs Trading": continue
                try:
                    result_dict = module.run(ticker, start_date, end_date, market=market)
                    summary = result_dict.get("summary", {})
                    if 'Return [%]' in summary: summary['Total Return %'] = summary.pop('Return [%]')
                    summary['Strategy'] = name
                    summary['Ticker'] = ticker
                    all_summaries.append(summary)
                except Exception as e:
                    all_summaries.append({'Strategy': name, 'Ticker': ticker, 'Error': str(e)})
        if len(formatted_tickers) >= 2 and "Pairs Trading" in self.short_term_modules:
            pair_result = self.short_term_modules["Pairs Trading"].run(formatted_tickers[:2], start_date, end_date)
            pair_summary = pair_result.get("summary", {})
            if 'Return [%]' in pair_summary: pair_summary['Total Return %'] = pair_summary.pop('Return [%]')
            pair_summary['Ticker'] = f"{formatted_tickers[0]}/{formatted_tickers[1]}"
            all_summaries.append(pair_summary)
        return pd.DataFrame(all_summaries)

    def run_automated_ai_discovery_and_plan(self, user_profile_text: str, market: str) -> str:
        print("Orchestrator: Starting AUTOMATED AI discovery and planning workflow...")
        end_date = pd.Timestamp.now()
        start_date = end_date - pd.DateOffset(years=1)
        start_date_str, end_date_str = start_date.strftime('%Y-%m-%d'), end_date.strftime('%Y-%m-%d')

        print("--> Step 1: Analyzing sectors to find the top performer...")
        sector_rankings = self.sector_agent.analyze(start_date_str, end_date_str)
        top_sector_data = sector_rankings[sector_rankings['Market'].str.lower() == market.lower()].iloc[0]
        top_sector_name = top_sector_data['Sector']
        print(f"--> Top sector identified: {top_sector_name}")

        print(f"--> Step 2: Running stock picker for the '{top_sector_name}' sector...")
        picker_weights = {"momentum": 0.4, "value": 0.3, "quality": 0.3}
        top_stocks_df = self.stock_picker_agent.run(market, top_sector_name, picker_weights, top_n=1)
        if top_stocks_df.empty: return "Error: The Stock Picker could not identify a top stock."
        top_stock_ticker = top_stocks_df.iloc[0]['Ticker']
        print(f"--> Top stock identified: {top_stock_ticker}")
        
        print(f"--> Step 3: Running deep dive and portfolio backtest on {top_stock_ticker}...")
        deep_dive_data = self.run_deep_dive_analysis(top_stock_ticker, start_date_str, end_date_str, market)
        
        portfolio_strategies = ["Momentum", "Mean Reversion (Bollinger Bands)", "Sma Crossover"]
        portfolio_results = portfolio_engine.build_portfolio(
            self, [top_stock_ticker], market, start_date_str, end_date_str, portfolio_strategies
        )

        full_context = {
            "user_profile_text": user_profile_text,
            "automated_discovery_results": {
                "top_performing_sector": top_sector_data.to_dict(),
                "top_stock_in_sector": top_stocks_df.head(1).to_dict(orient='records')[0],
                "deep_dive_analysis": deep_dive_data,
                "strategy_backtest_on_stock": portfolio_results
            }
        }

        initial_prompt = f"""
        You are a junior financial analyst. Create a personalized investment plan based on the client's profile and the provided data package.
        **CLIENT PROFILE:** "{user_profile_text}"
        **DATA PACKAGE:**
        ```json
        {json.dumps(full_context, indent=2, default=str)}
        ```
        **TASK:** Write a detailed investment plan recommending the stock ({top_stock_ticker}) and a strategy from the backtest results. Justify your recommendations with data from the context.
        """
        
        # --- MODEL NAME UPDATED ---
        open_router_model = "mistralai/mistral-7b-instruct:free"
        
        print(f"--> Step 4: Querying Junior Analyst A ({open_router_model})...")
        report_a = self.llm_agent.run(prompt=initial_prompt, model_name=open_router_model)
        
        print(f"--> Step 5: Querying Junior Analyst B ({open_router_model})...")
        report_b = self.llm_agent.run(prompt=initial_prompt, model_name=open_router_model)

        synthesis_prompt = f"""
        You are a senior portfolio manager. Synthesize the two reports from your junior analysts into a single, cohesive investment plan.
        **CLIENT PROFILE:** "{user_profile_text}"
        ---
        **ANALYST A REPORT:**
        {report_a}
        ---
        **ANALYST B REPORT:**
        {report_b}
        ---
        **TASK:** Produce the final, unified investment plan in clear Markdown. Present it as your own expert recommendation.
        """
        print("--> Step 6: Synthesizing reports...")
        final_report = self.llm_agent.run(prompt=synthesis_prompt, model_name=open_router_model)
        print("Orchestrator: Automated AI discovery and plan complete.")
        return final_report

    def execute_analysis_flow(
        self,
        investor_type: str,
        tickers: List[str] = None,
        start_date: str = None,
        end_date: str = None,
        market: str = "us"
    ) -> Dict[str, Any]:
        """
        Main entry point for executing different analysis flows.
        Routes to the appropriate method based on investor_type.

        Args:
            investor_type: One of 'ai_driven', 'long-term', or 'short-term'
            tickers: Optional list of stock tickers
            start_date: Start date for analysis (YYYY-MM-DD)
            end_date: End date for analysis (YYYY-MM-DD)
            market: 'us' or 'india' (default: 'us')

        Returns:
            Dictionary containing analysis results
        """
        print(f"Orchestrator: Starting '{investor_type}' analysis flow...")

        # Set default dates if not provided
        if not end_date:
            end_date = pd.Timestamp.now().strftime('%Y-%m-%d')
        if not start_date:
            start_date = (pd.Timestamp.now() - pd.DateOffset(years=1)).strftime('%Y-%m-%d')

        try:
            if investor_type == "ai_driven":
                # AI-driven discovery and planning (no tickers needed)
                user_profile = "A balanced investor looking for growth opportunities with moderate risk tolerance."
                report = self.run_automated_ai_discovery_and_plan(user_profile, market)
                return {
                    "analysis_type": "ai_driven",
                    "market": market,
                    "report": report
                }

            elif investor_type == "short-term":
                # Short-term quantitative/technical analysis
                if not tickers:
                    return {"error": "Tickers are required for short-term analysis."}
                
                results_df = self.run_short_term_analysis(tickers, start_date, end_date, market)
                return {
                    "analysis_type": "short-term",
                    "tickers": tickers,
                    "start_date": start_date,
                    "end_date": end_date,
                    "market": market,
                    "backtest_results": results_df.to_dict(orient='records') if not results_df.empty else []
                }

            elif investor_type == "long-term":
                # Long-term fundamental analysis with deep dive
                if not tickers:
                    return {"error": "Tickers are required for long-term analysis."}
                
                results = {}
                formatted_tickers = self._format_tickers_for_market(tickers, market)
                
                for ticker in formatted_tickers:
                    deep_dive = self.run_deep_dive_analysis(ticker, start_date, end_date, market)
                    
                    # Run long-term fundamental strategies
                    long_term_results = {}
                    for name, module in self.long_term_modules.items():
                        try:
                            long_term_results[name] = module.analyze(ticker)
                        except Exception as e:
                            long_term_results[name] = {"error": str(e)}
                    
                    results[ticker] = {
                        "deep_dive": deep_dive,
                        "fundamental_analysis": long_term_results
                    }
                
                return {
                    "analysis_type": "long-term",
                    "tickers": tickers,
                    "market": market,
                    "results": results
                }

            else:
                return {"error": f"Unknown investor_type: '{investor_type}'. Use 'ai_driven', 'long-term', or 'short-term'."}

        except Exception as e:
            print(f"Orchestrator: Error during {investor_type} analysis: {e}")
            return {"error": str(e)}

    @classmethod
    def from_file(cls, path: str = "config.yaml") -> "Orchestrator":
        # --- Corrected to look for the right config file ---
        config_path = Path("quant-company-insights-agent") / path
        if not config_path.exists():
             config_path = path # Fallback to root if not found
        with open(config_path, "r", encoding="utf-8") as f:
            cfg = yaml.safe_load(f)
        return cls(cfg)

# from __future__ import annotations
# import yaml
# import pandas as pd
# from pathlib import Path
# from typing import Dict, Any, List
# import importlib.util
# import json

# # --- Agents ---
# from agents.screener_agent import ScreenerAgent
# from agents.llm_analyst_agent import LLMAnalystAgent as LLMAgent
# from agents.execution_agent import ExecutionAgent
# from agents.macro_agent import MacroAgent
# from agents.insider_agent import InsiderAgent
# from agents.social_media_sentiment import SentimentAgent
# from agents.yfinance_agent import YFinanceAgent
# from agents.sector_agent import SectorAgent
# from agents.stock_picker_agent import StockPickerAgent

# # --- Utilities ---
# from utils import portfolio_engine
# from utils.news_fetcher import get_company_news, calculate_headline_sentiment
# from utils.data_loader import format_ticker

# def _load_modules_from_path(path: Path, module_prefix: str):
#     modules = {}
#     for file_path in path.glob("*.py"):
#         if file_path.stem == "__init__": continue
#         module_name = f"{module_prefix}.{file_path.stem}"
#         spec = importlib.util.spec_from_file_location(module_name, file_path)
#         if spec and spec.loader:
#             module = importlib.util.module_from_spec(spec)
#             spec.loader.exec_module(module)
#             strategy_name = file_path.stem.replace('_', ' ').title()
#             modules[strategy_name] = module
#     return modules

# class Orchestrator:
#     def __init__(self, config: Dict[str, Any]):
#         self.cfg = config
#         self.keys = self.cfg.get("api_keys", {})
#         self.sets = self.cfg.get("agent_settings", {})
#         self.rapidapi_cfg = self.cfg.get("rapidapi", {})
#         print("Orchestrator: Initializing all agents...")
#         self._initialize_agents()
#         self._register_strategies()
#         print("Orchestrator: Initialization complete.")

#     def _initialize_agents(self):
#         self.yfinance_agent = YFinanceAgent()
#         self.llm_agent = LLMAgent(gemini_api_key=self.keys.get("gemini"))
#         self.macro_agent = MacroAgent(fred_api_key=self.keys.get("fred"))
#         self.sector_agent = SectorAgent(news_api_key=self.keys.get("newsapi"))
#         self.stock_picker_agent = StockPickerAgent()
#         self.screener_agent = ScreenerAgent(rapidapi_config=self.rapidapi_cfg)
#         self.execution_agent = ExecutionAgent(api_key=self.keys.get("alpaca_key_id"), api_secret=self.keys.get("alpaca_secret_key"), paper=self.sets.get("paper_trading", True))
#         self.insider_agent = InsiderAgent(finnhub_key=self.keys.get("finnhub"), rapidapi_config=self.rapidapi_cfg)
#         self.sentiment_agent = SentimentAgent(reddit_client_id=self.keys.get("reddit_client_id"), reddit_client_secret=self.keys.get("reddit_client_secret"), reddit_user_agent=self.keys.get("reddit_user_agent"))

#     def _register_strategies(self):
#         print("Orchestrator: Discovering and registering strategies...")
#         long_term_path, short_term_path = Path("Long_Term_Strategy"), Path("strategies")
#         self.long_term_modules = _load_modules_from_path(long_term_path, "Long_Term_Strategy")
#         self.short_term_modules = _load_modules_from_path(short_term_path, "strategies")
#         print(f"Registered {len(self.long_term_modules)} long-term strategies.")
#         print(f"Registered {len(self.short_term_modules)} short-term strategies.")

#     def _format_tickers_for_market(self, tickers: List[str], market: str) -> List[str]:
#         return [format_ticker(t, market) for t in tickers]

#     def run_deep_dive_analysis(self, ticker: str, start_date: str, end_date: str, market: str) -> Dict[str, Any]:
#         analysis_data = self.yfinance_agent.get_full_analysis(ticker, market)
#         if "error" in analysis_data: return analysis_data
#         analysis_data["social_sentiment"] = self.sentiment_agent.analyze(ticker)
#         news = get_company_news(ticker, self.keys.get("finnhub"), start_date, end_date)
#         headlines = [item.get("headline", "") for item in news]
#         analysis_data["news_sentiment"] = {"avg_score": calculate_headline_sentiment(headlines), "headlines": headlines[:10]}
#         if market.lower() == "india":
#             insider_analysis = {"summary": "N/A for this region", "transactions": pd.DataFrame()}
#         else:
#             insider_analysis = self.insider_agent.analyze(ticker)
#         analysis_data["insider_analysis"] = insider_analysis
#         return analysis_data

#     def run_market_overview(self) -> Dict[str, Any]:
#         return {
#             "us_indicators": self.macro_agent.analyze_us_market(),
#             "india_indicators": self.macro_agent.analyze_indian_market(),
#             "global_indicators": self.macro_agent.get_global_indicators()
#         }

#     def run_short_term_analysis(self, tickers: List[str], start_date: str, end_date: str, market: str) -> pd.DataFrame:
#         formatted_tickers = self._format_tickers_for_market(tickers, market)
#         if not formatted_tickers: return pd.DataFrame()
#         all_summaries = []
#         for ticker in formatted_tickers:
#             for name, module in self.short_term_modules.items():
#                 if name == "Pairs Trading": continue
#                 try:
#                     result_dict = module.run(ticker, start_date, end_date, market=market)
#                     summary = result_dict.get("summary", {})
#                     if 'Return [%]' in summary: summary['Total Return %'] = summary.pop('Return [%]')
#                     summary['Strategy'] = name
#                     summary['Ticker'] = ticker
#                     all_summaries.append(summary)
#                 except Exception as e:
#                     all_summaries.append({'Strategy': name, 'Ticker': ticker, 'Error': str(e)})
#         if len(formatted_tickers) >= 2 and "Pairs Trading" in self.short_term_modules:
#             pair_result = self.short_term_modules["Pairs Trading"].run(formatted_tickers[:2], start_date, end_date)
#             pair_summary = pair_result.get("summary", {})
#             if 'Return [%]' in pair_summary: pair_summary['Total Return %'] = pair_summary.pop('Return [%]')
#             pair_summary['Ticker'] = f"{formatted_tickers[0]}/{formatted_tickers[1]}"
#             all_summaries.append(pair_summary)
#         return pd.DataFrame(all_summaries)

#     # In Bloomberg/agents/orchestrator.py

#     # ... (rest of the file is the same until this method)

#     def run_automated_ai_discovery_and_plan(self, user_profile_text: str, market: str) -> str:
#         """
#         Runs a fully automated discovery and planning workflow.
#         """
#         print("Orchestrator: Starting AUTOMATED AI discovery and planning workflow...")
#         end_date = pd.Timestamp.now()
#         start_date = end_date - pd.DateOffset(years=1)
#         start_date_str, end_date_str = start_date.strftime('%Y-%m-%d'), end_date.strftime('%Y-%m-%d')

#         print("--> Step 1: Analyzing sectors to find the top performer...")
#         sector_rankings = self.sector_agent.analyze(start_date_str, end_date_str)
#         top_sector_data = sector_rankings[sector_rankings['Market'].str.lower() == market.lower()].iloc[0]
#         top_sector_name = top_sector_data['Sector']
#         print(f"--> Top sector identified: {top_sector_name}")

#         print(f"--> Step 2: Running stock picker for the '{top_sector_name}' sector...")
#         picker_weights = {"momentum": 0.4, "value": 0.3, "quality": 0.3}
#         top_stocks_df = self.stock_picker_agent.run(sector=top_sector_name, weights=picker_weights, top_n=1)
#         if top_stocks_df.empty: return "Error: The Stock Picker could not identify a top stock in the best-performing sector."
#         top_stock_ticker = top_stocks_df.iloc[0]['Ticker']
#         print(f"--> Top stock identified: {top_stock_ticker}")
        
#         print(f"--> Step 3: Running deep dive and portfolio backtest on {top_stock_ticker}...")
#         deep_dive_data = self.run_deep_dive_analysis(top_stock_ticker, start_date_str, end_date_str, market)
        
#         portfolio_strategies = ["Momentum", "Mean Reversion (Bollinger Bands)", "Sma Crossover"]
#         portfolio_results = portfolio_engine.build_portfolio(
#             self, [top_stock_ticker], market, start_date_str, end_date_str, portfolio_strategies
#         )

#         full_context = {
#             "user_profile_text": user_profile_text,
#             "automated_discovery_results": {
#                 "top_performing_sector": top_sector_data.to_dict(),
#                 "top_stock_in_sector": top_stocks_df.head(1).to_dict(orient='records')[0],
#                 "deep_dive_analysis": deep_dive_data,
#                 "strategy_backtest_on_stock": portfolio_results
#             }
#         }

#         initial_prompt = f"""
#         You are a junior financial analyst. Your task is to create a personalized investment plan for a client based on their profile and a comprehensive, automatically generated data package.

#         **CLIENT PROFILE (Natural Language):**
#         "{user_profile_text}"

#         **AUTOMATED ANALYSIS & DISCOVERY DATA PACKAGE:**
#         ```json
#         {json.dumps(full_context, indent=2, default=str)}
#         ```

#         **YOUR TASK:**
#         Based on ALL the provided data, write a detailed investment plan for the client. The plan should recommend the discovered stock ({top_stock_ticker}) and suggest a strategy based on the backtest results. Justify everything with data from the context.
#         """
        
#         # --- MODIFIED SECTION ---
#         print("--> Step 4: Querying Junior Analyst 'Qwen3 8B'...")
#         qwen_report = self.llm_agent.run(prompt=initial_prompt, model='qwen3:8b') # Use Qwen3 8B
        
#         print("--> Step 5: Querying Junior Analyst 'DeepSeek-R1'...")
#         deepseek_report = self.llm_agent.run(prompt=initial_prompt, model='deepseek-r1:latest') # Use DeepSeek-R1
#         # --- END MODIFIED SECTION ---

#         synthesis_prompt = f"""
#         You are a senior portfolio manager. Synthesize the two reports from your junior analysts (Qwen and DeepSeek) into a single, cohesive, and definitive investment plan. Identify the strongest points from each, resolve contradictions, and provide the final authoritative recommendation based on the client's profile.

#         **CLIENT PROFILE (Natural Language):**
#         "{user_profile_text}"
#         ---
#         **REPORT FROM JUNIOR ANALYST A (QWEN):**
#         {qwen_report}
#         ---
#         **REPORT FROM JUNIOR ANALYST B (DEEPSEEK):**
#         {deepseek_report}
#         ---
#         **YOUR TASK:**
#         Produce the final, unified investment plan in clear Markdown. Do not refer to the junior analysts; present the final plan as your own expert recommendation.
#         """
#         print("--> Step 6: Synthesizing reports...")
#         # Use one of your powerful models for the final synthesis
#         final_report = self.llm_agent.run(prompt=synthesis_prompt, model='qwen3:8b')
#         print("Orchestrator: Automated AI discovery and plan complete.")
#         return final_report

#     @classmethod
#     def from_file(cls, path: str = "config.yaml") -> "Orchestrator":
#         with open(path, "r", encoding="utf-8") as f:
#             cfg = yaml.safe_load(f)
#         return cls(cfg)
# from __future__ import annotations
# import yaml
# import pandas as pd
# from pathlib import Path
# from typing import Dict, Any, List
# import importlib.util
# import json

# # --- Agents ---
# from agents.screener_agent import ScreenerAgent
# from agents.llm_analyst_agent import LLMAnalystAgent as LLMAgent
# from agents.execution_agent import ExecutionAgent
# from agents.macro_agent import MacroAgent
# from agents.insider_agent import InsiderAgent
# from agents.social_media_sentiment import SentimentAgent
# from agents.yfinance_agent import YFinanceAgent
# from agents.sector_agent import SectorAgent # <-- Add SectorAgent
# from agents.stock_picker_agent import StockPickerAgent # <-- Add StockPickerAgent

# # --- Utilities ---
# from utils import portfolio_engine
# from utils.news_fetcher import get_company_news, calculate_headline_sentiment
# from utils.data_loader import format_ticker

# def _load_modules_from_path(path: Path, module_prefix: str):
#     modules = {}
#     for file_path in path.glob("*.py"):
#         if file_path.stem == "__init__": continue
#         module_name = f"{module_prefix}.{file_path.stem}"
#         spec = importlib.util.spec_from_file_location(module_name, file_path)
#         if spec and spec.loader:
#             module = importlib.util.module_from_spec(spec)
#             spec.loader.exec_module(module)
#             strategy_name = file_path.stem.replace('_', ' ').title()
#             modules[strategy_name] = module
#     return modules

# class Orchestrator:
#     def __init__(self, config: Dict[str, Any]):
#         self.cfg = config
#         self.keys = self.cfg.get("api_keys", {})
#         self.sets = self.cfg.get("agent_settings", {})
#         self.rapidapi_cfg = self.cfg.get("rapidapi", {})
#         print("Orchestrator: Initializing all agents...")
#         self._initialize_agents()
#         self._register_strategies()
#         print("Orchestrator: Initialization complete.")

#     def _initialize_agents(self):
#         self.yfinance_agent = YFinanceAgent()
#         self.llm_agent = LLMAgent(gemini_api_key=self.keys.get("gemini"))
#         self.macro_agent = MacroAgent(fred_api_key=self.keys.get("fred"))
#         # --- ADD INITIALIZATION FOR NEW AGENTS ---
#         self.sector_agent = SectorAgent(news_api_key=self.keys.get("newsapi"))
#         self.stock_picker_agent = StockPickerAgent()
#         # --- (rest of the initializations are the same) ---
#         self.screener_agent = ScreenerAgent(rapidapi_config=self.rapidapi_cfg)
#         self.execution_agent = ExecutionAgent(api_key=self.keys.get("alpaca_key_id"), api_secret=self.keys.get("alpaca_secret_key"), paper=self.sets.get("paper_trading", True))
#         self.insider_agent = InsiderAgent(finnhub_key=self.keys.get("finnhub"), rapidapi_config=self.rapidapi_cfg)
#         self.sentiment_agent = SentimentAgent(reddit_client_id=self.keys.get("reddit_client_id"), reddit_client_secret=self.keys.get("reddit_client_secret"), reddit_user_agent=self.keys.get("reddit_user_agent"))

#     # ... (rest of the class up to the new method is the same)
#     def _register_strategies(self):
#         print("Orchestrator: Discovering and registering strategies...")
#         long_term_path, short_term_path = Path("Long_Term_Strategy"), Path("strategies")
#         self.long_term_modules = _load_modules_from_path(long_term_path, "Long_Term_Strategy")
#         self.short_term_modules = _load_modules_from_path(short_term_path, "strategies")
#         print(f"Registered {len(self.long_term_modules)} long-term strategies.")
#         print(f"Registered {len(self.short_term_modules)} short-term strategies.")

#     def _format_tickers_for_market(self, tickers: List[str], market: str) -> List[str]:
#         return [format_ticker(t, market) for t in tickers]
        
#     def run_deep_dive_analysis(self, ticker: str, start_date: str, end_date: str, market: str) -> Dict[str, Any]:
#         analysis_data = self.yfinance_agent.get_full_analysis(ticker, market)
#         if "error" in analysis_data: return analysis_data
#         analysis_data["social_sentiment"] = self.sentiment_agent.analyze(ticker)
#         news = get_company_news(ticker, self.keys.get("finnhub"), start_date, end_date)
#         headlines = [item.get("headline", "") for item in news]
#         analysis_data["news_sentiment"] = {"avg_score": calculate_headline_sentiment(headlines), "headlines": headlines[:10]}
#         if market.lower() == "india":
#             insider_analysis = {"summary": "N/A for this region", "transactions": pd.DataFrame()}
#         else:
#             insider_analysis = self.insider_agent.analyze(ticker)
#         analysis_data["insider_analysis"] = insider_analysis
#         return analysis_data

#     def run_market_overview(self) -> Dict[str, Any]:
#         return {
#             "us_indicators": self.macro_agent.analyze_us_market(),
#             "india_indicators": self.macro_agent.analyze_indian_market(),
#             "global_indicators": self.macro_agent.get_global_indicators()
#         }
        
#     def run_short_term_analysis(self, tickers: List[str], start_date: str, end_date: str, market: str) -> pd.DataFrame:
#         formatted_tickers = self._format_tickers_for_market(tickers, market)
#         if not formatted_tickers: return pd.DataFrame()
#         all_summaries = []
#         for ticker in formatted_tickers:
#             for name, module in self.short_term_modules.items():
#                 if name == "Pairs Trading": continue
#                 try:
#                     result_dict = module.run(ticker, start_date, end_date, market=market)
#                     summary = result_dict.get("summary", {})
#                     if 'Return [%]' in summary: summary['Total Return %'] = summary.pop('Return [%]')
#                     summary['Strategy'] = name
#                     summary['Ticker'] = ticker
#                     all_summaries.append(summary)
#                 except Exception as e:
#                     all_summaries.append({'Strategy': name, 'Ticker': ticker, 'Error': str(e)})
#         if len(formatted_tickers) >= 2 and "Pairs Trading" in self.short_term_modules:
#             pair_result = self.short_term_modules["Pairs Trading"].run(formatted_tickers[:2], start_date, end_date)
#             pair_summary = pair_result.get("summary", {})
#             if 'Return [%]' in pair_summary: pair_summary['Total Return %'] = pair_summary.pop('Return [%]')
#             pair_summary['Ticker'] = f"{formatted_tickers[0]}/{formatted_tickers[1]}"
#             all_summaries.append(pair_summary)
#         return pd.DataFrame(all_summaries)

#     # --- ADD THE NEW AUTOMATED AI METHOD ---
#     def run_automated_ai_discovery_and_plan(self, user_profile_text: str, market: str) -> str:
#         """
#         Runs a fully automated discovery and planning workflow.
#         """
#         print("Orchestrator: Starting AUTOMATED AI discovery and planning workflow...")
#         end_date = pd.Timestamp.now()
#         start_date = end_date - pd.DateOffset(years=1)
#         start_date_str, end_date_str = start_date.strftime('%Y-%m-%d'), end_date.strftime('%Y-%m-%d')

#         # 1. FIND BEST SECTOR
#         print("--> Step 1: Analyzing sectors to find the top performer...")
#         sector_rankings = self.sector_agent.analyze(start_date_str, end_date_str)
#         top_sector_data = sector_rankings[sector_rankings['Market'].str.lower() == market.lower()].iloc[0]
#         top_sector_name = top_sector_data['Sector']
#         print(f"--> Top sector identified: {top_sector_name}")

#         # 2. FIND BEST STOCK IN THAT SECTOR
#         print(f"--> Step 2: Running stock picker for the '{top_sector_name}' sector...")
#         # Using a balanced weighting for the stock picker
#         picker_weights = {"momentum": 0.4, "value": 0.3, "quality": 0.3}
#         top_stocks_df = self.stock_picker_agent.run(sector=top_sector_name, weights=picker_weights, top_n=1)
#         if top_stocks_df.empty: return "Error: The Stock Picker could not identify a top stock in the best-performing sector."
#         top_stock_ticker = top_stocks_df.iloc[0]['Ticker']
#         print(f"--> Top stock identified: {top_stock_ticker}")
        
#         # 3. RUN DEEP DIVE & BACKTEST ON THE DISCOVERED STOCK
#         print(f"--> Step 3: Running deep dive and portfolio backtest on {top_stock_ticker}...")
#         deep_dive_data = self.run_deep_dive_analysis(top_stock_ticker, start_date_str, end_date_str, market)
        
#         # Use a default set of balanced strategies for the automated backtest
#         portfolio_strategies = ["Momentum", "Mean Reversion (Bollinger Bands)", "Sma Crossover"]
#         portfolio_results = portfolio_engine.build_portfolio(
#             self, [top_stock_ticker], market, start_date_str, end_date_str, portfolio_strategies
#         )

#         # 4. ASSEMBLE CONTEXT AND GENERATE AI REPORTS
#         full_context = {
#             "user_profile_text": user_profile_text,
#             "automated_discovery_results": {
#                 "top_performing_sector": top_sector_data.to_dict(),
#                 "top_stock_in_sector": top_stocks_df.head(1).to_dict(orient='records')[0],
#                 "deep_dive_analysis": deep_dive_data,
#                 "strategy_backtest_on_stock": portfolio_results
#             }
#         }

#         # 5. GENERATE & SYNTHESIZE AI REPORTS (same logic as before)
#         initial_prompt = f"""
#         You are a junior financial analyst. Your task is to create a personalized investment plan for a client based on their profile and a comprehensive, automatically generated data package.

#         **CLIENT PROFILE (Natural Language):**
#         "{user_profile_text}"

#         **AUTOMATED ANALYSIS & DISCOVERY DATA PACKAGE:**
#         ```json
#         {json.dumps(full_context, indent=2, default=str)}
#         ```

#         **YOUR TASK:**
#         Based on ALL the provided data, write a detailed investment plan for the client. The plan should recommend the discovered stock ({top_stock_ticker}) and suggest a strategy based on the backtest results. Justify everything with data from the context.
#         """
#         print("--> Step 4: Querying Junior Analyst 'Llama3'...")
#         llama_report = self.llm_agent.run(prompt=initial_prompt, model='llama3')
#         print("--> Step 5: Querying Junior Analyst 'Mistral'...")
#         mistral_report = self.llm_agent.run(prompt=initial_prompt, model='mistral')

#         synthesis_prompt = f"""
#         You are a senior portfolio manager. Synthesize the two reports from your junior analysts (Llama3 and Mistral) into a single, cohesive, and definitive investment plan. Identify the strongest points from each, resolve contradictions, and provide the final authoritative recommendation based on the client's profile.

#         **CLIENT PROFILE (Natural Language):**
#         "{user_profile_text}"
#         ---
#         **REPORT FROM JUNIOR ANALYST A (LLAMA3):**
#         {llama_report}
#         ---
#         **REPORT FROM JUNIOR ANALYST B (MISTRAL):**
#         {mistral_report}
#         ---
#         **YOUR TASK:**
#         Produce the final, unified investment plan in clear Markdown. Do not refer to the junior analysts; present the final plan as your own expert recommendation.
#         """
#         print("--> Step 6: Synthesizing reports...")
#         final_report = self.llm_agent.run(prompt=synthesis_prompt, model='llama3')
#         print("Orchestrator: Automated AI discovery and plan complete.")
#         return final_report

#     @classmethod
#     def from_file(cls, path: str = "config.yaml") -> "Orchestrator":
#         with open(path, "r", encoding="utf-8") as f:
#             cfg = yaml.safe_load(f)
#         return cls(cfg)

# from __future__ import annotations
# import yaml
# import json
# import pandas as pd
# from pathlib import Path
# from typing import Dict, Any, List
# import importlib.util
# from utils import portfolio_engine
# # --- Agents ---
# from agents.screener_agent import ScreenerAgent
# from agents.llm_analyst_agent import LLMAnalystAgent as LLMAgent
# from agents.execution_agent import ExecutionAgent
# from agents.macro_agent import MacroAgent
# from agents.insider_agent import InsiderAgent
# from agents.social_media_sentiment import SentimentAgent
# from agents.yfinance_agent import YFinanceAgent
# from strategies import (
#     sma_crossover,
#     ema_crossover,
#     momentum_strategy,
#     mean_inversion,
#     rsi_strategy,
#     reversal_strategy,
#     breakout_strategy,
#     channel_trading,
#     custom_strategy,
#     mcd_strategy,
#     pullback_fibonacci,
#     support_resistance,
#     pairs_trading
# )
# # --- Utilities ---
# from utils.news_fetcher import get_live_quote, get_company_news, calculate_headline_sentiment
# from utils.moneycontrol_scraper import scrape_moneycontrol_data
# from utils.data_loader import get_history, add_technical_indicators, get_company_snapshot, format_ticker

# def _load_modules_from_path(path: Path, module_prefix: str):
#     modules = {}
#     for file_path in path.glob("*.py"):
#         if file_path.stem == "__init__": continue
#         module_name = f"{module_prefix}.{file_path.stem}"
#         spec = importlib.util.spec_from_file_location(module_name, file_path)
#         if spec and spec.loader:
#             module = importlib.util.module_from_spec(spec)
#             spec.loader.exec_module(module)
#             strategy_name = file_path.stem.replace('_', ' ').title()
#             modules[strategy_name] = module
#     return modules

# class Orchestrator:
#     def __init__(self, config: Dict[str, Any]):
#         self.cfg = config
#         self.keys = self.cfg.get("api_keys", {})
#         self.sets = self.cfg.get("agent_settings", {})
#         self.rapidapi_cfg = self.cfg.get("rapidapi", {})
#         self.moneycontrol_map = {
#             "INFY": "https://www.moneycontrol.com/india/stockpricequote/computers-software/infosys/IT",
#             "TCS": "https://www.moneycontrol.com/india/stockpricequote/computers-software/tataconsultancyservices/TCS",
#             "RELIANCE": "https://www.moneycontrol.com/india/stockpricequote/refineries/relianceindustries/RI"
#         }
#         print("Orchestrator: Initializing all agents...")
#         self._initialize_agents()
#         self._register_strategies()
#         print("Orchestrator: Initialization complete.")

#     # --- inside Orchestrator class ---

#     def _format_tickers_for_market(self, tickers: List[str], market: str) -> List[str]:
#         formatted = []
#         for t in tickers:
#             try:
#                 formatted_ticker = format_ticker(t, market)
#                 # Extra safeguard: check if data exists for the formatted ticker
#                 df_check = get_history(formatted_ticker, market, "2024-01-01", "2024-02-01")

#                 if df_check.empty:
#                     print(f"⚠️ Warning: No historical data for ticker '{t}' formatted as '{formatted_ticker}' in market '{market}'")
#                     formatted.append(None)  # Mark as invalid
#                 else:
#                     formatted.append(formatted_ticker)

#             except Exception as e:
#                 print(f"⚠️ Failed to format ticker '{t}' for market '{market}': {e}")
#                 formatted.append(None)  # Fallback

#         # Filter out None values to avoid passing invalid tickers
#         return [t for t in formatted if t is not None]

    
#     def _initialize_agents(self):
#         self.yfinance_agent = YFinanceAgent()
#         self.screener_agent = ScreenerAgent(rapidapi_config=self.rapidapi_cfg)
#         self.llm_agent = LLMAgent(gemini_api_key=self.keys.get("gemini"))
#         self.execution_agent = ExecutionAgent(api_key=self.keys.get("alpaca_key_id"), api_secret=self.keys.get("alpaca_secret_key"), paper=self.sets.get("paper_trading", True))
#         self.macro_agent = MacroAgent(fred_api_key=self.keys.get("fred"))
#         self.insider_agent = InsiderAgent(finnhub_key=self.keys.get("finnhub"), rapidapi_config=self.rapidapi_cfg)
#         self.sentiment_agent = SentimentAgent(reddit_client_id=self.keys.get("reddit_client_id"), reddit_client_secret=self.keys.get("reddit_client_secret"), reddit_user_agent=self.keys.get("reddit_user_agent"))

#     def _register_strategies(self):
#         print("Orchestrator: Discovering and registering strategies...")
#         long_term_path, short_term_path = Path("Long_Term_Strategy"), Path("strategies")
#         self.long_term_modules = _load_modules_from_path(long_term_path, "Long_Term_Strategy")
#         self.short_term_modules = _load_modules_from_path(short_term_path, "strategies")
#         print(f"Registered {len(self.long_term_modules)} long-term strategies.")
#         print(f"Registered {len(self.short_term_modules)} short-term strategies.")

#     # --- REQUIRED CHANGE 1: SIMPLIFY DEEP DIVE ANALYSIS ---
#     def run_deep_dive_analysis(self, ticker: str, start_date: str, end_date: str, market: str) -> Dict[str, Any]:
#         """
#         Runs a comprehensive multi-agent analysis using the new market-aware data loader.
#         This version is simpler and more robust.
#         """
#         print(f"Orchestrator: Running deep-dive for {ticker} in market '{market}'...")

#         # 1. Get base data from yfinance_agent, which now handles market formatting.
#         analysis_data = self.yfinance_agent.get_full_analysis(ticker, market)
#         if "error" in analysis_data:
#             return analysis_data

#         # 2. Add social media and news sentiment (market-agnostic).
#         analysis_data["social_sentiment"] = self.sentiment_agent.analyze(ticker)
#         news = get_company_news(ticker, self.keys.get("finnhub"), start_date, end_date)
#         headlines = [item.get("headline", "") for item in news]
#         analysis_data["news_sentiment"] = {"avg_score": calculate_headline_sentiment(headlines), "headlines": headlines[:10]}

#         # 3. Handle region-specific data (Insider Trading). This is now much cleaner.
#         if market.lower() == "india":
#             insider_analysis = {"summary": "N/A for this region", "transactions": pd.DataFrame()}
#         else:
#             insider_analysis = self.insider_agent.analyze(ticker)

#         analysis_data["insider_analysis"] = insider_analysis
        
#         return analysis_data

#     def run_market_overview(self) -> Dict[str, Any]:
#         print("Orchestrator: Running market overview...")
#         return {
#             "us_indicators": self.macro_agent.analyze_us_market(),
#             "india_indicators": self.macro_agent.analyze_indian_market(),
#             "global_indicators": self.macro_agent.get_global_indicators()
#         }

#     def run_long_term_analysis(self, tickers: List[str], market: str) -> Dict[str, Any]:
#         formatted_tickers = self._format_tickers_for_market(tickers, market)
#         print(f"Orchestrator: Running long-term analysis for formatted tickers: {formatted_tickers}...")

#         results = {}
#         for ticker in formatted_tickers:
#             results[ticker] = {name: module.analyze(ticker) for name, module in self.long_term_modules.items()}

#         return results


#     # --- REQUIRED CHANGE 2: UPDATE SHORT-TERM ANALYSIS TO PASS 'market' ---
#     def run_short_term_analysis(self, tickers: List[str], start_date: str, end_date: str, market: str) -> pd.DataFrame:
#         formatted_tickers = self._format_tickers_for_market(tickers, market)
#         if not formatted_tickers:
#             print("⚠️ No valid tickers to analyze after formatting. Skipping backtest.")
#             return pd.DataFrame()

#         print(f"Orchestrator: Running short-term backtests for formatted tickers: {formatted_tickers} in market '{market}'...")

#         all_summaries = []
#         for ticker in formatted_tickers:
#             for name, module in self.short_term_modules.items():
#                 if name == "Pairs Trading":
#                     continue

#                 print(f">>> Running strategy '{name}' on ticker '{ticker}' in market '{market}'")

#                 try:
#                     result_dict = module.run(ticker, start_date, end_date, market)
#                     if not isinstance(result_dict, dict):
#                         print(f"⚠️ Invalid strategy result for '{name}' and ticker '{ticker}'")
#                         result_dict = {"summary": {"Error": "Invalid return"}}

#                 except Exception as e:
#                     print(f"❌ Exception in strategy '{name}' for ticker '{ticker}': {e}")
#                     result_dict = {"summary": {"Error": f"Exception: {str(e)}"}}

#                 summary = result_dict.get("summary", {"Error": "Missing summary key"})
#                 summary['Strategy'] = name
#                 summary['Ticker'] = ticker
#                 all_summaries.append(summary)

#         # Pairs Trading block stays as-is (with similar error handling)

#         final_df = pd.DataFrame(all_summaries)
#         if not final_df.empty and 'Strategy' in final_df.columns:
#             cols = ['Strategy', 'Ticker'] + [c for c in final_df.columns if c not in ['Strategy', 'Ticker']]
#             final_df = final_df[cols]

#         return final_df

#     def run_comprehensive_ai_analysis(self, user_profile: Dict[str, Any], analysis_ticker: str, portfolio_strategies: List[str], market: str, start_date: str, end_date: str) -> str:
#         """
#         Runs a full suite of analyses, gets recommendations from two AI models,
#         and synthesizes them into a single, final report.
#         """
#         print("Orchestrator: Starting comprehensive AI analysis...")

#         # 1. GATHER ALL MARKET & STOCK DATA
#         print("--> Step 1: Gathering market overview...")
#         market_overview = self.run_market_overview()

#         print(f"--> Step 2: Running deep dive on {analysis_ticker}...")
#         deep_dive_data = self.run_deep_dive_analysis(analysis_ticker, start_date, end_date, market)

#         print(f"--> Step 3: Running portfolio backtest on {analysis_ticker}...")
#         portfolio_results = portfolio_engine.build_portfolio(
#             orchestrator=self,
#             tickers=[analysis_ticker],
#             market=market,
#             start_date=start_date,
#             end_date=end_date,
#             strategies_config=portfolio_strategies
#         )

#         # 2. CREATE THE MASTER CONTEXT FOR THE AI MODELS
#         full_context = {
#             "client_profile": user_profile,
#             "market_overview": market_overview,
#             "deep_dive_stock_analysis": deep_dive_data,
#             "portfolio_strategy_backtest": portfolio_results
#         }

#         # 3. GENERATE THE INITIAL PROMPT
#         initial_prompt = f"""
#         You are a junior financial analyst at a top-tier investment firm. Your task is to create a personalized investment plan for a client based on their profile and a comprehensive data package.

#         **CLIENT PROFILE:**
#         {json.dumps(user_profile, indent=2)}

#         **COMPREHENSIVE DATA PACKAGE:**
#         ```json
#         {json.dumps(full_context, indent=2, default=str)}
#         ```

#         **YOUR TASK:**
#         Based on all the provided data, write a detailed investment plan for the client. Structure your response in clear Markdown with headings for:
#         1.  **Investment Strategy:** Recommend a core strategy (e.g., Growth, Value, Income) and justify it based on the client's profile.
#         2.  **Asset Allocation:** Suggest a portfolio allocation. Reference specific data points from your analysis (e.g., "Given the strong performance of the Momentum strategy in the backtest...").
#         3.  **Specific Recommendations:** Mention the analyzed stock ({analysis_ticker}) and discuss its suitability for the client based on the deep-dive data.
#         4.  **Risk Management:** Provide 2-3 key risk management tips tailored to the client's profile and your recommended strategy.
#         """

#         # 4. GET REPORTS FROM BOTH JUNIOR ANALYSTS (LLAMA & MISTRAL)
#         print("--> Step 4: Querying Junior Analyst 'Llama3'...")
#         try:
#             llama_report = self.llm_agent.run(prompt=initial_prompt, model='llama3')
#         except Exception as e:
#             llama_report = f"Llama3 analysis failed: {e}"

#         print("--> Step 5: Querying Junior Analyst 'Mistral'...")
#         try:
#             mistral_report = self.llm_agent.run(prompt=initial_prompt, model='mistral')
#         except Exception as e:
#             mistral_report = f"Mistral analysis failed: {e}"

#         # 5. CREATE THE SYNTHESIS PROMPT FOR THE SENIOR ANALYST
#         synthesis_prompt = f"""
#         You are a senior portfolio manager. You have received two investment plans from your junior analysts, Llama3 and Mistral, for the same client. Your job is to synthesize these two reports into a single, cohesive, and definitive investment plan. You must identify the strongest points from each, resolve any contradictions, and provide the final authoritative recommendation.

#         **CLIENT PROFILE:**
#         {json.dumps(user_profile, indent=2)}

#         ---
#         **REPORT FROM JUNIOR ANALYST A (LLAMA3):**
#         {llama_report}
#         ---
#         **REPORT FROM JUNIOR ANALYST B (MISTRAL):**
#         {mistral_report}
#         ---

#         **YOUR TASK:**
#         Produce the final, unified investment plan. Use a professional and confident tone. Structure the final report clearly in Markdown. Do not refer to the junior analysts; present the final plan as your own expert recommendation.
#         """

#         # 6. GENERATE AND RETURN THE FINAL, SYNTHESIZED REPORT
#         print("--> Step 6: Synthesizing reports with senior analyst model...")
#         final_report = self.llm_agent.run(prompt=synthesis_prompt, model='llama3') # Use Llama3 as the "senior" model
#         print("Orchestrator: Comprehensive AI analysis complete.")
#         return final_report

#     # --- REQUIRED CHANGE 3: UPDATE AI RECOMMENDATION TO PASS 'market' ---
#     def get_ai_recommendation(self, user_profile: Dict[str, Any], provider: str = 'ollama', model: str = 'llama3') -> str:
#     # Use formatted US tickers for sample backtest
#         backtest_results = self.run_short_term_analysis(["SPY"], "2024-01-01", "2025-01-01", market="US")

#         if 'Error' in backtest_results.columns:
#             valid_backtests = backtest_results[backtest_results['Error'].isnull()].to_dict(orient='records')
#         else:
#             valid_backtests = backtest_results.to_dict(orient='records')

#         market_context = {
#             "market_overview": self.run_market_overview(),
#             "sample_short_term_backtests": valid_backtests
#         }

#         prompt = f"""
#         You are "QuantVest AI," a certified financial advisor...
#         CLIENT PROFILE: {user_profile}
#         MARKET DATA: {market_context}
#         TASK: Create a personalized investment plan...
#         """
#         return self.llm_agent.run(prompt)


#     @classmethod
#     def from_file(cls, path: str = "config.yaml") -> "Orchestrator":
#         """A factory method to create an Orchestrator instance from a YAML config file."""
#         with open(path, "r", encoding="utf-8") as f:
#             cfg = yaml.safe_load(f)
#         return cls(cfg)
# from __future__ import annotations
# import yaml
# import pandas as pd
# from pathlib import Path
# from typing import Dict, Any, List
# import importlib.util

# # --- Agents ---
# from agents.screener_agent import ScreenerAgent
# from agents.llm_analyst_agent import LLMAnalystAgent as LLMAgent
# from agents.execution_agent import ExecutionAgent
# from agents.macro_agent import MacroAgent
# from agents.insider_agent import InsiderAgent
# from agents.social_media_sentiment import SentimentAgent
# from agents.yfinance_agent import YFinanceAgent
# from strategies import (
#     sma_crossover, 
#     ema_crossover, 
#     momentum_strategy, 
#     mean_inversion, 
#     rsi_strategy,
#     reversal_strategy, 
#     breakout_strategy, 
#     channel_trading, 
#     custom_strategy, 
#     mcd_strategy,
#     pullback_fibonacci, 
#     support_resistance, 
#     pairs_trading # <--- ENSURE THIS LINE EXISTS AND IS CORRECT
# )
# # --- Utilities ---
# from utils.news_fetcher import get_live_quote, get_company_news, calculate_headline_sentiment
# from utils.moneycontrol_scraper import scrape_moneycontrol_data
# from utils.data_loader import get_history, add_technical_indicators, get_company_snapshot, _get_indian_symbols_set
# # --- Add the new utility to your imports ---
# from utils.data_loader import get_company_snapshot, get_history, add_technical_indicators, format_ticker

# def _load_modules_from_path(path: Path, module_prefix: str):

#     modules = {}
#     for file_path in path.glob("*.py"):
#         if file_path.stem == "__init__": continue
#         module_name = f"{module_prefix}.{file_path.stem}"
#         spec = importlib.util.spec_from_file_location(module_name, file_path)
#         if spec and spec.loader:
#             module = importlib.util.module_from_spec(spec)
#             spec.loader.exec_module(module)
#             strategy_name = file_path.stem.replace('_', ' ').title()
#             modules[strategy_name] = module
#     return modules

# class Orchestrator:
#     def __init__(self, config: Dict[str, Any]):
#         self.cfg = config
#         self.keys = self.cfg.get("api_keys", {})
#         self.sets = self.cfg.get("agent_settings", {})
#         self.rapidapi_cfg = self.cfg.get("rapidapi", {})
#         self.moneycontrol_map = {
#             "INFY": "https://www.moneycontrol.com/india/stockpricequote/computers-software/infosys/IT",
#             "TCS": "https://www.moneycontrol.com/india/stockpricequote/computers-software/tataconsultancyservices/TCS",
#             "RELIANCE": "https://www.moneycontrol.com/india/stockpricequote/refineries/relianceindustries/RI"
#         }
#         print("Orchestrator: Initializing all agents...")
#         self._initialize_agents()
#         self._register_strategies()
#         print("Orchestrator: Initialization complete.")

#     def _initialize_agents(self):
#         self.yfinance_agent = YFinanceAgent()
#         self.screener_agent = ScreenerAgent(rapidapi_config=self.rapidapi_cfg)
#         self.llm_agent = LLMAgent(gemini_api_key=self.keys.get("gemini"))
#         self.execution_agent = ExecutionAgent(api_key=self.keys.get("alpaca_key_id"), api_secret=self.keys.get("alpaca_secret_key"), paper=self.sets.get("paper_trading", True))
#         self.macro_agent = MacroAgent(fred_api_key=self.keys.get("fred"))
#         self.insider_agent = InsiderAgent(finnhub_key=self.keys.get("finnhub"), rapidapi_config=self.rapidapi_cfg)
#         self.sentiment_agent = SentimentAgent(reddit_client_id=self.keys.get("reddit_client_id"), reddit_client_secret=self.keys.get("reddit_client_secret"), reddit_user_agent=self.keys.get("reddit_user_agent"))

#     def _register_strategies(self):
#         print("Orchestrator: Discovering and registering strategies...")
#         long_term_path, short_term_path = Path("Long_Term_Strategy"), Path("strategies")
#         self.long_term_modules = _load_modules_from_path(long_term_path, "Long_Term_Strategy")
#         self.short_term_modules = _load_modules_from_path(short_term_path, "strategies")
#         print(f"Registered {len(self.long_term_modules)} long-term strategies.")
#         print(f"Registered {len(self.short_term_modules)} short-term strategies.")

#     # In agents/orchestrator.py

#     def run_deep_dive_analysis(self, ticker: str, start_date: str, end_date: str, market: str = "usa") -> Dict[str, Any]:
#         """
#         Runs a comprehensive multi-agent analysis. It now robustly detects
#         Indian stocks using the master symbol list from the data_loader.
#         """
#         formatted_ticker = format_ticker(ticker, market)

#         print(f"Orchestrator: Running deep-dive analysis for {formatted_ticker}...")
       
#         # 1. Get the comprehensive base data from the YFinanceAgent. This works for ALL stocks.
#         analysis_data = self.yfinance_agent.get_full_analysis(formatted_ticker)
#         if "error" in analysis_data:
#             return analysis_data

#         # 2. Add social media and news sentiment (works for all stocks)
#         analysis_data["social_sentiment"] = self.sentiment_agent.analyze(formatted_ticker)
#         news = get_company_news(formatted_ticker, self.keys.get("finnhub"), start_date, end_date)
#         headlines = [item.get("headline", "") for item in news]
#         analysis_data["news_sentiment"] = {"avg_score": calculate_headline_sentiment(headlines), "headlines": headlines[:10]}
        
#         # 3. Handle region-specific data (Live Price & Insider Trading)
#         snapshot = analysis_data.get("snapshot", {})
        
#         # --- THIS IS THE NEW, ROBUST LOGIC ---
#         # We use the currency code from the yfinance snapshot to reliably detect the region.
#         if snapshot.get("currency") == "INR":
#             print(f"Orchestrator: Indian stock detected ({ticker}). Using yfinance data as primary source.")
            
#             # For Indian stocks, the price from yfinance is reliable and sufficient.
#             live_quote = {
#                 "c": snapshot.get("currentPrice") or snapshot.get("regularMarketPrice", 0),
#                 "pc": snapshot.get("previousClose", 0)
#             }
#             # Insider trading data is generally not available for this region via these APIs.
#             insider_analysis = {
#                 "summary": {"Net Sentiment": "N/A for this region"},
#                 "transactions": pd.DataFrame()
#             }
#         else:
#             print(f"Orchestrator: US stock detected ({formatted_ticker}). Fetching live API data for price.")
            
#             # For US stocks, we can get a faster, more "live" price from the Finnhub API.
#             live_quote = get_live_quote(formatted_ticker, self.keys.get("finnhub"))
#             insider_analysis = self.insider_agent.analyze(formatted_ticker)

#         # 4. Populate the final dictionary with the correct regional data
#         analysis_data["live_quote"] = live_quote
#         analysis_data["insider_analysis"] = insider_analysis
#         analysis_data["stock_name"] = snapshot.get("longName", formatted_ticker)

#         return analysis_data

#     def run_market_overview(self) -> Dict[str, Any]:
#         print("Orchestrator: Running market overview...")
#         return {
#             "us_indicators": self.macro_agent.analyze_us_market(),
#             "india_indicators": self.macro_agent.analyze_indian_market(), # <-- CORRECTED
#             "global_indicators": self.macro_agent.get_global_indicators()
#         }

#     def run_long_term_analysis(self, tickers: List[str], market: str = "usa") -> Dict[str, Any]:
#         """
#         Runs the suite of long-term fundamental analyses for the given tickers,
#         after formatting them for the correct market.
#         """
#         # --- THIS IS THE UPGRADE ---
#         # 1. Format all tickers for the specified market
#         formatted_tickers = [format_ticker(t, market) for t in tickers]
#         print(f"Orchestrator: Running long-term analysis for formatted tickers: {formatted_tickers}...")
#         # --- END OF UPGRADE ---
        
#         results = {}
#         # 2. Loop through the *formatted* tickers for analysis
#         for ticker in formatted_tickers:
#             results[ticker] = {name: module.analyze(ticker) for name, module in self.long_term_modules.items()}
        
#         return results

#     def run_short_term_analysis(self, tickers: List[str], start_date: str, end_date: str, market: str = "usa") -> pd.DataFrame:
#         """
#         Runs the suite of short-term backtests for the given tickers and date range,
#         after formatting them for the correct market.
#         """
#         # --- THIS IS THE UPGRADE ---
#         # 1. Format all tickers for the specified market
#         formatted_tickers = [format_ticker(t, market) for t in tickers]
#         print(f"Orchestrator: Running short-term backtests for formatted tickers: {formatted_tickers}...")
#         # --- END OF UPGRADE ---
        
#         all_summaries = []
#         # 2. Loop through the *formatted* tickers for backtesting
#         for ticker in formatted_tickers:
#             for name, module in self.short_term_modules.items():
#                 if name == "Pairs Trading": continue
                
#                 result_dict = module.run(ticker, start_date, end_date)
#                 summary = result_dict.get("summary", {})
                
#                 summary['Strategy'] = name 
#                 summary['Ticker'] = ticker # Store the formatted ticker (e.g., 'RELIANCE.NS')
#                 all_summaries.append(summary)

#         # 3. Handle Pairs Trading with formatted tickers
#         if len(formatted_tickers) >= 2:
#              # Use the first two formatted tickers for the pair
#              pair_tickers = formatted_tickers[:2]
#              pair_result = pairs_trading.run(pair_tickers, start_date, end_date)
#              pair_summary = pair_result.get("summary", {})
             
#              # The 'Strategy' key is already formatted by the module
#              pair_summary['Ticker'] = f"{pair_tickers[0]}/{pair_tickers[1]}"
#              all_summaries.append(pair_summary)
             
#         final_df = pd.DataFrame(all_summaries)
        
#         # Reorder columns for clarity
#         if 'Strategy' in final_df.columns:
#             cols = ['Strategy', 'Ticker'] + [c for c in final_df.columns if c not in ['Strategy', 'Ticker']]
#             final_df = final_df[cols]
            
#         return final_df

#     def get_ai_recommendation(self, user_profile: Dict[str, Any], provider: str = 'ollama', model: str = 'llama3') -> str:
#         backtest_results = self.run_short_term_analysis(["SPY"], "2024-01-01", "2025-01-01")
#         valid_backtests = backtest_results[backtest_results['Error'].isnull()].to_dict(orient='records')
#         market_context = {
#             "market_overview": self.run_market_overview(),
#             "sample_short_term_backtests": valid_backtests
#         }
#         prompt = f"""
#         You are "QuantVest AI," a certified financial advisor...
#         CLIENT PROFILE: {user_profile}
#         MARKET DATA: {market_context}
#         TASK: Create a personalized investment plan...
#         """
#         return self.llm_agent.run(prompt)

#     @classmethod
#     def from_file(cls, path: str = "config.yaml") -> "Orchestrator":
#         """A factory method to create an Orchestrator instance from a YAML config file."""
#         with open(path, "r", encoding="utf-8") as f:
#             cfg = yaml.safe_load(f)
#         return cls(cfg)

# from __future__ import annotations
# import yaml
# import pandas as pd
# import importlib.util
# import os
# from pathlib import Path
# from typing import Dict, Any, List

# # --- Import all REAL agents ---
# from agents.screener_agent import ScreenerAgent
# from agents.llm_analyst_agent import LLMAnalystAgent as LLMAgent
# from agents.execution_agent import ExecutionAgent
# from agents.macro_agent import MacroAgent
# from agents.insider_agent import InsiderAgent
# from agents.social_media_sentiment import SentimentAgent
# # --- Import ALL agents and utilities needed ---

# from agents.social_media_sentiment import SentimentAgent
# from utils.data_loader import get_company_snapshot, get_history, add_technical_indicators
# from utils.news_fetcher import get_live_quote, get_company_news, calculate_headline_sentiment
# from utils.moneycontrol_scraper import scrape_moneycontrol_data
# # --- Import all REAL utility modules ---
# from utils.data_loader import get_company_snapshot, get_history, add_technical_indicators
# from utils.news_fetcher import get_live_quote, get_company_news, calculate_headline_sentiment
# # --- Import the web scraper ---
# from utils.moneycontrol_scraper import scrape_moneycontrol_data


# def _load_modules_from_path(path: Path, module_prefix: str):
#     """Dynamically loads all python modules from a given directory path."""
#     modules = {}
#     for file_path in path.glob("*.py"):
#         if file_path.stem == "__init__":
#             continue
        
#         module_name = f"{module_prefix}.{file_path.stem}"
#         spec = importlib.util.spec_from_file_location(module_name, file_path)
#         if spec and spec.loader:
#             module = importlib.util.module_from_spec(spec)
#             spec.loader.exec_module(module)
#             strategy_name = file_path.stem.replace('_', ' ').title()
#             modules[strategy_name] = module
#     return modules

# class Orchestrator:
#     def __init__(self, config: Dict[str, Any]):
#         """
#         Initializes the entire ecosystem of agents based on the central config file.
#         """
#         self.cfg = config
#         self.keys = self.cfg.get("api_keys", {})
#         self.sets = self.cfg.get("agent_settings", {})
#         self.rapidapi_cfg = self.cfg.get("rapidapi", {})
        
#         self.moneycontrol_map = {
#             "INFY": "https://www.moneycontrol.com/india/stockpricequote/computers-software/infosys/IT",
#             "TCS": "https://www.moneycontrol.com/india/stockpricequote/computers-software/tataconsultancyservices/TCS",
#             "RELIANCE": "https://www.moneycontrol.com/india/stockpricequote/refineries/relianceindustries/RI"
#         }
        
#         print("Orchestrator: Initializing all agents...")
#         self._initialize_agents()
#         self._register_strategies()
#         print("Orchestrator: Initialization complete.")

#     def _initialize_agents(self):
#         """Creates instances of all agents the orchestrator can use."""
#         self.screener_agent = ScreenerAgent(rapidapi_config=self.rapidapi_cfg)
#         self.llm_agent = LLMAgent(gemini_api_key=self.keys.get("gemini"))
#         self.execution_agent = ExecutionAgent(
#             api_key=self.keys.get("alpaca_key_id"),
#             api_secret=self.keys.get("alpaca_secret_key"),
#             paper=self.sets.get("paper_trading", True)
#         )
#         self.macro_agent = MacroAgent(fred_api_key=self.keys.get("fred"))
#         self.insider_agent = InsiderAgent(
#             finnhub_key=self.keys.get("finnhub"),
#             rapidapi_config=self.rapidapi_cfg
#         )
#         self.sentiment_agent = SentimentAgent(
#             reddit_client_id=self.keys.get("reddit_client_id"),
#             reddit_client_secret=self.keys.get("reddit_client_secret"),
#             reddit_user_agent=self.keys.get("reddit_user_agent")
#         )

#     def _register_strategies(self):
#         """Dynamically discovers and registers all available strategy modules."""
#         print("Orchestrator: Discovering and registering strategies...")
#         long_term_path = Path("Long_Term_Strategy")
#         short_term_path = Path("strategies")
        
#         self.long_term_modules = _load_modules_from_path(long_term_path, "Long_Term_Strategy")
#         self.short_term_modules = _load_modules_from_path(short_term_path, "strategies")
        
#         print(f"Registered {len(self.long_term_modules)} long-term strategies.")
#         print(f"Registered {len(self.short_term_modules)} short-term strategies.")

#     # --- PRIMARY WORKFLOW METHODS CALLED BY THE FRONTEND ---

#     # In agents/orchestrator.py

#     def run_deep_dive_analysis(self, ticker: str, start_date: str, end_date: str) -> Dict[str, Any]:
#         """
#         Runs a comprehensive, multi-agent analysis on a single stock, with a special
#         combined data path for Indian stocks. This version is hardened against scraper failures.
#         """
#         print(f"Orchestrator: Running deep-dive analysis for {ticker}...")
        
#         # --- Universal Data Gathering ---
#         hist_df = get_history(ticker, start_date, end_date)
#         if hist_df.empty: return {"error": "Could not fetch historical data."}
        
#         enriched_df = add_technical_indicators(hist_df)
#         snapshot = get_company_snapshot(ticker)
#         social_sentiment = self.sentiment_agent.analyze(ticker)

#         # --- Conditional Data Gathering ---
#         clean_ticker = ticker.upper().replace(".NS", "")
        
#         if clean_ticker in self.moneycontrol_map:
#             # --- Path for Indian Stocks: Combine Scraper + APIs ---
#             print(f"Orchestrator: Indian stock detected. Using combined approach for {clean_ticker}...")
            
#             mc_url = self.moneycontrol_map[clean_ticker]
#             scraped_data = scrape_moneycontrol_data(mc_url)
            
#             # --- HARDENED PRICE HANDLING ---
#             # Step 1: Safely get the price string from the scraper's result.
#             price_str = scraped_data.get("nse_price") 
            
#             # Step 2: If the result is None (empty), default it to '0'.
#             if price_str is None:
#                 price_str = '0'
            
#             # Step 3: Now it's safe to call .replace() and convert to float.
#             cleaned_price_str = price_str.replace(',', '')
#             price_float = float(cleaned_price_str) if cleaned_price_str else 0.0
#             live_quote = {"c": price_float, "pc": 0} 
            
#             # Use APIs for news and sentiment
#             news = get_company_news(ticker, self.keys.get("finnhub"))
#             headlines = [item.get("headline", "") for item in news]
#             news_sentiment = {"avg_score": calculate_headline_sentiment(headlines), "headlines": headlines[:10]}
#             insider_analysis = {"summary": "Data not available for this region", "transactions": pd.DataFrame()}

#         else:
#             # --- Path for Other Stocks ---
#             print(f"Orchestrator: Using standard APIs for {ticker}...")
#             live_quote = get_live_quote(ticker, self.keys.get("finnhub"))
#             news = get_company_news(ticker, self.keys.get("finnhub"))
#             headlines = [item.get("headline", "") for item in news]
#             news_sentiment = {"avg_score": calculate_headline_sentiment(headlines), "headlines": headlines[:10]}
#             insider_analysis = self.insider_agent.analyze(ticker)
#             scraped_data = {}

#         return {
#             "snapshot": snapshot,
#             "live_quote": live_quote,
#             "news_sentiment": news_sentiment,
#             "social_sentiment": social_sentiment,
#             "insider_analysis": insider_analysis,
#             "technical_data": enriched_df.tail(1).to_dict(orient='records')[0] if not enriched_df.empty else {},
#             "scraped_data": scraped_data
#         }
#     def run_long_term_analysis(self, tickers: List[str]) -> Dict[str, Any]:
#         """Runs the suite of long-term fundamental analyses for the given tickers."""
#         print(f"Orchestrator: Running long-term analysis for {tickers}...")
#         results = {}
#         for ticker in tickers:
#             results[ticker] = {name: module.analyze(ticker) for name, module in self.long_term_modules.items()}
#         return results

#     def run_short_term_analysis(self, tickers: List[str], start_date: str, end_date: str) -> pd.DataFrame:
#         """Runs the suite of short-term backtests and returns a summary DataFrame."""
#         print(f"Orchestrator: Running short-term backtests for {tickers}...")
#         all_summaries = []
#         for ticker in tickers:
#             for name, module in self.short_term_modules.items():
#                 if name == "Pairs Trading": continue
#                 try:
#                     result_dict = module.run(ticker, start_date, end_date)
#                     summary = result_dict.get("summary", {})
#                     summary['Strategy'] = name
#                     summary['Ticker'] = ticker
#                     all_summaries.append(summary)
#                 except Exception as e:
#                     print(f"ERROR running strategy '{name}' for ticker '{ticker}': {e}")
#                     all_summaries.append({'Strategy': name, 'Ticker': ticker, 'Error': str(e)})

#         if len(tickers) >= 2 and "Pairs Trading" in self.short_term_modules:
#              try:
#                  pair_module = self.short_term_modules["Pairs Trading"]
#                  pair_result = pair_module.run(tickers[:2], start_date, end_date)
#                  pair_summary = pair_result.get("summary", {})
#                  pair_summary['Ticker'] = f"{tickers[0]}/{tickers[1]}"
#                  all_summaries.append(pair_summary)
#              except Exception as e:
#                  print(f"ERROR running strategy 'Pairs Trading' for tickers '{tickers[:2]}': {e}")
#                  all_summaries.append({'Strategy': 'Pairs Trading', 'Ticker': f"{tickers[0]}/{tickers[1]}", 'Error': str(e)})
             
#         return pd.DataFrame(all_summaries)

#     def run_market_overview(self) -> Dict[str, Any]:
#         """Provides a top-down view of the market using the MacroAgent."""
#         print("Orchestrator: Running market overview...")
#         return {
#             "us_indicators": self.macro_agent.analyze_us_market(),
#              "india_indicators": self.macro_agent.analyze_indian_market(),
#             "global_indicators": self.macro_agent.get_global_indicators()
#         }
        
#     def get_ai_recommendation(self, user_profile: Dict[str, Any], provider: str = 'ollama', model: str = 'llama3') -> str:
#         """Gathers market context and passes it to the LLMAgent for a personalized plan."""
#         print(f"Orchestrator: Gathering context for AI recommendation via {provider}:{model}...")
#         backtest_results = self.run_short_term_analysis(["SPY"], "2024-01-01", "2025-01-01")
        
#         valid_backtests = backtest_results[backtest_results['Error'].isnull()].to_dict(orient='records')

#         market_context = {
#             "market_overview": self.run_market_overview(),
#             "sample_short_term_backtests": valid_backtests
#         }
#         prompt = f"""
#         You are "QuantVest AI," a certified financial advisor...
#         CLIENT PROFILE: {user_profile}
#         MARKET DATA: {market_context}
#         TASK: Create a personalized investment plan...
#         """
#         return self.llm_agent.run(prompt)

#     @classmethod
#     def from_file(cls, path: str = "quant-company-insights-agent/config.yaml") -> "Orchestrator":
#         with open(path, "r", encoding="utf-8") as f:
#             cfg = yaml.safe_load(f)
#         return cls(cfg)


# from __future__ import annotations
# import yaml
# import pandas as pd
# import importlib.util
# import os
# from pathlib import Path
# from typing import Dict, Any, List

# # --- Import all REAL agents ---
# from agents.screener_agent import ScreenerAgent
# from agents.llm_analyst_agent import LLMAnalystAgent as LLMAgent
# from agents.execution_agent import ExecutionAgent
# from agents.macro_agent import MacroAgent
# from agents.insider_agent import InsiderAgent
# from agents.social_media_sentiment import SentimentAgent

# # --- Import all REAL utility modules ---
# from utils.data_loader import get_company_snapshot, get_history, add_technical_indicators
# from utils.news_fetcher import get_live_quote, get_company_news, calculate_headline_sentiment

# def _load_modules_from_path(path: Path, module_prefix: str):
#     """Dynamically loads all python modules from a given directory path."""
#     modules = {}
#     for file_path in path.glob("*.py"):
#         if file_path.stem == "__init__":
#             continue
        
#         module_name = f"{module_prefix}.{file_path.stem}"
#         spec = importlib.util.spec_from_file_location(module_name, file_path)
#         if spec and spec.loader:
#             module = importlib.util.module_from_spec(spec)
#             spec.loader.exec_module(module)
#             # Use a readable name for the strategy, e.g., "SMA Crossover" from "sma_crossover"
#             strategy_name = file_path.stem.replace('_', ' ').title()
#             modules[strategy_name] = module
#     return modules

# class Orchestrator:
#     def __init__(self, config: Dict[str, Any]):
#         """
#         Initializes the entire ecosystem of agents based on the central config file.
#         """
#         self.cfg = config
#         self.keys = self.cfg.get("api_keys", {})
#         self.sets = self.cfg.get("agent_settings", {})
#         self.rapidapi_cfg = self.cfg.get("rapidapi", {})
        
#         print("Orchestrator: Initializing all agents...")
#         self._initialize_agents()
#         self._register_strategies()
#         print("Orchestrator: Initialization complete.")

#     def _initialize_agents(self):
#         """Creates instances of all agents the orchestrator can use."""
#         self.screener_agent = ScreenerAgent(rapidapi_config=self.rapidapi_cfg)
#         self.llm_agent = LLMAgent(gemini_api_key=self.keys.get("gemini"))
#         self.execution_agent = ExecutionAgent(
#             api_key=self.keys.get("alpaca_key_id"),
#             api_secret=self.keys.get("alpaca_secret_key"),
#             paper=self.sets.get("paper_trading", True)
#         )
#         self.macro_agent = MacroAgent(fred_api_key=self.keys.get("fred"))
#         self.insider_agent = InsiderAgent(
#             finnhub_key=self.keys.get("finnhub"),
#             rapidapi_config=self.rapidapi_cfg
#         )
#         self.sentiment_agent = SentimentAgent(
#             reddit_client_id=self.keys.get("reddit_client_id"),
#             reddit_client_secret=self.keys.get("reddit_client_secret"),
#             reddit_user_agent=self.keys.get("reddit_user_agent")
#         )

#     def _register_strategies(self):
#         """Dynamically discovers and registers all available strategy modules."""
#         print("Orchestrator: Discovering and registering strategies...")
#         # Assuming the script is run from the root 'Boomerang' directory
#         long_term_path = Path("Long_Term_Strategy")
#         short_term_path = Path("strategies")
        
#         self.long_term_modules = _load_modules_from_path(long_term_path, "Long_Term_Strategy")
#         self.short_term_modules = _load_modules_from_path(short_term_path, "strategies")
        
#         print(f"Registered {len(self.long_term_modules)} long-term strategies.")
#         print(f"Registered {len(self.short_term_modules)} short-term strategies.")

#     # --- PRIMARY WORKFLOW METHODS CALLED BY THE FRONTEND ---

#     def run_deep_dive_analysis(self, ticker: str, start_date: str, end_date: str) -> Dict[str, Any]:
#         """Runs a comprehensive, multi-agent analysis on a single stock."""
#         print(f"Orchestrator: Running deep-dive analysis for {ticker}...")
#         hist_df = get_history(ticker, start_date, end_date)
#         if hist_df.empty: return {"error": "Could not fetch historical data."}
        
#         enriched_df = add_technical_indicators(hist_df)
        
#         snapshot = get_company_snapshot(ticker)
#         live_quote = get_live_quote(ticker, self.keys.get("finnhub"))
#         news = get_company_news(ticker, self.keys.get("finnhub"))
#         headlines = [item.get("headline", "") for item in news]
#         news_sentiment = calculate_headline_sentiment(headlines)
#         social_sentiment = self.sentiment_agent.analyze(ticker)
#         insider_analysis = self.insider_agent.analyze(ticker)

#         return {
#             "snapshot": snapshot,
#             "live_quote": live_quote,
#             "news_sentiment": {"avg_score": news_sentiment, "headlines": headlines[:10]},
#             "social_sentiment": social_sentiment,
#             "insider_analysis": insider_analysis,
#             "technical_data": enriched_df.tail(1).to_dict(orient='records')[0] if not enriched_df.empty else {}
#         }

#     def run_long_term_analysis(self, tickers: List[str]) -> Dict[str, Any]:
#         """Runs the suite of long-term fundamental analyses for the given tickers."""
#         print(f"Orchestrator: Running long-term analysis for {tickers}...")
#         results = {}
#         for ticker in tickers:
#             results[ticker] = {name: module.analyze(ticker) for name, module in self.long_term_modules.items()}
#         return results

#     def run_short_term_analysis(self, tickers: List[str], start_date: str, end_date: str) -> pd.DataFrame:
#         """Runs the suite of short-term backtests and returns a summary DataFrame."""
#         print(f"Orchestrator: Running short-term backtests for {tickers}...")
#         all_summaries = []
#         for ticker in tickers:
#             for name, module in self.short_term_modules.items():
#                 if name == "Pairs Trading": continue
#                 try:
#                     result_dict = module.run(ticker, start_date, end_date)
#                     summary = result_dict.get("summary", {})
#                     summary['Strategy'] = name
#                     summary['Ticker'] = ticker
#                     all_summaries.append(summary)
#                 except Exception as e:
#                     print(f"ERROR running strategy '{name}' for ticker '{ticker}': {e}")
#                     # Optionally, append a summary indicating the error
#                     all_summaries.append({'Strategy': name, 'Ticker': ticker, 'Error': str(e)})


#         if len(tickers) >= 2 and "Pairs Trading" in self.short_term_modules:
#              try:
#                  pair_module = self.short_term_modules["Pairs Trading"]
#                  pair_result = pair_module.run(tickers[:2], start_date, end_date)
#                  pair_summary = pair_result.get("summary", {})
#                  pair_summary['Ticker'] = f"{tickers[0]}/{tickers[1]}"
#                  all_summaries.append(pair_summary)
#              except Exception as e:
#                  print(f"ERROR running strategy 'Pairs Trading' for tickers '{tickers[:2]}': {e}")
#                  all_summaries.append({'Strategy': 'Pairs Trading', 'Ticker': f"{tickers[0]}/{tickers[1]}", 'Error': str(e)})
             
#         return pd.DataFrame(all_summaries)


#     def run_market_overview(self) -> Dict[str, Any]:
#         """Provides a top-down view of the market using the MacroAgent."""
#         print("Orchestrator: Running market overview...")
#         return {
#             "us_indicators": self.macro_agent.analyze_us_market(),
#             "india_indicators": self.macro_agent.analyze_indian_market(),
#             "global_indicators": self.macro_agent.get_global_indicators()
#         }
        
#     def get_ai_recommendation(self, user_profile: Dict[str, Any], provider: str = 'ollama', model: str = 'llama3') -> str:
#         """Gathers market context and passes it to the LLMAgent for a personalized plan."""
#         print(f"Orchestrator: Gathering context for AI recommendation via {provider}:{model}...")
#         backtest_results = self.run_short_term_analysis(["SPY"], "2024-01-01", "2025-01-01")
        
#         # Filter out any rows that have error information
#         valid_backtests = backtest_results[backtest_results['Error'].isnull()].to_dict(orient='records')

#         market_context = {
#             "market_overview": self.run_market_overview(),
#             "sample_short_term_backtests": valid_backtests
#         }
#         prompt = f"""
#         You are "QuantVest AI," a certified financial advisor...
#         CLIENT PROFILE: {user_profile}
#         MARKET DATA: {market_context}
#         TASK: Create a personalized investment plan...
#         """
#         return self.llm_agent.run(prompt)


#     @classmethod
#     def from_file(cls, path: str = "quant-company-insights-agent/config.yaml") -> "Orchestrator":
#         with open(path, "r", encoding="utf-8") as f:
#             cfg = yaml.safe_load(f)
#         return cls(cfg)