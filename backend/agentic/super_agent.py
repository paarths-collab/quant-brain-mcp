import asyncio
import json
from langgraph.graph import StateGraph, END
from typing import Dict, Any

from backend.agentic.state import AgentState
from backend.agentic.client import LLMClient
from backend.agentic.agents.financial_agent import FinancialAgent
from backend.agentic.agents.web_agent import WebAgent
from backend.agentic.agents.sector_agent import SectorAgent
from backend.agentic.agents.emotional_agent import EmotionalAgent
from backend.agentic.agents.reflection_agent import ReflectionAgent
from backend.agentic.agents.code_agent import CodeAgent
from backend.agentic.engines.confidence_engine import ConfidenceEngine
from backend.agentic.engines.divergence_detector import DivergenceDetector

class SuperAgent:
    def __init__(self):
        self.llm = LLMClient()
        
        # Agents
        self.financial = FinancialAgent()
        self.web = WebAgent()
        self.sector = SectorAgent()
        self.emotional = EmotionalAgent()
        self.reflection = ReflectionAgent()
        self.code = CodeAgent()
        
        # Engines
        self.confidence = ConfidenceEngine()
        self.divergence = DivergenceDetector()
        
        self.workflow = self._build_graph()

    def _build_graph(self):
        def emotional_check(state: AgentState):
            status = self.emotional.analyze(state.query)
            state.emotional_status = status
            return state

        def planner(state: AgentState):
            # GPT-OSS Reasoning for Plan
            messages = [
                {"role": "system", "content": "You are a Strategist. Create a JSON plan with 'plan': [{'agent': 'web'|'financial'|'sector', 'task': '...'}]."},
                {"role": "user", "content": f"Query: {state.query} Emotion: {state.emotional_status}"}
            ]
            try:
                plan_json = self.llm.run_reasoning(messages)
                if "```json" in plan_json:
                    plan_json = plan_json.split("```json")[1].split("```")[0]
                state.plan = json.loads(plan_json).get("plan", [])
            except:
                state.plan = [] 

            # Force Mandatory Agents for reliability
            existing_agents = [p["agent"] for p in state.plan]
            
            if "financial" not in existing_agents:
                state.plan.append({"agent": "financial", "task": state.query})
            if "web" not in existing_agents:
                state.plan.append({"agent": "web", "task": state.query})
            
            return state

        async def execute_parallel(state: AgentState):
            tasks = []
            
            # 1. Run Financial First (to get Sector info)
            fin_task = next((p for p in state.plan if p["agent"] == "financial"), None)
            if fin_task:
                 state.agent_outputs["financial"] = await self.financial.execute(fin_task["task"])
            
            # 2. Determine Sector from Financial Data
            fin_data = state.agent_outputs.get("financial", {}).get("analysis", {})
            detected_sector = "market"
            if fin_data:
                first_ticker = list(fin_data.keys())[0] if fin_data else None
                if first_ticker and "sector" in fin_data[first_ticker]:
                     detected_sector = fin_data[first_ticker]["sector"]
            
            # 3. Run Web & Sector (Parallel)
            web_task = next((p for p in state.plan if p["agent"] == "web"), None)
            sector_task = next((p for p in state.plan if p["agent"] == "sector"), None)
            
            sub_tasks = []
            keys = []
            
            if web_task:
                sub_tasks.append(self.web.execute(web_task["task"]))
                keys.append("web")
            
            # Force sector agent with detected sector
            if True: # Always run sector
                task_str = detected_sector if detected_sector != "market" else state.query
                sub_tasks.append(self.sector.execute(task_str))
                keys.append("sector")

            results = await asyncio.gather(*sub_tasks, return_exceptions=True)
            
            for k, res in zip(keys, results):
                state.agent_outputs[k] = res if not isinstance(res, Exception) else {"error": str(res)}
                
            return state

        def validate_data(state: AgentState):
            required = ["financial", "web"]
            missing = [r for r in required if r not in state.agent_outputs or "error" in state.agent_outputs[r]]
            if missing:
                state.execution_log.append({"step": "validation", "error": f"Missing/Error in agents: {missing}"})
            return state

        def reflect(state: AgentState):
            critique = self.reflection.review(
                state.query, state.agent_outputs, state.emotional_status, []
            )
            state.reflection_result = critique
            return state

        def synthesize(state: AgentState):
            context = {
                "query": state.query,
                "outputs": state.agent_outputs,
                "critique": state.reflection_result
            }
            messages = [
                {"role": "system", "content": "Synthesize the research into a final report."},
                {"role": "user", "content": str(context)[:10000]}
            ]
            state.final_report = self.llm.run_reasoning(messages)
            return state

        workflow = StateGraph(AgentState)
        workflow.add_node("emotional", emotional_check)
        workflow.add_node("planner", planner)
        workflow.add_node("executor", execute_parallel)
        workflow.add_node("validator", validate_data)
        workflow.add_node("reflector", reflect)
        workflow.add_node("synthesizer", synthesize)

        workflow.set_entry_point("emotional")
        workflow.add_edge("emotional", "planner")
        workflow.add_edge("planner", "executor")
        workflow.add_edge("executor", "validator")
        workflow.add_edge("validator", "reflector")
        workflow.add_edge("reflector", "synthesizer")
        workflow.add_edge("synthesizer", END)

        return workflow.compile()

    async def execute(self, query: str):
        initial = AgentState(query=query)
        final = await self.workflow.ainvoke(initial)
        # LangGraph returning dict or object depending on version/config
        if isinstance(final, dict):
            return final
        return final.__dict__
