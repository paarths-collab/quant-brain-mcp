class EmotionalAgent:
    def __init__(self):
        self.panic_keywords = ['crash', 'panic', 'sell everything', 'dump', 'ruined']
        self.fomo_keywords = ['moon', 'rocket', 'guaranteed', 'all in']

    def analyze(self, query: str):
        """Analyze emotional state of query"""
        q_lower = query.lower()
        
        status = "neutral"
        risk = "low"
        
        if any(w in q_lower for w in self.panic_keywords):
            status = "panic"
            risk = "high"
        elif any(w in q_lower for w in self.fomo_keywords):
            status = "fomo/overconfident"
            risk = "high"
            
        return {
            "emotional_state": status,
            "risk_level": risk
        }
