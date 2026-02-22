import { useState, useRef, useEffect, useCallback } from 'react';
import {
  Send,
  Terminal,
  Loader2,
  TrendingUp,
  TrendingDown,
  BarChart3,
  Activity,
  Zap,
  AlertTriangle,
  Globe2,
  Cpu,
  Maximize2,
  Minimize2,
  Copy,
  Check,
  User,
} from 'lucide-react';
import {
  BarChart, Bar,
  LineChart, Line,
  XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid, ReferenceLine, Cell,
} from 'recharts';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { createChart, ColorType, LineSeries, type IChartApi, type ISeriesApi } from 'lightweight-charts';
import { LightweightChart } from '@/components/LightweightChart';
import { investorProfileAPI } from '../api';

const API_BASE = (import.meta.env.VITE_API_BASE_URL || import.meta.env.VITE_API_BASE || 'http://127.0.0.1:8001').replace(/\/$/, '');
const WS_URL = `${API_BASE.replace(/^http/i, 'ws')}/ws/live`;
const BACKTEST_WS_URL = `${API_BASE.replace(/^http/i, 'ws')}/api/backtest/ws`;

// ─── Helper Functions ────────────────────────────────────────────────────────────

function stdev(values: number[]) {
  if (values.length < 2) return 0;
  const mean = values.reduce((a, b) => a + b, 0) / values.length;
  const variance = values.reduce((acc, v) => acc + (v - mean) ** 2, 0) / (values.length - 1);
  return Math.sqrt(variance);
}

function toReturns(series: { date: string; value: number }[]) {
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

// ─── Types ──────────────────────────────────────────────────────────────────────

interface AgentStep {
  tool: string;
  args: any;
  description: string;
  result?: string;
  status?: 'pending' | 'running' | 'done' | 'error';
}

interface StrategyData {
  regime?: { regime: string; volatility: number; trend_signal: string };
  best_strategy?: {
    strategy: string;
    return: number;
    win_rate: number;
    last_signal?: number;
    equity_curve?: Array<{ time: string; value: number; date?: string }>;
    signals?: Array<{ time: string; type: string; price: number }>;
    price_data?: Array<{ time: string; open: number; high: number; low: number; close: number; volume: number }>;
    trades?: Array<{ side: string; pnlPct?: number; [key: string]: any }>;
    monteCarlo?: {
      simulations?: number;
      histogram?: Array<{ return: number; count: number }>;
      percentiles?: Record<string, number>;
      riskMetrics?: {
        var95?: number;
        cvar95?: number;
        ruinProbability?: number;
        medianMaxDrawdown?: number;
        worstCase?: number;
        bestCase?: number;
        meanReturn?: number;
      };
      simulationPaths?: number[][];
      percentilePaths?: Record<string, number[]>;
      pathSteps?: number;
    };
  };
  all_strategies?: Array<{ strategy: string; return: number; win_rate: number }>;
  ai_reasoning?: string;
  trade_levels?: { action: string; entry_price: number; stop_loss: number; take_profit: number };
  monte_carlo?: { expected_price: number; worst_case: number; best_case: number; simulation_paths: number[][]; days?: number };
  position_sizing?: { position_size_shares: number; risk_amount: number };
}

interface FinancialData {
  ticker?: string;
  price?: number;
  score?: number;
}

interface RiskData {
  VaR?: number;
  CVaR?: number;
  Max_Drawdown?: number;
}

interface AgentResponse {
  report?: string;
  response?: string;
  request_id?: string;
  error?: string;
  financial?: FinancialData;
  strategy?: StrategyData;
  risk_engine?: RiskData;
  confidence?: number;
  divergence?: string[];
  plan?: { thought: string; steps: AgentStep[] };
  execution_log?: AgentStep[];
  status?: string;
}

interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: Date;
  agentData?: AgentResponse;
  isStreaming?: boolean;
}

interface UserProfile {
  user_id?: string;
  name?: string;
  age?: number;
  monthly_income?: number;
  monthly_savings?: number;
  risk_tolerance?: string;
  horizon_years?: number;
  primary_goal?: string;
  existing_investments?: string;
  market?: string;
}

let _idCounter = 0;
let _reqCounter = 0;

function uid() { 
  return "msg-" + Date.now() + "-" + (++_idCounter);
}

function reqid() {
  return "req-" + Date.now() + "-" + (++_reqCounter);
}

// ─── Terminal Scanline Effect ───────────────────────────────────────────────────

function TerminalScanlines() {
  return (
    <div className="pointer-events-none fixed inset-0 z-50">
      <div className="absolute inset-0 bg-[linear-gradient(transparent_50%,rgba(255,107,53,0.02)_50%)] bg-[length:100%_4px] animate-[scan_8s_linear_infinite]" />
      <div className="absolute inset-0 bg-[radial-gradient(circle_at_50%_50%,transparent_0%,rgba(0,0,0,0.3)_100%)]" />
    </div>
  );
}

// ─── Market Ticker Tape ──────────────────────────────────────────────────────────

function TickerTape({ ticker, price, change }: { ticker?: string; price?: number; change?: number }) {
  const safeTicker = (ticker || 'MARKET').toUpperCase();
  const hasPrice = typeof price === 'number' && Number.isFinite(price);
  const hasChange = typeof change === 'number' && Number.isFinite(change);

  const priceText = hasPrice ? `$${price.toFixed(2)}` : '—';
  const changeText = hasChange ? `${change >= 0 ? '+' : ''}${change.toFixed(2)}%` : '—';

  return (
    <div className="flex items-center gap-6 font-mono text-xs border-b border-orange-600/20 pb-2 mb-2">
      <div className="flex items-center gap-2">
        <div className="w-2 h-2 bg-orange-500 rounded-full animate-pulse" />
        <span className="text-orange-500 font-bold tracking-wider">{safeTicker}</span>
      </div>
      <div className="text-white font-bold">{priceText}</div>
      {hasChange ? (
        <div className={`flex items-center gap-1 ${change >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>
          {change >= 0 ? <TrendingUp size={12} /> : <TrendingDown size={12} />}
          <span className="font-bold">{changeText}</span>
        </div>
      ) : (
        <div className="flex items-center gap-1 text-white/40">
          <span className="font-bold">{changeText}</span>
        </div>
      )}
    </div>
  );
}

// ─── Backtest Chart Component ────────────────────────────────────────────────────

interface BacktestChartProps {
  // Accept either backend format ({ time, value }) or legacy demo format ({ date, equity })
  data?: Array<{ time: string; value: number } | { date: string; equity: number }>;
}

function BacktestChart({ data }: BacktestChartProps) {
  const chartContainerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<IChartApi | null>(null);
  const seriesRef = useRef<ISeriesApi<'Line'> | null>(null);

  useEffect(() => {
    if (!chartContainerRef.current) return;

    try {
      const chart = createChart(chartContainerRef.current, {
        layout: {
          background: { type: ColorType.Solid, color: 'transparent' },
          textColor: '#666',
        },
        grid: {
          vertLines: { color: 'rgba(255, 107, 53, 0.05)' },
          horzLines: { color: 'rgba(255, 107, 53, 0.05)' },
        },
        width: chartContainerRef.current.clientWidth,
        height: 200,
        timeScale: {
          borderColor: 'rgba(255, 107, 53, 0.2)',
          timeVisible: true,
        },
        rightPriceScale: {
          borderColor: 'rgba(255, 107, 53, 0.2)',
        },
      });

      const lineSeries = chart.addSeries(LineSeries, {
        color: '#FF6B35',
        lineWidth: 2,
      });

      chartRef.current = chart;
      seriesRef.current = lineSeries;

      const toPoint = (d: any) => {
        if (typeof d?.time === 'string' && typeof d?.value === 'number') {
          return { time: d.time, value: d.value };
        }
        if (typeof d?.date === 'string' && typeof d?.equity === 'number') {
          return { time: d.date, value: d.equity };
        }
        return null;
      };

      // Sample data if none provided - use simple incremental timestamps
      const prand = (n: number) => {
        const x = Math.sin(n * 9999.123) * 10000;
        return x - Math.floor(x);
      };

      const sampleData = (data?.map(toPoint).filter(Boolean) as Array<{ time: string; value: number }>) || Array.from({ length: 50 }, (_, i) => {
        const date = new Date(2024, 0, 1); // Jan 1, 2024
        date.setDate(date.getDate() + i);
        return {
          time: date.toISOString().split('T')[0],
          value: 10000 + prand(i) * 2000 + i * 100,
        };
      });

      lineSeries.setData(sampleData);
      chart.timeScale().fitContent();

      const handleResize = () => {
        if (chartContainerRef.current && chart) {
          chart.applyOptions({ width: chartContainerRef.current.clientWidth });
        }
      };

      window.addEventListener('resize', handleResize);
      
      // Use ResizeObserver to detect container size changes (e.g., when Analytics Terminal expands)
      let resizeObserver: ResizeObserver | null = null;
      
      if (chartContainerRef.current) {
        resizeObserver = new ResizeObserver(() => {
          requestAnimationFrame(handleResize);
        });
        resizeObserver.observe(chartContainerRef.current);
      }

      return () => {
        window.removeEventListener('resize', handleResize);
        if (resizeObserver && chartContainerRef.current) {
          resizeObserver.unobserve(chartContainerRef.current);
          resizeObserver.disconnect();
        }
        if (chart) {
          chart.remove();
        }
      };
    } catch (error) {
      console.error('Error creating chart:', error);
    }
  }, [data]);

  // Lightweight Charts needs a non-zero container height.
  return <div ref={chartContainerRef} className="w-full h-[200px]" />;
}

// ─── Monte Carlo Distribution Chart ──────────────────────────────────────────────

function MonteCarloChart({ expected, worst, best }: { expected?: number; worst?: number; best?: number }) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const drawChart = () => {
    try {
      const canvas = canvasRef.current;
      const container = containerRef.current;
      if (!canvas || !container) return;

      const ctx = canvas.getContext('2d');
      if (!ctx) return;

      // Get container dimensions and set canvas size with proper DPI scaling
      const dpr = window.devicePixelRatio || 1;
      const rect = container.getBoundingClientRect();
      
      // Skip if container has no size yet
      if (rect.width === 0 || rect.height === 0) return;
      
      canvas.width = rect.width * dpr;
      canvas.height = 250 * dpr;
      canvas.style.width = `${rect.width}px`;
      canvas.style.height = '250px';
      
      ctx.scale(dpr, dpr);

      const width = rect.width;
      const height = 250;
      const padding = 20; // Add padding to prevent cutoff

      // Clear canvas
      ctx.clearRect(0, 0, width, height);

      // Generate normal distribution curve
      const mean = expected || 0.05;
      const worstVal = worst || -0.05;
      const bestVal = best || 0.15;
      const stdDev = (bestVal - worstVal) / 4;
      const points = 150;

      // Calculate max height for proper scaling
      let maxY = 0;
      const yValues: number[] = [];
      for (let i = 0; i <= points; i++) {
        const value = worstVal + (bestVal - worstVal) * (i / points);
        const exponent = -Math.pow(value - mean, 2) / (2 * Math.pow(stdDev, 2));
        const normalizedY = Math.exp(exponent) / (stdDev * Math.sqrt(2 * Math.PI));
        yValues.push(normalizedY);
        maxY = Math.max(maxY, normalizedY);
      }

      // Draw the distribution curve
      ctx.beginPath();
      ctx.strokeStyle = '#FF6B35';
      ctx.lineWidth = 2.5;

      for (let i = 0; i <= points; i++) {
        const x = padding + (i / points) * (width - 2 * padding);
        const scaledY = (yValues[i] / maxY) * (height - 2 * padding);
        const y = height - padding - scaledY;

        if (i === 0) ctx.moveTo(x, y);
        else ctx.lineTo(x, y);
      }

      ctx.stroke();

      // Fill area under curve
      ctx.lineTo(width - padding, height - padding);
      ctx.lineTo(padding, height - padding);
      ctx.closePath();
      ctx.fillStyle = 'rgba(255, 107, 53, 0.15)';
      ctx.fill();

      // Draw expected value marker (dotted line)
      const markerX = padding + ((mean - worstVal) / (bestVal - worstVal)) * (width - 2 * padding);
      
      ctx.strokeStyle = '#ff00ff';
      ctx.lineWidth = 2;
      ctx.setLineDash([5, 5]);
      ctx.beginPath();
      ctx.moveTo(markerX, padding);
      ctx.lineTo(markerX, height - padding);
      ctx.stroke();
      ctx.setLineDash([]);

      // Draw worst case marker (left)
      ctx.strokeStyle = '#ef4444';
      ctx.lineWidth = 1.5;
      ctx.setLineDash([3, 3]);
      ctx.beginPath();
      ctx.moveTo(padding, padding);
      ctx.lineTo(padding, height - padding);
      ctx.stroke();
      ctx.setLineDash([]);

      // Draw best case marker (right)
      ctx.strokeStyle = '#22c55e';
      ctx.lineWidth = 1.5;
      ctx.setLineDash([3, 3]);
      ctx.beginPath();
      ctx.moveTo(width - padding, padding);
      ctx.lineTo(width - padding, height - padding);
      ctx.stroke();
      ctx.setLineDash([]);

    } catch (error) {
      console.error('MonteCarloChart error:', error);
    }
    };

    drawChart();

    // Redraw on window resize
    window.addEventListener('resize', drawChart);
    
    // Use ResizeObserver to detect container size changes (e.g., when Analytics Terminal expands)
    const container = containerRef.current;
    let resizeObserver: ResizeObserver | null = null;
    
    if (container) {
      resizeObserver = new ResizeObserver(() => {
        requestAnimationFrame(drawChart);
      });
      resizeObserver.observe(container);
    }
    
    return () => {
      window.removeEventListener('resize', drawChart);
      if (resizeObserver && container) {
        resizeObserver.unobserve(container);
        resizeObserver.disconnect();
      }
    };
  }, [expected, worst, best]);

  return (
    <div ref={containerRef} className="w-full h-[250px]">
      <canvas
        ref={canvasRef}
        className="w-full h-full"
      />
    </div>
  );
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

function MCDistributionChart({ histogram, riskMetrics }: { histogram?: any[]; riskMetrics?: any }) {
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
          {riskMetrics?.var95 != null && <ReferenceLine x={riskMetrics.var95 / 100} stroke="#f87171" strokeDasharray="5 5" label={{ value: 'VaR 95%', position: 'top', fill: '#f87171', fontSize: 9 }} />}
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

// ─── Return Histogram Chart ──────────────────────────────────────────────────────

function ReturnHistogramChart({ data, bins = 24 }: { data: { date: string; value: number }[]; bins?: number }) {
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

// ─── Rolling Volatility Chart ────────────────────────────────────────────────────

function RollingVolatilityChart({ data, window = 20 }: { data: { date: string; value: number }[]; window?: number }) {
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

// ─── Trade PnL Histogram Chart ───────────────────────────────────────────────────

function TradePnLHistogramChart({ trades, bins = 18 }: { trades: any[]; bins?: number }) {
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

// ─── Risk Gauge Set ──────────────────────────────────────────────────────────────

function RiskGaugeSet({ metrics }: { metrics: any }) {
  if (!metrics) return null;
  const items = [
    { label: 'VaR 95%', value: metrics.var95, color: 'text-red-400', fmt: (v: number) => `${v.toFixed(2)}%` },
    { label: 'CVaR 95%', value: metrics.cvar95, color: 'text-red-500', fmt: (v: number) => `${v.toFixed(2)}%` },
    { label: 'Mean Return', value: metrics.meanReturn, color: 'text-emerald-400', fmt: (v: number) => `${v.toFixed(2)}%` },
    { label: 'Worst Case', value: metrics.worstCase, color: 'text-red-300', fmt: (v: number) => `${v.toFixed(1)}%` },
    { label: 'Best Case', value: metrics.bestCase, color: 'text-green-300', fmt: (v: number) => `${v.toFixed(1)}%` },
    { label: 'Ruin Prob', value: metrics.ruinProbability, color: 'text-amber-400', fmt: (v: number) => `${v.toFixed(2)}%` },
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

// ─── Risk Gauge ──────────────────────────────────────────────────────────────────

function RiskGauge({ value, label }: { value: number; label: string }) {
  const percentage = Math.min(Math.abs(value * 100), 100);
  const rotation = (percentage / 100) * 180 - 90;

  return (
    <div className="flex flex-col items-center">
      <div className="relative w-24 h-12 overflow-hidden">
        <div className="absolute bottom-0 left-0 w-full h-1 bg-gradient-to-r from-emerald-500 via-yellow-500 to-red-500 rounded-full opacity-30" />
        <div
          className="absolute bottom-0 left-1/2 w-0.5 h-12 bg-orange-500 origin-bottom transition-all duration-1000 shadow-[0_0_10px_#FF6B35]"
          style={{ transform: `translateX(-50%) rotate(${rotation}deg)` }}
        />
        <div className="absolute bottom-0 left-1/2 w-2 h-2 bg-orange-500 rounded-full -translate-x-1/2 shadow-[0_0_10px_#FF6B35]" />
      </div>
      <div className="text-[10px] text-orange-500 font-mono mt-1 tracking-wider">{label}</div>
      <div className="text-xs text-white font-mono font-bold">{(value * 100).toFixed(2)}%</div>
    </div>
  );
}

// ─── Analytics Dashboard Panel ───────────────────────────────────────────────────

function AnalyticsDashboard({ 
  agentData, 
  ticker, 
  onExpandToggle, 
  isExpanded,
  runBacktestViaWebSocket,
  backtestWsStatus,
}: { 
  agentData?: AgentResponse; 
  ticker?: string;
  onExpandToggle: () => void;
  isExpanded: boolean;
  runBacktestViaWebSocket: (ticker: string, strategy: string) => void;
  backtestWsStatus: string;
}) {
  const [expandedSections, setExpandedSections] = useState({
    priceChart: true,
    backtest: true,
    monteCarlo: true,
    risk: true,
    strategy: true,
  });

  const toggleSection = (section: keyof typeof expandedSections) => {
    setExpandedSections(prev => ({ ...prev, [section]: !prev[section] }));
  };

  // Debug: Log received data structure
  useEffect(() => {
    try {
    if (agentData) {
      console.log('📊 Analytics Dashboard received data:', agentData);
      console.log('  - financial:', agentData.financial);
      console.log('  - strategy:', agentData.strategy);
      console.log('  - risk_engine:', agentData.risk_engine);
    }
    } catch (error) {
      console.error('Analytics debug error:', error);
    }
  }, [agentData]);

  return (
    <>
      <style>
        {`
          @keyframes scan {
            0% { transform: translateY(-100%); }
            100% { transform: translateY(100vh); }
          }
          @keyframes glitch {
            0%, 100% { transform: translateX(0); }
            20% { transform: translateX(-2px); }
            40% { transform: translateX(2px); }
            60% { transform: translateX(-2px); }
            80% { transform: translateX(2px); }
          }
          @keyframes pulse-data {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.7; }
          }
          .terminal-border {
            border-image: linear-gradient(
              135deg,
              rgba(255, 107, 53, 0.3),
              transparent,
              rgba(255, 0, 255, 0.3)
            ) 1;
          }
          .data-stream {
            animation: pulse-data 2s ease-in-out infinite;
          }
        `}
      </style>

      <div className="flex flex-col w-full">
        {/* Header */}
        <div className="flex items-center justify-between mb-4 border-b border-orange-600/20 pb-3">
          <div className="flex items-center gap-3">
            <div className="relative">
              <Terminal size={20} className="text-orange-500" />
              <div className="absolute -inset-1 bg-orange-500/20 blur rounded-full -z-10" />
            </div>
            <div>
              <h2 className="font-mono text-sm font-bold text-orange-500 tracking-wider">ANALYTICS TERMINAL</h2>
              <div className="flex items-center gap-2 mt-0.5">
                <div className="w-1.5 h-1.5 bg-emerald-400 rounded-full animate-pulse" />
                <span className="text-[9px] text-white/40 font-mono tracking-wider">LIVE FEED</span>
              </div>
            </div>
          </div>
          <div className="flex items-center gap-2">
            {ticker && (
              <button
                onClick={() => runBacktestViaWebSocket(ticker, 'momentum')}
                disabled={!!backtestWsStatus}
                className="px-2 py-1 text-[10px] font-mono bg-cyan-600/10 hover:bg-cyan-600/20 border border-cyan-500/30 rounded text-cyan-300 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                title="Run live backtest via WebSocket"
              >
                <div className="flex items-center gap-1.5">
                  <Zap size={10} />
                  WS BACKTEST
                </div>
              </button>
            )}
            <button
              onClick={onExpandToggle}
              className="p-1.5 hover:bg-orange-600/10 rounded border border-orange-600/20 transition-colors"
              title={isExpanded ? 'Minimize Analytics' : 'Expand Analytics Fullscreen'}
            >
              {isExpanded ? <Minimize2 size={14} className="text-orange-500" /> : <Maximize2 size={14} className="text-orange-500" />}
            </button>
          </div>
        </div>

        <div className="space-y-4 overflow-y-auto pr-2 flex-1">
            {/* Ticker Tape - Always show */}
            <div className="terminal-border border-2 rounded-lg p-3 bg-black/40 backdrop-blur-sm">
              <TickerTape
                ticker={ticker || 'MARKET'}
                price={agentData?.financial?.price}
                change={undefined}
              />
            </div>

            {/* Price Chart (when available) */}
            {agentData?.strategy?.best_strategy?.price_data && agentData.strategy.best_strategy.price_data.length > 0 && (() => {
              const priceData = agentData.strategy.best_strategy.price_data;
              const signals = agentData.strategy.best_strategy.signals;
              
              try {
                return (
                  <div className="terminal-border border-2 rounded-lg p-4 bg-black/40 backdrop-blur-sm">
                    <div className="flex items-center justify-between mb-3">
                      <div className="flex items-center gap-2">
                        <TrendingUp size={14} className="text-orange-500" />
                        <span className="font-mono text-xs text-orange-500 tracking-wider">PRICE ACTION</span>
                      </div>
                      <button
                        onClick={() => toggleSection('priceChart')}
                        className="p-1 hover:bg-orange-600/10 rounded transition-colors"
                      >
                        {expandedSections.priceChart ? <Minimize2 size={12} className="text-orange-500" /> : <Maximize2 size={12} className="text-orange-500" />}
                      </button>
                    </div>
                    {expandedSections.priceChart && (
                    <div className={`w-full transition-all duration-300 ${expandedSections.priceChart ? 'h-[340px]' : 'h-[160px]'}`}>
                      <LightweightChart
                    data={{
                      candleData: priceData.map((d) => ({
                        time: d.time,
                        open: d.open,
                        high: d.high,
                        low: d.low,
                        close: d.close,
                      })),
                      volumeData: priceData.map((d) => ({
                        time: d.time,
                        value: d.volume,
                        color: d.close >= d.open ? 'rgba(34, 197, 94, 0.35)' : 'rgba(239, 68, 68, 0.35)',
                      })),
                      markers: signals || [],
                    }}
                    chartType="candle"
                    height={expandedSections.priceChart ? 340 : 160}
                    colors={{
                      backgroundColor: 'transparent',
                      textColor: '#9ca3af',
                      gridColor: 'rgba(255, 255, 255, 0.05)',
                      upColor: '#22c55e',
                      downColor: '#ef4444',
                    }}
                  />
                </div>
                    )}
              </div>
                );
              } catch (error) {
                console.error('Price chart error:', error);
                return null;
              }
            })()}

            {/* Backtest Chart */}
            <div className="terminal-border border-2 rounded-lg p-4 bg-black/40 backdrop-blur-sm">
              <div className="flex items-center justify-between mb-3">
                <div className="flex items-center gap-2">
                  <Activity size={14} className="text-orange-500" />
                  <span className="font-mono text-xs text-orange-500 tracking-wider">BACKTEST EQUITY CURVE</span>
                </div>
                <button
                  onClick={() => toggleSection('backtest')}
                  className="p-1 hover:bg-orange-600/10 rounded transition-colors"
                >
                  {expandedSections.backtest ? <Minimize2 size={12} className="text-orange-500" /> : <Maximize2 size={12} className="text-orange-500" />}
                </button>
              </div>
              {expandedSections.backtest && (
                <>
              <BacktestChart data={agentData?.strategy?.best_strategy?.equity_curve} />
              <div className="grid grid-cols-3 gap-2 mt-3 pt-3 border-t border-orange-600/20">
                <div>
                  <div className="text-[9px] text-white/40 font-mono">TOTAL RETURN</div>
                  <div className="text-sm text-emerald-400 font-mono font-bold">
                    {typeof agentData?.strategy?.best_strategy?.return === 'number'
                      ? `${agentData.strategy.best_strategy.return >= 0 ? '+' : ''}${agentData.strategy.best_strategy.return.toFixed(2)}%`
                      : '+—'}
                  </div>
                </div>
                <div>
                  <div className="text-[9px] text-white/40 font-mono">SHARPE</div>
                  <div className="text-sm text-white font-mono font-bold">1.82</div>
                </div>
                <div>
                  <div className="text-[9px] text-white/40 font-mono">WIN RATE</div>
                  <div className="text-sm text-orange-500 font-mono font-bold">
                    {typeof agentData?.strategy?.best_strategy?.win_rate === 'number'
                      ? `${agentData.strategy.best_strategy.win_rate.toFixed(0)}%`
                      : '—%'}
                  </div>
                </div>
              </div>
              
              {/* Advanced Analytics Grid */}
              {agentData?.strategy?.best_strategy?.equity_curve && (() => {
                const equityCurve = agentData.strategy.best_strategy.equity_curve.map(d => ({
                  date: d.date || d.time,
                  value: d.value
                }));
                
                return (
                <div className="grid grid-cols-1 lg:grid-cols-3 gap-4 mt-4 pt-4 border-t border-orange-600/20">
                  {/* Rolling Volatility */}
                  {equityCurve.length > 30 && (
                    <div className="bg-black/40 rounded-xl p-4 border border-white/5">
                      <div className="flex items-center justify-between mb-2">
                        <div className="text-[10px] text-white/40 uppercase tracking-[0.2em]">Stability</div>
                        <div className="text-[10px] font-mono text-orange-300/70">20D Vol</div>
                      </div>
                      <RollingVolatilityChart data={equityCurve} window={20} />
                    </div>
                  )}
                  
                  {/* Return Distribution */}
                  {equityCurve.length > 12 && (
                    <div className="bg-black/40 rounded-xl p-4 border border-white/5">
                      <div className="flex items-center justify-between mb-2">
                        <div className="text-[10px] text-white/40 uppercase tracking-[0.2em]">Returns</div>
                        <div className="text-[10px] font-mono text-orange-300/70">Daily</div>
                      </div>
                      <ReturnHistogramChart data={equityCurve} />
                    </div>
                  )}
                  
                  {/* Trade PnL Distribution */}
                  {agentData.strategy.best_strategy.trades && agentData.strategy.best_strategy.trades.length > 8 && (
                    <div className="bg-black/40 rounded-xl p-4 border border-white/5">
                      <div className="flex items-center justify-between mb-2">
                        <div className="text-[10px] text-white/40 uppercase tracking-[0.2em]">Trade PnL</div>
                        <div className="text-[10px] font-mono text-orange-300/70">Distribution</div>
                      </div>
                      <TradePnLHistogramChart trades={agentData.strategy.best_strategy.trades} />
                    </div>
                  )}
                </div>
                );
              })()}
                </>
              )}
            </div>

            {/* Monte Carlo Simulation */}
            <div className="terminal-border border-2 rounded-lg p-4 bg-black/40 backdrop-blur-sm">
              <div className="flex items-center justify-between mb-3">
                <div className="flex items-center gap-2">
                  <BarChart3 size={14} className="text-orange-500" />
                  <span className="font-mono text-xs text-orange-500 tracking-wider">MONTE CARLO SIMULATION</span>
                </div>
                <button
                  onClick={() => toggleSection('monteCarlo')}
                  className="p-1 hover:bg-orange-600/10 rounded transition-colors"
                >
                  {expandedSections.monteCarlo ? <Minimize2 size={12} className="text-orange-500" /> : <Maximize2 size={12} className="text-orange-500" />}
                </button>
              </div>
              {expandedSections.monteCarlo && (
                <>
                {/* Monte Carlo Paths Visualization */}
                {(agentData?.strategy?.best_strategy?.monteCarlo?.simulationPaths?.length || 
                  agentData?.strategy?.best_strategy?.monteCarlo?.percentilePaths) && (
                  <div className="mb-4">
                    <div className="text-[10px] text-white/40 uppercase mb-2 tracking-wider">
                      {agentData?.strategy?.best_strategy?.monteCarlo?.simulations?.toLocaleString()} Simulation Paths
                    </div>
                    <div className="h-72 bg-black/40 rounded-xl border border-white/5 overflow-hidden">
                      <MonteCarloPathsCanvas 
                        paths={agentData?.strategy?.best_strategy?.monteCarlo?.simulationPaths} 
                        percentilePaths={agentData?.strategy?.best_strategy?.monteCarlo?.percentilePaths} 
                      />
                    </div>
                    <div className="flex items-center gap-4 text-[10px] text-white/30 mt-2">
                      <span className="text-red-400">━ P5</span>
                      <span className="text-amber-400">━ P25</span>
                      <span className="text-orange-300 font-bold">━ Median</span>
                      <span className="text-emerald-400">━ P75</span>
                      <span className="text-emerald-400">━ P95</span>
                    </div>
                  </div>
                )}
                
                {/* Distribution Histogram */}
                {agentData?.strategy?.best_strategy?.monteCarlo?.histogram && (
                  <div className="mb-4">
                    <div className="text-[10px] text-white/40 uppercase mb-2 tracking-wider">Return Distribution</div>
                    <MCDistributionChart 
                      histogram={agentData?.strategy?.best_strategy?.monteCarlo?.histogram} 
                      riskMetrics={agentData?.strategy?.best_strategy?.monteCarlo?.riskMetrics} 
                    />
                  </div>
                )}
                
                {/* Risk Metrics */}
                {agentData?.strategy?.best_strategy?.monteCarlo?.riskMetrics && (
                  <div className="mb-4">
                    <div className="text-[10px] text-white/40 uppercase mb-2 tracking-wider">Risk Metrics</div>
                    <RiskGaugeSet metrics={agentData?.strategy?.best_strategy?.monteCarlo?.riskMetrics} />
                  </div>
                )}
                
                {/* Legacy Simple Distribution (fallback) */}
                {!agentData?.strategy?.best_strategy?.monteCarlo?.histogram && (
                  <>
                    <MonteCarloChart
                      expected={agentData?.strategy?.monte_carlo?.expected_price ? agentData.strategy.monte_carlo.expected_price / 100 : 0.08}
                      worst={agentData?.strategy?.monte_carlo?.worst_case ? agentData.strategy.monte_carlo.worst_case / 100 : -0.05}
                      best={agentData?.strategy?.monte_carlo?.best_case ? agentData.strategy.monte_carlo.best_case / 100 : 0.18}
                    />
                    <div className="grid grid-cols-3 gap-2 mt-3 pt-3 border-t border-orange-600/20">
                      <div>
                        <div className="text-[9px] text-red-400 font-mono">5% VaR</div>
                        <div className="text-xs text-red-400 font-mono font-bold">
                          {((agentData?.strategy?.monte_carlo?.worst_case || -5) ).toFixed(1)}%
                        </div>
                      </div>
                      <div>
                        <div className="text-[9px] text-orange-500 font-mono">EXPECTED</div>
                        <div className="text-xs text-orange-500 font-mono font-bold">
                          {((agentData?.strategy?.monte_carlo?.expected_price || 8) ).toFixed(1)}%
                        </div>
                      </div>
                      <div>
                        <div className="text-[9px] text-emerald-400 font-mono">95% BEST</div>
                        <div className="text-xs text-emerald-400 font-mono font-bold">
                          {((agentData?.strategy?.monte_carlo?.best_case || 18) ).toFixed(1)}%
                        </div>
                      </div>
                    </div>
                  </>
                )}
                
                {/* Percentile Breakdown */}
                {agentData?.strategy?.best_strategy?.monteCarlo?.percentiles && (
                  <div className="mt-4">
                    <div className="text-[10px] text-white/40 uppercase mb-2 tracking-wider">Percentile Breakdown</div>
                    <div className="grid grid-cols-7 gap-2">
                      {Object.entries(agentData.strategy.best_strategy.monteCarlo.percentiles).map(([key, val]) => (
                        <div key={key} className="bg-black/40 rounded-lg p-2.5 border border-white/5 text-center">
                          <div className="text-[9px] text-white/30 uppercase">{key}</div>
                          <div className="text-sm font-mono font-bold text-white">{((val as number)).toFixed(1)}%</div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
                </>
              )}
            </div>

            {/* Risk Metrics */}
            <div className="terminal-border border-2 rounded-lg p-4 bg-black/40 backdrop-blur-sm">
              <div className="flex items-center justify-between mb-4">
                <div className="flex items-center gap-2">
                  <AlertTriangle size={14} className="text-orange-500" />
                  <span className="font-mono text-xs text-orange-500 tracking-wider">RISK ANALYSIS</span>
                </div>
                <button
                  onClick={() => toggleSection('risk')}
                  className="p-1 hover:bg-orange-600/10 rounded transition-colors"
                >
                  {expandedSections.risk ? <Minimize2 size={12} className="text-orange-500" /> : <Maximize2 size={12} className="text-orange-500" />}
                </button>
              </div>
              {expandedSections.risk && (
              <div className="grid grid-cols-3 gap-4">
                <RiskGauge value={Math.abs(agentData?.risk_engine?.VaR || 0.05)} label="VaR" />
                <RiskGauge value={Math.abs(agentData?.risk_engine?.CVaR || 0.08)} label="CVaR" />
                <RiskGauge value={Math.abs(agentData?.risk_engine?.Max_Drawdown || 0.12)} label="MAX DD" />
              </div>
              )}
            </div>

            {/* Strategy Intelligence */}
            <div className="terminal-border border-2 rounded-lg p-4 bg-black/40 backdrop-blur-sm">
              <div className="flex items-center justify-between mb-3">
                <div className="flex items-center gap-2">
                  <Zap size={14} className="text-orange-500" />
                  <span className="font-mono text-xs text-orange-500 tracking-wider">STRATEGY ENGINE</span>
                </div>
                <button
                  onClick={() => toggleSection('strategy')}
                  className="p-1 hover:bg-orange-600/10 rounded transition-colors"
                >
                  {expandedSections.strategy ? <Minimize2 size={12} className="text-orange-500" /> : <Maximize2 size={12} className="text-orange-500" />}
                </button>
              </div>
              {expandedSections.strategy && (
              <div className="space-y-2">
                <div className="flex justify-between items-center p-2 bg-zinc-900/90 rounded border border-orange-600/10">
                  <span className="text-[10px] text-white/40 font-mono">MARKET REGIME</span>
                  <span className="text-xs text-orange-500 font-mono font-bold">
                    {agentData?.strategy?.regime?.regime || 'ANALYZING'}
                  </span>
                </div>
                <div className="flex justify-between items-center p-2 bg-zinc-900/90 rounded border border-orange-600/10">
                  <span className="text-[10px] text-white/40 font-mono">OPTIMAL STRATEGY</span>
                  <span className="text-xs text-emerald-400 font-mono font-bold">
                    {agentData?.strategy?.best_strategy?.strategy || 'MOMENTUM'}
                  </span>
                </div>
                {agentData?.strategy?.trade_levels && (
                  <div className="p-3 bg-zinc-900/90 rounded border border-orange-600/10 space-y-1.5">
                    <div className="flex justify-between">
                      <span className="text-[10px] text-white/40 font-mono">SIGNAL</span>
                      <span className={`text-xs font-mono font-bold ${
                        agentData.strategy.trade_levels.action === 'BUY' ? 'text-emerald-400' : 'text-red-400'
                      }`}>
                        {agentData.strategy.trade_levels.action}
                      </span>
                    </div>
                    <div className="grid grid-cols-3 gap-2 text-[10px]">
                      <div>
                        <div className="text-white/40">ENTRY</div>
                        <div className="text-white font-mono">${agentData.strategy.trade_levels.entry_price?.toFixed(2)}</div>
                      </div>
                      <div>
                        <div className="text-white/40">STOP</div>
                        <div className="text-red-400 font-mono">${agentData.strategy.trade_levels.stop_loss?.toFixed(2)}</div>
                      </div>
                      <div>
                        <div className="text-white/40">TARGET</div>
                        <div className="text-emerald-400 font-mono">${agentData.strategy.trade_levels.take_profit?.toFixed(2)}</div>
                      </div>
                    </div>
                  </div>
                )}
              </div>
              )}
            </div>

            {/* System Status */}
            <div className="terminal-border border-2 rounded-lg p-3 bg-black/40 backdrop-blur-sm">
              <div className="flex items-center gap-2 mb-2">
                <Cpu size={12} className="text-orange-500" />
                <span className="font-mono text-[10px] text-orange-500 tracking-wider">SYSTEM STATUS</span>
              </div>
              <div className="space-y-1.5 text-[9px] font-mono">
                <div className="flex justify-between">
                  <span className="text-white/40">NEURAL PROCESSORS</span>
                  <span className="text-emerald-400 data-stream">ONLINE</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-white/40">MARKET DATA FEED</span>
                  <span className="text-emerald-400 data-stream">STREAMING</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-white/40">RISK ENGINE</span>
                  <span className="text-orange-500 data-stream">ACTIVE</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-white/40">LATENCY</span>
                  <span className="text-white data-stream">24ms</span>
                </div>
              </div>
            </div>
          </div>
      </div>
    </>
  );
}

// ─── Message Bubble ─────────────────────────────────────────────────────────────

function MessageBubble({ message }: { message: Message }) {
  const [copied, setCopied] = useState(false);
  const isUser = message.role === 'user';

  const handleCopy = () => {
    navigator.clipboard.writeText(message.content);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className={`flex gap-3 ${isUser ? 'flex-row-reverse' : ''} group mb-4`}>
      <div className={`w-8 h-8 rounded-lg flex items-center justify-center shrink-0 border ${
        isUser
          ? 'bg-gradient-to-br from-purple-600/40 to-purple-600/20 border-purple-500/30'
          : 'bg-zinc-900/90 border-orange-600/30'
      }`}>
        {isUser ? (
          <Terminal size={14} className="text-purple-400" />
        ) : (
          <Cpu size={14} className="text-orange-500 animate-pulse" />
        )}
      </div>
      <div className={`flex-1 max-w-[70%]`}>
        <div className={`flex items-center gap-2 mb-1 ${isUser ? 'justify-end' : ''}`}>
          <span className="text-[9px] font-mono text-white/30 tracking-wider">
            {isUser ? 'USER@TERMINAL' : 'AGENT@BOOMERANG'}
          </span>
          <span className="text-[9px] font-mono text-white/20">
            {message.timestamp.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })}
          </span>
          {!isUser && (
            <button onClick={handleCopy} className="opacity-0 group-hover:opacity-70 hover:opacity-100 transition-opacity">
              {copied ? <Check size={10} className="text-emerald-400" /> : <Copy size={10} className="text-white/40" />}
            </button>
          )}
        </div>
        <div
          className={`rounded-lg p-4 font-mono text-sm border ${
            isUser
              ? 'bg-purple-600/10 border-purple-500/20 text-purple-100'
              : 'bg-zinc-900/90 border-orange-600/20 text-white/90 terminal-border'
          }`}
        >
          {message.isStreaming ? (
            <div className="flex items-center gap-2 text-orange-500">
              <div className="flex gap-1">
                {[0, 1, 2].map((i) => (
                  <div
                    key={i}
                    className="w-1 h-1 bg-orange-500 rounded-full animate-pulse"
                    style={{ animationDelay: `${i * 200}ms` }}
                  />
                ))}
              </div>
              <span className="text-xs">PROCESSING...</span>
            </div>
          ) : (
            <div className="prose prose-invert prose-sm max-w-none prose-code:text-orange-500 prose-code:bg-zinc-900/90 prose-code:px-1 prose-code:py-0.5 prose-code:rounded prose-code:border prose-code:border-orange-600/20 prose-table:border-collapse prose-table:w-full prose-th:border prose-th:border-orange-600/30 prose-th:bg-orange-600/10 prose-th:p-2 prose-th:text-left prose-th:text-orange-400 prose-th:font-mono prose-th:text-xs prose-td:border prose-td:border-orange-600/20 prose-td:p-2 prose-td:text-white/80 prose-td:font-mono prose-td:text-xs">
              <ReactMarkdown remarkPlugins={[remarkGfm]}>{message.content}</ReactMarkdown>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

// ─── Main Terminal Interface ────────────────────────────────────────────────────

export default function AIChat() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [wsConnected, setWsConnected] = useState(false);
  const [backtestWsStatus, setBacktestWsStatus] = useState<string>('');
  const [currentTicker, setCurrentTicker] = useState<string>('');
  const [latestAgentData, setLatestAgentData] = useState<AgentResponse>();
  const [userProfile, setUserProfile] = useState<UserProfile | null>(null);
  const [analyticsExpanded, setAnalyticsExpanded] = useState(false);
  const scrollAreaRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const wsRef = useRef<WebSocket | null>(null);
  const backtestWsRef = useRef<WebSocket | null>(null);
  const pendingRequestIdRef = useRef<string | null>(null);
  const responseTimeoutRef = useRef<number | null>(null);
  const awaitingResponseRef = useRef(false);

  // Load user profile on mount
  useEffect(() => {
    console.log('AIChat component mounted');
    loadUserProfile();
  }, []);

  const loadUserProfile = async () => {
    try {
      const { data } = await investorProfileAPI.load();
      if (data.status === 'ok' && data.profile) {
        setUserProfile(data.profile);
        console.log('User profile loaded:', data.profile);
      }
    } catch (error) {
      console.log('No user profile found or error loading:', error);
    }
  };

  useEffect(() => { inputRef.current?.focus(); }, []);

  const scrollToBottom = useCallback(() => {
    if (scrollAreaRef.current) {
      scrollAreaRef.current.scrollTo({ top: scrollAreaRef.current.scrollHeight, behavior: 'smooth' });
    }
  }, []);

  useEffect(() => { scrollToBottom(); }, [messages, scrollToBottom]);

  useEffect(() => {
    try {
      const ws = new WebSocket(WS_URL);
      wsRef.current = ws;
      
      ws.onopen = () => {
        console.log('WebSocket connected');
        setWsConnected(true);
      };
      
      ws.onclose = () => {
        console.log('WebSocket disconnected');
        setWsConnected(false);
      };
      
      ws.onerror = (error) => {
        console.log('WebSocket error:', error);
        setWsConnected(false);
      };
      
      ws.onmessage = (event) => {
        try {
          const data: AgentResponse = JSON.parse(event.data);
          // Ignore late responses if we already completed via HTTP fallback.
          if (awaitingResponseRef.current && pendingRequestIdRef.current && data.request_id && data.request_id !== pendingRequestIdRef.current) {
            return;
          }
          if (!awaitingResponseRef.current && data.request_id) {
            return;
          }

          const content = data.report || data.response || 'Analysis complete.';
          
          // Extract ticker from response
          if (data.financial?.ticker) {
            setCurrentTicker(data.financial.ticker);
          }
          setLatestAgentData(data);

          setMessages((prev) => {
            const filtered = prev.filter((m) => !m.isStreaming);
            return [...filtered, { id: uid(), role: 'assistant', content, timestamp: new Date(), agentData: data }];
          });
          awaitingResponseRef.current = false;
          pendingRequestIdRef.current = null;
          if (responseTimeoutRef.current) {
            window.clearTimeout(responseTimeoutRef.current);
            responseTimeoutRef.current = null;
          }
          setIsLoading(false);
        } catch (err) {
          console.error('Error parsing message:', err);
          setMessages((prev) => {
            const filtered = prev.filter((m) => !m.isStreaming);
            return [...filtered, { id: uid(), role: 'assistant', content: 'CONNECTION ERROR: Malformed response from backend.', timestamp: new Date() }];
          });
          awaitingResponseRef.current = false;
          pendingRequestIdRef.current = null;
          if (responseTimeoutRef.current) {
            window.clearTimeout(responseTimeoutRef.current);
            responseTimeoutRef.current = null;
          }
          setIsLoading(false);
        }
      };
      
      return () => { 
        if (ws.readyState === WebSocket.OPEN || ws.readyState === WebSocket.CONNECTING) {
          ws.close(); 
        }
      };
    } catch (error) {
      console.error('Error creating WebSocket:', error);
      setWsConnected(false);
    }
  }, []);

  // WebSocket backtest function
  const runBacktestViaWebSocket = useCallback((ticker: string, strategy: string) => {
    if (backtestWsRef.current?.readyState === WebSocket.OPEN) {
      backtestWsRef.current.close();
    }

    try {
      const ws = new WebSocket(BACKTEST_WS_URL);
      backtestWsRef.current = ws;

      ws.onopen = () => {
        console.log('Backtest WebSocket connected');
        setBacktestWsStatus('connecting');
        ws.send(JSON.stringify({ ticker, strategy }));
      };

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          
          if (data.status === 'starting') {
            setBacktestWsStatus('starting');
          } else if (data.status === 'fetching') {
            setBacktestWsStatus('fetching data');
          } else if (data.status === 'processing') {
            setBacktestWsStatus('processing backtest');
          } else if (data.status === 'complete' && data.data) {
            setBacktestWsStatus('complete');
            setLatestAgentData(prev => ({
              ...prev,
              strategy: data.data.strategy,
              financial: data.data.financial,
              report: data.data.report || prev?.report,
              response: data.data.response || prev?.response,
            }));
            
            setMessages((prev) => [
              ...prev,
              {
                id: uid(),
                role: 'assistant',
                content: `✅ Backtest complete for ${ticker} using ${strategy} strategy`,
                timestamp: new Date(),
                agentData: data.data,
              },
            ]);
            
            setTimeout(() => setBacktestWsStatus(''), 3000);
            ws.close();
          } else if (data.status === 'error') {
            setBacktestWsStatus('error');
            setMessages((prev) => [
              ...prev,
              {
                id: uid(),
                role: 'assistant',
                content: `❌ Backtest error: ${data.message || 'Unknown error'}`,
                timestamp: new Date(),
              },
            ]);
            setTimeout(() => setBacktestWsStatus(''), 3000);
            ws.close();
          }
        } catch (err) {
          console.error('Error parsing backtest message:', err);
          setBacktestWsStatus('error');
          setTimeout(() => setBacktestWsStatus(''), 3000);
        }
      };

      ws.onerror = (error) => {
        console.error('Backtest WebSocket error:', error);
        setBacktestWsStatus('error');
        setTimeout(() => setBacktestWsStatus(''), 3000);
      };

      ws.onclose = () => {
        console.log('Backtest WebSocket closed');
        if (backtestWsStatus !== 'complete' && backtestWsStatus !== 'error') {
          setBacktestWsStatus('');
        }
      };
    } catch (err) {
      console.error('Error creating backtest WebSocket:', err);
      setBacktestWsStatus('error');
      setTimeout(() => setBacktestWsStatus(''), 3000);
    }
  }, [backtestWsStatus]);

  const sendMessage = async (query: string) => {
    if (!query.trim() || isLoading) return;
    const request_id = reqid();
    
    // Enhance query with user profile context if available
    let enhancedQuery = query.trim();
    if (userProfile && (userProfile.name || userProfile.risk_tolerance || userProfile.primary_goal)) {
      const profileContext = [];
      if (userProfile.name) profileContext.push(`User: ${userProfile.name}`);
      if (userProfile.risk_tolerance) profileContext.push(`Risk Tolerance: ${userProfile.risk_tolerance}`);
      if (userProfile.primary_goal) profileContext.push(`Goal: ${userProfile.primary_goal}`);
      if (userProfile.horizon_years) profileContext.push(`Time Horizon: ${userProfile.horizon_years} years`);
      if (userProfile.monthly_savings) profileContext.push(`Monthly Savings: $${userProfile.monthly_savings}`);
      if (userProfile.market) profileContext.push(`Market: ${userProfile.market}`);
      
      const contextStr = `[User Profile Context: ${profileContext.join(', ')}]`;
      enhancedQuery = `${contextStr}\n\n${query.trim()}`;
      console.log('Enhanced query with profile:', enhancedQuery);
    }
    
    const userMsg: Message = { id: uid(), role: 'user', content: query.trim(), timestamp: new Date() };
    const streamingMsg: Message = { id: uid(), role: 'assistant', content: '', timestamp: new Date(), isStreaming: true };
    setMessages((prev) => [...prev, userMsg, streamingMsg]);
    setInput('');
    setIsLoading(true);
    awaitingResponseRef.current = true;
    pendingRequestIdRef.current = request_id;

    // Try to extract ticker from user query
    const tickerMatch = query.match(/\b([A-Z]{1,5})\b/);
    if (tickerMatch) {
      setCurrentTicker(tickerMatch[1]);
    }

    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ query: enhancedQuery, request_id }));

      if (responseTimeoutRef.current) window.clearTimeout(responseTimeoutRef.current);
      responseTimeoutRef.current = window.setTimeout(async () => {
        if (!awaitingResponseRef.current) return;
        try {
          const res = await fetch(`${API_BASE}/api/super-agent`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ query: enhancedQuery, request_id }),
          });
          const data = await res.json();
          const responseContent = data.report || data.response || JSON.stringify(data);
          setLatestAgentData(data);
          setMessages((prev) => {
            const filtered = prev.filter((m) => !m.isStreaming);
            return [...filtered, { id: uid(), role: 'assistant', content: responseContent, timestamp: new Date(), agentData: data }];
          });
        } catch (e) {
          setMessages((prev) => {
            const filtered = prev.filter((m) => !m.isStreaming);
            return [...filtered, { id: uid(), role: 'assistant', content: 'CONNECTION TIMEOUT: Backend is taking too long to respond.', timestamp: new Date() }];
          });
        } finally {
          awaitingResponseRef.current = false;
          pendingRequestIdRef.current = null;
          setIsLoading(false);
        }
      }, 35000);
    } else {
      try {
        const res = await fetch(`${API_BASE}/api/super-agent`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ query: enhancedQuery, request_id }),
        });
        const data = await res.json();
        
        // Check for ticker mismatch
        let responseContent = data.report || data.response || JSON.stringify(data);
        if (data.financial?.ticker && tickerMatch && data.financial.ticker !== tickerMatch[1]) {
          const warning = `⚠️ **TICKER MISMATCH DETECTED**\nYou asked for **${tickerMatch[1]}** but backend analyzed **${data.financial.ticker}**\n\n---\n\n`;
          responseContent = warning + responseContent;
          console.warn(`Ticker mismatch: requested ${tickerMatch[1]}, got ${data.financial.ticker}`);
        }
        
        if (data.financial?.ticker) {
          setCurrentTicker(data.financial.ticker);
        }
        setLatestAgentData(data);

        setMessages((prev) => {
          const filtered = prev.filter((m) => !m.isStreaming);
          return [...filtered, { id: uid(), role: 'assistant', content: responseContent, timestamp: new Date(), agentData: data }];
        });
      } catch {
        setMessages((prev) => {
          const filtered = prev.filter((m) => !m.isStreaming);
          return [...filtered, { id: uid(), role: 'assistant', content: 'CONNECTION ERROR: Backend unreachable', timestamp: new Date() }];
        });
      } finally {
        awaitingResponseRef.current = false;
        pendingRequestIdRef.current = null;
        if (responseTimeoutRef.current) {
          window.clearTimeout(responseTimeoutRef.current);
          responseTimeoutRef.current = null;
        }
        setIsLoading(false);
      }
    }
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    sendMessage(input);
  };

  const quickCommands = [
    { cmd: 'analyze NVDA', icon: TrendingUp },
    { cmd: 'backtest TSLA momentum', icon: BarChart3 },
    { cmd: 'risk analysis portfolio', icon: AlertTriangle },
    { cmd: 'market regime detection', icon: Activity },
    { cmd: 'optimal portfolio AI sector', icon: Globe2 },
  ];

  return (
    <div className="h-[calc(100vh-4rem)] flex gap-4 relative overflow-hidden">
      <TerminalScanlines />

      {/* Left Panel - Chat Interface */}
      <div className={`flex flex-col terminal-border border-2 rounded-lg bg-zinc-900/90 backdrop-blur-sm p-4 transition-all duration-500 ${
        analyticsExpanded ? 'w-16' : 'flex-1'
      }`}>
        {/* Header */}
        <div className="flex items-center justify-between mb-4 pb-3 border-b border-orange-600/20">
          <div className="flex-1 min-w-0">
            {!analyticsExpanded && (
              <>
            <h1 className="font-mono text-lg font-bold text-orange-500 tracking-wider">
              COMMAND INTERFACE
            </h1>
            <div className="flex items-center gap-3 mt-1">
              <div className="flex items-center gap-2">
                <div className={`w-1.5 h-1.5 rounded-full ${wsConnected ? 'bg-emerald-400 shadow-[0_0_6px_#34d399]' : 'bg-red-400'}`} />
                <span className="text-[9px] text-white/30 font-mono tracking-wider">
                  {wsConnected ? 'WEBSOCKET ACTIVE' : 'HTTP FALLBACK'}
                </span>
              </div>
              {backtestWsStatus && (
                <div className="flex items-center gap-2 px-2 py-0.5 bg-cyan-600/10 border border-cyan-500/20 rounded">
                  <Loader2 size={10} className="text-cyan-400 animate-spin" />
                  <span className="text-[9px] text-cyan-300 font-mono tracking-wider uppercase">
                    {backtestWsStatus}
                  </span>
                </div>
              )}
              {userProfile && userProfile.name && (
                <div className="flex items-center gap-1.5 px-2 py-0.5 bg-purple-600/10 border border-purple-500/20 rounded">
                  <User size={10} className="text-purple-400" />
                  <span className="text-[9px] text-purple-300 font-mono tracking-wider">
                    {userProfile.name.toUpperCase()} | {userProfile.risk_tolerance?.toUpperCase() || 'MODERATE'}
                  </span>
                </div>
              )}
            </div>
              </>
            )}
          </div>
          {!analyticsExpanded && messages.length > 0 && (
            <button
              onClick={() => setMessages([])}
              className="text-[10px] text-white/40 hover:text-white/70 font-mono border border-orange-600/20 px-2 py-1 rounded hover:bg-orange-600/10 transition-colors"
            >
              CLEAR
            </button>
          )}
        </div>

        {/* Messages */}
        {!analyticsExpanded && (
        <div ref={scrollAreaRef} className="flex-1 overflow-y-auto pr-2 scroll-smooth">
          {messages.length === 0 ? (
            <div className="h-full flex flex-col justify-center items-center">
              <div className="relative mb-6">
                <div className="w-16 h-16 rounded-lg bg-gradient-to-br from-orange-600/20 to-purple-500/20 border border-orange-600/30 flex items-center justify-center">
                  <Terminal size={28} className="text-orange-500" />
                </div>
                <div className="absolute -inset-2 bg-orange-600/10 blur-xl -z-10" />
              </div>
              <h2 className="font-mono text-sm text-white/80 mb-6 tracking-wider">INITIATE MARKET ANALYSIS</h2>
              <div className="grid grid-cols-1 gap-2 w-full max-w-md">
                {quickCommands.map((cmd) => {
                  const Icon = cmd.icon;
                  return (
                    <button
                      key={cmd.cmd}
                      onClick={() => sendMessage(cmd.cmd)}
                      className="group flex items-center gap-3 p-3 bg-zinc-900/90 hover:bg-orange-600/10 border border-orange-600/20 hover:border-orange-600/40 rounded text-left transition-all"
                    >
                      <Icon size={14} className="text-orange-500" />
                      <span className="font-mono text-xs text-white/70 group-hover:text-white transition-colors">
                        &gt; {cmd.cmd}
                      </span>
                    </button>
                  );
                })}
              </div>
            </div>
          ) : (
            messages.map((msg) => <MessageBubble key={msg.id} message={msg} />)
          )}
        </div>
        )}

        {/* Input */}
        {!analyticsExpanded && (
        <div className="mt-4 pt-3 border-t border-orange-600/20">
          <form onSubmit={handleSubmit}>
            <div className="flex items-center gap-2 bg-zinc-900/90 border border-orange-600/30 focus-within:border-orange-600/60 rounded px-3 py-2 transition-all">
              <span className="text-orange-500 font-mono text-sm shrink-0">&gt;</span>
              <input
                ref={inputRef}
                type="text"
                value={input}
                onChange={(e) => setInput(e.target.value)}
                placeholder="Enter command..."
                className="flex-1 bg-transparent text-white placeholder:text-white/20 font-mono text-sm focus:outline-none"
                disabled={isLoading}
              />
              <button
                type="submit"
                disabled={!input.trim() || isLoading}
                className="shrink-0 w-7 h-7 rounded bg-orange-600/20 hover:bg-orange-600/30 disabled:opacity-20 flex items-center justify-center border border-orange-600/30 transition-all"
              >
                {isLoading ? (
                  <Loader2 size={12} className="text-orange-500 animate-spin" />
                ) : (
                  <Send size={12} className="text-orange-500" />
                )}
              </button>
            </div>
            <div className="flex justify-between mt-2 px-1">
              <span className="text-[9px] text-white/20 font-mono">BOOMERANG NEURAL ENGINE v2.0</span>
              <span className="text-[9px] text-white/20 font-mono">{messages.filter(m => m.role === 'user').length} QUERIES</span>
            </div>
          </form>
        </div>
        )}
      </div>

      {/* Right Panel - Analytics Dashboard */}
      <div className={`terminal-border border-2 rounded-lg bg-zinc-900/90 backdrop-blur-sm p-4 overflow-y-auto transition-all duration-500 ${
        analyticsExpanded ? 'flex-1' : 'w-[45%]'
      }`}>
        <AnalyticsDashboard 
          agentData={latestAgentData} 
          ticker={currentTicker} 
          onExpandToggle={() => setAnalyticsExpanded(!analyticsExpanded)}
          isExpanded={analyticsExpanded}
          runBacktestViaWebSocket={runBacktestViaWebSocket}
          backtestWsStatus={backtestWsStatus}
        />
      </div>
    </div>
  );
}
