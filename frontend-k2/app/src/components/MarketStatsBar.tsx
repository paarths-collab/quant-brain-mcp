import { useEffect, useState } from 'react';
import { fredAPI } from '@/api';

const MARKET_SERIES = [
    { id: 'SP500', label: 'S&P 500' },
    { id: 'NASDAQ100', label: 'Nasdaq' },
    { id: 'DJIA', label: 'Dow' },
    { id: 'VIXCLS', label: 'VIX', reverseColor: true }, // High VIX is usually bad (red)
    { id: 'GOLDAMGBD228NLBM', label: 'Gold' },
    { id: 'DCOILWTICO', label: 'Crude' },
    { id: 'DTWEXBGS', label: 'DXY' }, // Dollar Index
];

interface MarketPoint {
    id: string;
    name: string;
    value: number;
    change: number;
    date: string;
}

export const MarketStatsBar = () => {
    const [data, setData] = useState<MarketPoint[]>([]);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        const fetchData = async () => {
            try {
                const ids = MARKET_SERIES.map(s => s.id);
                const { data: response } = await fredAPI.getLatestCached(ids, 12); // 12 hour cache

                if (response && response.status === 'success' && response.data) {
                    const points = MARKET_SERIES.map(series => {
                        const item = response.data[series.id];
                        if (!item) return null;
                        return {
                            id: series.id,
                            name: series.label,
                            value: item.value ?? 0,
                            change: item.change_pct ?? 0,
                            date: item.date || ''
                        };
                    }).filter(Boolean) as MarketPoint[];
                    setData(points);
                } else {
                    console.warn('MarketStatsBar: Invalid response format or data missing', {
                        status: response?.status,
                        hasData: !!response?.data,
                        response
                    });
                }
            } catch (e) {
                console.error('Failed to load market stats', e);
            } finally {
                setLoading(false);
            }
        };

        fetchData();
    }, []);

    if (loading) return <div className="h-10 w-full animate-pulse bg-white/5 rounded-lg mb-6" />;
    if (!data.length) return null;

    return (
        <div className="flex flex-wrap gap-4 p-3 bg-white/5 border border-white/10 rounded-xl mb-6 items-center">
            <div className="text-xs font-bold text-white/40 uppercase tracking-wider mr-2 border-r border-white/10 pr-4">
                Market Pulse
            </div>
            {data.map(item => {
                const isPos = item.change >= 0;
                const colorClass = isPos ? 'text-green-400' : 'text-red-400';

                return (
                    <div key={item.id} className="flex items-center gap-2 pr-4 border-r border-white/5 last:border-0">
                        <span className="text-xs font-semibold text-white/70">{item.name}</span>
                        <span className="text-sm font-mono font-bold text-white">
                            {item.value.toLocaleString(undefined, { maximumFractionDigits: 2 })}
                        </span>
                        <span className={`flex items-center text-xs ${colorClass}`}>
                            {isPos ? '+' : ''}{(item.change ?? 0).toFixed(2)}%
                        </span>
                    </div>
                );
            })}
            <div className="ml-auto text-[10px] text-white/30">
                Source: FRED • Delayed
            </div>
        </div>
    );
};
