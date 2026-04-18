from __future__ import annotations

import json
from typing import Any

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import vectorbt as vbt
import yfinance as yf

from core.data_loader import fetch_data
from core.sector_data import INDIAN_SECTORS, US_SECTORS
from main import run_generate_optimized_verdict
from tools.intelligence.alpha_engine import calculate_alpha_metrics
from tools.intelligence.engine import get_quant_analysis
from tools.strategies.sector_pipeline import find_sector_stock_pipeline


def _to_pct_number(value: Any) -> float | None:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    text = str(value).replace("%", "").strip()
    try:
        return float(text)
    except Exception:
        return None


def _to_plotly_json(fig: go.Figure) -> dict[str, Any]:
    # Round-trip via JSON to guarantee each chart payload is fully detached.
    return json.loads(json.dumps(fig.to_plotly_json(), default=str))


_DEFAULT_CHART_ORDER = [
    "allocation_weights",
    "portfolio_equity_curve",
    "portfolio_drawdown_curve",
    "risk_return_scatter",
    "optimization_comparison_bars",
    "var_es_distribution",
    "rolling_sharpe",
    "asset_correlation_heatmap",
    "allocation_difference_heatmap",
    "strategy_vs_buyhold_equity",
    "trade_overlay",
    "strategy_diagnostics",
    "rolling_beta",
    "rolling_hurst_exponent",
    "regime_timeline",
    "alpha_decomposition_waterfall",
    "fundamental_revenue_ebitda_eps",
    "margin_roe_trend",
    "debt_interest_coverage_trend",
    "valuation_multiples_vs_sector",
    "sector_relative_strength",
    "sector_stock_funnel",
    "confidence_data_trace_panel",
]


_CHART_CATEGORIES = {
    "allocation_weights": "portfolio",
    "portfolio_equity_curve": "portfolio",
    "portfolio_drawdown_curve": "portfolio",
    "rolling_sharpe": "portfolio",
    "var_es_distribution": "portfolio",
    "monthly_returns_heatmap": "portfolio",
    "rolling_max_drawdown": "portfolio",
    "optimization_comparison_bars": "optimization",
    "risk_return_scatter": "optimization",
    "allocation_difference_heatmap": "optimization",
    "asset_correlation_heatmap": "optimization",
    "strategy_diagnostics": "strategy",
    "strategy_vs_buyhold_equity": "strategy",
    "trade_overlay": "strategy",
    "rolling_beta": "quant",
    "alpha_decomposition_waterfall": "quant",
    "rolling_hurst_exponent": "quant",
    "regime_timeline": "quant",
    "fundamental_revenue_ebitda_eps": "fundamentals",
    "margin_roe_trend": "fundamentals",
    "debt_interest_coverage_trend": "fundamentals",
    "valuation_multiples_vs_sector": "fundamentals",
    "sector_relative_strength": "sector_pipeline",
    "sector_stock_funnel": "sector_pipeline",
    "confidence_data_trace_panel": "sector_pipeline",
}


def _prepare_price_frame(tickers: list[str], period: str = "2y") -> tuple[pd.DataFrame, dict[str, pd.DataFrame], list[str]]:
    close_map: dict[str, pd.Series] = {}
    ohlc_map: dict[str, pd.DataFrame] = {}
    warnings: list[str] = []

    for ticker in tickers:
        df, err = fetch_data(ticker, period=period)
        if err or df is None or df.empty:
            warnings.append(f"Failed to fetch data for {ticker}: {err}")
            continue

        clean_df = df.copy()
        clean_df.index = pd.to_datetime(clean_df.index).tz_localize(None)
        if "Close" not in clean_df.columns:
            warnings.append(f"Ticker {ticker} missing Close column")
            continue

        ohlc_map[ticker] = clean_df
        close_map[ticker] = clean_df["Close"].astype(float)

    if not close_map:
        return pd.DataFrame(), {}, warnings

    price_df = pd.DataFrame(close_map).ffill().dropna()
    return price_df, ohlc_map, warnings


def _build_portfolio(price_df: pd.DataFrame, weights: dict[str, float]) -> vbt.Portfolio:
    w = pd.Series(weights, dtype=float).reindex(price_df.columns).fillna(0.0)
    orders = pd.DataFrame(np.nan, index=price_df.index, columns=price_df.columns)
    orders.iloc[0] = w
    return vbt.Portfolio.from_orders(
        price_df,
        size=orders,
        size_type="target_percent",
        group_by=True,
        cash_sharing=True,
        freq="1D",
    )


def _rolling_hurst(close: pd.Series, window: int = 120) -> pd.Series:
    values: list[float] = []
    idx: list[pd.Timestamp] = []

    for i in range(window, len(close)):
        sub = close.iloc[i - window : i]
        if sub.isna().any():
            continue
        lags = range(2, 20)
        tau = []
        for lag in lags:
            diff = sub.diff(lag).dropna()
            if diff.empty:
                continue
            std = float(np.std(diff))
            if std > 0:
                tau.append(np.sqrt(std))
        if len(tau) < 5:
            continue
        hurst = float(2.0 * np.polyfit(np.log(list(range(2, 2 + len(tau)))), np.log(tau), 1)[0])
        values.append(hurst)
        idx.append(close.index[i])

    if not values:
        return pd.Series(dtype=float)
    return pd.Series(values, index=idx)


def _safe_strategy_metrics(stock_df: pd.DataFrame) -> dict[str, dict[str, Any]]:
    metrics: dict[str, dict[str, Any]] = {}

    runners = [
        ("MACD Momentum", "tools.strategies.macd_momentum", "run_strategy", {}),
        ("MACD Trend Follower", "tools.strategies.macd_trend_follower", "run_backtest", {"fast": 12, "slow": 26, "signal": 9}),
        ("RSI-BB Mean Reversion", "tools.strategies.mean_reversion_rsi_bb", "run_strategy", {"rsi_lower": 30, "rsi_upper": 70}),
        ("RSI Mean Reversion", "tools.strategies.rsi_mean_reversion", "run_backtest", {"length": 14, "lower": 30, "upper": 70}),
        ("SMA Crossover", "tools.strategies.sma_crossover_bt", "run_backtest", {"fast": 50, "slow": 200}),
        ("Trend Crossover", "tools.strategies.trend_crossover", "run_strategy", {"fast": 50, "slow": 200}),
        ("Volatility Breakout", "tools.strategies.volatility_breakout", "run_backtest", {"length": 20}),
    ]

    for label, module_path, fn_name, kwargs in runners:
        try:
            module = __import__(module_path, fromlist=[fn_name])
            fn = getattr(module, fn_name)
            metrics[label] = fn(stock_df, **kwargs)
        except Exception as exc:
            metrics[label] = {"error": str(exc)}

    return metrics


def _build_fundamental_series(ticker: str) -> dict[str, Any]:
    data: dict[str, Any] = {
        "years": [],
        "revenue": [],
        "ebitda": [],
        "eps": [],
        "net_margin": [],
        "debt": [],
        "interest_coverage": [],
        "roe": [],
        "multiples": {},
        "sector_medians": {},
    }

    t = yf.Ticker(ticker)
    info = t.info or {}
    income = t.financials if isinstance(t.financials, pd.DataFrame) else pd.DataFrame()
    balance = t.balance_sheet if isinstance(t.balance_sheet, pd.DataFrame) else pd.DataFrame()

    years = []
    if not income.empty:
        years = [str(c.year) if hasattr(c, "year") else str(c) for c in income.columns[:5]][::-1]
        columns = list(income.columns[:5])[::-1]

        def _row(df: pd.DataFrame, names: list[str]) -> list[float | None]:
            for name in names:
                if name in df.index:
                    vals = []
                    for c in columns:
                        v = df.loc[name, c]
                        vals.append(None if pd.isna(v) else float(v))
                    return vals
            return [None for _ in columns]

        revenue = _row(income, ["Total Revenue", "Operating Revenue"])
        ebitda = _row(income, ["EBITDA", "Ebitda"])
        net_income = _row(income, ["Net Income", "Net Income Common Stockholders"])
        eps = _row(income, ["Diluted EPS", "Basic EPS"])

        net_margin = []
        for ni, rev in zip(net_income, revenue):
            if ni is None or rev in (None, 0):
                net_margin.append(None)
            else:
                net_margin.append((ni / rev) * 100)

        data.update(
            {
                "years": years,
                "revenue": revenue,
                "ebitda": ebitda,
                "eps": eps,
                "net_margin": net_margin,
            }
        )

    if years and not balance.empty:
        cols = list(balance.columns[: len(years)])[::-1]
        debt = None
        for row_name in ["Total Debt", "Long Term Debt", "Total Liabilities Net Minority Interest"]:
            if row_name in balance.index:
                debt = [None if pd.isna(balance.loc[row_name, c]) else float(balance.loc[row_name, c]) for c in cols]
                break
        if debt is not None:
            data["debt"] = debt

    interest_cov: list[float | None] = []
    if not income.empty and years:
        cols = list(income.columns[: len(years)])[::-1]
        if "EBIT" in income.index and "Interest Expense" in income.index:
            for c in cols:
                ebit = income.loc["EBIT", c]
                interest = income.loc["Interest Expense", c]
                if pd.isna(ebit) or pd.isna(interest) or float(interest) == 0:
                    interest_cov.append(None)
                else:
                    interest_cov.append(abs(float(ebit) / float(interest)))
    data["interest_coverage"] = interest_cov if interest_cov else [None for _ in years]

    roe_value = info.get("returnOnEquity")
    if years:
        data["roe"] = [None if roe_value is None else float(roe_value) * 100 for _ in years]

    data["multiples"] = {
        "PE": info.get("trailingPE"),
        "PB": info.get("priceToBook"),
        "EV_EBITDA": info.get("enterpriseToEbitda"),
    }

    all_sector_maps = [INDIAN_SECTORS, US_SECTORS]
    peers: list[str] = []
    target = ticker.upper()
    for sector_map in all_sector_maps:
        for _, cfg in sector_map.items():
            tickers = cfg.get("tickers", [])
            if target in [str(t).upper() for t in tickers]:
                peers = [str(t) for t in tickers if str(t).upper() != target]
                break
        if peers:
            break

    peer_vals = {"PE": [], "PB": [], "EV_EBITDA": []}
    for p in peers[:4]:
        try:
            p_info = yf.Ticker(p).info or {}
            for key, src in [("PE", "trailingPE"), ("PB", "priceToBook"), ("EV_EBITDA", "enterpriseToEbitda")]:
                val = p_info.get(src)
                if val is not None:
                    peer_vals[key].append(float(val))
        except Exception:
            continue

    data["sector_medians"] = {k: (float(np.median(v)) if v else None) for k, v in peer_vals.items()}
    return data


def build_chart_pack(
    tickers: list[str],
    amount: float = 10000,
    market: str = "us",
    company_ticker: str | None = None,
    timeframe: str = "2y",
) -> dict[str, Any]:
    """Build a full institutional chart pack for dashboard rendering."""
    if not tickers:
        return {"error": "tickers is required"}

    charts: dict[str, dict[str, Any]] = {}
    warnings: list[str] = []

    methods = [
        "mvo",
        "hrp",
        "max_sharpe",
        "min_volatility",
        "black_litterman",
        "cvar",
        "semivariance",
    ]

    selected_timeframe = (timeframe or "2y").strip()

    price_df, ohlc_map, prep_warnings = _prepare_price_frame(tickers, period=selected_timeframe)
    warnings.extend(prep_warnings)
    if price_df.empty:
        return {"error": "Unable to build chart pack: no valid price data", "warnings": warnings}

    method_rows: list[dict[str, Any]] = []
    method_weights: dict[str, dict[str, float]] = {}

    asset_returns = price_df.pct_change(fill_method=None).dropna()
    cov_ann = asset_returns.cov() * 252 if not asset_returns.empty else pd.DataFrame()

    for method in methods:
        try:
            result = run_generate_optimized_verdict(tickers=tickers, amount=amount, optimize_type=method)
            if "error" in result:
                warnings.append(f"Optimization {method} failed: {result['error']}")
                continue

            bt = result.get("backtest_metrics", {})
            risk = result.get("risk_assessment", {})
            weights = result.get("recommended_weights", {})
            method_weights[method] = {k: float(v) for k, v in weights.items()}

            total_ret = _to_pct_number(bt.get("portfolio_total_return"))
            sharpe = bt.get("portfolio_sharpe")
            drawdown = _to_pct_number(bt.get("portfolio_drawdown"))
            var95 = _to_pct_number(risk.get("one_day_var_95_pct"))

            vol = None
            if not cov_ann.empty and weights:
                w = pd.Series(weights, dtype=float).reindex(cov_ann.columns).fillna(0.0).values
                vol = float(np.sqrt(np.dot(w.T, np.dot(cov_ann.values, w))) * 100)

            method_rows.append(
                {
                    "method": method.upper(),
                    "total_return_pct": total_ret,
                    "sharpe": float(sharpe) if sharpe is not None else None,
                    "max_drawdown_pct": drawdown,
                    "var_95_pct": var95,
                    "volatility_pct": vol,
                }
            )
        except Exception as exc:
            warnings.append(f"Optimization {method} exception: {exc}")

    if method_rows:
        compare_df = pd.DataFrame(method_rows)

        fig_compare = go.Figure()
        for col, label in [
            ("total_return_pct", "Total Return %"),
            ("sharpe", "Sharpe"),
            ("max_drawdown_pct", "Max Drawdown %"),
            ("var_95_pct", "VaR 95%"),
        ]:
            fig_compare.add_trace(go.Bar(name=label, x=compare_df["method"], y=compare_df[col]))
        fig_compare.update_layout(title="Optimization Method Comparison", barmode="group")
        charts["optimization_comparison_bars"] = _to_plotly_json(fig_compare)

        fig_scatter = px.scatter(
            compare_df,
            x="volatility_pct",
            y="total_return_pct",
            color="method",
            size="sharpe",
            hover_data=["max_drawdown_pct", "var_95_pct"],
            title="Risk-Return Scatter by Optimization Method",
        )
        charts["risk_return_scatter"] = _to_plotly_json(fig_scatter)

    selected_method = "mvo" if "mvo" in method_weights else (next(iter(method_weights)) if method_weights else None)
    if selected_method:
        selected_weights = method_weights[selected_method]

        fig_weights = px.bar(
            x=list(selected_weights.keys()),
            y=list(selected_weights.values()),
            title=f"Allocation Weights ({selected_method.upper()})",
            labels={"x": "Ticker", "y": "Weight"},
        )
        charts["allocation_weights"] = _to_plotly_json(fig_weights)

        pf = _build_portfolio(price_df, selected_weights)
        equity = pf.value()
        drawdown = (equity / equity.cummax() - 1.0) * 100
        returns = pf.returns().dropna()
        roll_window = 63
        rolling_sharpe = (returns.rolling(roll_window).mean() / returns.rolling(roll_window).std()) * np.sqrt(252)

        fig_equity = go.Figure()
        fig_equity.add_trace(go.Scatter(x=equity.index, y=equity.values, mode="lines", name="Portfolio"))
        charts["portfolio_equity_curve"] = _to_plotly_json(fig_equity)

        fig_drawdown = go.Figure()
        fig_drawdown.add_trace(go.Scatter(x=drawdown.index, y=drawdown.values, mode="lines", fill="tozeroy", name="Drawdown %"))
        fig_drawdown.update_layout(title="Portfolio Drawdown Curve")
        charts["portfolio_drawdown_curve"] = _to_plotly_json(fig_drawdown)

        fig_rsharpe = go.Figure()
        fig_rsharpe.add_trace(go.Scatter(x=rolling_sharpe.index, y=rolling_sharpe.values, mode="lines", name="Rolling Sharpe (63d)"))
        fig_rsharpe.update_layout(title="Rolling Sharpe")
        charts["rolling_sharpe"] = _to_plotly_json(fig_rsharpe)

        var95 = float(np.percentile(returns.values, 5)) if not returns.empty else None
        es95 = float(returns[returns <= var95].mean()) if var95 is not None and not returns.empty else None
        fig_dist = go.Figure()
        fig_dist.add_trace(go.Histogram(x=returns.values, nbinsx=70, name="Daily Returns"))
        if var95 is not None:
            fig_dist.add_vline(x=var95, line_dash="dash", annotation_text=f"VaR95 {var95:.2%}")
        if es95 is not None:
            fig_dist.add_vline(x=es95, line_dash="dot", annotation_text=f"ES95 {es95:.2%}")
        fig_dist.update_layout(title="Return Distribution with VaR / ES")
        charts["var_es_distribution"] = _to_plotly_json(fig_dist)

        monthly = returns.resample("ME").apply(lambda x: (1 + x).prod() - 1)
        if not monthly.empty:
            hm_df = pd.DataFrame({"date": monthly.index, "ret": monthly.values})
            hm_df["year"] = hm_df["date"].dt.year
            hm_df["month"] = hm_df["date"].dt.month_name().str.slice(stop=3)
            pivot = hm_df.pivot(index="year", columns="month", values="ret")
            month_order = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
            pivot = pivot.reindex(columns=[m for m in month_order if m in pivot.columns])
            fig_mh = px.imshow(pivot * 100, text_auto=".2f", title="Monthly Returns Heatmap (%)", aspect="auto")
            charts["monthly_returns_heatmap"] = _to_plotly_json(fig_mh)

        rolling_mdd = drawdown.rolling(63).min()
        fig_rmdd = go.Figure()
        fig_rmdd.add_trace(go.Scatter(x=rolling_mdd.index, y=rolling_mdd.values, mode="lines", name="Rolling Max Drawdown"))
        fig_rmdd.update_layout(title="Rolling Max Drawdown")
        charts["rolling_max_drawdown"] = _to_plotly_json(fig_rmdd)

    if method_weights:
        matrix = pd.DataFrame(method_weights).reindex(price_df.columns).fillna(0.0)
        fig_hm = px.imshow(
            matrix.values,
            x=[c.upper() for c in matrix.columns],
            y=matrix.index,
            text_auto=".2f",
            aspect="auto",
            title="Allocation Difference Heatmap",
            labels={"x": "Method", "y": "Ticker", "color": "Weight"},
        )
        charts["allocation_difference_heatmap"] = _to_plotly_json(fig_hm)

    if not asset_returns.empty:
        corr = asset_returns.corr()
        fig_corr = px.imshow(
            corr.values,
            x=corr.columns,
            y=corr.index,
            text_auto=".2f",
            aspect="auto",
            title="Asset Correlation Heatmap",
        )
        charts["asset_correlation_heatmap"] = _to_plotly_json(fig_corr)

    stock_ticker = tickers[0]
    stock_df = ohlc_map.get(stock_ticker)
    if stock_df is not None and not stock_df.empty:
        strategy_metrics = _safe_strategy_metrics(stock_df)

        sm_rows = []
        for name, out in strategy_metrics.items():
            if isinstance(out, dict) and "error" not in out:
                sm_rows.append(
                    {
                        "strategy": name,
                        "win_rate": _to_pct_number(out.get("win_rate")),
                        "profit_factor": out.get("profit_factor"),
                        "expectancy": out.get("expectancy"),
                    }
                )
            else:
                warnings.append(f"Strategy {name} failed: {out.get('error') if isinstance(out, dict) else out}")

        if sm_rows:
            sm_df = pd.DataFrame(sm_rows)
            fig_sm = go.Figure()
            fig_sm.add_trace(go.Bar(name="Win Rate %", x=sm_df["strategy"], y=sm_df["win_rate"]))
            fig_sm.add_trace(go.Bar(name="Profit Factor", x=sm_df["strategy"], y=sm_df["profit_factor"]))
            fig_sm.add_trace(go.Bar(name="Expectancy", x=sm_df["strategy"], y=sm_df["expectancy"]))
            fig_sm.update_layout(barmode="group", title="Strategy Diagnostics")
            charts["strategy_diagnostics"] = _to_plotly_json(fig_sm)

        close = stock_df["Close"].astype(float)
        fast_ma = vbt.MA.run(close, 50)
        slow_ma = vbt.MA.run(close, 200)
        entries = fast_ma.ma_crossed_above(slow_ma)
        exits = fast_ma.ma_crossed_below(slow_ma)
        strategy_pf = vbt.Portfolio.from_signals(close, entries, exits, fees=0.001, freq="1D")

        fig_eq = go.Figure()
        fig_eq.add_trace(go.Scatter(x=close.index, y=(close / close.iloc[0]) * 100, mode="lines", name="Buy & Hold"))
        fig_eq.add_trace(go.Scatter(x=strategy_pf.value().index, y=(strategy_pf.value() / strategy_pf.value().iloc[0]) * 100, mode="lines", name="SMA Strategy"))
        fig_eq.update_layout(title=f"Strategy vs Buy-and-Hold ({stock_ticker})")
        charts["strategy_vs_buyhold_equity"] = _to_plotly_json(fig_eq)

        entry_idx = close.index[entries.fillna(False)]
        exit_idx = close.index[exits.fillna(False)]
        fig_trades = go.Figure()
        fig_trades.add_trace(go.Scatter(x=close.index, y=close.values, mode="lines", name="Close"))
        if len(entry_idx) > 0:
            fig_trades.add_trace(go.Scatter(x=entry_idx, y=close.loc[entry_idx], mode="markers", name="Entry", marker_symbol="triangle-up", marker_size=10))
        if len(exit_idx) > 0:
            fig_trades.add_trace(go.Scatter(x=exit_idx, y=close.loc[exit_idx], mode="markers", name="Exit", marker_symbol="triangle-down", marker_size=10))
        fig_trades.update_layout(title=f"Trade Entry/Exit Overlay ({stock_ticker})")
        charts["trade_overlay"] = _to_plotly_json(fig_trades)

        benchmark = "^NSEI" if stock_ticker.endswith((".NS", ".BO")) else "^GSPC"
        bdf, berr = fetch_data(benchmark, period=selected_timeframe)
        if not berr and bdf is not None and not bdf.empty:
            combo = pd.DataFrame({"asset": close, "bench": bdf["Close"]}).ffill().pct_change(fill_method=None).dropna()
            if not combo.empty:
                win = 63
                rolling_beta = combo["asset"].rolling(win).cov(combo["bench"]) / combo["bench"].rolling(win).var()
                fig_beta = go.Figure()
                fig_beta.add_trace(go.Scatter(x=rolling_beta.index, y=rolling_beta.values, mode="lines", name="Rolling Beta"))
                fig_beta.update_layout(title=f"Rolling Beta vs {benchmark}")
                charts["rolling_beta"] = _to_plotly_json(fig_beta)

                quant = get_quant_analysis(stock_df, benchmark_ticker=benchmark)
                alpha = calculate_alpha_metrics(stock_df, benchmark_ticker=benchmark)

                bench_ann = float(combo["bench"].mean() * 252)
                beta_val = float(alpha.get("beta", 0.0)) if isinstance(alpha, dict) else 0.0
                alpha_val = float(alpha.get("alpha_annualized", 0.0)) if isinstance(alpha, dict) else 0.0
                contrib = [bench_ann, beta_val * bench_ann, alpha_val]
                fig_wf = go.Figure(
                    go.Waterfall(
                        name="Alpha Decomposition",
                        orientation="v",
                        measure=["relative", "relative", "total"],
                        x=["Benchmark Return", "Beta Contribution", "Alpha"],
                        y=contrib,
                    )
                )
                fig_wf.update_layout(title="Alpha Decomposition Waterfall")
                charts["alpha_decomposition_waterfall"] = _to_plotly_json(fig_wf)

                hurst = _rolling_hurst(close)
                if not hurst.empty:
                    fig_hurst = go.Figure()
                    fig_hurst.add_trace(go.Scatter(x=hurst.index, y=hurst.values, mode="lines", name="Hurst"))
                    fig_hurst.add_hline(y=0.55, line_dash="dash")
                    fig_hurst.add_hline(y=0.45, line_dash="dash")
                    fig_hurst.update_layout(title="Rolling Hurst Exponent")
                    charts["rolling_hurst_exponent"] = _to_plotly_json(fig_hurst)

                    regime = pd.Series(np.where(hurst > 0.55, 1, np.where(hurst < 0.45, -1, 0)), index=hurst.index)
                    fig_reg = go.Figure()
                    fig_reg.add_trace(go.Scatter(x=regime.index, y=regime.values, mode="lines", name="Regime"))
                    fig_reg.update_layout(
                        title=f"Regime Timeline ({quant.get('regime', 'UNKNOWN')})",
                        yaxis=dict(tickvals=[-1, 0, 1], ticktext=["Mean Reverting", "Stochastic", "Trending"]),
                    )
                    charts["regime_timeline"] = _to_plotly_json(fig_reg)

    target_company = company_ticker or tickers[0]
    try:
        fdata = _build_fundamental_series(target_company)
        years = fdata.get("years", [])
        if years:
            fig_fin = go.Figure()
            fig_fin.add_trace(go.Scatter(x=years, y=fdata.get("revenue", []), mode="lines+markers", name="Revenue"))
            fig_fin.add_trace(go.Scatter(x=years, y=fdata.get("ebitda", []), mode="lines+markers", name="EBITDA"))
            fig_fin.add_trace(go.Scatter(x=years, y=fdata.get("eps", []), mode="lines+markers", name="EPS", yaxis="y2"))
            fig_fin.update_layout(
                title=f"Revenue / EBITDA / EPS Trend ({target_company})",
                yaxis2=dict(overlaying="y", side="right", title="EPS"),
            )
            charts["fundamental_revenue_ebitda_eps"] = _to_plotly_json(fig_fin)

            fig_margin = go.Figure()
            fig_margin.add_trace(go.Scatter(x=years, y=fdata.get("net_margin", []), mode="lines+markers", name="Net Margin %"))
            fig_margin.add_trace(go.Scatter(x=years, y=fdata.get("roe", []), mode="lines+markers", name="ROE %"))
            fig_margin.update_layout(title="Margin and ROE Trend")
            charts["margin_roe_trend"] = _to_plotly_json(fig_margin)

            fig_debt = go.Figure()
            fig_debt.add_trace(go.Bar(x=years, y=fdata.get("debt", []), name="Debt"))
            fig_debt.add_trace(go.Scatter(x=years, y=fdata.get("interest_coverage", []), mode="lines+markers", name="Interest Coverage", yaxis="y2"))
            fig_debt.update_layout(
                title="Debt and Interest Coverage Trend",
                yaxis2=dict(overlaying="y", side="right", title="Interest Coverage"),
            )
            charts["debt_interest_coverage_trend"] = _to_plotly_json(fig_debt)

        mult = fdata.get("multiples", {})
        med = fdata.get("sector_medians", {})
        labels = ["PE", "PB", "EV_EBITDA"]
        fig_mult = go.Figure()
        fig_mult.add_trace(go.Bar(name="Company", x=labels, y=[mult.get(k) for k in labels]))
        fig_mult.add_trace(go.Bar(name="Sector Median", x=labels, y=[med.get(k) for k in labels]))
        fig_mult.update_layout(title="Valuation Multiples vs Sector", barmode="group")
        charts["valuation_multiples_vs_sector"] = _to_plotly_json(fig_mult)
    except Exception as exc:
        warnings.append(f"Fundamental charts failed for {target_company}: {exc}")

    try:
        pipeline = find_sector_stock_pipeline(market=market, top_n_sectors=4, top_n_stocks=3)
        sector_rankings = pd.DataFrame(pipeline.get("sector_rankings", []))
        if not sector_rankings.empty:
            fig_sector = px.bar(
                sector_rankings,
                x="sector",
                y="performance_3m_pct",
                title=f"Sector Relative Strength ({market.upper()})",
            )
            charts["sector_relative_strength"] = _to_plotly_json(fig_sector)

        stocks = pipeline.get("selected_stocks", [])
        top_sector = float(sector_rankings["performance_3m_pct"].iloc[0]) if not sector_rankings.empty else 0.0
        top_stock = float(stocks[0]["score"]) if stocks else 0.0
        conf = float(pipeline.get("confidence", 0.0)) * 100

        fig_funnel = go.Figure(go.Funnel(y=["Top Sector Score", "Top Stock Score", "Pipeline Confidence"], x=[top_sector, top_stock, conf]))
        fig_funnel.update_layout(title="Sector-to-Stock Funnel")
        charts["sector_stock_funnel"] = _to_plotly_json(fig_funnel)

        ok_count = sum(1 for row in pipeline.get("data_trace", []) if row.get("status") == "ok")
        fail_count = sum(1 for row in pipeline.get("data_trace", []) if row.get("status") != "ok")

        fig_conf = go.Figure()
        fig_conf.add_trace(
            go.Indicator(
                mode="gauge+number",
                value=conf,
                title={"text": "Pipeline Confidence"},
                gauge={"axis": {"range": [0, 100]}},
                domain={"x": [0, 0.55], "y": [0, 1]},
            )
        )
        fig_conf.add_trace(
            go.Bar(
                x=["Data Trace OK", "Data Trace Failed"],
                y=[ok_count, fail_count],
                xaxis="x2",
                yaxis="y2",
                name="Data Trace",
            )
        )
        fig_conf.update_layout(
            title="Confidence and Data Trace",
            xaxis2={"domain": [0.62, 1.0], "anchor": "y2"},
            yaxis2={"domain": [0.0, 1.0], "anchor": "x2"},
            showlegend=False,
        )
        charts["confidence_data_trace_panel"] = _to_plotly_json(fig_conf)
    except Exception as exc:
        warnings.append(f"Sector pipeline charts failed: {exc}")

    default_order = [chart_id for chart_id in _DEFAULT_CHART_ORDER if chart_id in charts]

    chart_specs: dict[str, dict[str, Any]] = {}
    legacy_charts: dict[str, dict[str, Any]] = {}
    for chart_id, figure in charts.items():
        detached_figure = json.loads(json.dumps(figure, default=str))
        legacy_charts[chart_id] = detached_figure
        title = (
            figure.get("layout", {})
            .get("title", {})
            .get("text")
        )
        chart_specs[chart_id] = {
            "id": chart_id,
            "title": title or chart_id.replace("_", " ").title(),
            "category": _CHART_CATEGORIES.get(chart_id, "other"),
            "figure": detached_figure,
            "isolation": {
                "independent": True,
                "shared_state": False,
                "safe_to_mutate_individually": True,
            },
        }

    return {
        "status": "ok",
        "chart_count": len(chart_specs),
        "default_display": {
            "enabled": True,
            "mode": "chart_first",
            "layout": "grid_2_col",
            "order": default_order,
            "pinned": default_order[:8],
        },
        # Backward-compatible shape: chart_id -> Plotly figure JSON.
        "charts": legacy_charts,
        # Rich metadata shape for clients that want grouped rendering controls.
        "chart_specs": chart_specs,
        "warnings": warnings,
        "meta": {
            "tickers": tickers,
            "amount": amount,
            "market": market,
            "company_ticker": target_company,
            "timeframe": selected_timeframe,
            "optimization_methods": methods,
        },
    }


# Backward-compatible alias for older imports.
build_plotly_chart_pack = build_chart_pack
