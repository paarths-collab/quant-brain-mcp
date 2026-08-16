"""Tests for the sector composite score.

The previous formula used `-dist_from_high` as its momentum term. That value is
non-negative by construction, so sectors trading further BELOW their 52-week
high scored higher -- inverting the signal at the largest weight (0.35). Raw
units also went unscaled, so momentum (~±40) swamped risk_adjusted (~±2).
"""

from tools.strategies.sector_pipeline import _apply_composite_scores, _zscores


def _sector(name, risk_adjusted, momentum, drawdown):
    return {
        "sector": name,
        "_risk_adjusted_raw": risk_adjusted,
        "_momentum_raw": momentum,
        "_drawdown_raw": drawdown,
    }


def _ranked(analytics):
    _apply_composite_scores(analytics)
    return [a["sector"] for a in sorted(analytics, key=lambda x: x["composite_score"], reverse=True)]


def test_zscores_standardize():
    z = _zscores([1.0, 2.0, 3.0])
    assert abs(sum(z)) < 1e-9
    assert z[0] < z[1] < z[2]


def test_zscores_handle_no_spread():
    assert _zscores([5.0, 5.0, 5.0]) == [0.0, 0.0, 0.0]


def test_zscores_handle_empty_and_nonfinite():
    assert _zscores([]) == []
    z = _zscores([float("inf"), 1.0, 2.0])
    assert all(isinstance(v, float) for v in z)


def test_better_sector_outranks_worse():
    """Higher return, better risk-adjusted, shallower drawdown must win."""
    analytics = [
        _sector("Good", risk_adjusted=1.4, momentum=19.4, drawdown=7.5),
        _sector("Bad", risk_adjusted=-0.4, momentum=-10.0, drawdown=34.7),
    ]
    assert _ranked(analytics)[0] == "Good"


def test_regression_pharma_beats_it_services():
    """Real values from a live run that the old formula ranked backwards.

    Old formula scored IT Services 1.799 (2nd) and Pharma -0.001 (near last),
    despite Pharma having +19.38% return vs IT's -9.98%.
    """
    analytics = [
        _sector("Metals", risk_adjusted=1.548, momentum=34.95, drawdown=12.94),
        _sector("IT Services", risk_adjusted=-0.393, momentum=-9.98, drawdown=34.74),
        _sector("FMCG", risk_adjusted=-0.738, momentum=-10.81, drawdown=20.25),
        _sector("Energy", risk_adjusted=0.862, momentum=13.95, drawdown=9.18),
        _sector("Pharma", risk_adjusted=1.407, momentum=19.38, drawdown=7.46),
        _sector("Automobiles", risk_adjusted=0.566, momentum=12.36, drawdown=17.82),
        _sector("Private Banks", risk_adjusted=0.231, momentum=3.88, drawdown=18.32),
        _sector("Realty", risk_adjusted=0.169, momentum=4.47, drawdown=32.78),
    ]
    ranking = _ranked(analytics)

    assert ranking.index("Pharma") < ranking.index("IT Services")
    assert ranking[0] in {"Metals", "Pharma"}
    assert ranking[-1] in {"FMCG", "IT Services", "Realty"}


def test_deep_drawdown_is_penalized_not_rewarded():
    """Two sectors identical except drawdown: the shallower one must win."""
    analytics = [
        _sector("Shallow", risk_adjusted=1.0, momentum=10.0, drawdown=5.0),
        _sector("Deep", risk_adjusted=1.0, momentum=10.0, drawdown=40.0),
    ]
    assert _ranked(analytics)[0] == "Shallow"


def test_components_exposed_and_raw_keys_removed():
    analytics = [
        _sector("A", 1.0, 10.0, 5.0),
        _sector("B", 0.5, 5.0, 9.0),
    ]
    _apply_composite_scores(analytics)
    for item in analytics:
        assert set(item["score_components"]) == {"risk_adjusted_z", "momentum_z", "drawdown_z"}
        assert not any(k.startswith("_") for k in item)


def test_single_sector_does_not_crash():
    analytics = [_sector("Only", 1.0, 10.0, 5.0)]
    _apply_composite_scores(analytics)
    assert analytics[0]["composite_score"] == 0.0


def test_empty_is_safe():
    analytics = []
    _apply_composite_scores(analytics)
    assert analytics == []
