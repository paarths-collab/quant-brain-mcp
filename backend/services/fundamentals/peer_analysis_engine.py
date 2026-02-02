def filter_by_sector(peers: List[Dict[str, Any]], sector: str) -> List[Dict[str, Any]]:
    return [
        p for p in peers
        if p.get("sector", "").lower() == sector.lower()
    ]

class PeerAnalysisEngine:
    def __init__(
        self,
        competitor_service,
        valuation_service,
        performance_service,
        llm_peer_analyst
    ):
        self.competitors = competitor_service
        self.valuation = valuation_service
        self.performance = performance_service
        self.llm = llm_peer_analyst

    def run(self, symbol: str) -> dict:
        peers = self.competitors.get_competitors(symbol)

        symbols = [p["symbol"] for p in peers]

        valuations = self.valuation.get_peer_valuations(symbols)
        performance = self.performance.compare_performance(symbols)

        ranked = sorted(peers, key=lambda x: x["market_cap"], reverse=True)

        summary = self.llm.generate_summary(
            symbol, ranked, valuations, performance
        )

        return {
            "peers": ranked,
            "valuations": valuations,
            "performance": performance,
            "llm_summary": summary
        }
