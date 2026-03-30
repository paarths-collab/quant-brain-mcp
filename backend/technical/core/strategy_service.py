
from .strategy_adapter import (
    SMACrossoverStrategy,
    RSIMomentumStrategy,
    BreakoutStrategy,
)

# 
# 

STRATEGY_REGISTRY = {
    "sma_crossover": SMACrossoverStrategy,
    "rsi_momentum": RSIMomentumStrategy,
    "breakout": BreakoutStrategy,
}

def get_strategy(name: str, **params):
    """
    Factory function to get a strategy instance.
    """
    if name not in STRATEGY_REGISTRY:
        # Fallback or error? For now, raise error.
        # Check if we have a loose match?
        available = ", ".join(STRATEGY_REGISTRY.keys())
        raise ValueError(f"Strategy '{name}' not found. Available: {available}")
    
    strategy_class = STRATEGY_REGISTRY[name]
    # Filter params to only those accepted by the init? 
    # For now, assume dynamic kwargs are passed safely or we let Python raise TypeError if invalid args
    return strategy_class(**params)

def get_available_strategies():
    """
    Return a list of available strategies with default parameters.
    This helps the frontend build the dropdowns dynamically.
    """
    strategies = []
    for name, cls in STRATEGY_REGISTRY.items():
        # Instantiate with defaults to get parameters
        # valid assumption? Most inits have defaults.
        try:
            instance = cls()
            strategies.append({
                "id": name,
                "name": cls.name,
                "parameters": instance.parameters 
            })
        except Exception:
            # If init fails without args, we might need a workaround.
            # For now, skip or manually define.
            strategies.append({
                "id": name,
                "name": cls.name,
                "parameters": {} # Placeholder
            })
            
    return strategies
