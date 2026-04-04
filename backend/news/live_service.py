from __future__ import annotations

import json
import re
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.parse import urljoin, urlparse
import xml.etree.ElementTree as ET

import httpx
try:
    from bs4 import BeautifulSoup  # type: ignore
except Exception:
    BeautifulSoup = None

try:
    from playwright.sync_api import sync_playwright  # type: ignore
except Exception:
    sync_playwright = None


@dataclass
class LiveNewsSource:
    source_id: str
    name: str
    mode: str
    url: str
    seed_urls: List[str]
    max_pages: int
    shard: int
    is_live: bool
    trust_tier: int


class LiveNewsService:
    """Live scraper for RSS and HTML news sources configured in backend/data/live_news_sources.json."""

    _CACHE_TTL_SECONDS = 900
    _BASE_CACHE_KEY = "__all_sources_snapshot__"

    def __init__(self) -> None:
        data_path = Path(__file__).parent.parent / "data" / "live_news_sources.json"
        self._sources: List[LiveNewsSource] = self._load_sources(data_path)
        self._cache: Dict[str, Dict[str, Any]] = {}
        self._summary_cache: Dict[str, Dict[str, Any]] = {}

    def _load_sources(self, path: Path) -> List[LiveNewsSource]:
        if not path.exists():
            return []

        raw = json.loads(path.read_text(encoding="utf-8"))
        out: List[LiveNewsSource] = []
        for item in raw:
            if not isinstance(item, dict):
                continue
            out.append(
                LiveNewsSource(
                    source_id=str(item.get("source_id") or ""),
                    name=str(item.get("name") or "Unknown"),
                    mode=str(item.get("mode") or "rss").lower(),
                    url=str(item.get("url") or ""),
                    seed_urls=[str(u) for u in (item.get("seed_urls") or []) if str(u).strip()],
                    max_pages=int(item.get("max_pages") or 2),
                    shard=int(item.get("shard") or 0),
                    is_live=bool(item.get("is_live", True)),
                    trust_tier=int(item.get("trust_tier") or 1),
                )
            )
        return [s for s in out if s.url and s.is_live]

    def _http_get(self, client: httpx.Client, url: str) -> Optional[str]:
        try:
            r = client.get(url, follow_redirects=True)
            if r.status_code >= 400:
                return None
            return r.text
        except Exception:
            return None

    def _http_get_playwright(self, url: str, timeout_ms: int = 12000) -> Optional[str]:
        if sync_playwright is None:
            return None
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                context = browser.new_context(
                    user_agent=(
                        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
                    )
                )
                page = context.new_page()
                page.goto(url, wait_until="domcontentloaded", timeout=timeout_ms)
                page.wait_for_timeout(1200)
                html = page.content()
                context.close()
                browser.close()
                return html
        except Exception:
            return None

    def _parse_rss(self, source: LiveNewsSource, text: str) -> List[Dict[str, Any]]:
        items: List[Dict[str, Any]] = []
        try:
            root = ET.fromstring(text)
        except Exception:
            return items

        rss_items = root.findall(".//item")
        if rss_items:
            for item in rss_items[:25]:
                title = (item.findtext("title") or "").strip()
                link = (item.findtext("link") or "").strip()
                pub = (item.findtext("pubDate") or item.findtext("date") or "").strip()
                desc = (item.findtext("description") or "").strip()
                if not title or not link:
                    continue
                items.append({
                    "source": source.name,
                    "source_id": source.source_id,
                    "title": re.sub(r"\s+", " ", title),
                    "url": link,
                    "date": pub,
                    "summary": re.sub(r"<[^>]+>", "", desc)[:280],
                    "mode": "rss",
                })
            return items

        # Atom fallback
        ns = {"a": "http://www.w3.org/2005/Atom"}
        entries = root.findall(".//a:entry", ns) if root is not None else []
        for entry in entries[:25]:
            title = (entry.findtext("a:title", default="", namespaces=ns) or "").strip()
            link_el = entry.find("a:link", ns)
            link = (link_el.attrib.get("href") if link_el is not None else "") or ""
            pub = (
                entry.findtext("a:published", default="", namespaces=ns)
                or entry.findtext("a:updated", default="", namespaces=ns)
            ).strip()
            summary = (entry.findtext("a:summary", default="", namespaces=ns) or "").strip()
            if not title or not link:
                continue
            items.append({
                "source": source.name,
                "source_id": source.source_id,
                "title": re.sub(r"\s+", " ", title),
                "url": link,
                "date": pub,
                "summary": re.sub(r"<[^>]+>", "", summary)[:280],
                "mode": "rss",
            })
        return items

    def _valid_headline(self, title: str, href: str, base_domain: str) -> bool:
        t = (title or "").strip()
        if len(t) < 30:
            return False
        if any(x in t.lower() for x in ["subscribe", "sign in", "advert", "cookie", "privacy policy"]):
            return False
        if not href or href.startswith("#"):
            return False
        if href.startswith("javascript:") or href.startswith("mailto:"):
            return False
        if href.startswith("/"):
            return True
        if href.startswith("http"):
            return base_domain in href
        return False

    def _parse_html(self, source: LiveNewsSource, html: str, base_url: str) -> List[Dict[str, Any]]:
        if BeautifulSoup is None:
            return self._parse_html_fallback(source, html, base_url)

        soup = BeautifulSoup(html, "html.parser")
        base_domain = urlparse(base_url).netloc
        out: List[Dict[str, Any]] = []

        # Try high-signal heading anchors first.
        selectors = [
            "article a[href]",
            "h1 a[href]",
            "h2 a[href]",
            "h3 a[href]",
            "a[href]",
        ]

        seen = set()
        for sel in selectors:
            for a in soup.select(sel):
                title = re.sub(r"\s+", " ", a.get_text(" ", strip=True) or "")
                href = (a.get("href") or "").strip()
                if not self._valid_headline(title, href, base_domain):
                    continue
                link = urljoin(base_url, href)
                key = (title.lower(), link)
                if key in seen:
                    continue
                seen.add(key)
                out.append(
                    {
                        "source": source.name,
                        "source_id": source.source_id,
                        "title": title,
                        "url": link,
                        "date": "",
                        "summary": "",
                        "mode": "html",
                    }
                )
                if len(out) >= 25:
                    return out
        return out

    def _parse_html_fallback(self, source: LiveNewsSource, html: str, base_url: str) -> List[Dict[str, Any]]:
        base_domain = urlparse(base_url).netloc
        out: List[Dict[str, Any]] = []
        seen = set()

        for m in re.finditer(r'<a[^>]+href=["\']([^"\']+)["\'][^>]*>(.*?)</a>', html, flags=re.IGNORECASE | re.DOTALL):
            href = (m.group(1) or "").strip()
            inner = re.sub(r"<[^>]+>", " ", (m.group(2) or ""))
            title = re.sub(r"\s+", " ", inner).strip()
            if not self._valid_headline(title, href, base_domain):
                continue
            link = urljoin(base_url, href)
            key = (title.lower(), link)
            if key in seen:
                continue
            seen.add(key)
            out.append(
                {
                    "source": source.name,
                    "source_id": source.source_id,
                    "title": title,
                    "url": link,
                    "date": "",
                    "summary": "",
                    "mode": "html",
                }
            )
            if len(out) >= 25:
                break
        return out

    def _filter_by_query(self, items: List[Dict[str, Any]], query: str) -> List[Dict[str, Any]]:
        q = (query or "").strip().lower()
        if not q or q == "stock market news":
            return items

        tokens = [t for t in re.findall(r"[a-zA-Z0-9]+", q) if len(t) > 2]
        if not tokens:
            return items

        def score(item: Dict[str, Any]) -> int:
            text = f"{item.get('title','')} {item.get('summary','')}".lower()
            return sum(1 for t in tokens if t in text)

        ranked = [(score(i), i) for i in items]
        ranked.sort(key=lambda x: x[0], reverse=True)
        filtered = [i for s, i in ranked if s > 0]
        return filtered if filtered else items

    def _cached_get(self, key: str, allow_stale: bool = False) -> Optional[List[Dict[str, Any]]]:
        row = self._cache.get(key)
        if not row:
            return None
        if time.time() > row["expires"]:
            if allow_stale:
                return row["items"]
            self._cache.pop(key, None)
            return None
        return row["items"]

    def _cached_set(self, key: str, items: List[Dict[str, Any]]) -> None:
        self._cache[key] = {"items": items, "expires": time.time() + self._CACHE_TTL_SECONDS}

    def _summary_cached_get(self, key: str) -> Optional[Dict[str, Any]]:
        row = self._summary_cache.get(key)
        if not row:
            return None
        if time.time() > row["expires"]:
            self._summary_cache.pop(key, None)
            return None
        return row["item"]

    def _summary_cached_set(self, key: str, item: Dict[str, Any]) -> None:
        self._summary_cache[key] = {"item": item, "expires": time.time() + 600}

    def get_cached_news(self, query: str = "stock market news", limit: int = 20) -> Dict[str, Any]:
        """Return cached/stale news only. Never triggers a live scrape."""
        normalized_query = (query or "stock market news").strip().lower()
        cache_key = f"{normalized_query}|{limit}"

        cached = self._cached_get(cache_key, allow_stale=True)
        if cached is not None:
            return {
                "status": "success",
                "query": query,
                "cached": True,
                "stale": True,
                "articles": cached[:limit],
                "source_count": len({a.get('source_id') for a in cached}),
                "fetched_at": datetime.now(timezone.utc).isoformat(),
            }

        base_snapshot = self._cached_get(self._BASE_CACHE_KEY, allow_stale=True)
        if base_snapshot is not None:
            filtered = self._filter_by_query(base_snapshot, normalized_query)
            final_items = filtered[:limit]
            return {
                "status": "success",
                "query": query,
                "cached": True,
                "stale": True,
                "articles": final_items,
                "source_count": len({a.get('source_id') for a in final_items}),
                "fetched_at": datetime.now(timezone.utc).isoformat(),
            }

        return {
            "status": "success",
            "query": query,
            "cached": True,
            "stale": True,
            "articles": [],
            "source_count": 0,
            "fetched_at": datetime.now(timezone.utc).isoformat(),
        }

    def summarize_article(self, url: str, max_chars: int = 1200) -> Dict[str, Any]:
        u = (url or "").strip()
        parsed = urlparse(u)
        if parsed.scheme not in {"http", "https"}:
            return {"status": "error", "detail": "Invalid URL"}

        cache_key = f"{u}|{max_chars}"
        cached = self._summary_cached_get(cache_key)
        if cached is not None:
            return cached

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        }

        with httpx.Client(timeout=10.0, headers=headers) as client:
            html = self._http_get(client, u)
        if not html:
            return {"status": "error", "detail": "Unable to fetch article"}

        title = ""
        body_text = ""
        if BeautifulSoup is not None:
            soup = BeautifulSoup(html, "html.parser")
            title = (soup.title.get_text(" ", strip=True) if soup.title else "")
            blocks = []
            for p in soup.select("article p, main p, p"):
                txt = re.sub(r"\s+", " ", p.get_text(" ", strip=True) or "").strip()
                if len(txt) < 40:
                    continue
                if any(k in txt.lower() for k in ["cookie", "subscribe", "newsletter", "sign up", "advertisement"]):
                    continue
                blocks.append(txt)
                if len(blocks) >= 25:
                    break
            body_text = " ".join(blocks)
        else:
            title_m = re.search(r"<title>(.*?)</title>", html, flags=re.IGNORECASE | re.DOTALL)
            if title_m:
                title = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", title_m.group(1))).strip()
            para = re.findall(r"<p[^>]*>(.*?)</p>", html, flags=re.IGNORECASE | re.DOTALL)
            cleaned = []
            for p in para:
                txt = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", p)).strip()
                if len(txt) >= 40:
                    cleaned.append(txt)
                if len(cleaned) >= 25:
                    break
            body_text = " ".join(cleaned)

        body_text = re.sub(r"\s+", " ", body_text).strip()
        if not body_text:
            return {
                "status": "success",
                "url": u,
                "title": title or parsed.netloc,
                "summary": "Summary unavailable from source page content.",
                "source": parsed.netloc,
                "cached": False,
            }

        sentences = re.split(r"(?<=[.!?])\s+", body_text)
        picked: List[str] = []
        total = 0
        for s in sentences:
            ss = s.strip()
            if len(ss) < 30:
                continue
            if total + len(ss) > max_chars:
                break
            picked.append(ss)
            total += len(ss) + 1
            if len(picked) >= 6:
                break

        summary = " ".join(picked).strip() or body_text[:max_chars]
        out = {
            "status": "success",
            "url": u,
            "title": title or parsed.netloc,
            "summary": summary,
            "source": parsed.netloc,
            "cached": False,
        }
        self._summary_cached_set(cache_key, out)
        return out

    def get_news(self, query: str = "stock market news", limit: int = 20) -> Dict[str, Any]:
        normalized_query = (query or "stock market news").strip().lower()
        cache_key = f"{normalized_query}|{limit}"
        cached = self._cached_get(cache_key)
        if cached is not None:
            return {
                "status": "success",
                "query": query,
                "cached": True,
                "articles": cached[:limit],
                "source_count": len({a.get('source_id') for a in cached}),
                "fetched_at": datetime.now(timezone.utc).isoformat(),
            }

        # Reuse a shared, query-agnostic snapshot if available.
        base_snapshot = self._cached_get(self._BASE_CACHE_KEY)
        if base_snapshot is not None:
            filtered = self._filter_by_query(base_snapshot, normalized_query)
            final_items = filtered[:limit]
            self._cached_set(cache_key, final_items)
            return {
                "status": "success",
                "query": query,
                "cached": True,
                "articles": final_items,
                "source_count": len({a.get('source_id') for a in final_items}),
                "fetched_at": datetime.now(timezone.utc).isoformat(),
            }

        all_items: List[Dict[str, Any]] = []
        start_ts = time.time()
        max_runtime_seconds = 12.0
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        }

        with httpx.Client(timeout=8.0, headers=headers) as client:
            for source in self._sources:
                if time.time() - start_ts > max_runtime_seconds:
                    break
                source_items: List[Dict[str, Any]] = []
                if source.mode == "rss":
                    text = self._http_get(client, source.url)
                    if text:
                        source_items = self._parse_rss(source, text)
                else:
                    urls = [source.url, *source.seed_urls][: max(1, source.max_pages)]
                    for u in urls:
                        if time.time() - start_ts > max_runtime_seconds:
                            break
                        html = self._http_get(client, u)
                        # Dynamic sites may require JS rendering.
                        if not html:
                            html = self._http_get_playwright(u)
                        if not html:
                            continue
                        parsed = self._parse_html(source, html, u)
                        if not parsed:
                            rendered = self._http_get_playwright(u)
                            if rendered:
                                parsed = self._parse_html(source, rendered, u)
                        source_items.extend(parsed)
                        if len(source_items) >= 25:
                            break

                all_items.extend(source_items[:25])

        # Deduplicate globally.
        seen = set()
        uniq: List[Dict[str, Any]] = []
        for item in all_items:
            title = str(item.get("title") or "").strip()
            url = str(item.get("url") or "").strip()
            if not title or not url:
                continue
            key = (title.lower(), url)
            if key in seen:
                continue
            seen.add(key)
            uniq.append(item)

        filtered = self._filter_by_query(uniq, normalized_query)
        final_items = filtered[:limit]
        self._cached_set(self._BASE_CACHE_KEY, uniq)
        self._cached_set(cache_key, final_items)

        # If scrape yielded no rows (e.g., broad blocks), fall back to stale snapshot.
        if not final_items:
            stale = self._cached_get(self._BASE_CACHE_KEY, allow_stale=True)
            if stale:
                stale_filtered = self._filter_by_query(stale, normalized_query)
                final_items = stale_filtered[:limit]

        return {
            "status": "success",
            "query": query,
            "cached": False if uniq else True,
            "articles": final_items,
            "source_count": len({a.get('source_id') for a in final_items}),
            "fetched_at": datetime.now(timezone.utc).isoformat(),
        }


live_news_service = LiveNewsService()
