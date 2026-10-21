"""Coverage is successful / attempted-or-required, with failed and missing sources in the denominator."""
import asyncio
from datetime import datetime, timezone
from types import SimpleNamespace

import pytest

from core.research_evaluation import evaluate_report
from core.research_evidence import source_coverage
from core.research_workflow import Claim, Evidence, Findings, ResearchReport, run_research
from tests.research_fakes import ScriptedRuntime

NOW = datetime(2026, 1, 1, tzinfo=timezone.utc)


def web(i, source_type="filing"):
    return SimpleNamespace(id=f"e{i}", url=f"https://example.com/{i}", source_type=source_type)


def tool_evidence():
    return SimpleNamespace(id="t1", url="urn:tool:quant_internal:get_quote", source_type="market_data")


def records(*statuses):
    return {f"e{i}": {"status": status} for i, status in enumerate(statuses)}


# --- the function --------------------------------------------------------------------------

def test_two_of_five_sources_failing():
    result = source_coverage([web(i) for i in range(5)], records("retrieved", "retrieved", "retrieved", "failed", "failed"))
    assert result == {"total": 5, "attempted": 5, "retrieved": 3, "failed": 2, "not_attempted": 0,
                      "coverage": 0.6, "attempt_success_rate": 0.6}


def test_never_attempted_sources_stay_in_the_denominator():
    # 1 failed, 1 blocked by the allowlist/limit: attempted = 4, but coverage is still over all 5.
    result = source_coverage([web(i) for i in range(5)], records("retrieved", "retrieved", "retrieved", "failed", "not_attempted"))
    assert result["coverage"] == 0.6 and result["attempt_success_rate"] == 0.75
    assert (result["attempted"], result["failed"], result["not_attempted"]) == (4, 1, 1)


def test_a_source_with_no_retrieval_record_counts_as_not_attempted():
    result = source_coverage([web(i) for i in range(5)], records("retrieved", "retrieved", "retrieved"))
    assert result["total"] == 5 and result["not_attempted"] == 2 and result["coverage"] == 0.6


def test_empty_denominators_are_none_not_a_perfect_score():
    assert source_coverage([], {})["coverage"] is None
    assert source_coverage([tool_evidence()], {})["total"] == 0          # tool URNs are not retrievable documents
    only_blocked = source_coverage([web(0)], records("not_attempted"))
    assert only_blocked["coverage"] == 0.0 and only_blocked["attempt_success_rate"] is None


# --- the report ----------------------------------------------------------------------------------

class FiveSources(ScriptedRuntime):
    async def run(self, role, prompt):
        result = await super().run(role, prompt)
        evidence = [{"id": f"company_e{i}", "url": f"https://example.com/{i}", "title": f"Source {i}",
                     "retrieved_at": "2026-01-01T10:00:00Z", "published_at": "2026-01-01T09:00:00Z",
                     "source_type": "company", "excerpt": f"Fact {i}"} for i in range(1, 6)]
        claims = [{"id": f"company_c{i}", "text": f"Fact {i}", "evidence_ids": [f"company_e{i}"], "kind": "fact"}
                  for i in range(1, 6)]
        if role == "company":
            result.update(evidence=evidence, claims=claims)
        if role == "auditor":
            result.update(verified_claim_ids=[c["id"] for c in claims])
        if role == "synthesizer":
            result.update(claims=claims, evidence=[])
        self.last_prompt = prompt
        return result


def retrievals(statuses):
    async def retrieve(evidence, cache):
        return {e.id: {"status": statuses[e.id], "reason": "Source HTTP 403"} for e in evidence
                if e.source_type in ("filing", "company", "official")}
    return retrieve


def test_two_of_five_sources_failing_is_reported_and_reaches_the_auditor(monkeypatch):
    import core.research_workflow as workflow
    statuses = {f"company_e{i}": s for i, s in enumerate(["retrieved"] * 3 + ["failed"] * 2, start=1)}
    monkeypatch.setattr(workflow, "retrieve_sources", retrievals(statuses))
    runtime = FiveSources()
    report = asyncio.run(run_research("Investigate", ["TCS.NS"], "quick", runtime=runtime))

    assert report.source_coverage == {"total": 5, "attempted": 5, "retrieved": 3, "failed": 2, "not_attempted": 0,
                                      "coverage": 0.6, "attempt_success_rate": 0.6}
    assert any("3 of 5 cited web sources retrieved (60%); 2 failed, 0 not attempted" in w for w in report.warnings)
    assert report.confidence == "low" and report.outcome == "mixed"        # cited sources failed retrieval
    assert '"coverage": 0.6' in runtime.last_prompt and '"collected_web_source_coverage"' in runtime.last_prompt


def test_full_coverage_adds_no_coverage_warning(monkeypatch):
    import core.research_workflow as workflow
    statuses = {f"company_e{i}": "retrieved" for i in range(1, 6)}
    monkeypatch.setattr(workflow, "retrieve_sources", retrievals(statuses))
    report = asyncio.run(run_research("Investigate", ["TCS.NS"], "quick", runtime=FiveSources()))
    assert report.source_coverage["coverage"] == 1.0
    assert not any("Source coverage" in w for w in report.warnings)


# --- the scorecard -------------------------------------------------------------------------------

def scorecard_report(n_sources, retrieval_statuses):
    evidence = [Evidence(id=f"e{i}", url=f"https://example.com/{i}", title="Source", published_at=NOW, retrieved_at=NOW,
                         source_type="filing", excerpt="x") for i in range(n_sources)]
    claims = [Claim(id=f"c{i}", text="x", evidence_ids=[f"e{i}"], kind="fact") for i in range(n_sources)]
    return ResearchReport(
        question="q", tickers=["TCS.NS"], created_at=NOW, depth="quick", summary="s", outcome="mixed",
        confidence="low", claims=claims, evidence=evidence, verified_claim_ids=[c.id for c in claims],
        assumptions=[], warnings=[], disagreements=[], invocation_count=4,
        agent_findings={"company": Findings(summary="s", evidence=evidence, claims=claims)},
        source_retrievals={f"e{i}": {"status": s} for i, s in enumerate(retrieval_statuses)})


def test_scorecard_two_of_five_failing():
    automatic = evaluate_report(scorecard_report(5, ["retrieved"] * 3 + ["failed"] * 2))["automatic"]
    assert automatic["retrieved_source_coverage"] == 0.6
    assert automatic["retrieval_attempt_success_rate"] == 0.6
    assert automatic["failed_source_citation_rate"] == 0.4
    assert automatic["cited_web_source_count"] == 5


def test_scorecard_counts_cited_sources_that_were_never_retrieved():
    # Only the 3 sources that were fetched have records. Dividing by records (3/3) said 100%.
    automatic = evaluate_report(scorecard_report(5, ["retrieved"] * 3))["automatic"]
    assert automatic["retrieved_source_coverage"] == 0.6
    assert automatic["retrieval_attempt_success_rate"] == 1.0              # of those attempted, all worked
    assert automatic["cited_web_source_count"] == 5


def test_scorecard_without_web_sources_is_unknown():
    automatic = evaluate_report(scorecard_report(0, []))["automatic"]
    assert automatic["retrieved_source_coverage"] is None and automatic["retrieval_attempt_success_rate"] is None
    assert automatic["cited_web_source_count"] == 0
