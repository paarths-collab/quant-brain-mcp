"""Regressions for issues found in the code review (no network access).

Each test pins one previously broken behavior: silent timeframe fallback,
chart weights keyed by raw input, crashes on negative Sharpe or a missing
benchmark, fabricated pipeline confidence, fake backtest results on short
history, missing VaR read as 0%, undefined max-Sharpe in down markets, and
late research configuration errors.
"""

from unittest.mock import patch

import numpy as np
import pandas as pd
import pytest

from core.data_loader import VALID_PERIODS, period_covering


def _ohlc(seed=1, periods=300, drift=0.0006, vol=0.01, start="2023-01-02"):
    idx = pd.bdate_range(start, periods=periods)
    rng = np.random.default_rng(seed)
    close = pd.Series(100 * np.exp(np.cumsum(rng.normal(drift, vol, periods))), index=idx)
    return pd.DataFrame(
        {"Open": close, "High": close * 1.01, "Low": close * 0.99, "Close": close, "Volume": 1_000_000.0}
    )


# ----------------------------- sector timeframes -----------------------------


@pytest.mark.parametrize("period", sorted(VALID_PERIODS))
def test_canonical_periods_are_not_replaced(period):
    from tools.strategies.sector_pipeline import _normalize_timeframe

    assert _normalize_timeframe(period) == period


@pytest.mark.parametrize("alias,expected", [("6m", "6mo"), ("12m", "1y"), ("120m", "10y")])
def test_aliases_map_to_valid_periods(alias, expected):
    from tools.strategies.sector_pipeline import _TIMEFRAME_ALIASES, _normalize_timeframe

    assert _normalize_timeframe(alias) == expected
    assert set(_TIMEFRAME_ALIASES.values()) <= VALID_PERIODS


@pytest.mark.parametrize("bad", ["2m", "3y", "36m", "forever"])
def test_unsupported_timeframe_is_rejected_not_defaulted(bad):
    from tools.strategies.sector_pipeline import _normalize_timeframe

    with pytest.raises(ValueError, match="Unsupported timeframe"):
        _normalize_timeframe(bad)


# ----------------------------- benchmark window -----------------------------


def test_period_covering_matches_history_span():
    today = pd.Timestamp.today().normalize()
    assert period_covering(pd.bdate_range(end=today, periods=60)) == "3mo"
    assert period_covering(pd.bdate_range(end=today, periods=100)) == "6mo"
    assert period_covering(pd.bdate_range(end=today, periods=1200)) == "5y"
    assert period_covering(pd.bdate_range(end=today, periods=2400)) == "10y"
    assert period_covering(pd.DatetimeIndex([])) == "2y"


def test_benchmark_fetched_over_asset_window():
    from tools.intelligence.engine import get_quant_analysis

    asset = _ohlc(1, periods=1200, start=pd.Timestamp.today() - pd.offsets.BDay(1200))
    seen = []

    def fake_fetch(ticker, period="2y", interval="1d"):
        seen.append(period)
        return asset, None

    with patch("tools.intelligence.engine.fetch_data", side_effect=fake_fetch):
        get_quant_analysis(asset, "^GSPC")
    assert seen == ["5y"]


def test_quant_and_alpha_betas_agree():
    from tools.intelligence.alpha_engine import calculate_alpha_metrics
    from tools.intelligence.engine import get_quant_analysis

    asset, bench = _ohlc(1, vol=0.02), _ohlc(2)
    quant = get_quant_analysis(asset, "^GSPC", benchmark_df=bench)
    alpha = calculate_alpha_metrics(asset, "^GSPC", bench_df=bench)
    assert quant["beta"] == alpha["beta"]


# ----------------------------- verdict risk + optimizers -----------------------------


def test_missing_var_is_unknown_not_zero():
    from main import _compute_portfolio_intelligence, _infer_benchmark_ticker, _to_float_pct

    assert _to_float_pct("n/a") is None
    frames = {"AAPL": _ohlc(1), "MSFT": _ohlc(2)}
    with patch("tools.intelligence.engine.fetch_data", return_value=(_ohlc(9), None)), patch(
        "tools.intelligence.alpha_engine.fetch_data", return_value=(_ohlc(9), None)
    ), patch("tools.intelligence.engine.np.percentile", return_value=float("nan")):
        _, blended = _compute_portfolio_intelligence({"AAPL": 0.5, "MSFT": 0.5}, frames, _infer_benchmark_ticker)
    assert blended is not None
    assert blended["one_day_var_95_pct"] is None


def test_benchmark_downloaded_once_per_window():
    from main import _compute_portfolio_intelligence, _infer_benchmark_ticker

    frames = {"AAPL": _ohlc(1), "MSFT": _ohlc(2), "NVDA": _ohlc(3)}
    calls = []

    def fake_fetch(ticker, period="2y", interval="1d"):
        calls.append(ticker)
        return _ohlc(9), None

    with patch("core.data_loader.fetch_data", side_effect=fake_fetch):
        _, blended = _compute_portfolio_intelligence(
            {"AAPL": 0.4, "MSFT": 0.3, "NVDA": 0.3}, frames, _infer_benchmark_ticker, benchmark_cache={}
        )
    assert calls == ["^GSPC"]
    assert blended["tickers_used"] == ["AAPL", "MSFT", "NVDA"]


def test_max_sharpe_falls_back_when_every_asset_declines():
    from tools.optimization.mean_variance import run_mvo_basic

    mu = pd.Series({"A": -0.10, "B": -0.05})
    cov = pd.DataFrame([[0.04, 0.01], [0.01, 0.03]], index=["A", "B"], columns=["A", "B"])
    result = run_mvo_basic(mu, cov, target="max_sharpe")
    assert result["target_used"] == "min_volatility"
    assert result["fallback_note"]
    assert sum(result["weights"].values()) == pytest.approx(1.0, abs=1e-3)


def test_default_verdict_survives_bear_training_window():
    from main import run_generate_optimized_verdict

    frames = {"A": _ohlc(1, drift=-0.003), "B": _ohlc(2, drift=-0.004)}

    def resolve(ticker, **kwargs):
        return frames[ticker][["Close"]].copy(), None, ticker

    with patch("core.data_loader.resolve_ticker", side_effect=resolve), patch(
        "main._compute_portfolio_intelligence", return_value=([], None)
    ):
        result = run_generate_optimized_verdict(["A", "B"], 10000, "mvo")
    assert "error" not in result, result
    assert result["optimization_note"]
    assert result["risk_assessment"]["one_day_var_95_pct"] is None


def test_black_litterman_uses_equilibrium_prior():
    from tools.optimization.black_litterman import optimize

    prices = pd.DataFrame({"A": _ohlc(1)["Close"], "B": _ohlc(2)["Close"]})
    result = optimize(prices)
    assert result["prior"] == "equal_weight_equilibrium"
    assert result["view_mode"] == "historical_mean_returns"
    assert result["view_count"] == 2


# ----------------------------- chart pack -----------------------------


def test_chart_prices_keyed_by_resolved_symbol():
    from tools.intelligence.plotly_dashboard import _prepare_price_frame

    def resolve(ticker, period="2y", interval="1d"):
        symbol = ticker.strip().upper()
        resolved = symbol if symbol.endswith(".NS") or symbol == "AAPL" else symbol + ".NS"
        return _ohlc(len(resolved)), None, resolved

    with patch("tools.intelligence.plotly_dashboard.resolve_ticker", side_effect=resolve):
        price_df, ohlc, _, fetched = _prepare_price_frame(["aapl", "RELIANCE", "reliance.ns"])
    assert list(price_df.columns) == ["AAPL", "RELIANCE.NS"]
    assert set(ohlc) == {"AAPL", "RELIANCE.NS"}
    assert fetched["RELIANCE"][2] == "RELIANCE.NS"


def test_invalid_chart_timeframe_is_clean_error():
    from tools.intelligence.plotly_dashboard import build_chart_pack

    assert "Invalid timeframe" in build_chart_pack(["AAPL"], timeframe="3y")["error"]


# ----------------------------- sector pipeline -----------------------------


def _fake_sector_fetch(fail_benchmark):
    def fetch(ticker, period="1y", interval="1d"):
        if fail_benchmark and ticker in {"^NSEI", "^GSPC"}:
            return None, "benchmark down"
        return _ohlc(abs(hash(ticker)) % 1000, periods=260), None

    return fetch


def test_pipeline_survives_benchmark_failure():
    from tools.strategies import sector_pipeline as sp

    with patch.object(sp, "fetch_data", side_effect=_fake_sector_fetch(True)):
        result = sp.find_sector_stock_pipeline("india", 1, 1)
    assert result["selected_stocks"]
    stock_traces = [row for row in result["data_trace"] if row["stage"] == "stock"]
    assert stock_traces and all(row["status"] == "partial" for row in stock_traces)
    assert result["verdict"] == "NEUTRAL"


def test_pipeline_reports_no_fabricated_confidence():
    from tools.strategies import sector_pipeline as sp

    with patch.object(sp, "fetch_data", side_effect=_fake_sector_fetch(False)):
        result = sp.find_sector_stock_pipeline("us", 2, 2)
    assert result["confidence"] is None
    assert result["reproducibility"]["sector_window"] == "1y"
    expected = "ACCUMULATE" if result["confirmed_stocks"] else "NEUTRAL"
    assert result["verdict"] == expected
    for stock in result["selected_stocks"]:
        assert stock["confirmed"] == (not stock["unmet_confirmations"])


def test_pipeline_rejects_bad_counts():
    from tools.strategies.sector_pipeline import find_sector_stock_pipeline

    with pytest.raises(ValueError, match="top_n_sectors"):
        find_sector_stock_pipeline("us", top_n_sectors=-1)


def test_confirmation_requires_every_check():
    from tools.strategies.sector_pipeline import _confirmation

    good = {"breakout": True, "regime": "TRENDING", "alpha_annualized": 0.08, "sharpe_ratio": 1.4, "var_95": "-1.80%"}
    assert _confirmation(good) == (True, [])
    confirmed, unmet = _confirmation({**good, "var_95": "-4.10%"})
    assert not confirmed and len(unmet) == 1


# ----------------------------- strategy backtests -----------------------------


@pytest.mark.parametrize(
    "module,runner,kwargs",
    [
        ("tools.strategies.sma_crossover_bt", "run_backtest", {}),
        ("tools.strategies.trend_crossover", "run_strategy", {}),
        ("tools.strategies.macd_trend_follower", "run_backtest", {}),
        ("tools.strategies.volatility_breakout", "run_backtest", {"length": 60}),
    ],
)
def test_short_history_is_an_error_not_a_zero_trade_result(module, runner, kwargs):
    import importlib

    fn = getattr(importlib.import_module(module), runner)
    result = fn(_ohlc(1, periods=30), **kwargs)
    assert "Insufficient history" in result["error"]


def test_no_trades_formats_as_null_not_nan_string():
    from tools.strategies.rsi_mean_reversion import run_backtest

    flat_uptrend = _ohlc(1, periods=300, drift=0.004, vol=0.0005)
    from utils.serializer import serialize_output

    result = serialize_output(run_backtest(flat_uptrend, lower=1, upper=99))
    assert result["win_rate"] is None
    assert "nan" not in str(result).lower()


def test_crossover_parameters_validated():
    from tools.strategies.sma_crossover_bt import run_backtest

    assert "shorter than slow" in run_backtest(_ohlc(), fast=200, slow=50)["error"]
    with pytest.raises(ValueError):
        run_backtest(_ohlc(), fast=0, slow=50)


def test_strategy_names_are_distinct():
    from tools.strategies import macd_trend_follower, trend_crossover

    df = _ohlc(1, periods=400)
    assert macd_trend_follower.run_backtest(df)["strategy_name"] == "MACD Trend Follower"
    assert trend_crossover.run_strategy(df)["strategy_name"] == "Trend Crossover"


def test_single_strategy_rejects_unknown_indicator():
    from tools.backtesting.single_strategy_bt import run_single_backtest

    with pytest.raises(ValueError, match="Unsupported indicator_type"):
        run_single_backtest(_ohlc(), indicator_type="macd")


# ----------------------------- trade plan -----------------------------


def test_stop_basis_reports_min_distance_floor():
    from tools.trading.trade_plan import compute_trade_plan

    # Wide early bars keep ATR large; the last 10 bars are tight, so the swing
    # low sits inside 0.75 ATR and the floor must set the stop.
    idx = pd.bdate_range("2024-01-01", periods=60)
    df = pd.DataFrame({"Open": 100.0, "Close": 100.0, "High": 105.0, "Low": 95.0, "Volume": 1e6}, index=idx)
    df.iloc[-10:, df.columns.get_loc("High")] = 100.01
    df.iloc[-10:, df.columns.get_loc("Low")] = 99.99
    plan = compute_trade_plan(df, "AAPL", equity=100_000)
    assert plan["stop_basis"] == "min_distance"
    assert plan["stop_distance_atr"] == pytest.approx(0.75, abs=0.01)


# ----------------------------- alerts -----------------------------


def test_unpriced_alerts_are_reported(monkeypatch):
    from tools.trading import alerts

    rows = [{"id": 7, "ticker": "RELIANCE", "direction": "below", "level": 1000.0, "note": None}]
    monkeypatch.setattr(alerts, "_db_available", lambda: True)
    monkeypatch.setattr(alerts, "_fetch_alerts", lambda owner, active_only=True: rows)
    monkeypatch.setattr(
        alerts, "get_quotes", lambda tickers: {"quotes": {"RELIANCE": {"error": "No quote"}}, "as_of": "t"}
    )
    result = alerts.manage_alert("check", owner_id="alice")
    assert result["still_watching"] == 1
    assert result["unpriced"] == [{"alert_id": 7, "ticker": "RELIANCE", "reason": "No quote"}]
    assert "could not be priced" in result["warning"]


# ----------------------------- research configuration -----------------------------


def test_research_rejects_bad_runtime_config_before_queuing(tmp_path, monkeypatch):
    from core.research_service import ResearchService
    from core.research_store import ResearchStore

    monkeypatch.setenv("QUANT_INTERNAL_MCP_URL", "http://remote.example.com/mcp")
    service = ResearchService(store=ResearchStore(tmp_path / "research.sqlite3"))
    with pytest.raises(ValueError, match="misconfigured.*HTTPS"):
        service.start("alice", "Question", ["TCS.NS"])
    assert service.store.active_count() == 0
    service.close()
