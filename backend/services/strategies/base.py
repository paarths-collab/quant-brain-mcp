# services/strategies/base.py

class Strategy:
    name = "Base Strategy"

    def parameters(self) -> dict:
        return {}

    def generate_signals(self, data):
        raise NotImplementedError
