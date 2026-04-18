from fastmcp_server import mcp

# Use FastMCP's Starlette app directly so lifespan initializes session manager.
app = mcp.streamable_http_app()
