import asyncio

import pytest

from core.research_workflow import run_research

EVIDENCE = {"id": "company_e1", "url": "https://example.com/results", "title": "Results", "retrieved_at": "2026-01-01T10:00:00Z", "source_type": "company", "excerpt": "Revenue increased"}
CLAIM = {"id": "company_c1", "text": "Revenue increased", "evidence_ids": ["company_e1"], "kind": "fact"}


class FakeRuntime:
    def __init__(self, corrections=0):
        self.roles = []
        self.corrections = corrections
        self.started = set()
        self.both = asyncio.Event()

    async def run(self, role, prompt):
        self.roles.append(role)
        result = {"summary": role}
        if role in ("company", "quant"):
            self.started.add(role)
            if len(self.started) == 2:
                self.both.set()
            await asyncio.wait_for(self.both.wait(), 1)
        if role == "company":
            result.update(evidence=[EVIDENCE], claims=[CLAIM])
        if role == "auditor":
            result.update(verified_claim_ids=["company_c1"], outcome="supported", needs_correction=self.corrections > 0)
            self.corrections -= 1
        if role == "synthesizer":
            result.update(claims=[CLAIM], outcome="supported", confidence="moderate")
        return result


def test_parallel_research_and_audited_report():
    async def run():
        runtime = FakeRuntime()
        events = []
        async def event(role, payload):
            events.append((role, payload["status"]))
        report = await run_research("Research this company", ["RELIANCE.NS"], runtime=runtime, on_event=event)
        assert report.outcome == "supported"
        assert report.verified_claim_ids == ["company_c1"]
        assert report.invocation_count == 6
        assert runtime.roles == ["lead", "company", "quant", "skeptic", "auditor", "synthesizer"]
        assert len(events) == 12
    asyncio.run(run())


@pytest.mark.parametrize("depth,calls", [("quick", 4), ("standard", 8), ("deep", 10)])
def test_corrections_bounded(depth, calls):
    async def run():
        report = await run_research("Investigate", depth=depth, runtime=FakeRuntime(corrections=20))
        assert report.invocation_count == calls
        assert report.outcome == "insufficient_evidence"
        assert report.confidence == "low"
    asyncio.run(run())


def test_unknown_citation_rejected():
    class Invalid(FakeRuntime):
        async def run(self, role, prompt):
            result = await super().run(role, prompt)
            if role == "synthesizer":
                result["claims"] = [{**CLAIM, "id": "new_claim", "evidence_ids": ["made_up"]}]
            return result
    with pytest.raises(ValueError, match="Unknown evidence"):
        asyncio.run(run_research("Investigate", runtime=Invalid()))


def test_synthesis_cannot_add_unaudited_claim():
    class Invalid(FakeRuntime):
        async def run(self, role, prompt):
            result = await super().run(role, prompt)
            if role == "synthesizer":
                result["claims"] = [{**CLAIM, "id": "new_claim"}]
            return result
    with pytest.raises(ValueError, match="unaudited"):
        asyncio.run(run_research("Investigate", runtime=Invalid()))


def test_runtime_failure_cancels_parallel_worker():
    class Broken:
        cancelled = False
        async def run(self, role, prompt):
            if role == "company":
                await asyncio.sleep(0)
                raise RuntimeError("provider unavailable")
            if role == "quant":
                try:
                    await asyncio.sleep(20)
                except asyncio.CancelledError:
                    self.cancelled = True
                    raise
            return {"summary": role}
    async def run():
        runtime = Broken()
        with pytest.raises(RuntimeError, match="unavailable"):
            await run_research("Investigate", runtime=runtime)
        assert runtime.cancelled
    asyncio.run(run())


def test_auditor_cannot_verify_unknown_claim():
    class Invalid(FakeRuntime):
        async def run(self, role, prompt):
            result = await super().run(role, prompt)
            if role == "auditor":
                result["verified_claim_ids"] = ["nonexistent"]
            return result
    with pytest.raises(ValueError, match="unknown prior"):
        asyncio.run(run_research("Investigate", runtime=Invalid()))


def test_auditor_cannot_upgrade_insufficient_synthesis():
    class Insufficient(FakeRuntime):
        async def run(self, role, prompt):
            result = await super().run(role, prompt)
            if role == "auditor":
                result.update(outcome="mixed", confidence="high")
            if role == "synthesizer":
                result.update(outcome="insufficient_evidence", confidence="high")
            return result
    report = asyncio.run(run_research("Investigate", runtime=Insufficient()))
    assert report.outcome == "insufficient_evidence"
    assert report.confidence == "low"


def test_report_discloses_model_review_provenance():
    report = asyncio.run(run_research("Investigate", runtime=FakeRuntime()))
    assert report.verification_basis == "model_review"
    assert any("not been independently attested" in warning for warning in report.warnings)


def test_correction_prompt_has_distinct_call_namespace():
    class Capture(FakeRuntime):
        prompts = []
        async def run(self, role, prompt):
            self.prompts.append(prompt)
            return await super().run(role, prompt)
    runtime = Capture(corrections=1)
    asyncio.run(run_research("Investigate", runtime=runtime))
    assert any("CALL ID: company." in prompt for prompt in runtime.prompts)
    assert any("CALL ID: quant." in prompt for prompt in runtime.prompts)
    assert any("CALL ID: correction_1." in prompt for prompt in runtime.prompts)


def test_conflicting_parallel_claim_ids_fail_closed():
    class Collision(FakeRuntime):
        async def run(self, role, prompt):
            result = await super().run(role, prompt)
            if role == "quant":
                result.update(evidence=[EVIDENCE], claims=[{**CLAIM, "text": "Revenue declined"}])
            return result
    with pytest.raises(ValueError, match="Conflicting claim ID"):
        asyncio.run(run_research("Investigate", runtime=Collision()))


def test_analyst_self_checks_do_not_replace_auditor():
    class SelfChecked(FakeRuntime):
        async def run(self, role, prompt):
            result = await super().run(role, prompt)
            if role == "company":
                result["verified_claim_ids"] = [CLAIM["id"]]
            if role == "auditor":
                result["verified_claim_ids"] = []
            return result
    report = asyncio.run(run_research("Investigate", runtime=SelfChecked()))
    assert report.verified_claim_ids == []
    assert report.outcome == "insufficient_evidence"


def test_allowlisted_tool_evidence_is_preserved_without_fake_web_url():
    from core.research_workflow import Evidence
    tool_uri = "urn:tool:quant_internal:get_quote"
    evidence = Evidence.model_validate({**EVIDENCE, "url": tool_uri, "source_type": "market_data"})
    assert evidence.model_dump(mode="json")["url"] == tool_uri


@pytest.mark.parametrize("url", [
    "urn:tool:quant_internal:start_research",
    "urn:tool:quant_internal:execute_trade",
    "urn:tool:other:get_quote",
    "file:///etc/passwd",
    "javascript:alert(1)",
])
def test_tool_evidence_rejects_unknown_tools_and_unsafe_urls(url):
    from core.research_workflow import Evidence
    with pytest.raises(ValueError):
        Evidence.model_validate({**EVIDENCE, "url": url})


def test_report_preserves_runtime_owned_execution_trace():
    runtime = FakeRuntime()
    runtime.executions = [{"role": "quant", "tool_events": [
        {"type": "mcpToolCall", "server": "quant_internal", "tool": "get_quote", "status": "completed", "has_error": False},
        {"type": "webSearch"},
    ]}]
    report = asyncio.run(run_research("Investigate", runtime=runtime))
    assert report.execution_trace == runtime.executions
    assert report.verification_basis == "model_review"


def test_report_trace_defaults_empty_without_runtime_metadata():
    report = asyncio.run(run_research("Investigate", runtime=FakeRuntime()))
    assert report.execution_trace == []


def test_model_cannot_supply_execution_trace():
    class Fabricated(FakeRuntime):
        async def run(self, role, prompt):
            result = await super().run(role, prompt)
            if role == "company":
                result["execution_trace"] = [{"role": "company", "tool_events": [{"type": "webSearch"}]}]
            return result
    with pytest.raises(ValueError, match="execution_trace"):
        asyncio.run(run_research("Investigate", runtime=Fabricated()))
