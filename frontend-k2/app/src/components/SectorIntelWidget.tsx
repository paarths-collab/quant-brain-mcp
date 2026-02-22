import React, { useEffect, useState } from 'react';
import { sectorIntelAPI } from '@/api';
import { ArrowUpRight, ArrowDownRight, Minus, TrendingUp, AlertTriangle } from 'lucide-react';

interface SectorSnapshot {
    id: number;
    sector: string;
    market: string;
    score: number;
    momentum: number;
    sector_summary: string;
    risk_notes: string;
    top_stocks: Array<{ symbol: string; name?: string; score?: number }>;
    as_of: string;
}

interface SectorIntelWidgetProps {
    market: 'US' | 'IN';
    limit?: number;
}

export const SectorIntelWidget: React.FC<SectorIntelWidgetProps> = ({ market, limit = 6 }) => {
    // Rebuild Trigger
    const [snapshots, setSnapshots] = useState<SectorSnapshot[]>([]);
    const [loading, setLoading] = useState(true);
    const [selectedSector, setSelectedSector] = useState<SectorSnapshot | null>(null);

    useEffect(() => {
        loadData();
    }, [market]);

    const loadData = async () => {
        try {
            setLoading(true);
            const { data } = await sectorIntelAPI.getLatest(market);
            // Sort by score descending
            const sorted = (Array.isArray(data) ? data : [])
                .sort((a: SectorSnapshot, b: SectorSnapshot) => b.score - a.score)
                .slice(0, limit);
            setSnapshots(sorted);
        } catch (err) {
            console.error('Failed to load sector intel', err);
            // Don't show error to user, just empty state or fallback
            setSnapshots([]);
        } finally {
            setLoading(false);
        }
    };

    if (loading) {
        return (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 animate-pulse">
                {[1, 2, 3].map(i => (
                    <div key={i} className="h-40 bg-white/5 rounded-xl border border-white/5"></div>
                ))}
            </div>
        );
    }

    if (!snapshots.length) return null;




    return (
        <div className="space-y-4">
            <div className="flex items-center justify-between">
                <div className="flex items-center gap-2 text-white font-bold text-lg">
                    <TrendingUp className="text-blue-400" size={20} />
                    Sector Intelligence
                </div>
                <button onClick={loadData} className="text-xs text-white/40 hover:text-white transition-colors">
                    Refresh
                </button>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                {snapshots.map((sector) => (
                    <SectorCard key={sector.id} data={sector} onClick={() => setSelectedSector(sector)} />
                ))}
            </div>

            {/* Detail Modal */}
            {selectedSector && (
                <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm" onClick={() => setSelectedSector(null)}>
                    <div className="bg-[#0f172a] border border-white/10 rounded-xl w-full max-w-2xl max-h-[90vh] overflow-y-auto p-6 shadow-2xl relative" onClick={e => e.stopPropagation()}>
                        <button
                            onClick={() => setSelectedSector(null)}
                            className="absolute top-4 right-4 text-white/40 hover:text-white"
                        >
                            <Minus className="rotate-45" size={24} />
                        </button>

                        <div className="flex items-center gap-3 mb-6">
                            <h2 className="text-2xl font-bold text-white">{selectedSector.sector}</h2>
                            <span className={`px-3 py-1 rounded text-sm font-bold ${selectedSector.score >= 7 ? 'bg-green-500/20 text-green-300' : 'bg-yellow-500/20 text-yellow-300'}`}>
                                Score: {selectedSector.score} / 100
                            </span>
                        </div>

                        <div className="space-y-6">
                            <div>
                                <h3 className="text-sm font-bold text-white/60 uppercase mb-2">Summary</h3>
                                <p className="text-slate-300 leading-relaxed">{selectedSector.sector_summary}</p>
                            </div>

                            {selectedSector.risk_notes && (
                                <div className="bg-orange-500/10 border border-orange-500/20 p-4 rounded-lg">
                                    <h3 className="text-sm font-bold text-orange-400 uppercase mb-2 flex items-center gap-2">
                                        <AlertTriangle size={16} /> Risk Factors
                                    </h3>
                                    <p className="text-orange-200/80 text-sm">{selectedSector.risk_notes}</p>
                                </div>
                            )}

                            <div>
                                <h3 className="text-sm font-bold text-white/60 uppercase mb-3">Top Stocks</h3>
                                <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
                                    {(typeof selectedSector.top_stocks === 'string' ? JSON.parse(selectedSector.top_stocks) : selectedSector.top_stocks || []).map((stock: any, idx: number) => {
                                        const symbol = typeof stock === 'string' ? stock : (stock.symbol || stock.name);
                                        return (
                                            <div key={idx} className="bg-white/5 border border-white/10 p-3 rounded-lg flex items-center justify-between">
                                                <span className="font-mono font-bold text-white">{symbol}</span>
                                                {stock.score && <span className="text-xs text-white/40">{stock.score}</span>}
                                            </div>
                                        );
                                    })}
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
};

const SectorCard = ({ data, onClick }: { data: SectorSnapshot; onClick: () => void }) => {
    const isBullish = data.score >= 7;
    const isBearish = data.score <= 4;

    const scoreColor = isBullish ? 'text-green-400' : isBearish ? 'text-red-400' : 'text-yellow-400';
    const borderColor = isBullish ? 'border-green-500/30' : isBearish ? 'border-red-500/30' : 'border-white/10';

    // Parse top stocks if string or object
    let topStocks: any[] = data.top_stocks || [];
    if (typeof topStocks === 'string') {
        try { topStocks = JSON.parse(topStocks); } catch { topStocks = []; }
    }

    return (
        <div
            onClick={onClick}
            className={`bg-white/5 border ${borderColor} rounded-xl p-4 hover:bg-white/10 transition-all cursor-pointer group relative overflow-hidden hover:scale-[1.02] active:scale-[0.98]`}
        >
            {/* Background Gradient */}
            <div className={`absolute top-0 right-0 w-32 h-32 bg-gradient-to-br ${isBullish ? 'from-green-500/10' : isBearish ? 'from-red-500/10' : 'from-yellow-500/10'} to-transparent rounded-bl-full -mr-10 -mt-10 pointer-events-none`} />

            <div className="flex justify-between items-start mb-3 relative z-10">
                <div>
                    <h3 className="font-bold text-white text-lg leading-tight truncate pr-2" title={data.sector}>
                        {data.sector}
                    </h3>
                    <div className="flex items-center gap-2 mt-1">
                        <span className={`text-2xl font-mono font-bold ${scoreColor}`}>
                            {data.score}
                        </span>
                        <div className="flex flex-col">
                            <span className="text-[10px] uppercase text-white/40 leading-none">Score</span>
                            <span className="text-[10px] uppercase text-white/40 leading-none">/ 100</span>
                        </div>
                    </div>
                </div>

                {/* Momentum Badge */}
                <div className={`px-2 py-1 rounded text-xs font-bold flex items-center gap-1 ${data.momentum > 0 ? 'bg-green-500/20 text-green-300' : data.momentum < 0 ? 'bg-red-500/20 text-red-300' : 'bg-slate-500/20 text-slate-300'}`}>
                    {data.momentum > 0 ? <ArrowUpRight size={12} /> : data.momentum < 0 ? <ArrowDownRight size={12} /> : <Minus size={12} />}
                    {Math.abs(data.momentum)}%
                </div>
            </div>

            <div className="space-y-3 relative z-10">
                {/* Summary Snippet */}
                <div className="text-xs text-white/70 line-clamp-2 h-8">
                    {data.sector_summary || "No summary available."}
                </div>

                {/* Top Stocks Pills */}
                {topStocks && topStocks.length > 0 && (
                    <div className="flex flex-wrap gap-1.5 pt-2 border-t border-white/5">
                        {topStocks.slice(0, 3).map((stock, idx) => {
                            if (!stock) return null;
                            const symbol = typeof stock === 'string' ? stock : (stock.symbol || stock.name || '???');
                            return (
                                <span key={idx} className="px-2 py-0.5 bg-black/40 border border-white/10 rounded text-[10px] text-white/80 font-mono">
                                    {symbol}
                                </span>
                            );
                        })}
                        {topStocks.length > 3 && (
                            <span className="px-1.5 py-0.5 text-[10px] text-white/40">+{topStocks.length - 3}</span>
                        )}
                    </div>
                )}

                {/* Risk Note (Warning) */}
                {data.risk_notes && (
                    <div className="flex items-start gap-1.5 text-[10px] text-orange-300/80 bg-orange-500/5 p-1.5 rounded mt-1">
                        <AlertTriangle size={10} className="mt-0.5 shrink-0" />
                        <span className="line-clamp-1">{data.risk_notes}</span>
                    </div>
                )}
            </div>

            {/* Hover Action */}
            <div className="absolute inset-x-0 bottom-0 h-1 bg-gradient-to-r from-transparent via-white/20 to-transparent translate-y-full group-hover:translate-y-0 transition-transform" />
        </div>
    );
};
