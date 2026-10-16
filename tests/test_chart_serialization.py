"""Regression: chart payload arrays must survive JSON transport, not become strings."""
import json

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import pytest

from tools.intelligence.plotly_dashboard import _to_plotly_json


@pytest.mark.parametrize("figure", [
    go.Figure(go.Scatter(x=pd.date_range("2026-01-01", periods=3), y=np.array([1., 2., 3.]))),
    go.Figure(go.Bar(x=np.array(["Asset A", "Asset B"]), y=np.array([0.4, 0.6]))),
    go.Figure(go.Heatmap(x=np.array(["A", "B"]), y=np.array(["A", "B"]), z=np.array([[1., .5], [.5, 1.]]))),
])
def test_figure_payload_round_trips_arrays(figure):
    payload = _to_plotly_json(figure)
    # Standard JSON transport followed by reconstruction is the MCP image path.
    restored = go.Figure(json.loads(json.dumps(payload)))
    assert json.loads(restored.to_json()) == json.loads(figure.to_json())
    assert not isinstance(payload["data"][0]["x"], str)
    assert not isinstance(payload["data"][0]["y"], str)
