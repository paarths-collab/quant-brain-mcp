from backend.services.fred_macro_service import FREDMacroService

class MacroAgent:

    def __init__(self):
        self.service = FREDMacroService()

    def analyze(self):
        data = self.service.get_macro_snapshot()
        
        # Simple Institutional Logic:
        # Fed Rate < 5% generally implies easier money -> Risk On (simplification)
        # In reality, rate cuts can also mean recession fear. 
        # But for this heuristic: Lower rates = better for equity.
        
        fed_rate = data.get("fed_rate")
        if fed_rate is None:
            bias = "unknown"
            score = 50
            analysis = "Macro bias unavailable (FRED data missing)."
        else:
            bias = "risk_on" if fed_rate < 5.0 else "risk_off"
            score = 70 if bias == "risk_on" else 40
            analysis = f"Market is in {bias} mode. Fed rate at {fed_rate}%."

        return {
            "macro_data": data,
            "market_bias": bias,
            "score": score,
            "analysis": analysis
        }
