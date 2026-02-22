import type { QuantData } from '@/hooks/useQuantStream';
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer } from 'recharts';

const buildHistogram = (values: number[], bins = 18) => {
  if (!values.length) return [];
  const min = Math.min(...values);
  const max = Math.max(...values);
  const lo = Math.max(-0.15, min);
  const hi = Math.min(0.15, max);
  const step = (hi - lo) / bins || 0.01;

  const counts = Array.from({ length: bins }, () => 0);
  for (const v of values) {
    if (v < lo || v > hi) continue;
    const idx = Math.min(bins - 1, Math.max(0, Math.floor((v - lo) / step)));
    counts[idx] += 1;
  }

  return counts.map((c, i) => {
    const left = lo + i * step;
    const right = left + step;
    return { bucket: `${(left * 100).toFixed(1)}…${(right * 100).toFixed(1)}%`, count: c };
  });
};

export const ReturnsHistogram = ({ data }: { data: QuantData['strategy']['best_strategy'] }) => {
  const price = data?.price_data;
  if (!price?.length || price.length < 30) return null;

  const closes = price.map((p) => p.close);
  const returns: number[] = [];
  for (let i = 1; i < closes.length; i++) {
    const prev = closes[i - 1];
    const curr = closes[i];
    if (!prev || !curr) continue;
    returns.push(curr / prev - 1);
  }

  const hist = buildHistogram(returns, 18);
  const avg = returns.reduce((a, b) => a + b, 0) / (returns.length || 1);

  return (
    <div className="bg-black/40 border border-orange-500/20 rounded-2xl p-4">
      <div className="flex justify-between items-center mb-4">
        <h3 className="text-[11px] font-bold text-orange-300 uppercase tracking-[0.18em]">Daily Returns</h3>
        <div className="text-xs font-mono text-white/60">
          Avg: <span className={avg >= 0 ? 'text-orange-200' : 'text-red-300'}>{(avg * 100).toFixed(2)}%</span>
        </div>
      </div>
      <div className="h-[220px] w-full">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={hist} margin={{ top: 10, right: 10, bottom: 10, left: 0 }}>
            <XAxis dataKey="bucket" tick={{ fill: 'rgba(255,255,255,0.35)', fontSize: 10 }} interval={2} />
            <YAxis tick={{ fill: 'rgba(255,255,255,0.35)', fontSize: 10 }} width={28} />
            <Tooltip
              contentStyle={{
                background: 'rgba(0,0,0,0.85)',
                border: '1px solid rgba(249,115,22,0.25)',
                color: 'rgba(255,255,255,0.85)',
                fontSize: 12,
              }}
              cursor={{ fill: 'rgba(249,115,22,0.06)' }}
            />
            <Bar dataKey="count" fill="rgba(249,115,22,0.65)" radius={[6, 6, 0, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
};

