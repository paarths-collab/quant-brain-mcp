"""A risk metric that could not be computed is `unavailable`, never 0, neutral or "low risk".

Before this, a failed risk calculation fell back to 0.0 in several places: the
optimized verdict reported a 0.00% VaR and LUMP_SUM_ACCEPTABLE when every
ticker's analysis failed, zero-variance inputs produced beta=0 / Sharpe=0, and
sector scoring turned a NaN into an exactly-average z-score.
"""
import asyncio
import json
from unittest.mock import patch

import numpy as np
import pandas as pd
import pytest

from core.risk_state import count_unavailable, is_unavailable, unavailable
from main import _compute_portfolio_intelligence, _infer_benchmark_ticker, _to_float_pct, run_generate_optimized_verdict
from tools.intelligence import alpha_engine, engine


def ohlc(seed=1, periods=300, vol=0.01, drift=0.0005, flat=False):
    idx = pd.date_range("2023-01-02", periods=periods, freq="B")
    rng = np.random.default_rng(seed)
    close = pd.Series(100.0 if flat else 100 * np.exp(np.cumsum(rng.normal(drift, vol, periods))), index=idx)
    if flat:
        close = pd.Series(100.0, index=idx)
    return pd.DataFrame({"Open": close, "High": close * 1.01, "Low": close * 0.99, "Close": close, "Volume": 1_000_000})


class _Both:
    """Patch the benchmark fetch in both engines, which bind their own `fetch_data`."""

    def __init__(self, result):
        self.patches = [patch("tools.intelligence.engine.fetch_data", return_value=result),
                        patch("tools.intelligence.alpha_engine.fetch_data", return_value=result)]

    def __enter__(self):
        for p in self.patches:
            p.start()

    def __exit__(self, *exc):
        for p in self.patches:
            p.stop()


# --- the marker itself --------------------------------------------------------------

def test_unavailable_marker_is_explicit_and_stays_a_failure_for_error_consumers():
    marker = unavailable("benchmark missing")
    assert marker["status"] == "unavailable" and marker["reason"] == "benchmark missing"
    assert marker["error"] == "benchmark missing"      # existing `"error" in payload` checks still fire
    assert is_unavailable(marker) and not is_unavailable({"beta": 1.0})
    assert count_unavailable({"a": [marker, {"b": marker}], "c": {"risk_status": "partial"}}) == 3
    assert count_unavailable({"risk_status": "available", "beta": 1.0}) == 0


# --- calculation sources -------------------------------------------------------------

def test_zero_variance_benchmark_gives_unavailable_beta_not_zero():
    flat_benchmark = ohlc(flat=True)
    with _Both((flat_benchmark, None)):
        quant = engine.get_quant_analysis(ohlc(1))
        alpha = alpha_engine.calculate_alpha_metrics(ohlc(1))
    assert quant["beta"] is None and quant["risk_status"] == "partial"
    assert "beta" in quant["unavailable_metrics"] and "variance" in quant["unavailable_metrics"]["beta"]
    # beta=0 used to report the stock's whole annualized return as alpha, with a verdict derived from it.
    assert is_unavailable(alpha) and "alpha_annualized" not in alpha and "verdict" not in alpha
    assert "no return variance" in alpha["reason"]


def test_flat_asset_gets_unavailable_sharpe_and_no_reduce_signal():
    with _Both((ohlc(9), None)):
        quant = engine.get_quant_analysis(ohlc(flat=True))
    assert quant["sharpe_ratio"] is None
    assert quant["institutional_verdict"] == "UNAVAILABLE"      # a placeholder 0.0 used to fall through to REDUCE
    assert "sharpe_ratio" in quant["unavailable_metrics"]
    with _Both((ohlc(9), None)):
        assert engine.get_quant_context(ohlc(flat=True))["consensus_score"] == "Sharpe unavailable"


def test_healthy_inputs_report_available_with_no_gaps():
    with _Both((ohlc(9), None)):
        quant = engine.get_quant_analysis(ohlc(1))
        alpha = alpha_engine.calculate_alpha_metrics(ohlc(1))
    assert quant["risk_status"] == "available" and quant["unavailable_metrics"] == {}
    assert isinstance(quant["beta"], float) and isinstance(quant["sharpe_ratio"], float)
    assert not is_unavailable(alpha) and alpha["verdict"] in {"ALPHA_GENERATOR", "BETA_TRACKER"}


def test_benchmark_fetch_failure_is_unavailable_with_the_reason():
    with _Both((None, "No data found for ticker '^NSEI'")):
        alpha = alpha_engine.calculate_alpha_metrics(ohlc(1))
    assert alpha["status"] == "unavailable" and "^NSEI" in alpha["reason"]


def test_unparseable_var_is_unknown_not_zero():
    assert _to_float_pct("-2.50%") == -2.5
    assert _to_float_pct("bad") is None and _to_float_pct(None) is None and _to_float_pct("nan") is None
    assert _to_float_pct("bad", default=1.0) == 1.0          # an explicit default is still honoured


# --- portfolio blend --------------------------------------------------------------------

def test_failed_ticker_stays_in_the_coverage_denominator_with_its_reason():
    frames = {"AAPL": ohlc(1), "BAD": pd.DataFrame()}
    with _Both((ohlc(9), None)):
        per_ticker, blended = _compute_portfolio_intelligence({"AAPL": 0.6, "BAD": 0.4}, frames, _infer_benchmark_ticker)
    bad = next(e for e in per_ticker if e["ticker"] == "BAD")
    assert bad["risk_status"] == "unavailable" and bad["reason"]
    assert blended["risk_status"] == "partial"
    assert blended["coverage_weight"] == 0.6                    # 0.6 / (0.6 + 0.4), not 1.0
    assert blended["tickers_unavailable"] == [{"ticker": "BAD", "weight": 0.4, "reason": bad["reason"]}]


def test_held_ticker_without_price_history_is_reported_not_skipped():
    with _Both((ohlc(9), None)):
        per_ticker, blended = _compute_portfolio_intelligence({"AAPL": 0.5, "GONE": 0.5}, {"AAPL": ohlc(1)}, _infer_benchmark_ticker)
    gone = next(e for e in per_ticker if e["ticker"] == "GONE")
    assert gone["risk_status"] == "unavailable" and "No price history" in gone["reason"]
    assert blended["coverage_weight"] == 0.5


def test_unreadable_var_excludes_the_ticker_instead_of_blending_a_zero():
    healthy = {"AAPL": ohlc(1), "MSFT": ohlc(2)}
    real = engine.get_quant_analysis

    def broken_for_msft(df, benchmark_ticker="^NSEI"):
        result = real(df, benchmark_ticker=benchmark_ticker)
        if df is healthy["MSFT"]:
            result = {**result, "one_day_var_95": "n/a"}
        return result

    with _Both((ohlc(9), None)), patch("tools.intelligence.engine.get_quant_analysis", side_effect=broken_for_msft):
        per_ticker, blended = _compute_portfolio_intelligence({"AAPL": 0.5, "MSFT": 0.5}, healthy, _infer_benchmark_ticker)
    aapl = next(e for e in per_ticker if e["ticker"] == "AAPL")
    expected = _to_float_pct(aapl["quant_analysis"]["one_day_var_95"])
    assert blended["one_day_var_95_pct"] == pytest.approx(expected, abs=0.01)   # a 0 for MSFT would halve it
    assert blended["tickers_used"] == ["AAPL"]
    assert next(e for e in per_ticker if e["ticker"] == "MSFT")["risk_status"] == "unavailable"


def test_all_tickers_unavailable_gives_no_blend_and_marks_every_entry():
    with _Both((pd.DataFrame(), None)):
        per_ticker, blended = _compute_portfolio_intelligence(
            {"A": 0.5, "B": 0.5}, {"A": pd.DataFrame(), "B": pd.DataFrame()}, _infer_benchmark_ticker)
    assert blended is None
    assert [e["risk_status"] for e in per_ticker] == ["unavailable", "unavailable"]
    assert all("_var_pct" not in e for e in per_ticker)


# --- the optimized verdict (report) --------------------------------------------------------

def price_frame(n=300):
    rng = np.random.default_rng(12)
    return pd.DataFrame(100 * np.exp(np.cumsum(rng.normal(.001, .01, (n, 2)), axis=0)),
                        columns=["A", "B"], index=pd.bdate_range("2020-01-01", periods=n))


def representative_entries(*tickers):
    return [{"ticker": t, "weight": .5, "benchmark": "^GSPC", "risk_status": "available",
             "quant_analysis": {}, "alpha_analysis": {}} for t in tickers]


def verdict_with(intel):
    frame = price_frame()

    def resolve(ticker, **kwargs):
        return pd.DataFrame({"Close": frame[ticker]}), None, ticker

    with patch("core.data_loader.resolve_ticker", side_effect=resolve), \
         patch("main._compute_portfolio_intelligence", return_value=intel):
        return run_generate_optimized_verdict(["A", "B"], 10000, "mvo")


def test_verdict_with_no_risk_data_says_unavailable_everywhere_it_used_to_say_zero():
    entries = [{"ticker": t, "weight": .5, "benchmark": "^GSPC", "risk_status": "unavailable",
                "reason": "Benchmark data unavailable for ^GSPC: timeout",
                "quant_analysis": unavailable("x"), "alpha_analysis": unavailable("x")} for t in ("A", "B")]
    result = verdict_with((entries, None))
    assert "error" not in result
    risk = result["risk_assessment"]
    assert risk["status"] == "unavailable" and result["risk_status"] == "unavailable"
    assert "Benchmark data unavailable for ^GSPC: timeout" in risk["reason"]
    assert risk["one_day_var_95_pct"] is None and risk["one_day_var_95_amount"] is None
    assert risk["capital_plan"] == "UNAVAILABLE"            # was LUMP_SUM_ACCEPTABLE
    assert risk["risk_flags"] is None                       # [] would read as "no flags raised"
    assert risk["coverage_weight"] == 0.0
    assert result["factor_exposure"] == "UNAVAILABLE"       # was SYSTEMATIC_BETA
    assert "0.00" not in result["reasoning"].replace("Sharpe 0.00", "")
    assert "UNAVAILABLE" in result["reasoning"] and "not evidence of low risk" in result["reasoning"]
    json.dumps(result)                                       # still plain JSON


def test_verdict_with_partial_risk_data_is_labelled_partial_with_the_gap():
    blended = {"tickers_used": ["A"], "coverage_weight": .6, "alpha_annualized": .02, "beta": 1.0, "r_squared": .5,
               "one_day_var_95_pct": -2.0, "dominant_regime": "TRENDING", "risk_status": "partial",
               "tickers_unavailable": [{"ticker": "B", "weight": .4, "reason": "short history"}]}
    result = verdict_with((representative_entries("A"), blended))
    risk = result["risk_assessment"]
    assert risk["status"] == "partial" and risk["coverage_weight"] == .6
    assert "60%" in risk["reason"] and "B: short history" in risk["reason"]
    assert risk["one_day_var_95_pct"] == "-2.00%" and risk["capital_plan"] == "LUMP_SUM_ACCEPTABLE"
    assert "PARTIAL" in result["reasoning"]


def test_verdict_with_full_risk_data_is_unchanged_in_substance():
    blended = {"tickers_used": ["A", "B"], "coverage_weight": 1.0, "alpha_annualized": .08, "beta": 1.6, "r_squared": .95,
               "one_day_var_95_pct": -3.5, "dominant_regime": "TRENDING", "risk_status": "available",
               "tickers_unavailable": []}
    result = verdict_with((representative_entries("A", "B"), blended))
    risk = result["risk_assessment"]
    assert risk["status"] == "available" and risk["reason"] is None
    assert risk["one_day_var_95_pct"] == "-3.50%" and risk["one_day_var_95_amount"] == 350.0
    assert len(risk["risk_flags"]) == 3
    assert result["factor_exposure"] == "IDIOSYNCRATIC_ALPHA"
    assert result["data_coverage"] == {"requested": 2, "included": 2, "excluded": 0, "coverage": 1.0}


def test_excluded_tickers_lower_data_coverage():
    frame = price_frame()

    def resolve(ticker, **kwargs):
        if ticker == "GHOST":
            return None, "No data found", ticker
        return pd.DataFrame({"Close": frame[ticker]}), None, ticker

    with patch("core.data_loader.resolve_ticker", side_effect=resolve), \
         patch("main._compute_portfolio_intelligence", return_value=([], None)):
        result = run_generate_optimized_verdict(["A", "B", "GHOST"], 10000, "mvo")
    assert result["data_coverage"] == {"requested": 3, "included": 2, "excluded": 1, "coverage": round(2 / 3, 4)}


# --- sector scoring -----------------------------------------------------------------------------

def sector_universe(n):
    return {f"S{i}": {"index": f"^IDX{i}", "tickers": []} for i in range(n)}


def sector_frame(seed, flat=False, periods=120):
    return ohlc(seed, periods=periods, flat=flat)


def run_sectors(frames):
    from tools.strategies.sector_pipeline import analyze_sector_intelligence

    def fetch(ticker, **kwargs):
        value = frames[ticker]
        return (None, value) if isinstance(value, str) else (value, None)

    with patch("tools.strategies.sector_pipeline.fetch_data", side_effect=fetch), \
         patch("tools.strategies.sector_pipeline._pick_universe", return_value=sector_universe(len(frames))):
        return analyze_sector_intelligence("india", "1y")


def test_sector_with_zero_volatility_is_unranked_instead_of_scored_with_0_percent_risk():
    result = run_sectors({"^IDX0": sector_frame(1), "^IDX1": sector_frame(2), "^IDX2": sector_frame(3, flat=True)})
    ranked = [row["sector"] for row in result["sector_analytics"]]
    assert ranked and "S2" not in ranked
    [flat] = result["unranked_sectors"]
    assert flat["sector"] == "S2" and flat["risk_status"] == "unavailable" and "variance" in flat["reason"]
    assert "risk_volatility_pct" not in flat      # previously published as a measured 0.0
    assert all(row["risk_status"] == "available" and "composite_score" in row for row in result["sector_analytics"])
    assert any(t["sector"] == "S2" and t["status"] == "risk_unavailable" for t in result["data_trace"])


def test_two_of_five_sector_feeds_failing_cuts_coverage_and_confidence():
    frames = {f"^IDX{i}": (sector_frame(i) if i < 3 else "No data found") for i in range(5)}
    result = run_sectors(frames)
    assert result["coverage"] == {"attempted": 5, "ranked": 3, "failed": 2, "risk_unavailable": 0, "coverage": 0.6}
    assert result["confidence"] == pytest.approx(round(min(0.95, 0.55 + 3 * 0.04) * 0.6, 2), abs=0.01)


def test_full_sector_coverage_leaves_confidence_formula_unchanged():
    result = run_sectors({f"^IDX{i}": sector_frame(i) for i in range(4)})
    assert result["coverage"]["coverage"] == 1.0
    assert result["confidence"] == round(min(0.95, 0.55 + 4 * 0.04), 2)


def test_stock_whose_risk_cannot_be_computed_is_not_selected_as_confirmed():
    from tools.strategies import sector_pipeline

    universe = {"S0": {"index": "^IDX0", "tickers": ["GOOD.NS", "NOBENCH.NS", "NODATA.NS"]}}

    def fetch(ticker, **kwargs):
        if ticker == "NODATA.NS":
            return None, "No data found"
        return ohlc(abs(hash(ticker)) % 1000, periods=120), None

    real_quant = engine.get_quant_analysis

    def quant(df, benchmark_ticker="^NSEI"):
        if quant.calls == 1:                       # second stock: benchmark outage
            quant.calls += 1
            raise ValueError("Benchmark data unavailable for ^NSEI: timeout")
        quant.calls += 1
        return real_quant(df, benchmark_ticker=benchmark_ticker)
    quant.calls = 0

    with patch.object(sector_pipeline, "fetch_data", side_effect=fetch), \
         patch.object(sector_pipeline, "_pick_universe", return_value=universe), \
         patch.object(sector_pipeline, "get_quant_analysis", side_effect=quant), \
         patch.object(sector_pipeline, "calculate_alpha_metrics", return_value=unavailable("unused")) as alpha, \
         patch("tools.intelligence.engine.fetch_data", return_value=(ohlc(9), None)):
        alpha.side_effect = lambda df, benchmark_ticker: alpha_engine.calculate_alpha_metrics(df, benchmark_ticker=benchmark_ticker)
        with patch("tools.intelligence.alpha_engine.fetch_data", return_value=(ohlc(9), None)):
            result = sector_pipeline.find_sector_stock_pipeline("india", top_n_sectors=1, top_n_stocks=3)

    selected = {c["ticker"] for c in result["selected_stocks"]}
    unconfirmed = {c["ticker"]: c for c in result["unconfirmed_stocks"]}
    assert selected == {"GOOD.NS"}
    assert unconfirmed["NOBENCH.NS"]["risk_status"] == "unavailable" and "timeout" in unconfirmed["NOBENCH.NS"]["reason"]
    assert unconfirmed["NOBENCH.NS"]["beta"] is None and unconfirmed["NOBENCH.NS"]["sharpe_ratio"] is None
    stocks = result["coverage"]["stocks"]
    assert stocks["attempted"] == 3 and stocks["confirmed"] == 1 and stocks["failed"] == 1 and stocks["risk_unavailable"] == 1
    assert stocks["coverage"] == round(1 / 3, 4)
    assert result["verdict"] == "ACCUMULATE"


def test_pipeline_is_neutral_when_no_stock_can_be_risk_confirmed():
    from tools.strategies import sector_pipeline

    universe = {"S0": {"index": "^IDX0", "tickers": ["A.NS"]}}
    with patch.object(sector_pipeline, "fetch_data", side_effect=lambda t, **kw: (ohlc(3, periods=120), None)), \
         patch.object(sector_pipeline, "_pick_universe", return_value=universe), \
         patch.object(sector_pipeline, "get_quant_analysis", side_effect=ValueError("benchmark down")), \
         patch.object(sector_pipeline, "calculate_alpha_metrics", return_value=unavailable("benchmark down")):
        result = sector_pipeline.find_sector_stock_pipeline("india", top_n_sectors=1, top_n_stocks=1)
    assert result["selected_stocks"] == [] and result["verdict"] == "NEUTRAL"
    assert result["unconfirmed_stocks"][0]["reason"] == "benchmark down"


# --- carried into the research report and the auditor --------------------------------------------------

def test_runtime_trace_flags_unavailable_risk_without_storing_payload_text():
    from types import SimpleNamespace
    from core.research_runtime import _execution_events

    def call(payload, text=None):
        content = [SimpleNamespace(text=json.dumps(text if text is not None else payload))]
        return SimpleNamespace(root=SimpleNamespace(
            type="mcpToolCall", server="quant_internal", tool="get_quote",
            status=SimpleNamespace(value="completed"), error=None,
            result=SimpleNamespace(structured_content=payload, content=content)))

    nested = {"risk_assessment": {"status": "unavailable", "reason": "SECRET timeout", "error": "SECRET timeout"}}
    clean = {"price": 1.0}
    events = _execution_events(SimpleNamespace(items=[call(nested), call(clean)]))
    assert events[0]["has_error"] is True and events[0]["risk_unavailable"] == 1   # same payload twice, counted once
    assert "risk_unavailable" not in events[1] and events[1]["has_error"] is False
    assert "SECRET" not in json.dumps(events)

    partial = _execution_events(SimpleNamespace(items=[call({"risk_status": "partial", "beta": None})]))
    assert partial[0]["risk_unavailable"] == 1 and partial[0]["has_error"] is True


class RiskGapRuntime:
    """Fake model whose tool trace reports unavailable risk metrics."""

    def __init__(self, events, confidence="high"):
        from tests.research_fakes import ScriptedRuntime
        self.inner = ScriptedRuntime()
        self.executions = [{"role": "quant", "tool_events": events}]
        self.prompts = {}
        self.confidence = confidence

    async def run(self, role, prompt):
        self.prompts[role] = prompt
        result = await self.inner.run(role, prompt)
        if role in ("auditor", "synthesizer"):
            result["confidence"] = self.confidence
        return result


def mcp_event(**extra):
    return {"type": "mcpToolCall", "server": "quant_internal", "tool": "get_quote", "status": "completed",
            "has_error": False, **extra}


def run_report(runtime):
    from core.research_workflow import run_research
    return asyncio.run(run_research("Investigate", ["TCS.NS"], "quick", runtime=runtime))


def test_unavailable_risk_downgrades_the_report_and_reaches_the_auditor():
    runtime = RiskGapRuntime([mcp_event(risk_unavailable=2, has_error=True), mcp_event()])
    report = run_report(runtime)
    assert report.risk_data_status == "gaps_observed" and report.risk_unavailable_calls == 1
    assert report.confidence == "low" and report.outcome == "mixed"
    assert any("unavailable in 1 of 2 observed MCP calls" in w and "not zero" in w for w in report.warnings)
    assert report.summary.startswith("Partial research")
    for role in ("auditor", "synthesizer"):
        assert "SERVER DATA GAPS" in runtime.prompts[role]
        assert '"tool_calls_with_unavailable_risk": 1' in runtime.prompts[role]
    assert "SERVER DATA GAPS" not in runtime.prompts["company"]
    assert "never zero, neutral or low risk" in runtime.prompts["quant"]


def test_gap_signal_alone_downgrades_even_if_the_error_flag_was_lost():
    report = run_report(RiskGapRuntime([mcp_event(risk_unavailable=1)]))
    assert report.execution_status == "observed_calls_passed"      # transport/payload looked fine
    assert report.risk_data_status == "gaps_observed" and report.outcome == "mixed" and report.confidence == "low"


@pytest.mark.parametrize("events,status", [([mcp_event()], "no_gaps_observed"), ([], "not_observed")])
def test_report_does_not_claim_gaps_that_were_not_observed(events, status):
    runtime = RiskGapRuntime(events, confidence="moderate")
    report = run_report(runtime)
    assert report.risk_data_status == status and report.risk_unavailable_calls == 0
    assert not any("Risk metrics were unavailable" in w for w in report.warnings)
    assert report.outcome == "supported"
    # The unfetched example.com source is a real gap and is shown; risk gaps are shown as zero, not invented.
    assert '"tool_calls_with_unavailable_risk": 0' in runtime.prompts["auditor"]


def test_evaluation_scorecard_exposes_risk_gaps():
    from core.research_evaluation import evaluate_report
    report = run_report(RiskGapRuntime([mcp_event(risk_unavailable=1, has_error=True)]))
    automatic = evaluate_report(report)["automatic"]
    assert automatic["risk_data_status"] == "gaps_observed" and automatic["risk_unavailable_tool_calls"] == 1
    assert automatic["tool_call_success_rate"] == 0.0
