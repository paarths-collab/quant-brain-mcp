# Evaluation and benchmark scorecard

Quant Brain separates three questions that are often incorrectly collapsed into
one score:

1. **Did the system run?** Measure latency, completion, tool failures, source
   retrieval failures, and cost.
2. **Is the report internally traceable?** Measure citations, verified-claim
   coverage, calculation methods, publication dates, and source retrieval.
3. **Is the conclusion correct?** Use fixed datasets and independent human or
   programmatic labels. A model reviewing itself is not ground truth.

Run the deterministic scorecard against an exported `ResearchReport`:

```bash
python scripts/evaluate_research_report.py report.json \
  --labels labels.json \
  --latency-ms 182000 \
  --estimated-cost-usd 0.00
```

The optional labels file is deliberately small and reviewable:

```json
{
  "expected_outcome": "mixed",
  "claim_support": {"company_c1": true, "quant_c2": false},
  "calculation_correctness": {"quant_c2": false}
}
```

## Metrics to publish

| Group | Metrics |
|---|---|
| Report integrity | citation coverage, verified-claim coverage, calculation-method coverage, publication-date coverage, source diversity |
| Evidence | retrieved-source coverage (retrieved ÷ all cited web sources), retrieval attempt success rate (retrieved ÷ attempted), failed-source citation rate, independently labelled claim-support accuracy |
| Data gaps | `risk_data_status` and `risk_unavailable_tool_calls`: observed tool calls whose result marked a risk metric `unavailable` |
| Quant accuracy | fixed arithmetic cases, calculation accuracy, unit correctness, benchmark alignment, look-ahead leakage checks |
| Reliability | job completion rate, tool-call success rate, cancellation success, timeout rate, malformed-output recovery |
| Performance | median and p95 job latency, role latency, MCP-call latency, model invocations, estimated cost per report |
| Decision quality | outcome match on adjudicated cases, abstention accuracy when evidence is insufficient, unsupported-claim rate |
| Historical strategies | out-of-sample return, Sharpe, Sortino, maximum drawdown, turnover and costs versus an explicit benchmark |

Coverage denominators include failures: a source that failed, was never attempted, or has no retrieval record still counts in the total, so 3 retrieved of 5 cited is 60%, not 100%. A ratio with an empty denominator is `null`, never 1.0. Every percentage must include its sample size. Publish results by dataset version,
model, reasoning level, market-data snapshot, code commit, and evaluation date.
Do not combine these into one opaque “AI accuracy” number.

## Initial benchmark set

Start with at least 30 frozen cases:

- 10 deterministic calculation cases with hand-checked answers and units.
- 5 stale, missing, conflicting, or delayed market-data cases.
- 5 filing/news cases with independently labelled claim-to-source support.
- 5 adversarial cases containing prompt injection or unsupported certainty.
- 5 failure cases covering provider errors, timeouts, cancellation and malformed
  agent output.

For strategy claims, use expanding-window or rolling walk-forward evaluation,
include delisted instruments where available, freeze the investable universe at
each historical date, model fees and slippage, and compare with a declared index
and simple equal-weight baseline. A single 70/30 holdout is a useful regression
test, not a sufficient public performance benchmark.
