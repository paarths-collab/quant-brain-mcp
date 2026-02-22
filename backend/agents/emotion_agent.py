from typing import Dict, Any, List

class EmotionAnalysisAgent:
    """
    Analyzes user text to detect emotional biases and intensity.
    Used by EmotionAdvisor and MarketPulse.
    """

    # Simple keyword-based bias detection
    BIAS_KEYWORDS = {
        "panic_selling": ["panic", "crash", "sell all", "dump", "crashing", "scared", "fear", "plunge", "collapse"],
        "fomo_buying": ["moon", "rocket", "miss out", "fomo", "all in", "yolo", "skyrocket", "flying"],
        "overconfidence": ["guaranteed", "sure thing", "easy money", "cannot lose", "safe bet"],
        "revenge_trading": ["make it back", "recover loss", "get even", "revenge", "makeup"]
    }

    EMOTION_INTENSITY_MAP = {
        "panic_selling": 0.8,
        "fomo_buying": 0.7,
        "overconfidence": 0.6,
        "revenge_trading": 0.9
    }

    def analyze(self, message: str) -> Dict[str, Any]:
        """
        Analyze the text for emotional cues.
        Returns a dictionary with intensity, label, and detected biases.
        """
        message = message.lower()
        
        detected_biases = []
        max_intensity = 0.0
        dominant_bias = None
        
        for bias, keywords in self.BIAS_KEYWORDS.items():
            hits = [w for w in keywords if w in message]
            if hits:
                score = self.EMOTION_INTENSITY_MAP.get(bias, 0.5)
                # Boost score slightly if multiple keywords found
                if len(hits) > 1:
                    score = min(1.0, score + 0.1)
                
                detected_biases.append({
                    "bias": bias,
                    "score": score,
                    "keywords": hits
                })
                
                if score > max_intensity:
                    max_intensity = score
                    dominant_bias = bias
        
        # Determine label based on intensity and dominant bias
        emotion_label = "calm"
        if max_intensity >= 0.7:
            emotion_label = "highly_emotional"
            if dominant_bias == "panic_selling": emotion_label = "anxious"
            elif dominant_bias == "fomo_buying": emotion_label = "excited"
            elif dominant_bias == "overconfidence": emotion_label = "confident"
        elif max_intensity >= 0.4:
            emotion_label = "concerned" if dominant_bias == "panic_selling" else "optimistic"

        return {
            "text": message,
            "emotion_intensity": max_intensity,
            "emotion_label": emotion_label,
            "dominant_bias": dominant_bias,
            "biases": detected_biases,
            "is_emotional": max_intensity >= 0.5
        }
