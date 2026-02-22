import { useState, useEffect, useRef } from 'react';
import {
  AreaChart, Area, BarChart, Bar,
  LineChart, Line,
  XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid, ReferenceLine, Cell,
} from 'recharts';
import {
  Activity, Brain, BarChart3, Shield, Zap, TrendingUp,
  Loader2, Search, Layers, AlertTriangle,
} from 'lucide-react';
import { backtestAPI } from '@/api';

// const API_BASE = import.meta.env.VITE_API_BASE || 'http://localhost:8001';

// ─── Types ──────────────────────────────────────────────────────────────────────

interface MonteCarloResult {
  simulations: number;
  histogram: { return: number; count: number }[];
  percentiles: Record<string, number>;
  riskMetrics: {
    var95: number; cvar95: number; ruinProbability: number;
    medianMaxDrawdown: number; worstCase: number; bestCase: number; meanReturn: number;
  };
  simulationPaths?: number[][];
  percentilePaths?: Record<string, number[]>;
  pathSteps?: number;
}

interface BacktestMetrics {
  totalReturn: number; maxDrawdown: number; sharpeRatio: number;
  sortinoRatio: number; calmarRatio: number; winRate: number;
  totalTrades: number; initialCapital: number; finalEquity: number;
  annualVolatility: number; profitFactor: number | null;
  expectancy: number | null; sqn: number | null;
  avgWin: number | null; avgLoss: number | null;
  bestTrade: number | null; worstTrade: number | null;
}

interface Trade {
  side: string; entryDate: string; entryPrice: number;
  exitDate: string; exitPrice: number; pnl: number; pnlPct: number;
  entryReason: string; exitReason: string;
}

interface BacktestResult {
  symbol: string; strategy: string; metrics: BacktestMetrics;
  chartData: unknown[]; trades: Trade[];
  equity_curve: { date: string; value: number; benchmark?: number }[];
  monteCarlo?: MonteCarloResult;
}

type EquityCurvePoint = BacktestResult['equity_curve'][number];

function stdev(values: number[]) {
  if (values.length < 2) return 0;
  const mean = values.reduce((a, b) => a + b, 0) / values.length;
  const variance = values.reduce((acc, v) => acc + (v - mean) ** 2, 0) / (values.length - 1);
  return Math.sqrt(variance);
}

function toReturns(series: EquityCurvePoint[]) {
  if (!series?.length) return [] as { date: string; r: number }[];
  const out: { date: string; r: number }[] = [];
  for (let i = 1; i < series.length; i++) {
    const prev = series[i - 1]?.value;
    const cur = series[i]?.value;
    if (!Number.isFinite(prev) || !Number.isFinite(cur) || prev === 0) continue;
    out.push({ date: series[i].date, r: (cur / prev) - 1 });
  }
  return out;
}

function getErrorMessage(err: unknown) {
  if (typeof err === 'string') return err;
  if (err && typeof err === 'object') {
    const rec = err as Record<string, unknown>;
    const response = rec.response;
    if (response && typeof response === 'object') {
      const resRec = response as Record<string, unknown>;
      const data = resRec.data;
      if (data && typeof data === 'object') {
        const detail = (data as Record<string, unknown>).detail;
        if (typeof detail === 'string' && detail.trim()) return detail;
      }
    }
    const message = rec.message;
    if (typeof message === 'string' && message.trim()) return message;
  }
  return 'Analysis failed';
}

// ─── Monte Carlo Paths Canvas ────────────────────────────────────────────────────

function MonteCarloPathsCanvas({ paths, percentilePaths }: { paths?: number[][]; percentilePaths?: Record<string, number[]> }) {
  const canvasRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    if (!canvasRef.current || (!paths?.length && !percentilePaths)) return;
    const canvas = canvasRef.current;
    const ctx = canvas.getContext('2d')!;
    const dpr = window.devicePixelRatio || 1;
    const w = canvas.clientWidth; const h = canvas.clientHeight;
    canvas.width = w * dpr; canvas.height = h * dpr;
    ctx.scale(dpr, dpr);
    ctx.clearRect(0, 0, w, h);

    // Draw background grid
    ctx.strokeStyle = 'rgba(255,255,255,0.03)';
    ctx.lineWidth = 1;
    for (let i = 0; i < 5; i++) {
      const y = (h / 5) * i;
      ctx.beginPath(); ctx.moveTo(0, y); ctx.lineTo(w, y); ctx.stroke();
    }

    if (paths?.length) {
      // Flatten to find min/max
      let allMin = Infinity, allMax = -Infinity;
      const steps = paths[0]?.length || 0;
      paths.forEach(p => p.forEach(v => { allMin = Math.min(allMin, v); allMax = Math.max(allMax, v); }));
      const range = allMax - allMin || 1;

      // Draw individual paths
      paths.slice(0, 80).forEach((path) => {
        const endVal = path[path.length - 1] || 0;
        const color = endVal >= (path[0] || 0)
          ? `rgba(52, 211, 153, 0.06)` // green
          : `rgba(248, 113, 113, 0.06)`; // red
        ctx.beginPath();
        ctx.strokeStyle = color;
        ctx.lineWidth = 0.5;
        path.forEach((val, j) => {
          const x = (j / (steps - 1)) * w;
          const y = h - ((val - allMin) / range) * h;
          if (j === 0) ctx.moveTo(x, y);
          else ctx.lineTo(x, y);
        });
        ctx.stroke();
      });

      // Draw percentile bands
      if (percentilePaths) {
        const drawBand = (key: string, color: string, width: number) => {
          const pPath = percentilePaths[key];
          if (!pPath) return;
          ctx.beginPath();
          ctx.strokeStyle = color;
          ctx.lineWidth = width;
          pPath.forEach((val, j) => {
            const x = (j / (pPath.length - 1)) * w;
            const y = h - ((val - allMin) / range) * h;
            if (j === 0) ctx.moveTo(x, y);
            else ctx.lineTo(x, y);
          });
          ctx.stroke();
        };
        drawBand('p5', 'rgba(248, 113, 113, 0.6)', 1.5);
        drawBand('p25', 'rgba(251, 191, 36, 0.5)', 1);
        drawBand('p50', 'rgba(249, 115, 22, 1)', 2);
        drawBand('p75', 'rgba(52, 211, 153, 0.5)', 1);
        drawBand('p95', 'rgba(52, 211, 153, 0.6)', 1.5);
      }
    }
  }, [paths, percentilePaths]);

  return <canvas ref={canvasRef} className="w-full h-full" style={{ imageRendering: 'auto' }} />;
}

// ─── Monte Carlo Distribution Chart ──────────────────────────────────────────────

function MCDistributionChart({ histogram, riskMetrics }: { histogram: MonteCarloResult['histogram']; riskMetrics: MonteCarloResult['riskMetrics'] }) {
  if (!histogram?.length) return null;
  return (
    <div className="h-64">
      <ResponsiveContainer>
        <BarChart data={histogram} barCategoryGap={0}>
          <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.03)" />
          <XAxis dataKey="return" tickFormatter={(v: number) => `${(v * 100).toFixed(0)}%`} tick={{ fontSize: 10, fill: 'rgba(255,255,255,0.3)' }} />
          <YAxis tick={{ fontSize: 10, fill: 'rgba(255,255,255,0.3)' }} />
          <Tooltip
            contentStyle={{ background: '#0a0a0a', border: '1px solid rgba(255,255,255,0.1)', borderRadius: 12, fontSize: 11 }}
            formatter={(val: number) => [val, 'Count']}
            labelFormatter={(v: number) => `Return: ${(v * 100).toFixed(1)}%`}
          />
          {riskMetrics?.var95 != null && <ReferenceLine x={riskMetrics.var95} stroke="#f87171" strokeDasharray="5 5" label={{ value: 'VaR 95%', position: 'top', fill: '#f87171', fontSize: 9 }} />}
          <Bar dataKey="count" radius={[2, 2, 0, 0]}>
            {histogram.map((entry, i) => (
              <Cell key={i} fill={entry.return >= 0 ? 'rgba(52, 211, 153, 0.6)' : 'rgba(248, 113, 113, 0.4)'} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}

// ─── Equity Curve Chart ──────────────────────────────────────────────────────────

function EquityCurveChart({ data }: { data: { date: string; value: number; benchmark?: number }[] }) {
  if (!data?.length) return null;
  return (
    <div className="h-64">
      <ResponsiveContainer>
        <AreaChart data={data}>
          <defs>
            <linearGradient id="eqGrad" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor="#F97316" stopOpacity={0.28} />
              <stop offset="95%" stopColor="#F97316" stopOpacity={0} />
            </linearGradient>
          </defs>
          <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.03)" />
          <XAxis dataKey="date" tick={{ fontSize: 9, fill: 'rgba(255,255,255,0.3)' }} interval="preserveStartEnd" />
          <YAxis tick={{ fontSize: 10, fill: 'rgba(255,255,255,0.3)' }} tickFormatter={(v: number) => `$${(v / 1000).toFixed(0)}k`} />
          <Tooltip
            contentStyle={{ background: '#0a0a0a', border: '1px solid rgba(255,255,255,0.1)', borderRadius: 12, fontSize: 11 }}
            formatter={(val: number) => [`$${val.toLocaleString()}`, 'Portfolio']}
          />
          <Area type="monotone" dataKey="value" stroke="#F97316" fill="url(#eqGrad)" strokeWidth={2} dot={false} />
          {data[0]?.benchmark != null && (
            <Area type="monotone" dataKey="benchmark" stroke="#FBBF24" fill="none" strokeWidth={1.5} strokeDasharray="4 4" dot={false} />
          )}
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
}

function DrawdownChart({ data }: { data: EquityCurvePoint[] }) {
  if (!data?.length) return null;
  const dd = data.reduce<{ peak: number; points: { date: string; drawdown: number }[] }>((acc, pt) => {
    const peak = Math.max(acc.peak, pt.value ?? 0);
    const v = pt.value ?? 0;
    const drawdown = peak > 0 ? (v / peak - 1) * 100 : 0;
    return { peak, points: [...acc.points, { date: pt.date, drawdown }] };
  }, { peak: -Infinity, points: [] }).points;

  return (
    <div className="h-44">
      <ResponsiveContainer>
        <AreaChart data={dd}>
          <defs>
            <linearGradient id="ddGrad" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor="#FB923C" stopOpacity={0.18} />
              <stop offset="95%" stopColor="#FB923C" stopOpacity={0} />
            </linearGradient>
          </defs>
          <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.03)" />
          <XAxis dataKey="date" tick={{ fontSize: 9, fill: 'rgba(255,255,255,0.3)' }} interval="preserveStartEnd" />
          <YAxis tick={{ fontSize: 10, fill: 'rgba(255,255,255,0.3)' }} tickFormatter={(v: number) => `${v.toFixed(0)}%`} />
          <Tooltip
            contentStyle={{ background: '#0a0a0a', border: '1px solid rgba(255,255,255,0.1)', borderRadius: 12, fontSize: 11 }}
            formatter={(val: number) => [`${val.toFixed(2)}%`, 'Drawdown']}
          />
          <ReferenceLine y={0} stroke="rgba(255,255,255,0.10)" />
          <Area type="monotone" dataKey="drawdown" stroke="#FB923C" fill="url(#ddGrad)" strokeWidth={1.75} dot={false} />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
}

function RollingVolatilityChart({ data, window = 20 }: { data: EquityCurvePoint[]; window?: number }) {
  const rets = toReturns(data);
  if (rets.length < window + 2) return null;

  const points = rets.map((pt, i) => {
    const start = Math.max(0, i - window + 1);
    const slice = rets.slice(start, i + 1).map(r => r.r);
    const vol = stdev(slice) * Math.sqrt(252) * 100;
    return { date: pt.date, vol };
  });

  return (
    <div className="h-44">
      <ResponsiveContainer>
        <LineChart data={points}>
          <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.03)" />
          <XAxis dataKey="date" tick={{ fontSize: 9, fill: 'rgba(255,255,255,0.3)' }} interval="preserveStartEnd" />
          <YAxis tick={{ fontSize: 10, fill: 'rgba(255,255,255,0.3)' }} tickFormatter={(v: number) => `${v.toFixed(0)}%`} />
          <Tooltip
            contentStyle={{ background: '#0a0a0a', border: '1px solid rgba(255,255,255,0.1)', borderRadius: 12, fontSize: 11 }}
            formatter={(val: number) => [`${val.toFixed(2)}%`, 'Ann. Vol']}
          />
          <Line type="monotone" dataKey="vol" stroke="#F97316" strokeWidth={2} dot={false} />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}

function ReturnHistogramChart({ data, bins = 24 }: { data: EquityCurvePoint[]; bins?: number }) {
  const rets = toReturns(data).map(r => r.r);
  if (rets.length < 3) return null;

  let min = Math.min(...rets);
  let max = Math.max(...rets);
  if (!Number.isFinite(min) || !Number.isFinite(max) || min === max) return null;

  const pad = 0.0025;
  min -= pad;
  max += pad;
  const width = (max - min) / bins;
  const hist = Array.from({ length: bins }, (_, i) => {
    const lo = min + i * width;
    const hi = lo + width;
    return { mid: (lo + hi) / 2, count: 0 };
  });

  for (const r of rets) {
    const idx = Math.min(bins - 1, Math.max(0, Math.floor((r - min) / width)));
    hist[idx].count += 1;
  }

  return (
    <div className="h-44">
      <ResponsiveContainer>
        <BarChart data={hist} barCategoryGap={0}>
          <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.03)" />
          <XAxis
            dataKey="mid"
            tickFormatter={(v: number) => `${(v * 100).toFixed(0)}%`}
            tick={{ fontSize: 9, fill: 'rgba(255,255,255,0.3)' }}
          />
          <YAxis tick={{ fontSize: 10, fill: 'rgba(255,255,255,0.3)' }} allowDecimals={false} />
          <Tooltip
            contentStyle={{ background: '#0a0a0a', border: '1px solid rgba(255,255,255,0.1)', borderRadius: 12, fontSize: 11 }}
            formatter={(val: number) => [val, 'Days']}
            labelFormatter={(v: number) => `Return: ${(v * 100).toFixed(2)}%`}
          />
          <Bar dataKey="count" radius={[2, 2, 0, 0]}>
            {hist.map((entry, i) => (
              <Cell key={i} fill={entry.mid >= 0 ? 'rgba(52, 211, 153, 0.55)' : 'rgba(248, 113, 113, 0.45)'} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}

function TradePnLHistogramChart({ trades, bins = 18 }: { trades: Trade[]; bins?: number }) {
  const vals = (trades || []).map(t => t.pnlPct).filter((v): v is number => typeof v === 'number' && Number.isFinite(v)).map(v => v / 100);
  if (vals.length < 3) return null;

  let min = Math.min(...vals);
  let max = Math.max(...vals);
  if (!Number.isFinite(min) || !Number.isFinite(max) || min === max) return null;

  const pad = 0.0025;
  min -= pad;
  max += pad;
  const width = (max - min) / bins;
  const hist = Array.from({ length: bins }, (_, i) => {
    const lo = min + i * width;
    const hi = lo + width;
    return { mid: (lo + hi) / 2, count: 0 };
  });

  for (const r of vals) {
    const idx = Math.min(bins - 1, Math.max(0, Math.floor((r - min) / width)));
    hist[idx].count += 1;
  }

  return (
    <div className="h-44">
      <ResponsiveContainer>
        <BarChart data={hist} barCategoryGap={0}>
          <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.03)" />
          <XAxis
            dataKey="mid"
            tickFormatter={(v: number) => `${(v * 100).toFixed(0)}%`}
            tick={{ fontSize: 9, fill: 'rgba(255,255,255,0.3)' }}
          />
          <YAxis tick={{ fontSize: 10, fill: 'rgba(255,255,255,0.3)' }} allowDecimals={false} />
          <Tooltip
            contentStyle={{ background: '#0a0a0a', border: '1px solid rgba(255,255,255,0.1)', borderRadius: 12, fontSize: 11 }}
            formatter={(val: number) => [val, 'Trades']}
            labelFormatter={(v: number) => `PnL: ${(v * 100).toFixed(2)}%`}
          />
          <ReferenceLine x={0} stroke="rgba(255,255,255,0.12)" />
          <Bar dataKey="count" radius={[2, 2, 0, 0]}>
            {hist.map((entry, i) => (
              <Cell key={i} fill={entry.mid >= 0 ? 'rgba(52, 211, 153, 0.55)' : 'rgba(248, 113, 113, 0.45)'} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}

// ─── Risk Gauges ─────────────────────────────────────────────────────────────────

function RiskGaugeSet({ metrics }: { metrics: MonteCarloResult['riskMetrics'] }) {
  if (!metrics) return null;
  const items = [
    { label: 'VaR 95%', value: metrics.var95, color: 'text-red-400', fmt: (v: number) => `${(v * 100).toFixed(2)}%` },
    { label: 'CVaR 95%', value: metrics.cvar95, color: 'text-red-500', fmt: (v: number) => `${(v * 100).toFixed(2)}%` },
    { label: 'Mean Return', value: metrics.meanReturn, color: 'text-emerald-400', fmt: (v: number) => `${(v * 100).toFixed(2)}%` },
    { label: 'Worst Case', value: metrics.worstCase, color: 'text-red-300', fmt: (v: number) => `${(v * 100).toFixed(1)}%` },
    { label: 'Best Case', value: metrics.bestCase, color: 'text-green-300', fmt: (v: number) => `${(v * 100).toFixed(1)}%` },
    { label: 'Ruin Prob', value: metrics.ruinProbability, color: 'text-amber-400', fmt: (v: number) => `${(v * 100).toFixed(2)}%` },
  ];
  return (
    <div className="grid grid-cols-3 md:grid-cols-6 gap-3">
      {items.map(itm => (
        <div key={itm.label} className="bg-black/40 rounded-xl p-3 border border-white/5 text-center">
          <div className="text-[10px] text-white/40 uppercase tracking-wider mb-1">{itm.label}</div>
          <div className={`text-lg font-mono font-bold ${itm.color}`}>{itm.value != null ? itm.fmt(itm.value) : '—'}</div>
        </div>
      ))}
    </div>
  );
}

// ─── Trade Log ───────────────────────────────────────────────────────────────────

function TradeLog({ trades }: { trades: Trade[] }) {
  const [expanded, setExpanded] = useState(false);
  if (!trades?.length) return null;
  const shown = expanded ? trades : trades.slice(0, 5);
  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between">
        <div className="text-xs font-bold uppercase tracking-[0.2em] text-white/40">Trade Log ({trades.length})</div>
        {trades.length > 5 && (
          <button onClick={() => setExpanded(!expanded)} className="text-[10px] text-orange-400 hover:text-orange-300">
            {expanded ? 'Show less' : `Show all ${trades.length}`}
          </button>
        )}
      </div>
      <div className="space-y-1">
        {shown.map((t, i) => (
          <div key={i} className="flex items-center gap-3 text-[11px] py-2 px-3 rounded-lg bg-white/[0.02] border border-white/[0.04]">
            <span className={`font-bold uppercase ${t.side === 'long' ? 'text-emerald-400' : 'text-red-400'}`}>{t.side}</span>
            <span className="text-white/40">{t.entryDate?.slice(0, 10)}</span>
            <span className="text-white/50">→</span>
            <span className="text-white/40">{t.exitDate?.slice(0, 10)}</span>
            <span className="ml-auto font-mono">
              <span className={t.pnl >= 0 ? 'text-emerald-400' : 'text-red-400'}>
                {t.pnl >= 0 ? '+' : ''}{t.pnlPct?.toFixed(2)}%
              </span>
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}

// ─── Metric Card ────────────────────────────────────────────────────────────────

function MetricCard({ label, value, suffix, good }: { label: string; value: number | null | undefined; suffix?: string; good?: boolean }) {
  if (value == null) return null;
  return (
    <div className="bg-black/40 rounded-xl p-3 border border-white/5">
      <div className="text-[10px] text-white/40 uppercase tracking-wider mb-1">{label}</div>
      <div className={`text-lg font-mono font-bold ${good === true ? 'text-emerald-400' : good === false ? 'text-red-400' : 'text-white'}`}>
        {typeof value === 'number' ? value.toFixed(2) : value}{suffix || ''}
      </div>
    </div>
  );
}

// ─── Main Component ──────────────────────────────────────────────────────────────

export default function QuantLab() {
  const [symbol, setSymbol] = useState('AAPL');
  const [strategy, setStrategy] = useState('momentum');
  const [strategies, setStrategies] = useState<{ id: string; name: string; description: string }[]>([]);
  const [result, setResult] = useState<BacktestResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<'equity' | 'montecarlo' | 'risk' | 'trades'>('equity');

  // Load strategies
  useEffect(() => {
    backtestAPI.getStrategies().then(res => {
      setStrategies(res.data?.strategies || []);
    }).catch(() => {});
  }, []);

  const runAnalysis = async () => {
    if (!symbol.trim()) return;
    setLoading(true); setError(null);
    try {
      const { data } = await backtestAPI.run({
        symbol: symbol.toUpperCase(),
        strategy,
        range: '2y',
      });
      setResult(data);
    } catch (err: unknown) {
      setError(getErrorMessage(err));
    } finally { setLoading(false); }
  };

  const metrics = result?.metrics;
  const mc = result?.monteCarlo;
  const equity = result?.equity_curve || [];
  const trades = result?.trades || [];

  return (
    <div className="relative space-y-6">
      <div className="pointer-events-none absolute inset-0 -z-10 overflow-hidden">
        <div className="absolute -top-24 -left-24 h-96 w-96 rounded-full bg-orange-500/10 blur-3xl" />
        <div className="absolute top-16 -right-32 h-[28rem] w-[28rem] rounded-full bg-amber-400/10 blur-3xl" />
        <div className="absolute -bottom-40 left-1/4 h-[34rem] w-[34rem] rounded-full bg-red-500/5 blur-3xl" />
        <div
          className="absolute inset-0 opacity-[0.07]"
          style={{
            backgroundImage: [
              'radial-gradient(circle at 18% 14%, rgba(249,115,22,0.22), transparent 40%)',
              'radial-gradient(circle at 82% 10%, rgba(251,191,36,0.18), transparent 44%)',
              'radial-gradient(circle at 50% 70%, rgba(255,255,255,0.06), transparent 52%)',
            ].join(','),
          }}
        />
        <div className="absolute inset-0 opacity-[0.05] [background-image:linear-gradient(rgba(255,255,255,0.06)_1px,transparent_1px),linear-gradient(90deg,rgba(255,255,255,0.04)_1px,transparent_1px)] [background-size:28px_28px] [mask-image:radial-gradient(ellipse_at_top,black_40%,transparent_75%)]" />
      </div>
      {/* Header */}
      <div className="flex items-start justify-between">
        <div>
          <div className="flex items-center gap-2 text-xs font-bold tracking-[0.3em] text-orange-300 uppercase mb-2">
            <Zap size={14} /> Quantitative Laboratory
          </div>
          <h1 className="font-display text-3xl font-bold text-white">Quant Lab</h1>
          <p className="text-white/50 mt-1 text-sm">Monte Carlo simulations, regime detection, risk analytics & backtesting</p>
        </div>
      </div>

      {/* Control Bar */}
      <div className="flex flex-wrap items-end gap-4 bg-white/[0.02] border border-white/[0.06] rounded-2xl p-5">
        <div className="flex-1 min-w-[200px]">
          <label className="text-[10px] text-white/40 uppercase tracking-wider block mb-1.5">Symbol</label>
          <div className="relative">
            <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-white/30" />
            <input
              value={symbol}
              onChange={(e) => setSymbol(e.target.value.toUpperCase())}
              onKeyDown={(e) => e.key === 'Enter' && runAnalysis()}
              className="w-full bg-black/40 border border-white/10 rounded-xl pl-9 pr-4 py-2.5 text-white text-sm font-mono focus:outline-none focus:border-orange-500/40"
              placeholder="Enter ticker"
            />
          </div>
        </div>

        <div className="flex-1 min-w-[200px]">
          <label className="text-[10px] text-white/40 uppercase tracking-wider block mb-1.5">Strategy</label>
          <select
            value={strategy}
            onChange={(e) => setStrategy(e.target.value)}
            className="w-full bg-black/40 border border-white/10 rounded-xl px-4 py-2.5 text-white text-sm focus:outline-none focus:border-orange-500/40 appearance-none"
          >
            {strategies.map(s => <option key={s.id} value={s.id}>{s.name}</option>)}
            {!strategies.length && <option value="momentum">Momentum</option>}
          </select>
        </div>

        <button
          onClick={runAnalysis}
          disabled={loading || !symbol.trim()}
          className="px-8 py-2.5 bg-gradient-to-r from-orange-600 to-amber-500 hover:from-orange-500 hover:to-amber-400 disabled:opacity-30 text-white text-sm font-medium rounded-xl transition-all duration-200 flex items-center gap-2 shadow-[0_0_0_1px_rgba(255,255,255,0.06)]"
        >
          {loading ? <Loader2 size={14} className="animate-spin" /> : <Zap size={14} />}
          Run Analysis
        </button>
      </div>

      {/* Error */}
      {error && (
        <div className="bg-red-500/10 border border-red-500/20 rounded-xl p-4 flex items-center gap-3">
          <AlertTriangle size={16} className="text-red-400 shrink-0" />
          <p className="text-sm text-red-300">{error}</p>
        </div>
      )}

      {/* Results */}
      {result && (
        <div className="space-y-6 animate-in fade-in slide-in-from-bottom-4 duration-500">
          {/* Summary Header */}
          <div className="flex items-center justify-between bg-white/[0.02] border border-white/[0.06] rounded-2xl p-5">
            <div className="flex items-center gap-4">
              <div className="w-12 h-12 rounded-2xl bg-gradient-to-br from-orange-500/20 to-amber-500/10 border border-white/10 flex items-center justify-center">
                <BarChart3 size={20} className="text-orange-300" />
              </div>
              <div>
                <div className="text-xl font-bold text-white font-display">{result.symbol}</div>
                <div className="text-xs text-white/40">{result.strategy} — 2 Year Backtest</div>
              </div>
            </div>
            <div className="flex gap-6">
              <div className="text-right">
                <div className="text-[10px] text-white/40 uppercase">Return</div>
                <div className={`text-2xl font-mono font-bold ${(metrics?.totalReturn ?? 0) >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>
                  {metrics?.totalReturn?.toFixed(2)}%
                </div>
              </div>
              <div className="text-right">
                <div className="text-[10px] text-white/40 uppercase">Sharpe</div>
                <div className="text-2xl font-mono font-bold text-white">{metrics?.sharpeRatio?.toFixed(2)}</div>
              </div>
              <div className="text-right">
                <div className="text-[10px] text-white/40 uppercase">Max DD</div>
                <div className="text-2xl font-mono font-bold text-red-400">{metrics?.maxDrawdown?.toFixed(2)}%</div>
              </div>
            </div>
          </div>

          {/* Core Metrics Grid */}
          <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-8 gap-3">
            <MetricCard label="Sortino" value={metrics?.sortinoRatio} good={(metrics?.sortinoRatio ?? 0) > 1} />
            <MetricCard label="Calmar" value={metrics?.calmarRatio} good={(metrics?.calmarRatio ?? 0) > 1} />
            <MetricCard label="Win Rate" value={metrics?.winRate} suffix="%" good={(metrics?.winRate ?? 0) > 50} />
            <MetricCard label="Trades" value={metrics?.totalTrades} />
            <MetricCard label="Profit Factor" value={metrics?.profitFactor} good={(metrics?.profitFactor ?? 0) > 1.5} />
            <MetricCard label="Ann. Vol" value={metrics?.annualVolatility} suffix="%" />
            <MetricCard label="SQN" value={metrics?.sqn} good={(metrics?.sqn ?? 0) > 2} />
            <MetricCard label="Expectancy" value={metrics?.expectancy} suffix="%" good={(metrics?.expectancy ?? 0) > 0} />
          </div>

          {/* Tab Navigation */}
          <div className="flex gap-1 bg-white/[0.02] border border-white/[0.06] rounded-xl p-1">
            {([
              { key: 'equity', label: 'Equity Curve', icon: TrendingUp },
              { key: 'montecarlo', label: 'Monte Carlo', icon: Activity },
              { key: 'risk', label: 'Risk Metrics', icon: Shield },
              { key: 'trades', label: 'Trade Log', icon: Layers },
            ] as const).map(tab => {
              const Icon = tab.icon;
              return (
                <button
                  key={tab.key}
                  onClick={() => setActiveTab(tab.key)}
                  className={`flex-1 flex items-center justify-center gap-2 py-2.5 rounded-lg text-xs font-medium transition-all ${
                    activeTab === tab.key
                      ? 'bg-orange-600/20 text-orange-300 border border-orange-500/30'
                      : 'text-white/40 hover:text-white/60 hover:bg-white/5'
                  }`}
                >
                  <Icon size={14} />
                  {tab.label}
                </button>
              );
            })}
          </div>

          {/* Tab Content */}
          <div className="bg-white/[0.02] border border-white/[0.06] rounded-2xl p-6">
            {activeTab === 'equity' && (
              <div className="space-y-4">
                <div className="flex items-center gap-2 text-xs font-bold uppercase tracking-[0.2em] text-orange-300 mb-4">
                  <TrendingUp size={14} /> Equity Curve
                </div>
                <EquityCurveChart data={equity} />
                {equity?.[0]?.benchmark != null && (
                  <div className="flex items-center gap-4 text-[10px] text-white/40">
                    <div className="flex items-center gap-2"><div className="w-4 h-0.5 bg-[#F97316]" /> Strategy</div>
                    <div className="flex items-center gap-2"><div className="w-4 h-0.5 bg-[#FBBF24] opacity-80" style={{ borderTop: '2px dashed #FBBF24' }} /> Benchmark</div>
                  </div>
                )}

                <div className="grid grid-cols-1 lg:grid-cols-3 gap-4 pt-2">
                  {equity.length > 1 && (
                    <div className="bg-black/40 rounded-xl p-4 border border-white/5">
                      <div className="flex items-center justify-between mb-2">
                        <div className="text-[10px] text-white/40 uppercase tracking-[0.2em]">Underwater</div>
                        <div className="text-[10px] font-mono text-orange-300/70">Drawdown</div>
                      </div>
                      <DrawdownChart data={equity} />
                    </div>
                  )}

                  {equity.length > 30 && (
                    <div className="bg-black/40 rounded-xl p-4 border border-white/5">
                      <div className="flex items-center justify-between mb-2">
                        <div className="text-[10px] text-white/40 uppercase tracking-[0.2em]">Stability</div>
                        <div className="text-[10px] font-mono text-orange-300/70">20D Vol</div>
                      </div>
                      <RollingVolatilityChart data={equity} window={20} />
                    </div>
                  )}

                  {equity.length > 12 && (
                    <div className="bg-black/40 rounded-xl p-4 border border-white/5">
                      <div className="flex items-center justify-between mb-2">
                        <div className="text-[10px] text-white/40 uppercase tracking-[0.2em]">Texture</div>
                        <div className="text-[10px] font-mono text-orange-300/70">Daily Returns</div>
                      </div>
                      <ReturnHistogramChart data={equity} />
                    </div>
                  )}
                </div>
              </div>
            )}

            {activeTab === 'montecarlo' && mc && (
              <div className="space-y-6">
                <div className="flex items-center gap-2 text-xs font-bold uppercase tracking-[0.2em] text-orange-200 mb-2">
                  <Activity size={14} /> Monte Carlo Simulation — {mc.simulations?.toLocaleString()} Paths
                </div>

                {/* Paths */}
                {(mc.simulationPaths?.length || mc.percentilePaths) && (
                  <div className="space-y-2">
                    <div className="text-[10px] text-white/40 uppercase">Simulation Paths</div>
                    <div className="h-72 bg-black/40 rounded-xl border border-white/5 overflow-hidden">
                      <MonteCarloPathsCanvas paths={mc.simulationPaths} percentilePaths={mc.percentilePaths} />
                    </div>
                    <div className="flex items-center gap-4 text-[10px] text-white/30">
                      <span className="text-red-400">━ P5</span>
                      <span className="text-amber-400">━ P25</span>
                      <span className="text-orange-300 font-bold">━ Median</span>
                      <span className="text-emerald-400">━ P75</span>
                      <span className="text-emerald-400">━ P95</span>
                    </div>
                  </div>
                )}

                {/* Distribution */}
                <div className="space-y-2">
                  <div className="text-[10px] text-white/40 uppercase">Return Distribution</div>
                  <MCDistributionChart histogram={mc.histogram} riskMetrics={mc.riskMetrics} />
                </div>

                {/* Percentiles */}
                {mc.percentiles && (
                  <div className="space-y-2">
                    <div className="text-[10px] text-white/40 uppercase">Percentile Breakdown</div>
                    <div className="grid grid-cols-7 gap-2">
                      {Object.entries(mc.percentiles).map(([key, val]) => (
                        <div key={key} className="bg-black/40 rounded-lg p-2.5 border border-white/5 text-center">
                          <div className="text-[9px] text-white/30 uppercase">{key}</div>
                          <div className="text-sm font-mono font-bold text-white">{((val as number) * 100).toFixed(1)}%</div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            )}

            {activeTab === 'risk' && mc?.riskMetrics && (
              <div className="space-y-6">
                <div className="flex items-center gap-2 text-xs font-bold uppercase tracking-[0.2em] text-red-400 mb-2">
                  <Shield size={14} /> Risk Analytics
                </div>
                <RiskGaugeSet metrics={mc.riskMetrics} />

                {/* Risk Breakdown */}
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div className="bg-black/40 rounded-xl p-5 border border-white/5 space-y-3">
                    <div className="text-xs font-bold text-white/60">Downside Risk</div>
                    <div className="space-y-2">
                      <div className="flex justify-between text-sm">
                        <span className="text-white/40">Max Drawdown</span>
                        <span className="font-mono text-red-400">{(metrics?.maxDrawdown ?? 0).toFixed(2)}%</span>
                      </div>
                      <div className="flex justify-between text-sm">
                        <span className="text-white/40">Median Max DD (MC)</span>
                        <span className="font-mono text-red-400">{((mc.riskMetrics.medianMaxDrawdown ?? 0) * 100).toFixed(2)}%</span>
                      </div>
                      <div className="flex justify-between text-sm">
                        <span className="text-white/40">Annualized Vol</span>
                        <span className="font-mono text-white">{(metrics?.annualVolatility ?? 0).toFixed(2)}%</span>
                      </div>
                    </div>
                  </div>
                  <div className="bg-black/40 rounded-xl p-5 border border-white/5 space-y-3">
                    <div className="text-xs font-bold text-white/60">Trade Quality</div>
                    <div className="space-y-2">
                      <div className="flex justify-between text-sm">
                        <span className="text-white/40">Avg Win</span>
                        <span className="font-mono text-emerald-400">{metrics?.avgWin != null ? `${metrics.avgWin.toFixed(2)}%` : '—'}</span>
                      </div>
                      <div className="flex justify-between text-sm">
                        <span className="text-white/40">Avg Loss</span>
                        <span className="font-mono text-red-400">{metrics?.avgLoss != null ? `${metrics.avgLoss.toFixed(2)}%` : '—'}</span>
                      </div>
                      <div className="flex justify-between text-sm">
                        <span className="text-white/40">Best Trade</span>
                        <span className="font-mono text-emerald-400">{metrics?.bestTrade != null ? `${metrics.bestTrade.toFixed(2)}%` : '—'}</span>
                      </div>
                      <div className="flex justify-between text-sm">
                        <span className="text-white/40">Worst Trade</span>
                        <span className="font-mono text-red-400">{metrics?.worstTrade != null ? `${metrics.worstTrade.toFixed(2)}%` : '—'}</span>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            )}

            {activeTab === 'trades' && (
              <div className="space-y-4">
                <div className="flex items-center gap-2 text-xs font-bold uppercase tracking-[0.2em] text-orange-300 mb-2">
                  <Layers size={14} /> Trade History
                </div>

                {trades.length > 8 && (
                  <div className="bg-black/40 rounded-xl p-4 border border-white/5">
                    <div className="flex items-center justify-between mb-2">
                      <div className="text-[10px] text-white/40 uppercase tracking-[0.2em]">Distribution</div>
                      <div className="text-[10px] font-mono text-orange-300/70">PnL / Trade</div>
                    </div>
                    <TradePnLHistogramChart trades={trades} />
                  </div>
                )}

                <TradeLog trades={trades} />
              </div>
            )}
          </div>
        </div>
      )}

      {/* Empty State */}
      {!result && !loading && !error && (
        <div className="flex flex-col items-center justify-center py-20 text-center">
          <div className="w-20 h-20 rounded-3xl bg-gradient-to-br from-orange-600/10 to-amber-500/5 border border-white/[0.04] flex items-center justify-center mb-6">
            <Brain size={32} className="text-orange-300/50" />
          </div>
          <h2 className="font-display text-xl font-bold text-white/60 mb-2">Select a symbol to begin</h2>
          <p className="text-white/30 text-sm max-w-md">
            The Quant Lab runs institutional-grade backtests with Monte Carlo simulations,
            risk analysis, and strategy optimization.
          </p>
        </div>
      )}

      {/* Loading */}
      {loading && (
        <div className="flex flex-col items-center justify-center py-20">
          <Loader2 size={32} className="text-orange-300 animate-spin mb-4" />
          <p className="text-white/40 text-sm">Running quantitative analysis...</p>
          <p className="text-white/20 text-[10px] mt-1">Monte Carlo · Backtest · Risk Engine</p>
        </div>
      )}
    </div>
  );
}
