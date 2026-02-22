import { LightweightChart } from '../LightweightChart';
import type { QuantData } from '@/hooks/useQuantStream';

export const StockChart = ({ data }: { data: QuantData['strategy']['best_strategy'] }) => {
    if (!data || !data.price_data) return null;

    // Convert API data to Lightweight Charts format
    const candleData = data.price_data.map(d => ({
        time: d.time,
        open: d.open,
        high: d.high,
        low: d.low,
        close: d.close
    }));

    const volumeData = data.price_data.map(d => ({
        time: d.time,
        value: d.volume,
        color: d.close >= d.open ? 'rgba(249, 115, 22, 0.35)' : 'rgba(239, 68, 68, 0.35)'
    }));

    // Signals as markers (raw format is fine; LightweightChart normalizes)
    const markers = data.signals;

    const chartData = {
        candleData,
        volumeData,
        markers
    };

    return (
        <div className="bg-white/5 border border-white/10 rounded-2xl p-4">
            <div className="flex justify-between items-center mb-4">
                <h3 className="text-sm font-bold text-white uppercase tracking-wider">Price Action & Signals</h3>
                <div className="text-xs text-white/50">Strategy: <span className="text-white font-bold">{data.strategy}</span></div>
            </div>
            <div className="h-[350px] w-full">
                <LightweightChart
                    data={chartData}
                    chartType="candle"
                    height={350}
                    colors={{
                        backgroundColor: 'transparent',
                        textColor: '#9ca3af',
                        gridColor: 'rgba(255, 255, 255, 0.05)',
                        accentColor: '#f97316',
                        upColor: '#f97316',
                        downColor: '#ef4444'
                    }}
                />
            </div>
        </div>
    );
};
