"""LangGraph routing for a single bounded research job.

Model execution and evidence admission remain in research_workflow. The graph
owns scheduling, the analyst join, and correction routing. It deliberately has
no checkpointer: the existing job store persists jobs/reports, not resumable
model calls. Automatic node retries could repeat paid research and are disabled.
"""
from __future__ import annotations

from typing import Awaitable, Callable, TypedDict

from langgraph.graph import END, START, StateGraph
from langsmith import tracing_context

from core.research_workflow import Findings


class ResearchGraphState(TypedDict, total=False):
    lead_result: Findings
    company_result: Findings
    quant_result: Findings
    skeptic_result: Findings
    audit_result: Findings
    correction_result: Findings
    synthesis_result: Findings
    correction_round: int


InvokeRole = Callable[[str, str | None], Awaitable[Findings]]


def build_research_graph(invoke: InvokeRole, depth: str):
    """Compile a fresh graph per job; no state is shared between users/jobs."""
    if depth not in ("quick", "standard", "deep"):
        raise ValueError("Unsupported research depth")
    correction_limit = {"quick": 0, "standard": 1, "deep": 2}[depth]
    builder = StateGraph(ResearchGraphState)

    def role_node(role: str, output: str):
        async def node(state: ResearchGraphState):
            return {output: await invoke(role, None)}
        return node

    for role in ("company", "quant", "synthesizer"):
        output = "synthesis_result" if role == "synthesizer" else f"{role}_result"
        builder.add_node(role, role_node(role, output))

    async def audit(state: ResearchGraphState):
        index = state["correction_round"]
        label = f"audit_{index}" if index else None
        return {"audit_result": await invoke("auditor", label)}

    async def correction(state: ResearchGraphState):
        index = state["correction_round"] + 1
        return {
            "correction_result": await invoke("company", f"correction_{index}"),
            "correction_round": index,
        }

    def after_audit(state: ResearchGraphState):
        if state["audit_result"].needs_correction and state["correction_round"] < correction_limit:
            return "correction"
        return "synthesizer"

    builder.add_node("auditor", audit)
    builder.add_node("correction", correction)
    if depth == "quick":
        entry, joined = START, "auditor"
    else:
        builder.add_node("lead", role_node("lead", "lead_result"))
        builder.add_node("skeptic", role_node("skeptic", "skeptic_result"))
        builder.add_edge(START, "lead")
        builder.add_edge("skeptic", "auditor")
        entry, joined = "lead", "skeptic"
    builder.add_edge(entry, "company")
    builder.add_edge(entry, "quant")
    # A list edge is a barrier: review runs once, only after BOTH analysts.
    builder.add_edge(["company", "quant"], joined)
    builder.add_conditional_edges("auditor", after_audit, {
        "correction": "correction", "synthesizer": "synthesizer",
    })
    builder.add_edge("correction", "auditor")
    builder.add_edge("synthesizer", END)
    return builder.compile()


async def run_role_graph(invoke: InvokeRole, depth: str) -> ResearchGraphState:
    graph = build_research_graph(invoke, depth)
    # Deep needs nine supersteps, at most ten model calls. Keep an independent
    # graph bound as well as the workflow's invocation budget.
    # Research prompts must not be exported by an ambient LangSmith setting.
    with tracing_context(enabled=False):
        return await graph.ainvoke({"correction_round": 0}, {"recursion_limit": 16})
