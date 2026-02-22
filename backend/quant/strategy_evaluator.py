class StrategyEvaluator:

    def evaluate(self, strategy_result, regime_data):
        """
        Scoring system for strategies based on market regime.
        """
        score = strategy_result.get("return", 0) * 0.6
        score += strategy_result.get("win_rate", 0) * 0.3

        regime = regime_data.get("regime", "Unknown")

        # Contextual Boosting
        if regime == "Bullish Trending" and strategy_result["strategy"] == "EMA_Crossover":
            score += 10 # trend following works best in trends

        if regime == "Sideways / Bearish" and strategy_result["strategy"] == "RSI_Reversion":
            score += 10 # mean reversion works best in chop

        if regime == "High Volatility" and strategy_result["strategy"] == "Breakout":
            score += 10 # breakouts work well in volatility

        return float(score)
