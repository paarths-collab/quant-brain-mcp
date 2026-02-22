from backend.strategies.ema_strategy import EMAStrategy
from backend.strategies.rsi_strategy import RSIStrategy
from backend.strategies.breakout_strategy import BreakoutStrategy

class StrategySelector:

    def __init__(self):
        self.strategies = [
            EMAStrategy(),
            RSIStrategy(),
            BreakoutStrategy()
        ]

    def select_best(self, ticker):
        results = [s.run(ticker) for s in self.strategies]
        
        # Filter out errors
        valid_results = [r for r in results if "error" not in r and "return" in r]
        
        if not valid_results:
             # Return a default/dummy if all failed
             return {
                "strategy": "None",
                "return": 0.0,
                "win_rate": 0.0,
                "last_signal": 0
            }, results

        best = max(valid_results, key=lambda x: x["return"])
        return best, results
