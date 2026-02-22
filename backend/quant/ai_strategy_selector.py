from backend.core.llm_client import LLMClient
from backend.quant.rl_strategy_selector import RLStrategySelector
import json

class AIStrategySelector:

    def __init__(self):
        # Initialize RL Agent with known strategy names
        self.rl = RLStrategySelector(["EMA_Crossover", "RSI_Reversion", "Breakout"])
        self.llm = LLMClient()

    def select(self, strategy_results, regime, macro_data):

        # Step 1: RL suggestion (What worked historically?)
        rl_choice = self.rl.choose_strategy()
        
        # Prepare data for LLM
        strategies_summary = []
        for s in strategy_results:
            strategies_summary.append(f"- {s['strategy']}: Return {s.get('return',0):.2f}%, Win Rate {s.get('win_rate',0):.2f}%")
        
        strategies_text = "\n".join(strategies_summary)
        
        # Step 2: LLM reasoning (Reasoning Engine)
        prompt = [
            {"role": "system", "content": "You are a Quantitative Strategy Manager. Select the best trading strategy based on Market Regime, Macro Data, and Backtest Metrics."},
            {"role": "user", "content": f"""
            Market Context:
            - Regime: {regime.get('regime')}
            - Volatility: {regime.get('volatility'):.2%}
            - Macro Bias: {macro_data.get('market_bias', 'Neutral')}

            Available Strategies & Recent Performance:
            {strategies_text}
            
            RL Agent Suggestion: {rl_choice}

            TASK:
            1. Analyze which strategy fits the current regime (e.g., EMA for Trend, RSI for Chop/Sideways, Breakout for Volatility).
            2. Select the ONE best strategy name.
            3. Return JSON: {{ "selected_strategy": "NAME", "reasoning": "..." }}
            """}
        ]

        try:
            response = self.llm.deep_reason(prompt).choices[0].message.content
            print(f"DEBUG LLM Strategy Selection: {response}")
            
            # Simple parsing or ensure JSON mode in client
            # Assuming the client returns string, let's try to extract JSON
            import re
            match = re.search(r"\{.*\}", response, re.DOTALL)
            if match:
                json_str = match.group(0)
                data = json.loads(json_str)
                llm_choice = data.get("selected_strategy", rl_choice)
                reasoning = data.get("reasoning", "LLM reasoning.")
            else:
                # Fallback if no JSON found
                llm_choice = rl_choice
                reasoning = "LLM parsing failed, used RL default."
                
        except Exception as e:
            print(f"AI Selector Error: {e}")
            llm_choice = rl_choice
            reasoning = f"Error: {e}"

        # Validation: Ensure choice is valid
        valid_strategies = [s["strategy"] for s in strategy_results]
        final_choice = llm_choice if llm_choice in valid_strategies else rl_choice

        # Step 3: Update RL (Reinforcement Learning)
        # We simulate the "reward" as the backtest return of the chosen strategy (immediate feedback loop)
        # In a real live loop, this would be updated next day. Here we use backtest proxy.
        chosen_strategy_result = next((s for s in strategy_results if s["strategy"] == final_choice), None)
        if chosen_strategy_result:
             self.rl.update(final_choice, chosen_strategy_result.get("return", 0))

        return {
            "selected_strategy": final_choice,
            "reasoning": reasoning,
            "rl_suggestion": rl_choice,
            "q_table": self.rl.get_q_table()
        }
