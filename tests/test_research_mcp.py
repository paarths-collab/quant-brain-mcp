import asyncio

from core.http_security import authenticated_owner


def test_internal_surface_excludes_research_and_mutations():
    from internal_app import internal_mcp
    from core.research_tools import ALLOWED_TOOLS
    tools = asyncio.run(internal_mcp.list_tools())
    names = {t.name for t in tools}
    assert all(t.annotations.readOnlyHint is True for t in tools)
    assert all(t.annotations.destructiveHint is False for t in tools)
    assert names == set(ALLOWED_TOOLS)
    assert 'start_research' not in names
    assert 'price_alert' not in names


def test_research_requires_authenticated_owner():
    import fastmcp_server as server
    assert 'error' in server.start_research('Analyze', ['TCS.NS'])
    assert 'error' in server.get_research_report('not-a-job')


def test_mcp_research_passes_trusted_identity(monkeypatch):
    import fastmcp_server as server
    from core import research_service
    captured = {}
    class Service:
        def start(self, owner, **kwargs):
            captured.update(owner=owner, **kwargs)
            return {'id': 'example', 'status': 'queued'}
    monkeypatch.setattr(research_service, 'get_research_service', lambda: Service())
    async def run():
        token = authenticated_owner.set('test-owner')
        try:
            await server.mcp.call_tool('start_research', {'question': 'Analyze TCS', 'tickers': ['TCS.NS']})
        finally:
            authenticated_owner.reset(token)
    asyncio.run(run())
    assert captured['owner'] == 'test-owner'
    assert captured['tickers'] == ['TCS.NS']


def test_research_not_enabled_by_default(monkeypatch):
    from core.research_service import get_research_service
    import pytest
    monkeypatch.delenv('QUANT_RESEARCH_ENABLED', raising=False)
    with pytest.raises(ValueError, match='disabled'):
        get_research_service()
