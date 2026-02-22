from backend1.agents.financial_agent import FinancialAnalystAgent
from backend1.agents.risk_agent import RiskAgent
from backend1.agents.strategy_lab import StrategyLab
from backend1.agents.validation_agent import ValidationAgent
# Keeping WebSearchAgent from previous step just in case, though user replaced it in snippet
from backend1.agents.web_search_agent import WebSearchAgent 

class ExecutionEngine:

    def __init__(self):
        self.financial = FinancialAnalystAgent()
        self.risk = RiskAgent()
        self.strategy = StrategyLab()
        self.validator = ValidationAgent()
        self.web_agent = WebSearchAgent()

    def execute(self, schema, state=None):
        if state is None:
            state = {}

        agent_tasks = schema.get("agent_tasks", {})

        # Run Web Search (Preserving generic capability)
        if "WebSearchAgent" in schema.get("selected_agents", []):
            search_queries = schema.get("search_queries", [])
            # Only send first 2 queries to prevent overload
            limited_queries = search_queries[:2]
            
            web_results = []
            for q in limited_queries:
                print(f"Executing WebSearchAgent with query: {q}")
                result = self.web_agent.run(q)
                web_results.append(result)
            
            state["web_search"] = web_results

        # Helper to find ticker from intent/queries
        ticker_context = ""
        intent = schema.get("intent", "")
        queries = schema.get("search_queries", [])
        
        # Simple extraction for context injection
        import re
        candidates = re.findall(r'\b[A-Z]{2,5}\b', intent) + re.findall(r'\b[A-Z]{2,5}\b', " ".join(queries))
        valid_candidates = [c for c in candidates if c not in ["AND", "THE", "FOR", "AI", "US", "UK"]]
        if valid_candidates:
            ticker_context = valid_candidates[0]

        # Run Financial
        if "FinancialAnalystAgent" in schema.get("selected_agents", []):
            task = agent_tasks.get("FinancialAnalystAgent", "")
            # Inject ticker if not present
            if ticker_context and ticker_context not in task:
                task = f"{task} for {ticker_context}"
                
            state["financial"] = self.financial.run(task)

        if "FinancialAnalyst" in schema.get("selected_agents", []): # Alias matching controller prompt
             task = agent_tasks.get("FinancialAnalyst", "")
             if ticker_context and ticker_context not in task:
                task = f"{task} for {ticker_context}"
             
             state["financial"] = self.financial.run(task)

        # Run Risk
        if "RiskAgent" in schema.get("selected_agents", []):
            state["risk"] = self.risk.run(
                agent_tasks.get("RiskAgent", "")
            )

        # Run Strategy
        if "StrategyLab" in schema.get("selected_agents", []):
            if "financial" in state and "error" not in state["financial"] and "current_price" in state["financial"]:
                state["strategy"] = self.strategy.run(
                    agent_tasks.get("StrategyLab", ""),
                    state
                )
            else:
                 print("Skipping StrategyLab: Missing or invalid financial data.")
                 state["strategy"] = {"error": "Skipped due to missing financial data"}

        # Validate Final Output
        state["validation"] = self.validator.run(state)

        return state
