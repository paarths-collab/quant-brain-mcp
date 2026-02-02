class LLMPeerAnalyst:
    def __init__(self, llm_agent):
        self.llm = llm_agent

    def generate_summary(
        self,
        target_symbol: str,
        peers: list,
        valuations: list,
        performance: list
    ) -> str:
        prompt = f"""
You are an equity research analyst.

Target Company: {target_symbol}

Peer Market Data:
{peers}

Valuation Comparison:
{valuations}

Relative Performance (% return):
{performance}

Write a concise peer comparison covering:
- Valuation premium/discount
- Market cap positioning
- Relative performance
- Competitive positioning

Avoid markdown tables. Write like a brokerage note.
"""

        return self.llm.run(prompt)
