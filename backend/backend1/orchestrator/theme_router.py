import re
from backend.backend1.orchestrator.sector_decision_orchestrator import SectorDecisionOrchestrator
from backend.backend1.utils.region_detector import detect_region
from backend.backend1.utils.market_context import get_market_context
from backend.backend1.utils.universe_loader import get_global_universe

class ThemeRouter:

    def __init__(self):
        self.orchestrator = SectorDecisionOrchestrator()

    async def route(self, user_query, risk_profile="moderate", **kwargs):
        
        # 1. Detect Region
        region = detect_region(user_query)
        print(f"DEBUG: detect_region('{user_query}') -> {region}")
        print(f"Region Detected: {region}")

        # 2. Detect Horizon
        horizon = self._detect_horizon(user_query)
        print(f"Horizon Detected: {horizon.upper()}")

        # 3. Fetch Market Context (PE, RF Rate)
        market_context = get_market_context(region)
        
        query = user_query.lower()

        # 4. Check for "Generic Best Stock" query
        if self._is_generic_best_stock(query):
            print(f"ℹ️  Generic 'Best Stock' query detected. Loading {region} Universe.")
            universe = get_global_universe(region)
            
            if not universe:
                return {"error": f"No global universe defined for region {region}"}

            return await self.orchestrator.run_custom_universe(
                universe,
                risk_profile=risk_profile,
                region=region,
                market_context=market_context,
                horizon=horizon,  # Pass horizon
                **kwargs
            )

        # 5. Extract Theme / Sector intent
        theme = self._extract_clean_theme(query)
        print(f"Extracted Theme/Topic: '{theme}'")

        return await self.orchestrator.run(
            theme,
            risk_profile=risk_profile,
            region=region,
            market_context=market_context,
            horizon=horizon, # Pass horizon
            **kwargs
        )

    def _detect_horizon(self, query: str) -> str:
        q = query.lower()
        
        short_keywords = ["short", "swing", "intraday", "quick", "next month", "3 month", "weeks", "trade"]
        long_keywords = ["long", "retirement", "5 year", "10 year", "decade", "compound", "invest", "wealth"]
        medium_keywords = ["1 year", "12 month", "mid term", "medium"]

        if any(k in q for k in short_keywords):
            return "short"

        if any(k in q for k in long_keywords):
            return "long"

        if any(k in q for k in medium_keywords):
            return "medium"

        return "long"  # default

    def _is_generic_best_stock(self, query):
        # Patterns that imply "Overall Best" without a specific theme
        patterns = [
            r"best stock$", # "What is the best stock"
            r"best stock to buy",
            r"which stock should i buy",
            r"top stock right now",
            r"best investment",
            r"strongest stock",
            r"recommend a stock",
            r"stock recommendation"
        ]
        
        # If query has specific theme words, it might NOT be generic.
        # But strict generic patterns usually work.
        # E.g. "Best AI stock" -> contains "AI", but also matches "Best ... stock"?
        # No, patterns above are specific. "best stock$" means ends with "best stock".
        # "best stock to buy" matches "best stock to buy now".
        # But "best stock to buy for ai" -> matches "best stock to buy"?
        # If regex finds match, we might need to check if there are other nouns.
        # Simplified approach: If it matches generic pattern AND doesn't look like it has a theme specifier.
        
        # Actually, let's look for " theme " words?
        # If I say "Best AI stock", does it match "best stock to buy"? No.
        # "Best stock to buy" matches.
        
        for pattern in patterns:
            if re.search(pattern, query):
                # Ensure it doesn't have a qualifier like "in tech" or "for ai" if the pattern allows suffixes
                # The patterns above are somewhat loose.
                # Let's rely on the specific patterns provided in plan.
                return True
        return False

    def _extract_clean_theme(self, query):
        # Remove "best", "stock", "to buy", etc. to leave the core subject
        # e.g. "Best AI stock for long term" -> "aistockforlongterm" -> "ai"
        
        stopwords = [
            "best", "top", "good", "stock", "stocks", "company", "companies",
            "to", "buy", "invest", "in", "for", "the", "market", "share", "shares",
            "recommend", "recommendation", "which", "should", "i", "get", "now", "right",
            "long", "term", "short", "aggressive", "conservative", "india", "us", "usa"
        ]
        
        words = query.split()
        filtered = [w for w in words if w not in stopwords]
        
        result = " ".join(filtered)
        
        # If result is empty, fallback to original query or "Technology"
        if not result.strip():
            return query
            
        return result
