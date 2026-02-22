from backend.core.llm_client import LLMClient

class ReportAgent:

    def __init__(self):
        self.llm = LLMClient()

    def _fallback_memo(self, financial, web, sector, emotion) -> str:
        ticker = (financial or {}).get("ticker", "UNKNOWN")
        price = (financial or {}).get("price")
        score = (financial or {}).get("score")
        technicals = (financial or {}).get("technicals") or {}
        fundamentals = (financial or {}).get("fundamentals") or {}

        web_sent = (web or {}).get("sentiment")
        web_score = (web or {}).get("score")
        sector_summary = (sector or {}).get("summary") if isinstance(sector, dict) else None

        rsi = technicals.get("rsi")
        pe = fundamentals.get("pe")
        mcap = fundamentals.get("market_cap")

        def fmt_num(v, digits=2):
            try:
                return f"{float(v):.{digits}f}"
            except Exception:
                return "N/A"

        verdict = "HOLD"
        conviction = 5
        if isinstance(score, (int, float)):
            if score >= 55:
                verdict = "BUY"
                conviction = 6
            elif score <= 25:
                verdict = "SELL"
                conviction = 6

        return (
            "# Executive Summary\n"
            f"- Ticker: **{ticker}**\n"
            f"- Price: **{fmt_num(price)}**\n"
            f"- Technical Score: **{score if isinstance(score, (int, float)) else 'N/A'}**\n"
            f"- Sentiment: **{web_sent or 'unknown'}** (score {web_score if isinstance(web_score, (int, float)) else 'N/A'})\n"
            f"- Verdict: **{verdict}** (Conviction **{conviction}/10**)\n"
            "\n"
            "# Bull Case (Key Points)\n"
            "- If price trend stabilizes and momentum improves, risk/reward can improve.\n"
            "- If macro/sector tailwinds strengthen, upside asymmetry increases.\n"
            "\n"
            "# Bear Case (Key Risks)\n"
            "- Data gaps: some fundamentals/news may be unavailable in this environment.\n"
            "- Volatility/regime shifts can invalidate signals quickly.\n"
            "\n"
            "# Synthesis & Pivot Variable\n"
            f"- Pivot: **RSI + earnings quality + macro backdrop** (RSI={fmt_num(rsi, 1)}, PE={pe if pe is not None else 'N/A'}).\n"
            "\n"
            "# Final Verdict & Strategy\n"
            f"- **{verdict}** with staged sizing; re-evaluate on material price move or macro shift.\n"
            "\n"
            "## Raw Inputs Snapshot\n"
            f"- Fundamentals: PE={pe if pe is not None else 'N/A'}, MarketCap={mcap if mcap is not None else 'N/A'}\n"
            f"- Sector: {sector_summary or 'N/A'}\n"
            f"- Emotion: {emotion or 'N/A'}\n"
        )

    def generate(self, financial, web, sector, emotion):
        # Prepare context data
        context = f"""
        Financial Data: {financial}
        Web Sentiment: {web}
        Sector Context: {sector}
        Emotion Analysis: {emotion}
        """

        try:
            # One-shot report to avoid 3 separate LLM calls (reduces 429s dramatically on Groq free tier).
            prompt = [
                {"role": "system", "content": "You are the CIO of a Multi-Strategy Hedge Fund writing an Investment Committee memo. Be concise, data-backed, and structured."},
                {"role": "user", "content": f"""
                Using the raw data below, produce a structured memo with BOTH sides and a final decision.

                Raw Data:
                {context}

                Requirements:
                - Max 650 words total.
                - Avoid hallucinating; if a datapoint is missing, say it's unavailable.
                - Include a Conviction Rating (1-10) and Final Verdict (BUY / SELL / HOLD).

                Structure:
                # Executive Summary
                # Bull Case (Key Points)
                # Bear Case (Key Risks)
                # Synthesis & Pivot Variable
                # Final Verdict & Strategy
                """},
            ]

            return self.llm.deep_reason(prompt).choices[0].message.content
        except Exception as e:
            # Don't fail the entire response on LLM connectivity/rate-limit issues.
            # Return a deterministic memo so the UI stays usable.
            return (
                f"**LLM Unavailable** (reason: {e}). Using a deterministic fallback memo.\n\n"
                + self._fallback_memo(financial, web, sector, emotion)
            )
