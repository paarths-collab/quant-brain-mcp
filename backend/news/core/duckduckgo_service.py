try:
    # New package name (preferred)
    from ddgs import DDGS  # type: ignore
except Exception:
    # Backward-compat fallback (emits deprecation warning in newer versions)
    from duckduckgo_search import DDGS  # type: ignore

class DuckDuckGoService:

    def search(self, query, max_results=5):

        results = []
        try:
            with DDGS() as ddgs:
                # ddgs/duckduckgo_search have slightly different call signatures across versions.
                try:
                    iterator = ddgs.text(query, max_results=max_results)
                except TypeError:
                    iterator = ddgs.text(keywords=query, max_results=max_results)

                for r in iterator:
                    results.append({
                        "title": r.get("title"),
                        "href": r.get("href") or r.get("url"),
                        "body": r.get("body") or r.get("snippet") or r.get("description")
                    })
        except Exception as e:
            # Return empty list on failure so fallback can trigger
            print(f"DDG Search failed: {e}")
            return []

        return results
