"""
Isolated backtest_agent_service for backtest/core.
Provides AI-powered backtest analysis using Groq.
"""
import os
from typing import Dict, Any


def run_backtest_agent(ticker: str, strategy: str, results: Dict[str, Any]) -> Dict[str, Any]:
    """
    Run an AI agent to analyze backtest results and provide insights.
    Falls back to a structured summary if AI is unavailable.
    """
    try:
        from .groq_agent import GroqAgent
        agent = GroqAgent()
        
        metrics = results.get("metrics", {})
        prompt = f"""Analyze this backtest for {ticker} using {strategy} strategy:
        
- Total Return: {metrics.get('totalReturn', 'N/A')}%
- Max Drawdown: {metrics.get('maxDrawdown', 'N/A')}%
- Sharpe Ratio: {metrics.get('sharpeRatio', 'N/A')}
- Win Rate: {metrics.get('winRate', 'N/A')}%
- Total Trades: {metrics.get('totalTrades', 'N/A')}

Provide: 1) Key strengths 2) Key risks 3) Improvement suggestions"""

        analysis = agent.query(prompt)
        return {
            "ticker": ticker,
            "strategy": strategy,
            "analysis": analysis,
            "status": "success"
        }
    except Exception as e:
        print(f"[backtest_agent_service] AI analysis failed: {e}")
        metrics = results.get("metrics", {})
        return {
            "ticker": ticker,
            "strategy": strategy,
            "analysis": _generate_fallback_analysis(metrics),
            "status": "fallback"
        }


def _generate_fallback_analysis(metrics: Dict[str, Any]) -> str:
    """Generate a rule-based analysis when AI is unavailable."""
    total_return = metrics.get("totalReturn", 0) or 0
    max_drawdown = metrics.get("maxDrawdown", 0) or 0
    sharpe = metrics.get("sharpeRatio", 0) or 0
    win_rate = metrics.get("winRate", 0) or 0

    strengths = []
    risks = []

    if total_return > 10:
        strengths.append(f"Strong positive return of {total_return:.1f}%")
    if sharpe > 1:
        strengths.append(f"Good risk-adjusted return (Sharpe: {sharpe:.2f})")
    if win_rate > 55:
        strengths.append(f"Above-average win rate ({win_rate:.1f}%)")

    if max_drawdown < -20:
        risks.append(f"High max drawdown of {max_drawdown:.1f}% — consider position sizing")
    if sharpe < 0.5:
        risks.append("Low Sharpe ratio — strategy may not justify its risk")
    if win_rate < 40:
        risks.append(f"Low win rate ({win_rate:.1f}%) — consider tightening entry criteria")

    parts = []
    if strengths:
        parts.append("**Strengths:** " + "; ".join(strengths))
    if risks:
        parts.append("**Risks:** " + "; ".join(risks))
    if not parts:
        parts.append("Backtesting completed. Review metrics above for detailed analysis.")

    return " | ".join(parts)
