import { LightweightChart } from '../LightweightChart';
import type { QuantData } from '@/hooks/useQuantStream';

const computeDrawdownSeries = (equity: Array<{ time: string; value: number }>) => {
  let peak = -Infinity;
  return equity.map((p) => {
    peak = Math.max(peak, p.value);
    const dd = peak > 0 ? (p.value / peak - 1) * 100 : 0;
    return { time: p.time, value: dd };
  });
};

export const DrawdownChart = ({ data }: { data: QuantData['strategy']['best_strategy'] }) => {
  const equity = data?.equity_curve;
  if (!equity?.length) return null;

  const dd = computeDrawdownSeries(equity);
  const minDd = Math.min(...dd.map((d) => d.value));

  return (
    <div className="bg-black/40 border border-orange-500/20 rounded-2xl p-4 shadow-[0_0_0_1px_rgba(249,115,22,0.08),0_0_40px_rgba(249,115,22,0.06)]">
      <div className="flex justify-between items-center mb-4">
        <h3 className="text-[11px] font-bold text-orange-300 uppercase tracking-[0.18em]">Drawdown Curve</h3>
        <div className="text-xs font-mono text-white/60">
          Worst: <span className="text-red-300">{minDd.toFixed(2)}%</span>
        </div>
      </div>
      <div className="h-[220px] w-full">
        <LightweightChart
          data={{ candleData: [], areaData: dd }}
          chartType="area"
          height={220}
          colors={{
            backgroundColor: 'transparent',
            textColor: '#9ca3af',
            gridColor: 'rgba(255, 255, 255, 0.05)',
            accentColor: '#fb7185',
            upColor: '#fb7185',
            downColor: '#fb7185',
          }}
        />
      </div>
    </div>
  );
};

