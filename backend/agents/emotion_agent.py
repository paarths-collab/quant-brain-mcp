from __future__ import annotations

import re
from typing import Any, Dict, List, Optional


class EmotionAnalysisAgent:
    """
    Lightweight, rule-based detector for emotion-driven investing language.
    Returns detected biases and an overall emotion intensity score.
    """

    def __init__(self) -> None:
        self._rules = [
            {
                "bias": "panic_selling",
                "tone": "anxious",
                "weight": 0.45,
                "patterns": [
                    r"\bpanic\w*\b",
                    r"\bcrash\b",
                    r"\bmeltdown\b",
                    r"\bsell everything\b",
                    r"\bsell all\b",
                    r"\bget out now\b",
                    r"\bexit now\b",
                    r"\bbleeding\b",
                    r"\bdown big\b",
                ],
            },
            {
                "bias": "fomo_buying",
                "tone": "excited",
                "weight": 0.45,
                "patterns": [
                    r"\bfomo\b",
                    r"\bto the moon\b",
                    r"\bmoon\b",
                    r"\bcan't miss\b",
                    r"\bbuy now\b",
                    r"\bbefore it's too late\b",
                    r"\bgoing up\b",
                    r"\bspiking\b",
                    r"\bexploding\b",
                ],
            },
            {
                "bias": "overconfidence",
                "tone": "overconfident",
                "weight": 0.25,
                "patterns": [
                    r"\ball in\b",
                    r"\bdouble down\b",
                    r"\bguaranteed\b",
                    r"\bcan't lose\b",
                    r"\b100%\b",
                    r"\bno risk\b",
                ],
            },
            {
                "bias": "revenge_trading",
                "tone": "frustrated",
                "weight": 0.2,
                "patterns": [
                    r"\bmake it back\b",
                    r"\bwin it back\b",
                    r"\bget even\b",
                    r"\brevenge\b",
                    r"\bchasing losses\b",
                ],
            },
            {
                "bias": "anchoring_regret",
                "tone": "regretful",
                "weight": 0.15,
                "patterns": [
                    r"\bshould have\b",
                    r"\bif only\b",
                    r"\bback to\b",
                    r"\breturn to\b",
                    r"\bmissed out\b",
                ],
            },
        ]

    def analyze(self, text: str) -> Dict[str, Any]:
        raw = text or ""
        cleaned = raw.strip()
        if not cleaned:
            return {
                "emotion_intensity": 0.0,
                "emotion_label": "calm",
                "dominant_bias": None,
                "biases": [],
            }

        biases: List[Dict[str, Any]] = []
        total_score = 0.0

        for rule in self._rules:
            matches = self._find_matches(raw, rule["patterns"])
            if not matches:
                continue

            rule_score = min(1.0, len(matches) / max(1.0, len(rule["patterns"]) / 2))
            total_score += rule_score * float(rule["weight"])

            biases.append(
                {
                    "bias": rule["bias"],
                    "score": round(rule_score, 2),
                    "evidence": matches,
                    "tone": rule["tone"],
                }
            )

        intensity = min(1.0, total_score + self._arousal_adjust(raw))
        dominant = max(biases, key=lambda b: b["score"], default=None)
        emotion_label = self._label_from_bias(dominant, intensity)

        return {
            "emotion_intensity": round(intensity, 2),
            "emotion_label": emotion_label,
            "dominant_bias": dominant["bias"] if dominant else None,
            "biases": biases,
        }

    def _find_matches(self, text: str, patterns: List[str]) -> List[str]:
        matches: List[str] = []
        for pattern in patterns:
            if re.search(pattern, text, flags=re.IGNORECASE):
                matches.append(pattern.strip(r"\b"))
        return matches

    def _arousal_adjust(self, text: str) -> float:
        bonus = 0.0
        exclamations = text.count("!")
        caps_words = re.findall(r"\b[A-Z]{3,}\b", text)

        if exclamations >= 3:
            bonus += 0.1
        if exclamations >= 6:
            bonus += 0.1
        if len(caps_words) >= 2:
            bonus += 0.1
        return bonus

    def _label_from_bias(self, dominant: Optional[Dict[str, Any]], intensity: float) -> str:
        if intensity < 0.2:
            return "calm"
        if dominant:
            return dominant.get("tone", "concerned")
        if intensity < 0.45:
            return "concerned"
        if intensity < 0.7:
            return "activated"
        return "highly_emotional"
