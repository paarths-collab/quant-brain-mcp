import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from backend.services.crowd_insight_service import (
    analyze_crowd_insight,
    _score_from_counts,
    _label_from_score,
)


def test_score_from_counts():
    score, label = _score_from_counts(buys=5, sells=1)
    assert score > 0
    assert label == "bullish"

    score, label = _score_from_counts(buys=1, sells=4)
    assert score < 0
    assert label == "bearish"

    score, label = _score_from_counts(buys=0, sells=0)
    assert score == 0
    assert label == "neutral"


def test_label_from_score_thresholds():
    assert _label_from_score(0.25) == "bullish"
    assert _label_from_score(-0.25) == "bearish"
    assert _label_from_score(0.0) == "neutral"


def test_crowd_insight_without_network():
    result = analyze_crowd_insight(
        ticker="AAPL",
        include_insider=False,
        include_news=False,
    )

    assert result["signal"]["label"] == "neutral"
    assert result["components"]["insider"]["available"] is False
    assert result["components"]["news"]["available"] is False
