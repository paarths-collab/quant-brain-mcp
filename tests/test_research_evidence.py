import asyncio
import io
import json
import socket
from types import SimpleNamespace

import pytest

from core import research_evidence as sources


@pytest.mark.parametrize("url", [
    "https://www.tcs.com/results.pdf", "https://nsearchives.nseindia.com/results.pdf",
    "https://www.sec.gov/Archives/report.html",
])
def test_official_allowlist(url):
    assert sources.allowed_url(url)


@pytest.mark.parametrize("url", [
    "http://tcs.com/results", "https://tcs.com.attacker.test/a", "https://127.0.0.1/a",
    "https://user:password@tcs.com/a", "https://tcs.com:8000/a", "file:///etc/passwd",
    "https://169.254.169.254/latest/meta-data/", "https://example.com/report.pdf",
])
def test_untrusted_urls_never_reach_network(monkeypatch, url):
    monkeypatch.setattr(sources, "public_addresses", lambda _: pytest.fail("DNS must not run"))
    assert sources.fetch_source(url)["status"] == "not_attempted"


@pytest.mark.parametrize("address", ["127.0.0.1", "10.0.0.1", "169.254.169.254", "::1", "::ffff:127.0.0.1"])
def test_dns_rejects_private_and_mapped_addresses(monkeypatch, address):
    monkeypatch.setattr(sources.subprocess, "run", lambda *a, **k: SimpleNamespace(stdout=json.dumps([
        [socket.AF_INET, socket.SOCK_STREAM, 6, "", [address, 443]],
    ])))
    with pytest.raises(ValueError, match="non-public"):
        sources.public_addresses("www.tcs.com")


class Response:
    def __init__(self, status=200, headers=None, body=b"<p>Revenue result</p>"):
        self.status = status
        self.headers = headers or {"Content-Type": "text/html"}
        self.body = io.BytesIO(body)

    def getheader(self, name, default=None):
        return self.headers.get(name, default)

    def read1(self, size):
        return self.body.read(size)


def setup_fetch(monkeypatch, responses):
    calls = []
    monkeypatch.setattr(sources, "public_addresses", lambda _: [(2, 1, 6, "", ("93.184.216.34", 443))])
    class Connection:
        sock = None
        def __init__(self, *args):
            pass
        def request(self, method, target, headers):
            calls.append((method, target, headers))
        def getresponse(self):
            return responses.pop(0)
        def close(self):
            pass
    monkeypatch.setattr(sources, "_PinnedHTTPS", Connection)
    return calls


def test_text_retrieval_records_bytes_hash_and_actual_time(monkeypatch):
    calls = setup_fetch(monkeypatch, [Response()])
    result = sources.fetch_source("https://www.tcs.com/results")
    assert result["status"] == "retrieved"
    assert result["text_excerpt"] == "Revenue result"
    assert result["retrieved_at"]
    assert result["published_at"] is None
    assert len(result["sha256"]) == 64
    assert "Authorization" not in calls[0][2]


def test_redirect_private_or_unreviewed_host_blocked(monkeypatch):
    calls = setup_fetch(monkeypatch, [Response(302, {"Location": "https://127.0.0.1/secret"})])
    result = sources.fetch_source("https://www.tcs.com/results")
    assert result["status"] == "failed"
    assert "Redirect outside" in result["reason"]
    assert len(calls) == 1


def test_oversize_stream_without_length_is_rejected(monkeypatch):
    setup_fetch(monkeypatch, [Response(body=b"x" * (sources.MAX_BYTES + 1))])
    assert "2 MiB" in sources.fetch_source("https://tcs.com/results")["reason"]


def test_html_ignores_scripts_and_bounds_text():
    text, truncated = sources.extract_text(b"<script>evil()</script><p>Revenue</p>", "text/html")
    assert text == "Revenue"
    assert not truncated
    assert sources.extract_text(b"a" * 20000, "text/plain")[1]


def test_fetch_cache_and_total_budget(monkeypatch):
    calls = []
    def fetch(url):
        calls.append(url)
        return {"status": "retrieved", "url": url}
    monkeypatch.setattr(sources, "bounded_fetch_source", fetch)
    evidence = [SimpleNamespace(id=str(i), source_type="filing", url=f"https://tcs.com/{i}") for i in range(8)]
    cache = {}
    first = asyncio.run(sources.retrieve_sources(evidence, cache))
    second = asyncio.run(sources.retrieve_sources(evidence, cache))
    assert len(calls) == sources.MAX_SOURCES
    assert first == second
    assert first["7"]["status"] == "not_attempted"


def test_pdf_extracts_text_in_limited_subprocess():
    from pypdf import PdfWriter
    from pypdf.generic import DictionaryObject, NameObject, DecodedStreamObject
    writer = PdfWriter()
    page = writer.add_blank_page(width=300, height=300)
    font = DictionaryObject({NameObject("/Type"): NameObject("/Font"), NameObject("/Subtype"): NameObject("/Type1"), NameObject("/BaseFont"): NameObject("/Helvetica")})
    page[NameObject("/Resources")] = DictionaryObject({NameObject("/Font"): DictionaryObject({NameObject("/F1"): writer._add_object(font)})})
    stream = DecodedStreamObject()
    stream.set_data(b"BT /F1 12 Tf 20 100 Td (Reported revenue) Tj ET")
    page[NameObject("/Contents")] = writer._add_object(stream)
    data = io.BytesIO()
    writer.write(data)
    text, truncated = sources.extract_text(data.getvalue(), "application/pdf")
    assert "Reported revenue" in text
    assert not truncated


def test_pdf_timeout_is_bounded(monkeypatch):
    def timeout(*args, **kwargs):
        assert kwargs["timeout"] == 10
        raise sources.subprocess.TimeoutExpired("pdf", 10)
    monkeypatch.setattr(sources.subprocess, "run", timeout)
    with pytest.raises(sources.subprocess.TimeoutExpired):
        sources.extract_text(b"%PDF-bad", "application/pdf")


def test_tls_connects_pinned_address_but_verifies_original_hostname(monkeypatch):
    events = []
    class Sock:
        def settimeout(self, value):
            events.append(("timeout", value))
        def connect(self, address):
            events.append(("connect", address))
        def close(self):
            pass
    class Context:
        def wrap_socket(self, sock, server_hostname):
            events.append(("tls_hostname", server_hostname))
            return sock
    monkeypatch.setattr(sources.socket, "socket", lambda *a: Sock())
    connection = sources._PinnedHTTPS("www.tcs.com", (2, 1, 6, "", ["93.184.216.34", 443]), 5)
    connection._context = Context()
    connection.connect()
    assert ("connect", ("93.184.216.34", 443)) in events
    assert ("tls_hostname", "www.tcs.com") in events


def test_subprocess_does_not_inherit_credentials(monkeypatch):
    monkeypatch.setenv("QUANT_INTERNAL_TOKEN", "private-test-value")
    def run(*args, **kwargs):
        assert kwargs["env"] == {"LANG": "C.UTF-8"}
        return SimpleNamespace(stdout=b'{"text": "report", "truncated": false}')
    monkeypatch.setattr(sources.subprocess, "run", run)
    assert sources.extract_text(b"%PDF-fake", "application/pdf") == ("report", False)


def test_source_worker_has_hard_deadline_and_no_credentials(monkeypatch):
    def timeout(*args, **kwargs):
        assert kwargs["timeout"] == 26
        assert kwargs["env"] == {"LANG": "C.UTF-8"}
        raise sources.subprocess.TimeoutExpired("source", 26)
    monkeypatch.setattr(sources.subprocess, "run", timeout)
    result = sources.bounded_fetch_source("https://www.tcs.com/results")
    assert result["status"] == "failed"
    assert "TimeoutExpired" in result["reason"]


@pytest.mark.parametrize("html,expected", [
    ('<meta property="article:published_time" content="2026-10-16T17:00:00Z">', '2026-10-16T17:00:00+00:00'),
    ('<meta itemprop="datePublished" content="2026-10-16">', '2026-10-16'),
    ('<script type="application/ld+json">{"@type":"NewsArticle","datePublished":"2026-10-16T11:00:00+05:30"}</script>', '2026-10-16T11:00:00+05:30'),
    ('<script type="application/ld+json">{"@graph":[{"@type":"Article","datePublished":"2030-01-01"}]}</script>', '2030-01-01'),
])
def test_explicit_publisher_dates_are_preserved_without_inventing_times(html, expected):
    assert sources.publication_metadata(html.encode(), "text/html") == (expected, "publisher_metadata")


@pytest.mark.parametrize("html", [
    '<meta name="date" content="2026-10-16">',
    '<meta property="article:modified_time" content="2026-10-16T17:00:00Z">',
    '<meta property="article:published_time" content="2026-99-50">',
    '<meta property="article:published_time" content="yesterday">',
    '<script type="application/ld+json">not-json</script>',
    '<script type="application/ld+json">{"@type":"Article","comments":[{"datePublished":"2026-10-16"}]}</script>',
    '<p>Accessed 2026-10-16. Report URL /2026/10/16/.</p>',
])
def test_ambiguous_or_malformed_dates_remain_unknown(html):
    assert sources.publication_metadata(html.encode(), "text/html") == (None, "not_extracted")


def test_conflicting_explicit_dates_do_not_choose_arbitrarily():
    html = b'<meta property="article:published_time" content="2026-10-16"><meta itemprop="datePublished" content="2026-10-15">'
    assert sources.publication_metadata(html, "text/html") == (None, "conflicting_publisher_metadata")


def test_fetch_records_publisher_date_separately_from_actual_retrieval(monkeypatch):
    setup_fetch(monkeypatch, [Response(body=b'<meta property="article:published_time" content="2025-04-01"><p>Result</p>')])
    result = sources.fetch_source("https://www.tcs.com/results")
    assert result["published_at"] == "2025-04-01"
    assert result["publication_date_basis"] == "publisher_metadata"
    assert result["retrieved_at"] != result["published_at"]
