import { LightweightChart } from '../LightweightChart';
import type { QuantData } from '@/hooks/useQuantStream';

export const BacktestChart = ({ data }: { data: QuantData['strategy']['best_strategy'] }) => {
    if (!data || !data.equity_curve) return null;

    const chartData = {
        candleData: [], // unused for area
        areaData: data.equity_curve
    };

    return (
        <div className="bg-black/50 border border-orange-500/20 rounded-2xl p-4">
            <div className="flex justify-between items-center mb-4">
                <h3 className="text-[11px] font-bold text-orange-300 uppercase tracking-[0.18em]">Equity Curve</h3>
                <div className="flex gap-4 text-xs font-mono">
                    <span className="text-green-400">Return: {data.return.toFixed(2)}%</span>
                    <span className="text-orange-200">Win Rate: {data.win_rate.toFixed(0)}%</span>
                </div>
            </div>
            <div className="h-[250px] w-full">
                <LightweightChart
                    data={chartData}
                    chartType="area"
                    height={250}
                    colors={{
                        backgroundColor: 'transparent',
                        textColor: '#9ca3af',
                        gridColor: 'rgba(255, 255, 255, 0.05)',
                        accentColor: '#f97316',
                        upColor: '#4ade80',
                        downColor: '#f87171'
                    }}
                />
            </div>
        </div>
    );
};
