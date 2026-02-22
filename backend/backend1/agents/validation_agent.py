from backend1.core.llm_client import LLMClient


class ValidationAgent:

    def __init__(self):
        self.llm = LLMClient()

    def run(self, structured_output):

        messages = [
            {
                "role": "system",
                "content": "You are a financial output validator. Focus on MATHEMATICAL CONSISTENCY and DATA INTEGRITY. Do not judge high values (like multi-trillion market caps) as unrealistic if they are mathematically consistent."
            },
            {
                "role": "user",
                "content": f"""
Validate the following financial analysis output.

RULES:
1. CHECK CONSISTENCY: Does Price * Shares roughly equal Market Cap? (Allow 5% variance)
2. CHECK TIMEFRAME ALIGNMENT: Revenue growth might differ between Quarterly (YoY) and Annual. Mismatch is expected if labeled differently.
3. CHECK COMPLETENESS: Are Ticker, Price, and basic metrics present?
4. REPORTING:
   - Flag "High" severity only for logic breaks (e.g. neg price, missing data).
   - Flag "Low" severity for missing optional fields.
   - Do NOT flag "Unrealistic" for correct large numbers (e.g. NVDA > $3T cap is VALID).

Respond strictly in JSON:
{{
  "is_valid": true/false,
  "issues": [
      {{"severity": "high|medium|low", "message": "..."}}
  ],
  "confidence_score": 0-100
}}

Output to validate:
{structured_output}
"""
            }
        ]

        return self.llm.run_model(
            model="validator",
            messages=messages
        )
