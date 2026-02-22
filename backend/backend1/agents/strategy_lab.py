class StrategyLab:

    def run(self, task: str, state=None):

        if not state or "financial" not in state or "risk" not in state:
            return {"error": "Missing financial or risk data"}

        price = state["financial"]["current_price"]
        volatility = state["risk"]["volatility_annual"]

        # Simple logic:
        target = price * (1 + 0.20)
        stop_loss = price * (1 - 0.15)

        recommendation = "BUY"

        if volatility > 0.6:
            recommendation = "HOLD"

        return {
            "recommendation": recommendation,
            "entry_price": price,
            "target_price": round(target, 2),
            "stop_loss": round(stop_loss, 2)
        }
