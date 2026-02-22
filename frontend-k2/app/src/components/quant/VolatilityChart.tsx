import { LightweightChart } from '../LightweightChart';
import type { QuantData } from '@/hooks/useQuantStream';

const rollingVolAnnualized = (closes: number[], window = 20) => {
  const out: Array<number | null> = Array(closes.length).fill(null);
  for (let i = window; i < closes.length; i++) {
    const slice = closes.slice(i - window, i + 1);
    const rets: number[] = [];
    for (let j = 1; j < slice.length; j++) {
      const prev = slice[j - 1];
      const curr = slice[j];
      if (!prev || !curr) continue;
      rets.push(curr / prev - 1);
    }
    if (rets.length < 5) continue;
    const mean = rets.reduce((a, b) => a + b, 0) / rets.length;
    const variance = rets.reduce((a, b) => a + Math.pow(b - mean, 2), 0) / (rets.length - 1);
    const std = Math.sqrt(Math.max(0, variance));
    out[i] = std * Math.sqrt(252) * 100;
  }
  return out;
};

export const VolatilityChart = ({ data }: { data: QuantData['strategy']['best_strategy'] }) => {
  const price = data?.price_data;
  if (!price?.length) return null;

  const closes = price.map((p) => p.close);
  const vol = rollingVolAnnualized(closes, 20);
  const series = price
    .map((p, i) => (vol[i] == null ? null : ({ time: p.time, value: Number(vol[i]!.toFixed(2)) })))
    .filter(Boolean) as Array<{ time: string; value: number }>;

  if (series.length < 10) return null;

  const latest = series[series.length - 1]?.value ?? 0;

  return (
    <div className="bg-black/40 border border-orange-500/20 rounded-2xl p-4">
      <div className="flex justify-between items-center mb-4">
        <h3 className="text-[11px] font-bold text-orange-300 uppercase tracking-[0.18em]">Rolling Volatility</h3>
        <div className="text-xs font-mono text-white/60">
          20D: <span className="text-orange-200">{latest.toFixed(2)}%</span>
        </div>
      </div>
      <div className="h-[220px] w-full">
        <LightweightChart
          data={{ candleData: [], areaData: series }}
          chartType="line"
          height={220}
          colors={{
            backgroundColor: 'transparent',
            textColor: '#9ca3af',
            gridColor: 'rgba(255, 255, 255, 0.05)',
            accentColor: '#f97316',
            upColor: '#f97316',
            downColor: '#f97316',
          }}
        />
      </div>
    </div>
  );
};

