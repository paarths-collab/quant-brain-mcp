class StressTesting:

    def simulate_crash(self, price, crash_percent=0.3):
        if price is None: return {}
        stressed_price = price * (1 - crash_percent)

        return {
            "crash_percent": crash_percent * 100,
            "original_price": float(price),
            "stressed_price": float(stressed_price),
            "loss": float(price - stressed_price)
        }
