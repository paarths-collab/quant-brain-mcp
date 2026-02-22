from backend.backend1.core.llm_client import LLMClient
import json

class DecidingAgent:

    def __init__(self):
        self.llm = LLMClient()

    def decide(self, stock_summaries, horizon="long"):
        # Deterministic pre-sorting
        sorted_stocks = sorted(
            stock_summaries,
            key=lambda x: x["final_score"],
            reverse=True
        )
        
        # Limit to top 5 for LLM context to save tokens
        top_candidates = sorted_stocks[:5]
        
        # Calculate Confidence Level
        spread = 0.0
        confidence_level = "Low"
        top_score = sorted_stocks[0]["final_score"] if sorted_stocks else 0
        
        if len(sorted_stocks) > 1:
             runner_up_score = sorted_stocks[1]["final_score"]
             spread = top_score - runner_up_score
             
             if spread > 1.0:
                  confidence_level = "High"
             elif spread > 0.5:
                  confidence_level = "Moderate"
        elif sorted_stocks:
             confidence_level = "High (Single Candidate)"

        prompt = f"""
        You are a professional investment analyst.
        Review these top candidates for investment.
        Investment Horizon: {horizon.upper()}
        
        The top candidate is {sorted_stocks[0]["ticker"]} (Score: {top_score}).
        The runner up is {sorted_stocks[1]["ticker"] if len(sorted_stocks) > 1 else "None"} (Score: {runner_up_score if len(sorted_stocks) > 1 else 0}).
        The score spread is {spread:.2f}, indicating {confidence_level} confidence in the relative ranking.

        Based on the structured analysis below, recommend the best stock and explain why, specifically for a {horizon} term strategy.
        
        CRITICAL: You MUST provide specific price action advice for the recommended stock:
        1. **Buy Price**: Ideally a range or specific level based on support/techs.
        2. **Sell Target**: A target price based on resistance or expected return.
        3. **Stop Loss**: A specific price level to limit downside.
        
        Use the provided technical data (Support/Resistance, SMA, RSI) to determine these levels. If exact levels aren't in data, estimate conservative levels based on volatility/current price.

        Do not fabricate data.
        Only use provided information.
        
        Compare the top candidate against the runner-up.
        Mention key risks if any.
        
        Data:
        {json.dumps(top_candidates, indent=2)}
        """

        explanation = self.llm.run_model(
            model="deep_reason",
            messages=[{"role": "user", "content": prompt}]
        )

        return {
            "ranked": sorted_stocks,
            "explanation": explanation,
            "top_pick": sorted_stocks[0]["ticker"] if sorted_stocks else None,
            "features": {
                "confidence_level": confidence_level,
                "spread": round(spread, 2)
            }
        }
