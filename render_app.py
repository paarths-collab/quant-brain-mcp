from fastmcp_server import mcp
from core.http_security import SecureMCPMiddleware
from core.research_service import ResearchLifecycle

# Preserve the FastMCP lifespan while authenticating all hosted MCP traffic.
app = ResearchLifecycle(SecureMCPMiddleware(mcp.streamable_http_app()))
