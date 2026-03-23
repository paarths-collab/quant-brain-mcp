import random
import json
import os
from pathlib import Path

class RLStrategySelector:

    def __init__(self, strategies, q_table_path="outputs/trained_qtable.json"):
        self.strategies = strategies
        self.q_table_path = Path(q_table_path)
        self.lr = 0.1
        self.gamma = 0.95
        self.epsilon = 0.05  # Low epsilon for exploitation of trained Q-table
        self.q_table = self._load_q_table()

    def _load_q_table(self):
        if self.q_table_path.exists():
            try:
                with open(self.q_table_path, "r") as f:
                    data = json.load(f)
                    # Load the flat regime-prefixed keys (e.g., "Bull_macd")
                    qt = data.get("q_table_flat", {})
                    print(f"  [RL] Loaded trained Q-table: {len(qt)} keys")
                    return qt
            except Exception as e:
                print(f"  [RL] Failed to load Q-table: {e}")
        
        print("  [RL] No trained Q-table found, starting fresh")
        return {}

    def _save_q_table(self):
        # We typically save the full payload with metadata, 
        # but for compatibility we'll just save the flat table if needed.
        # However, training is usually done via the training script.
        pass

    def choose_strategy(self, regime: str) -> str:
        """
        Uses regime-aware Q-values to select the best strategy.
        Keys are 'Bull_strategy', 'Bear_strategy', 'Choppy_strategy'.
        """
        import numpy as np
        
        # Epsilon-greedy (mostly exploitation now)
        if random.uniform(0, 1) < self.epsilon:
            return random.choice(self.strategies)
        
        # Try regime-specific keys first
        scores = {
            s: self.q_table.get(f"{regime}_{s}", 0.0)
            for s in self.strategies
        }
        
        # Fallback to flat keys if no regime-specific data exists
        if all(v == 0.0 for v in scores.values()):
            scores = {
                s: self.q_table.get(s, 0.0)
                for s in self.strategies
            }
        
        if not scores:
            return random.choice(self.strategies)
            
        max_val = max(scores.values())
        best_strategies = [s for s, v in scores.items() if v == max_val]
        return random.choice(best_strategies)

    def update(self, regime: str, strategy: str, reward: float):
        """
        Update with regime-prefixed key.
        """
        k = f"{regime}_{strategy}"
        old_val = self.q_table.get(k, 0.0)
        
        # For max_future, we stay in the same regime as we don't know the next one yet
        futures = [self.q_table.get(f"{regime}_{s}", 0.0) for s in self.strategies]
        max_future = max(futures) if futures else 0.0
        
        # Q-learning update rule
        new_val = old_val + self.lr * (reward + self.gamma * max_future - old_val)
        self.q_table[k] = round(new_val, 6)
        # Note: Auto-saving is disabled here to avoid corrupted payloads,
        # training is handled by the dedicated script.

    def get_q_table(self):
        return self.q_table

