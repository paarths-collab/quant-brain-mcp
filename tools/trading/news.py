"""Recent news headlines for a ticker via yfinance's news API.

Deliberately NOT a scraper: yfinance exposes Yahoo Finance's aggregated news
feed (publisher, headline, link, timestamp) through a stable API. The MCP
client (Claude) does the reading and summarizing -- this tool supplies
structured facts with sources.
"""

from __future__ import annotations

from datetime import datetime, timezone

import yfinance as yf


def _parse_item(item: dict) -> dict | None:
    content = item.get("content") if isinstance(item, dict) else None
    if not isinstance(content, dict):
        return None
    title = content.get("title")
    if not title:
        return None

    provider = content.get("provider") or {}
    url_obj = content.get("canonicalUrl") or {}
    return {
        "title": title,
        "publisher": provider.get("displayName"),
        "url": url_obj.get("url"),
        "published_at": content.get("pubDate"),
        "summary": content.get("summary"),
    }


def get_ticker_news(ticker: str, limit: int = 8) -> dict:
    """Return recent headlines for one ticker, newest first as Yahoo orders them."""
    symbol = str(ticker).strip().upper()
    if not symbol:
        return {"error": "Provide a ticker symbol."}

    limit = max(1, min(int(limit), 25))

    try:
        raw_items = yf.Ticker(symbol).news or []
    except Exception as exc:
        return {"error": f"News fetch failed for '{symbol}': {exc}"}

    articles = []
    for item in raw_items:
        parsed = _parse_item(item)
        if parsed is not None:
            articles.append(parsed)
        if len(articles) >= limit:
            break

    return {
        "ticker": symbol,
        "articles": articles,
        "as_of": datetime.now(timezone.utc).isoformat(),
        "source": "Yahoo Finance news aggregation via yfinance",
    }
