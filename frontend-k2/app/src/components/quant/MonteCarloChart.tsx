import { LightweightChart } from '../LightweightChart';
import type { QuantData } from '@/hooks/useQuantStream';

export const MonteCarloChart = ({ data }: { data: QuantData['strategy']['monte_carlo'] }) => {
    if (!data || !data.simulation_paths) return null;

    // Lightweight charts handles one line series well. For multiple, we might need a different approach 
    // or just render the component multiple times overlaid? No, that's messy.
    // The LightweightChart component I read supports `lineData` as an array of series.

    // We need to generate 'time' for the future paths.
    // We'll create hypothetical dates starting from "Day 1", "Day 2".
    // Actually, LWC needs strictly increasing time. "1", "2", "3" works if unit is generic? 
    // Or we can just use dummy dates.

    const today = new Date();
    const lineData = data.simulation_paths.map((path, index) => {
        const seriesData = path.map((price, i) => {
            const date = new Date(today);
            date.setDate(today.getDate() + i + 1);
            return {
                time: date.toISOString().split('T')[0],
                value: price
            };
        });

        // Color logic: Highlight best/worst, fade others
        let color = 'rgba(255, 255, 255, 0.05)'; // Very faint by default
        if (index === 0) color = 'rgba(255, 255, 255, 0.1)';

        return {
            name: `Sim ${index}`,
            data: seriesData,
            color
        };
    });

    // Add Mean Path (Expected)
    // We don't have the mean path array from backend, just the final value. 
    // So let's just show the fan.

    const chartData = {
        candleData: [],
        lineData: lineData
    };

    return (
        <div className="bg-black/50 border border-orange-500/20 rounded-2xl p-4">
            <div className="flex justify-between items-center mb-4">
                <h3 className="text-[11px] font-bold text-orange-300 uppercase tracking-[0.18em]">Monte Carlo Paths</h3>
                <div className="text-xs font-mono">
                    <span className="text-green-400 mr-3">Bull: ${data.best_case.toFixed(2)}</span>
                    <span className="text-red-400">Bear: ${data.worst_case.toFixed(2)}</span>
                </div>
            </div>
            <div className="h-[250px] w-full">
                <LightweightChart
                    data={chartData}
                    chartType="line" // The component handles 'lineData' array internally
                    height={250}
                    colors={{
                        backgroundColor: 'transparent',
                        textColor: '#9ca3af',
                        gridColor: 'rgba(255, 255, 255, 0.05)',
                        accentColor: '#f97316',
                    }}
                />
            </div>
        </div>
    );
};
