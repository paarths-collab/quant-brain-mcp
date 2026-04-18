from starlette.applications import Starlette
from starlette.responses import JSONResponse
from starlette.routing import Mount, Route

from fastmcp_server import mcp


async def health(_request):
    return JSONResponse({"status": "ok"})


# Reuse the FastMCP streamable HTTP ASGI app so /mcp works unchanged.
mcp_app = mcp.streamable_http_app()

app = Starlette(
    routes=[
        Route("/health", health),
        Mount("/", mcp_app),
    ]
)
