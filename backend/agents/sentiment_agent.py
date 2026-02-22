from backend.core.llm_client import LLMClient

class SentimentAgent:

    def __init__(self):
        self.llm = LLMClient()

    def analyze(self, news_results):
        
        if not news_results:
             return {
                "sentiment": "neutral",
                "score": 50,
                "summary": "No news found."
            }

        # Combine text from snippets
        text_blob = "\n".join([f"- {r.get('title', '')}: {r.get('body', '')}" for r in news_results if r.get("body")])

        messages = [
            {"role": "system", "content": "You are a specialized Sentiment Analysis Engine. Classify overall market news sentiment as 'bullish', 'bearish', or 'neutral'. Provide a score (0-100) where 0 is extremely bearish, 100 is extremely bullish, 50 is neutral."},
            {"role": "user", "content": f"Analyze these news headlines/snippets:\n\n{text_blob[:5000]}"} # Limit context
        ]

        try:
            # Using deep reasoning for nuanced sentiment
            response = self.llm.deep_reason(messages)
            content = response.choices[0].message.content
            
            content_lower = content.lower()
            
            # Simple parsing logic (can be made more robust with JSON mode if model supports)
            score = 50
            sentiment = "neutral"
            
            if "bearish" in content_lower:
                sentiment = "bearish"
                score = 30
            elif "bullish" in content_lower:
                sentiment = "bullish"
                score = 70
            
            # Try to extract exact score if present? 
            # For now, sticking to user's logic + basic defaults
            
            return {
                "sentiment": sentiment,
                "score": score,
                "reasoning": content[:200] + "..."
            }
            
        except Exception as e:
            print(f"Sentiment Analysis failed: {e}")
            return {
                "sentiment": "neutral",
                "score": 50,
                "error": str(e)
            }
