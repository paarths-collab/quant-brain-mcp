import random
import json
import os

class RLStrategySelector:

    def __init__(self, strategies, q_table_path="q_table.json"):
        self.strategies = strategies
        self.q_table_path = q_table_path
        self.learning_rate = 0.1
        self.gamma = 0.9
        self.epsilon = 0.2
        self.q_table = self._load_q_table()

    def _load_q_table(self):
        if os.path.exists(self.q_table_path):
            try:
                with open(self.q_table_path, "r") as f:
                    return json.load(f)
            except:
                pass
        return {s: 0.0 for s in self.strategies}

    def _save_q_table(self):
        try:
            with open(self.q_table_path, "w") as f:
                json.dump(self.q_table, f)
        except:
            pass

    def choose_strategy(self):
        # Epsilon-greedy
        if random.uniform(0, 1) < self.epsilon:
            return random.choice(self.strategies)
        
        # Select best, handle ties randomly
        max_val = max(self.q_table.values())
        best_strategies = [s for s, v in self.q_table.items() if v == max_val]
        return random.choice(best_strategies)

    def update(self, strategy, reward):
        if strategy not in self.q_table:
            self.q_table[strategy] = 0.0
            
        old_val = self.q_table[strategy]
        max_future = max(self.q_table.values())
        
        # Q-learning update rule
        new_val = old_val + self.learning_rate * (reward + self.gamma * max_future - old_val)
        self.q_table[strategy] = new_val
        self._save_q_table()

    def get_q_table(self):
        return self.q_table
