from __future__ import annotations

from typing import Any, Dict, List, Optional


class GNewsService:
    def __init__(
        self,
        *,
        language: str = "en",
        max_results: int = 5,
        period: str = "7d",
        default_country: str = "US",
    ) -> None:
        self.language = language
        self.max_results = max_results
        self.period = period
        self.default_country = default_country

    def search(self, query: str, *, country: Optional[str] = None) -> List[Dict[str, Any]]:
        query = (query or "").strip()
        if not query:
            return []

        try:
            from gnews import GNews  # type: ignore
        except Exception:
            return []

        resolved_country = (country or self._infer_country(query) or self.default_country).upper()

        try:
            client = GNews(
                language=self.language,
                country=resolved_country,
                max_results=self.max_results,
                period=self.period,
            )
            return list(client.get_news(query) or [])
        except Exception:
            return []

    def _infer_country(self, query: str) -> Optional[str]:
        q = query.lower()
        if ".ns" in q or ".bo" in q or "nse" in q or "bse" in q or "india" in q:
            return "IN"
        return "US"

