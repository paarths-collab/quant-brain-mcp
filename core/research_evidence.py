"""Bounded public-source retrieval. Retrieved text is evidence, never instructions.

Only reviewed official hosts are fetched. DNS is checked and the TLS socket is
connected to that exact public address, preventing DNS-rebinding and redirect SSRF.
No credentials, cookies, environment proxies or browser sessions are forwarded.
"""
from __future__ import annotations

import asyncio
import hashlib
import http.client
import ipaddress
import json
import socket
import ssl
import subprocess
import sys
import time
from datetime import date, datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urljoin, urlsplit

OFFICIAL_DOMAINS = (
    "nseindia.com", "bseindia.com", "sebi.gov.in", "rbi.org.in",
    "tcs.com", "infosys.com", "ril.com", "sec.gov",
)
MAX_BYTES = 2 * 1024 * 1024
MAX_TEXT = 16000
MAX_SOURCES = 6
FETCH_SECONDS = 12


def allowed_url(url: str) -> bool:
    try:
        parts = urlsplit(url)
        host = (parts.hostname or "").lower()
        return (parts.scheme == "https" and parts.port in (None, 443)
                and not parts.username and not parts.password
                and any(host == d or host.endswith("." + d) for d in OFFICIAL_DOMAINS))
    except ValueError:
        return False


def public_addresses(host: str) -> list[tuple]:
    # libc DNS resolution is not bounded by a socket timeout. Resolve in a
    # short-lived subprocess so a broken resolver cannot retain worker threads.
    result = subprocess.run(
        [sys.executable, "-c", "import socket,json,sys; print(json.dumps(socket.getaddrinfo(sys.argv[1],443,type=socket.SOCK_STREAM)))", host],
        capture_output=True, text=True, timeout=3, check=True, env={"LANG": "C.UTF-8"},
    )
    addresses = json.loads(result.stdout)
    if not addresses or any(not ipaddress.ip_address(a[4][0]).is_global for a in addresses):
        raise ValueError("Source DNS includes a non-public address")
    return addresses


class _PinnedHTTPS(http.client.HTTPSConnection):
    def __init__(self, host, address, timeout):
        super().__init__(host, timeout=timeout, context=ssl.create_default_context())
        self.address = address

    def connect(self):
        family, socktype, proto, _, sockaddr = self.address
        sock = socket.socket(family, socktype, proto)
        try:
            sock.settimeout(self.timeout)
            sock.connect(tuple(sockaddr))
            self.sock = self._context.wrap_socket(sock, server_hostname=self.host)
        except BaseException:
            sock.close()
            raise


class _Text(HTMLParser):
    def __init__(self):
        super().__init__()
        self.hidden = 0
        self.parts = []

    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style", "noscript"):
            self.hidden += 1

    def handle_endtag(self, tag):
        if tag in ("script", "style", "noscript"):
            self.hidden = max(0, self.hidden - 1)

    def handle_data(self, data):
        if not self.hidden and data.strip():
            self.parts.append(data.strip())



class _PublicationMetadata(HTMLParser):
    def __init__(self):
        super().__init__()
        self.dates = []
        self.jsonld = []
        self.current = None

    def handle_starttag(self, tag, attrs):
        attrs = {key.lower(): value for key, value in attrs}
        if tag == "meta":
            kind = attrs.get("property") or attrs.get("itemprop") or attrs.get("name") or ""
            if kind.lower() in ("article:published_time", "datepublished"):
                self.dates.append(attrs.get("content"))
        if tag == "script" and (attrs.get("type") or "").lower() == "application/ld+json":
            self.current = []

    def handle_data(self, data):
        if self.current is not None:
            self.current.append(data)

    def handle_endtag(self, tag):
        if tag == "script" and self.current is not None:
            self.jsonld.append("".join(self.current))
            self.current = None


def publication_metadata(body: bytes, content_type: str) -> tuple[str | None, str]:
    """Extract publisher-declared dates; never infer dates or verify their truth."""
    if "html" not in content_type or body.startswith(b"%PDF-"):
        return None, "not_extracted"
    parser = _PublicationMetadata()
    parser.feed(body.decode("utf-8", errors="replace"))
    candidates = list(parser.dates)
    if not candidates:
        allowed_types = {"Article", "NewsArticle", "Report", "WebPage", "BlogPosting", "ScholarlyArticle"}
        for raw in parser.jsonld:
            try:
                obj = json.loads(raw)
            except (ValueError, RecursionError):
                continue
            nodes = obj if isinstance(obj, list) else [obj]
            for node in nodes:
                if not isinstance(node, dict):
                    continue
                # Root publication metadata or explicit publication nodes in @graph;
                # do not adopt nested comment/review dates as the article date.
                if "datePublished" in node:
                    candidates.append(node["datePublished"])
                graph = node.get("@graph", [])
                if isinstance(graph, list):
                    for item in graph:
                        if not isinstance(item, dict):
                            continue
                        types = item.get("@type", [])
                        types = [types] if isinstance(types, str) else types
                        if isinstance(types, list) and any(t in allowed_types for t in types if isinstance(t, str)):
                            candidates.append(item.get("datePublished"))
    valid = set()
    for value in candidates:
        if not isinstance(value, str):
            continue
        value = value.strip()
        try:
            if len(value) == 10:
                normalized = date.fromisoformat(value).isoformat()
            elif len(value) >= 19 and value[10] == "T":
                normalized = datetime.fromisoformat(value.replace("Z", "+00:00")).isoformat()
            else:
                continue
            valid.add(normalized)
        except ValueError:
            continue
    if len(valid) == 1:
        return valid.pop(), "publisher_metadata"
    return None, "conflicting_publisher_metadata" if len(valid) > 1 else "not_extracted"


def extract_text(body: bytes, content_type: str) -> tuple[str, bool]:
    if body.startswith(b"%PDF-") or "application/pdf" in content_type:
        # Parsing untrusted PDFs happens in a disposable process with time/CPU and
        # address-space limits, not on the server event loop. No PDF actions run.
        code = '''import sys, json, io, resource
# Linux VPS: cap address space. macOS does not reliably enforce RLIMIT_AS.
if sys.platform.startswith("linux"):
    resource.setrlimit(resource.RLIMIT_AS, (512 * 1024 * 1024, 512 * 1024 * 1024))
resource.setrlimit(resource.RLIMIT_CPU, (8, resource.getrlimit(resource.RLIMIT_CPU)[1]))
from pypdf import PdfReader
reader = PdfReader(io.BytesIO(sys.stdin.buffer.read()), strict=False)
parts = []
for page in reader.pages[:20]:
    parts.append(page.extract_text() or "")
    if sum(map(len, parts)) > 16000:
        break
text = "\\n".join(parts)
print(json.dumps({"text": text[:16000], "truncated": len(reader.pages) > len(parts) or len(text) > 16000}))
'''
        result = subprocess.run([sys.executable, "-c", code], input=body,
                                capture_output=True, timeout=10, check=True, env={"LANG": "C.UTF-8"})
        parsed = json.loads(result.stdout)
        return parsed["text"], parsed["truncated"]
    if "html" in content_type:
        parser = _Text()
        parser.feed(body.decode("utf-8", errors="replace"))
        text = "\n".join(parser.parts)
    elif content_type.startswith("text/plain"):
        text = body.decode("utf-8", errors="replace")
    else:
        raise ValueError("Unsupported source content type")
    return text[:MAX_TEXT], len(text) > MAX_TEXT


def fetch_source(url: str) -> dict:
    record = {"url": url, "status": "failed", "retrieved_at": None,
              "published_at": None, "publication_date_basis": "not_extracted"}
    if not allowed_url(url):
        return {**record, "status": "not_attempted", "reason": "Outside official HTTPS source allowlist"}
    current = url
    deadline = time.monotonic() + FETCH_SECONDS
    try:
        for _ in range(4):
            if not allowed_url(current):
                raise ValueError("Redirect outside official HTTPS source allowlist")
            parts = urlsplit(current)
            addresses = public_addresses(parts.hostname)
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise TimeoutError("Source retrieval deadline exceeded")
            connection = _PinnedHTTPS(parts.hostname, addresses[0], remaining)
            try:
                target = parts.path or "/"
                if parts.query:
                    target += "?" + parts.query
                connection.request("GET", target, headers={
                    "User-Agent": "QuantBrainResearch/1.0", "Accept": "application/pdf,text/html,text/plain",
                    "Accept-Encoding": "identity",
                })
                response = connection.getresponse()
                if response.status in (301, 302, 303, 307, 308):
                    location = response.getheader("Location")
                    if not location:
                        raise ValueError("Redirect missing location")
                    current = urljoin(current, location)
                    continue
                if response.status != 200:
                    raise ValueError(f"Source HTTP {response.status}")
                if response.getheader("Content-Encoding", "identity") != "identity":
                    raise ValueError("Compressed source response is not supported")
                length = response.getheader("Content-Length")
                if length and int(length) > MAX_BYTES:
                    raise ValueError("Source exceeds 2 MiB limit")
                chunks = []
                size = 0
                while True:
                    remaining = deadline - time.monotonic()
                    if remaining <= 0:
                        raise TimeoutError("Source retrieval deadline exceeded")
                    if connection.sock:
                        connection.sock.settimeout(remaining)
                    chunk = response.read1(min(65536, MAX_BYTES + 1 - size))
                    if not chunk:
                        break
                    chunks.append(chunk)
                    size += len(chunk)
                    if size > MAX_BYTES:
                        raise ValueError("Source exceeds 2 MiB limit")
                body = b"".join(chunks)
                content_type = response.getheader("Content-Type", "").lower()
                text, truncated = extract_text(body, content_type)
                published_at, publication_basis = publication_metadata(body, content_type)
                if not text.strip():
                    raise ValueError("No extractable source text (OCR is not supported)")
                return {**record, "status": "retrieved", "final_url": current,
                        "retrieved_at": datetime.now(timezone.utc).isoformat(),
                        "published_at": published_at, "publication_date_basis": publication_basis,
                        "sha256": hashlib.sha256(body).hexdigest(), "bytes": len(body),
                        "text_excerpt": text, "truncated": truncated,
                        "scope": "Document retrieved; claim support is not independently verified"}
            finally:
                connection.close()
        raise ValueError("Too many source redirects")
    except Exception as exc:
        # No raw response content, request headers, exception URLs or credentials.
        reason = str(exc) if isinstance(exc, (ValueError, TimeoutError)) else type(exc).__name__
        return {**record, "reason": reason[:300]}


def bounded_fetch_source(url: str) -> dict:
    """Hard wall-clock bound also covers slow response headers and TLS peers."""
    if not allowed_url(url):
        return fetch_source(url)
    code = "import json,sys; sys.path.insert(0,sys.argv[1]); from core.research_evidence import fetch_source; print(json.dumps(fetch_source(sys.argv[2])))"
    try:
        result = subprocess.run(
            [sys.executable, "-c", code, str(Path(__file__).resolve().parent.parent), url],
            capture_output=True, text=True, timeout=26, check=True,
            env={"LANG": "C.UTF-8"},
        )
        return json.loads(result.stdout)
    except Exception as exc:
        return {"url": url, "status": "failed", "retrieved_at": None,
                "published_at": None, "reason": "Bounded source worker failed: " + type(exc).__name__}


async def retrieve_sources(evidence, cache: dict[str, dict]) -> dict[str, dict]:
    selected = [e for e in evidence if e.source_type in ("filing", "company", "official")]
    semaphore = asyncio.Semaphore(2)
    async def retrieve(url):
        async with semaphore:
            cache[url] = await asyncio.to_thread(bounded_fetch_source, url)
    pending = []
    for e in selected:
        url = str(e.url)
        if url in cache:
            continue
        if not allowed_url(url):
            cache[url] = {"url": url, "status": "not_attempted", "reason": "Outside official HTTPS source allowlist"}
        elif sum(allowed_url(u) for u in cache) + len(pending) >= MAX_SOURCES:
            cache[url] = {"url": url, "status": "not_attempted", "reason": "Per-job source retrieval limit reached"}
        elif url not in pending:
            pending.append(url)
    await asyncio.gather(*(retrieve(url) for url in pending))
    return {e.id: cache[str(e.url)] for e in selected}


def source_coverage(evidence, retrievals: dict[str, dict]) -> dict:
    """Retrieval coverage over web evidence, with failures and gaps in the denominator.

    ``coverage`` is retrieved / total web sources. A source that failed, was
    never attempted (outside the allowlist, over the per-job limit, or a type
    the server does not fetch) or has no retrieval record at all still counts in
    the total, so it lowers coverage instead of vanishing from it.
    ``attempt_success_rate`` is retrieved / attempted (retrieved + failed).
    Either ratio is None, never 1.0, when its denominator is empty. Tool URNs
    are not retrievable documents and are excluded.
    """
    web = [e for e in evidence if str(e.url).startswith(("http://", "https://"))]
    statuses = [(retrievals.get(e.id) or {}).get("status", "not_attempted") for e in web]
    retrieved = statuses.count("retrieved")
    failed = statuses.count("failed")
    attempted = retrieved + failed
    total = len(web)
    return {
        "total": total,
        "attempted": attempted,
        "retrieved": retrieved,
        "failed": failed,
        "not_attempted": total - attempted,
        "coverage": round(retrieved / total, 4) if total else None,
        "attempt_success_rate": round(retrieved / attempted, 4) if attempted else None,
    }
