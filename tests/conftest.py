import socket

import pytest

_LOOPBACK = {"127.0.0.1", "::1", "localhost"}


@pytest.fixture
def no_live_network(monkeypatch):
    """Fail loudly if a test tries to reach anything but loopback or a unix socket.

    Also stubs the repo's own market-data and source-fetch entry points, because
    those would otherwise spawn subprocesses that this guard cannot see.
    """
    real_connect = socket.socket.connect
    real_getaddrinfo = socket.getaddrinfo

    def connect(self, address):
        if self.family == socket.AF_UNIX or (isinstance(address, tuple) and address[0] in _LOOPBACK):
            return real_connect(self, address)
        raise AssertionError(f"live network call attempted in a test: {address!r}")

    def getaddrinfo(host, *args, **kwargs):
        if host in _LOOPBACK or host is None:
            return real_getaddrinfo(host, *args, **kwargs)
        raise AssertionError(f"live DNS lookup attempted in a test: {host!r}")

    def forbidden(*args, **kwargs):
        raise AssertionError("live market-data or source fetch attempted in a test")

    monkeypatch.setattr(socket.socket, "connect", connect)
    monkeypatch.setattr(socket, "getaddrinfo", getaddrinfo)
    monkeypatch.setattr("core.data_loader.fetch_stock_data", forbidden)
    monkeypatch.setattr("core.research_evidence.bounded_fetch_source", forbidden)
