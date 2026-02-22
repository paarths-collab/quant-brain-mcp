import numpy as np

class RiskAgent:

    def evaluate(self, portfolio):
        """
        Evaluates portfolio concentration risk.
        Portfolio dict format: {"Ticker": weight_float}
        """
        if not portfolio:
            return {"concentration": 0.0, "risk_score": 100.0, "message": "Empty portfolio"}

        weights = np.array(list(portfolio.values()))
        
        # Max weight determines single-stock concentration risk
        concentration = float(np.max(weights))

        # Simple linear penalty: 100% concentration = 0 risk score (High Risk)
        # 0% concentration (impossible) = 100 score
        # e.g. 50% max weight -> 50 score. 
        # But user formula was: 100 - (concentration * 100)
        # So 0.5 concentration -> 100 - 50 = 50.
        
        risk_score = 100.0 - (concentration * 100.0)

        return {
            "concentration": concentration,
            "risk_score": risk_score,
            "analysis": f"Max concentration is {concentration*100:.1f}%."
        }
