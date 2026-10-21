"""Deterministic metrics for persisted research reports.

These metrics evaluate report integrity and independently supplied labels. They
do not ask a model to grade another model and do not estimate future returns.
"""
from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from core.research_evidence import source_coverage
from core.research_workflow import ResearchReport


class BenchmarkLabels(BaseModel):
    """Optional human or programmatically adjudicated ground truth."""

    model_config = ConfigDict(extra="forbid")
    expected_outcome: str | None = None
    claim_support: dict[str, bool] = Field(default_factory=dict)
    calculation_correctness: dict[str, bool] = Field(default_factory=dict)


def _ratio(numerator: int, denominator: int) -> float | None:
    return round(numerator / denominator, 4) if denominator else None


def evaluate_report(
    report: ResearchReport | Mapping[str, Any],
    *,
    labels: BenchmarkLabels | Mapping[str, Any] | None = None,
    latency_ms: float | None = None,
    estimated_cost_usd: float | None = None,
) -> dict[str, Any]:
    """Return a JSON-safe scorecard for one completed research report.

    A missing denominator is reported as ``None`` instead of a perfect zero or
    one. Label-based metrics cover only IDs present in ``labels`` and publish
    the sample size beside every score.
    """
    parsed = report if isinstance(report, ResearchReport) else ResearchReport.model_validate(report)
    judged = labels if isinstance(labels, BenchmarkLabels) else BenchmarkLabels.model_validate(labels or {})

    claims = parsed.claims
    evidence = {item.id: item for item in parsed.evidence}
    cited_ids = {evidence_id for claim in claims for evidence_id in claim.evidence_ids}
    cited = [evidence[evidence_id] for evidence_id in cited_ids if evidence_id in evidence]
    web_evidence = [item for item in cited if str(item.url).startswith(("http://", "https://"))]
    calculations = [claim for claim in claims if claim.kind == "calculation"]
    verified = set(parsed.verified_claim_ids)

    # Cited web sources with no retrieval record (never fetched) stay in the
    # denominator rather than being dropped from it.
    retrieval = source_coverage(web_evidence, parsed.source_retrievals)

    tool_events = [
        event
        for execution in parsed.execution_trace
        for event in execution.get("tool_events", [])
        if event.get("type") == "mcpToolCall"
    ]
    successful_tools = sum(
        event.get("status") == "completed" and not event.get("has_error")
        for event in tool_events
    )

    support_labels = {
        claim.id: judged.claim_support[claim.id]
        for claim in claims
        if claim.id in judged.claim_support
    }
    calculation_labels = {
        claim.id: judged.calculation_correctness[claim.id]
        for claim in calculations
        if claim.id in judged.calculation_correctness
    }

    automatic = {
        "final_claim_count": len(claims),
        "evidence_count": len(parsed.evidence),
        "source_domain_count": len({getattr(item.url, "host", None) for item in web_evidence}),
        "citation_coverage": _ratio(sum(bool(claim.evidence_ids) for claim in claims), len(claims)),
        "verified_claim_coverage": _ratio(sum(claim.id in verified for claim in claims), len(claims)),
        "calculation_method_coverage": _ratio(sum(bool(claim.method) for claim in calculations), len(calculations)),
        "publication_date_coverage": _ratio(sum(item.published_at is not None for item in web_evidence), len(web_evidence)),
        "retrieved_source_coverage": retrieval["coverage"],
        "retrieval_attempt_success_rate": retrieval["attempt_success_rate"],
        "cited_web_source_count": retrieval["total"],
        "risk_data_status": parsed.risk_data_status,
        "risk_unavailable_tool_calls": parsed.risk_unavailable_calls,
        "tool_call_success_rate": _ratio(successful_tools, len(tool_events)),
        "failed_source_citation_rate": _ratio(
            sum(
                parsed.source_retrievals.get(item.id, {}).get("status") == "failed"
                for item in web_evidence
            ),
            len(web_evidence),
        ),
        "invocation_count": parsed.invocation_count,
        "execution_status": parsed.execution_status,
        "outcome": parsed.outcome,
        "confidence": parsed.confidence,
    }
    adjudicated = {
        "claim_support_accuracy": _ratio(sum(support_labels.values()), len(support_labels)),
        "claim_support_sample_size": len(support_labels),
        "calculation_accuracy": _ratio(sum(calculation_labels.values()), len(calculation_labels)),
        "calculation_sample_size": len(calculation_labels),
        "outcome_match": None if judged.expected_outcome is None else parsed.outcome == judged.expected_outcome,
    }
    operations = {
        "latency_ms": None if latency_ms is None else round(float(latency_ms), 2),
        "estimated_cost_usd": None if estimated_cost_usd is None else round(float(estimated_cost_usd), 6),
    }
    return {
        "metric_version": "1.1",
        "automatic": automatic,
        "adjudicated": adjudicated,
        "operations": operations,
        "limitations": [
            "Automatic metrics measure report structure and observed execution, not whether prose is financially correct.",
            "Adjudicated accuracy covers only explicitly labelled claim IDs.",
            "Historical evaluation is not evidence of future investment performance.",
        ],
    }
