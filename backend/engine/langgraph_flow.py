from langgraph.graph import StateGraph, END
from backend.engine.state_schema import AgentState
from backend.agents.super_agent import SuperAgent
import asyncio

# This function builds the graph, but needs the initialized super_agent instance
def build_graph(super_agent: SuperAgent):

    workflow = StateGraph(AgentState)

    # Define the main execution node
    # Since SuperAgent.run is async and returns a dict, we need a wrapper to map it to State
    async def run_super_agent_node(state: AgentState):
        query = state["query"]
        ticker = state.get("ticker")
        market = state.get("market", "us")
        session_id = state.get("session_id", "default")
        
        # SuperAgent.run logic handles memory and screener switching internally now
        result = await super_agent.run_orchestrator(query, ticker, market, session_id)
        
        # Result matches the keys in AgentState (mostly)
        # We update the state with the result
        return result

    # Add nodes
    workflow.add_node("super_agent", run_super_agent_node)

    # Set entry point
    workflow.set_entry_point("super_agent")

    # Set finish point
    workflow.add_edge("super_agent", END)

    return workflow.compile()
