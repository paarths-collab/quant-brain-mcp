"""
Unified Scoring System for Long-Term Strategies
-----------------------------------------------
Converts raw strategy analysis into normalized scores (0–100)

This layer enables:
- Strategy comparison
- Risk-profile based allocation
- Portfolio construction
- AI reasoning & explanations
"""

from typing import Dict, Any, Optional
import numpy as np


# ============================================================
# HELPERS
# ============================================================

def clamp(value: float, low: float = 0, high: float = 100) -> float:
    return max(low, min(high, value))


def normalize(value: float, min_val: float, max_val: float) -> float:
    """
    Linear normalization to 0–100
    """
    if value is None:
        return 0.0
    if max_val == min_val:
        return 0.0
    return clamp(((value - min_val) / (max_val - min_val)) * 100)


# ============================================================
# DCA SCORING
# ============================================================

def score_dca(result: Dict[str, Any]) -> Dict[str, Any]:
    """
    DCA favors:
    - Long duration
    - Positive return
    - Lower volatility implicitly
    """

    summary = result.get("summary", {})
    months = summary.get("Number of Monthly Investments", 0)

    try:
        total_return = float(summary.get("Total Return %", 0))
    except Exception:
        total_return = 0

    duration_score = normalize(months, 12, 120)          # 1y → 10y
    return_score = normalize(total_return, -20, 200)

    final_score = 0.6 * duration_score + 0.4 * return_score

    return {
        "strategy": "dca",
        "score": round(final_score, 2),
        "components": {
            "duration": round(duration_score, 2),
            "return": round(return_score, 2),
        }
    }


# ============================================================
# DIVIDEND SCORING
# ============================================================

def score_dividend(result: Dict[str, Any]) -> Dict[str, Any]:
    current = result.get("current_metrics", {})
    history = result.get("historical_performance", [])

    dividend_yield = current.get("Current Dividend Yield", 0) or 0
    payout_ratio = current.get("Payout Ratio", 100) or 100

    growth_rates = [
        p.get("Dividend Growth (CAGR) %")
        for p in history
        if p.get("Dividend Growth (CAGR) %") is not None
    ]

    avg_growth = np.mean(growth_rates) if growth_rates else 0

    yield_score = normalize(dividend_yield, 0, 8)
    growth_score = normalize(avg_growth, 0, 15)
    payout_score = clamp(100 - payout_ratio)  # lower payout = safer

    final_score = (
        0.4 * yield_score +
        0.35 * growth_score +
        0.25 * payout_score
    )

    return {
        "strategy": "dividend",
        "score": round(final_score, 2),
        "components": {
            "yield": round(yield_score, 2),
            "growth": round(growth_score, 2),
            "payout_safety": round(payout_score, 2),
        }
    }


# ============================================================
# GROWTH SCORING
# ============================================================

def score_growth(result: Dict[str, Any]) -> Dict[str, Any]:
    current = result.get("current_metrics", {})
    history = result.get("historical_performance", [])

    rev_growth = current.get("Current Revenue Growth (Quarterly YoY)") or 0
    earn_growth = current.get("Current Earnings Growth (Quarterly YoY)") or 0

    price_growth = [
        p.get("Price Growth YoY %")
        for p in history
        if p.get("Price Growth YoY %") is not None
    ]

    avg_price_growth = np.mean(price_growth) if price_growth else 0

    revenue_score = normalize(rev_growth * 100, 0, 40)
    earnings_score = normalize(earn_growth * 100, 0, 40)
    price_score = normalize(avg_price_growth, -20, 60)

    final_score = (
        0.35 * revenue_score +
        0.35 * earnings_score +
        0.30 * price_score
    )

    return {
        "strategy": "growth",
        "score": round(final_score, 2),
        "components": {
            "revenue": round(revenue_score, 2),
            "earnings": round(earnings_score, 2),
            "price_momentum": round(price_score, 2),
        }
    }


# ============================================================
# VALUE SCORING
# ============================================================

def score_value(result: Dict[str, Any]) -> Dict[str, Any]:
    current = result.get("current_metrics", {})
    history = result.get("historical_performance", [])

    pe = current.get("Current P/E Ratio")
    pb = current.get("Current P/B Ratio")
    roe = current.get("Current Return on Equity (ROE)")

    pe_score = normalize(40 - pe if pe else 0, 0, 40)
    pb_score = normalize(10 - pb if pb else 0, 0, 10)
    roe_score = normalize((roe or 0) * 100, 0, 30)

    final_score = (
        0.4 * pe_score +
        0.3 * pb_score +
        0.3 * roe_score
    )

    return {
        "strategy": "value",
        "score": round(final_score, 2),
        "components": {
            "pe": round(pe_score, 2),
            "pb": round(pb_score, 2),
            "roe": round(roe_score, 2),
        }
    }


# ============================================================
# INDEX / ETF SCORING
# ============================================================

def score_index_etf(result: Dict[str, Any]) -> Dict[str, Any]:
    perf = result.get("performance_data", [])

    cagr_values = [
        p.get("Annualized Return (CAGR) %")
        for p in perf
        if p.get("Annualized Return (CAGR) %") is not None
    ]

    avg_cagr = np.mean(cagr_values) if cagr_values else 0
    cagr_score = normalize(avg_cagr, 0, 15)

    return {
        "strategy": "index",
        "score": round(cagr_score, 2),
        "components": {
            "cagr": round(cagr_score, 2),
        }
    }


# ============================================================
# SCORING REGISTRY
# ============================================================

SCORERS = {
    "dca": score_dca,
    "dividend": score_dividend,
    "growth": score_growth,
    "value": score_value,
    "index": score_index_etf,
}


def score_strategy(
    strategy_name: str,
    result: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Public entry point for scoring
    """
    scorer = SCORERS.get(strategy_name)
    if not scorer:
        return {
            "strategy": strategy_name,
            "score": 0,
            "error": "No scorer available"
        }

    return scorer(result)
