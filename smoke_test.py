"""Offline release smoke test. Requires Chrome/Chromium for real PNG export.

Run: python smoke_test.py
Failures intentionally propagate to a nonzero exit status for CI/deploy checks.
"""
import asyncio
import base64

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from starlette.testclient import TestClient

from fastmcp_server import _image_contents_from_chart_pack, mcp
from tools.intelligence.plotly_dashboard import _to_plotly_json


async def check_tools():
    tools = await mcp.list_tools()
    names = {tool.name for tool in tools}
    required = {"generate_optimized_verdict", "analyze_momentum", "get_quote",
                "price_alert", "generate_charts"}
    assert required <= names, f"Missing tools: {required - names}"
    assert len(names) == len(tools), "Duplicate tool names"
    print(f"PASS: {len(tools)} MCP tools registered")


def run_test():
    asyncio.run(check_tools())
    with TestClient(mcp.streamable_http_app()) as client:
        response = client.get("/health")
        assert response.status_code == 200, response.text
    print("PASS: HTTP health and application lifespan")
    charts = {
        "timeseries": _to_plotly_json(go.Figure(go.Scatter(
            x=pd.date_range("2026-01-01", periods=3), y=np.array([2., 1., 4.])))),
        "allocation": _to_plotly_json(go.Figure(go.Bar(
            x=np.array(["Asset A", "Asset B"]), y=np.array([0.4, 0.6])))),
    }
    contents = _image_contents_from_chart_pack({"charts": charts})
    images = [item for item in contents if item.type == "image"]
    assert len(images) == len(charts), f"PNG rendering failed: {contents}"
    png = base64.b64decode(images[0].data, validate=True)
    assert png.startswith(b"\x89PNG\r\n\x1a\n"), "Invalid PNG payload"
    print(f"PASS: real MCP chart image export ({len(png)} bytes)")


if __name__ == "__main__":
    run_test()
