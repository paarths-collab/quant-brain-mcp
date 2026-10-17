from datetime import datetime, timezone

from core.research_evaluation import evaluate_report
from core.research_workflow import Claim, Evidence, Findings, ResearchReport


def report():
    now = datetime.now(timezone.utc)
    web = Evidence(id="e1", url="https://example.com/filing", title="Filing", published_at=now,
                   retrieved_at=now, source_type="filing", excerpt="Revenue was 100")
    tool = Evidence(id="e2", url="urn:tool:quant_internal:analyze_statistics", title="Statistics",
                    retrieved_at=now, source_type="market_data", excerpt="Return was 5%")
    fact = Claim(id="c1", text="Revenue was 100", evidence_ids=["e1"], kind="fact")
    calculation = Claim(id="c2", text="Return was 5%", evidence_ids=["e2"],
                        kind="calculation", method="(end/start)-1")
    finding = Findings(summary="done", evidence=[web, tool], claims=[fact, calculation])
    return ResearchReport(
        question="Evaluate", tickers=["TEST.NS"], created_at=now, depth="quick",
        summary="done", outcome="supported", confidence="moderate",
        claims=[fact, calculation], evidence=[web, tool], verified_claim_ids=["c1"],
        assumptions=[], warnings=[], disagreements=[], agent_findings={"company": finding},
        invocation_count=4, source_retrievals={"e1": {"status": "retrieved"}},
        execution_trace=[{"role": "quant", "tool_events": [
            {"type": "mcpToolCall", "status": "completed", "has_error": False},
            {"type": "mcpToolCall", "status": "failed", "has_error": True},
            {"type": "webSearch"},
        ]}], execution_status="partial_failure",
    )


def test_automatic_metrics_have_explicit_denominators():
    result = evaluate_report(report(), latency_ms=1234.567, estimated_cost_usd=.01234567)
    metrics = result["automatic"]
    assert metrics["citation_coverage"] == 1.0
    assert metrics["verified_claim_coverage"] == .5
    assert metrics["calculation_method_coverage"] == 1.0
    assert metrics["publication_date_coverage"] == 1.0
    assert metrics["retrieved_source_coverage"] == 1.0
    assert metrics["tool_call_success_rate"] == .5
    assert result["operations"] == {"latency_ms": 1234.57, "estimated_cost_usd": .012346}


def test_independent_labels_score_only_annotated_claims():
    result = evaluate_report(report(), labels={
        "expected_outcome": "mixed",
        "claim_support": {"c1": True, "unknown": False},
        "calculation_correctness": {"c2": False},
    })
    judged = result["adjudicated"]
    assert judged["claim_support_accuracy"] == 1.0
    assert judged["claim_support_sample_size"] == 1
    assert judged["calculation_accuracy"] == 0.0
    assert judged["calculation_sample_size"] == 1
    assert judged["outcome_match"] is False


def test_empty_categories_are_unknown_not_fake_perfect_scores():
    parsed = report().model_copy(update={
        "claims": [], "evidence": [], "verified_claim_ids": [],
        "source_retrievals": {}, "execution_trace": [], "agent_findings": {},
    })
    result = evaluate_report(parsed)
    assert result["automatic"]["citation_coverage"] is None
    assert result["automatic"]["tool_call_success_rate"] is None
    assert result["adjudicated"]["claim_support_accuracy"] is None
