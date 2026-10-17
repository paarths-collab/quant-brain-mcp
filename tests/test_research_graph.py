"""Scheduling contracts tested against the real LangGraph executor."""
import asyncio

import pytest

from core.research_graph import build_research_graph, run_role_graph
from core.research_workflow import Findings


@pytest.mark.parametrize("depth,limit,total", [("quick", 0, 4), ("standard", 1, 8), ("deep", 2, 10)])
def test_graph_bounds_and_joins(depth, limit, total):
    async def run():
        calls, finished = [], set()
        both_started = asyncio.Event()
        started = set()

        async def invoke(role, label):
            calls.append(label or role)
            if role in ("company", "quant") and label is None:
                started.add(role)
                if len(started) == 2:
                    both_started.set()
                await asyncio.wait_for(both_started.wait(), 1)
                if role == "quant":
                    await asyncio.sleep(0.01)
                finished.add(role)
            if role in ("skeptic", "auditor", "synthesizer"):
                assert finished == {"company", "quant"}
            return Findings(summary=label or role, needs_correction=role == "auditor")

        state = await run_role_graph(invoke, depth)
        assert len(calls) == total
        assert state["correction_round"] == limit
        assert calls[-1] == "synthesizer"
        assert state["audit_result"].summary == (f"audit_{limit}" if limit else "auditor")
        assert calls.count("skeptic") == (depth != "quick")
    asyncio.run(run())


def test_corrections_stop_when_audit_accepts():
    async def run():
        calls = []
        async def invoke(role, label):
            calls.append(label or role)
            return Findings(summary=role, needs_correction=role == "auditor" and label is None)
        state = await run_role_graph(invoke, "deep")
        assert state["correction_round"] == 1
        assert len(calls) == 8
        assert "correction_2" not in calls
    asyncio.run(run())


def test_external_cancellation_stops_both_branches():
    async def run():
        started, cancelled = set(), set()
        ready = asyncio.Event()
        async def invoke(role, label):
            started.add(role)
            if len(started) == 2:
                ready.set()
            try:
                await asyncio.Event().wait()
            except asyncio.CancelledError:
                cancelled.add(role)
                raise
        task = asyncio.create_task(run_role_graph(invoke, "quick"))
        await asyncio.wait_for(ready.wait(), 2)
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
        assert cancelled == {"company", "quant"}
    asyncio.run(run())


def test_compiled_graph_exposes_real_role_nodes():
    async def invoke(role, label):
        return Findings(summary=role)
    graph = build_research_graph(invoke, "standard")
    assert {"lead", "company", "quant", "skeptic", "auditor", "correction", "synthesizer"} <= set(graph.get_graph().nodes)
    assert graph.checkpointer is None


def test_invalid_depth_rejected_before_invocation():
    async def invoke(role, label):
        raise AssertionError("Must not execute")
    with pytest.raises(ValueError, match="depth"):
        build_research_graph(invoke, "unbounded")
