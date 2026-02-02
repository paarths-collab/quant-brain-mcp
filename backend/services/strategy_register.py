# services/strategy_registry.py

from backend.services.strategies.sma_crossover import SMACrossoverStrategy
from backend.services.strategies.ema_crossover import EMACrossoverStrategy
from backend.services.strategies.support_resistance import SupportResistanceStrategy
# import others…

STRATEGY_REGISTRY = {
    "sma_crossover": SMACrossoverStrategy,
    "ema_crossover": EMACrossoverStrategy,
    "support_resistance": SupportResistanceStrategy,
    # add others
}

def get_strategy(name: str, **params):
    if name not in STRATEGY_REGISTRY:
        raise ValueError(f"Strategy '{name}' not registered")
    return STRATEGY_REGISTRY[name](**params)
