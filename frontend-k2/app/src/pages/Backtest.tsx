import { useState, useRef, useEffect, useCallback } from 'react';
import { Play, TrendingUp, TrendingDown, DollarSign, IndianRupee, Activity, Zap, Target, BarChart3, Layers, ArrowUpDown, Crosshair, GitBranch, Shield } from 'lucide-react';
import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, Legend, Scatter, BarChart, Bar, CartesianGrid, ComposedChart } from 'recharts';
import { formatCurrency, getCurrencySymbol, backtestAPI } from '@/api';

/* ---- Canvas-based Monte Carlo Simulation Paths Chart ---- */
function MonteCarloCanvas({ monteCarlo }: { monteCarlo: any }) {
  const canvasRef = useRef<HTMLCanvasElement>(null);

  const draw = useCallback(() => {
    const canvas = canvasRef.current;
    if (!canvas || !monteCarlo?.simulationPaths?.length) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    const dpr = window.devicePixelRatio || 1;
    const rect = canvas.getBoundingClientRect();
    canvas.width = rect.width * dpr;
    canvas.height = rect.height * dpr;
    ctx.scale(dpr, dpr);
    const W = rect.width;
    const H = rect.height;

    const pad = { top: 20, right: 16, bottom: 30, left: 72 };
    const plotW = W - pad.left - pad.right;
    const plotH = H - pad.top - pad.bottom;

    const paths: number[][] = monteCarlo.simulationPaths;
    const steps = paths[0]?.length || 0;
    if (steps < 2) return;

    // Find min/max across all paths
    let yMin = Infinity, yMax = -Infinity;
    for (const p of paths) {
      for (const v of p) {
        if (v < yMin) yMin = v;
        if (v > yMax) yMax = v;
      }
    }
    const yPad = (yMax - yMin) * 0.05;
    yMin -= yPad; yMax += yPad;

    const xScale = (i: number) => pad.left + (i / (steps - 1)) * plotW;
    const yScale = (v: number) => pad.top + plotH - ((v - yMin) / (yMax - yMin)) * plotH;

    // Helper to format dollar values compactly
    const fmtDollar = (v: number) => {
      if (Math.abs(v) >= 1_000_000) return `$${(v / 1_000_000).toFixed(1)}M`;
      if (Math.abs(v) >= 1_000) return `$${(v / 1_000).toFixed(0)}K`;
      return `$${v.toFixed(0)}`;
    };

    // Background
    ctx.fillStyle = 'rgba(0,0,0,0)';
    ctx.clearRect(0, 0, W, H);

    // Grid lines
    ctx.strokeStyle = 'rgba(255,255,255,0.06)';
    ctx.lineWidth = 1;
    const nGridY = 5;
    for (let i = 0; i <= nGridY; i++) {
      const y = pad.top + (i / nGridY) * plotH;
      ctx.beginPath(); ctx.moveTo(pad.left, y); ctx.lineTo(W - pad.right, y); ctx.stroke();
    }

    // Draw all simulation paths
    ctx.lineWidth = 0.5;
    ctx.globalAlpha = 0.04;
    ctx.strokeStyle = '#f59e0b';
    for (const p of paths) {
      ctx.beginPath();
      for (let i = 0; i < steps; i++) {
        const x = xScale(i), y = yScale(p[i]);
        i === 0 ? ctx.moveTo(x, y) : ctx.lineTo(x, y);
      }
      ctx.stroke();
    }
    ctx.globalAlpha = 1;

    // Draw percentile paths
    const pctPaths = monteCarlo.percentilePaths;
    if (pctPaths) {
      const pctColors: [string, string, number][] = [
        ['p5', '#ef4444', 1.5],
        ['p25', '#f97316', 1.2],
        ['p50', '#22c55e', 2.5],
        ['p75', '#3b82f6', 1.2],
        ['p95', '#8b5cf6', 1.5],
      ];
      for (const [key, color, width] of pctColors) {
        const curve = pctPaths[key];
        if (!curve) continue;
        ctx.strokeStyle = color;
        ctx.lineWidth = width;
        ctx.beginPath();
        for (let i = 0; i < curve.length; i++) {
          const x = xScale(i), y = yScale(curve[i]);
          i === 0 ? ctx.moveTo(x, y) : ctx.lineTo(x, y);
        }
        ctx.stroke();
      }
    }

    // Initial capital baseline (dashed)
    const initCap = paths[0]?.[0] ?? 0;
    const baseY = yScale(initCap);
    if (baseY > pad.top && baseY < pad.top + plotH) {
      ctx.strokeStyle = 'rgba(255,255,255,0.3)';
      ctx.lineWidth = 1;
      ctx.setLineDash([4, 4]);
      ctx.beginPath(); ctx.moveTo(pad.left, baseY); ctx.lineTo(W - pad.right, baseY); ctx.stroke();
      ctx.setLineDash([]);
      // Label the baseline
      ctx.fillStyle = 'rgba(255,255,255,0.4)';
      ctx.font = '10px sans-serif';
      ctx.textAlign = 'left';
      ctx.fillText(fmtDollar(initCap), W - pad.right + 2, baseY + 3);
    }

    // Y-axis labels (dollar values)
    ctx.fillStyle = 'rgba(255,255,255,0.5)';
    ctx.font = '11px sans-serif';
    ctx.textAlign = 'right';
    for (let i = 0; i <= nGridY; i++) {
      const val = yMax - (i / nGridY) * (yMax - yMin);
      const y = pad.top + (i / nGridY) * plotH;
      ctx.fillText(fmtDollar(val), pad.left - 6, y + 4);
    }

    // X-axis labels
    ctx.textAlign = 'center';
    ctx.fillText('Start', xScale(0), H - 6);
    ctx.fillText('End', xScale(steps - 1), H - 6);
  }, [monteCarlo]);

  useEffect(() => {
    draw();
    const handler = () => draw();
    window.addEventListener('resize', handler);
    return () => window.removeEventListener('resize', handler);
  }, [draw]);

  if (!monteCarlo?.simulationPaths?.length) return null;

  return (
    <div className="space-y-2">
      <canvas ref={canvasRef} className="w-full rounded-lg" style={{ height: 280 }} />
      <div className="flex flex-wrap items-center gap-4 text-xs">
        <span className="text-red-400">● P5</span>
        <span className="text-orange-400">● P25</span>
        <span className="text-emerald-400 font-semibold">● P50 (Median)</span>
        <span className="text-blue-400">● P75</span>
        <span className="text-purple-400">● P95</span>
        <span className="text-amber-400/40">── All Paths</span>
      </div>
    </div>
  );
}

const strategies = [
  {
    id: 'momentum',
    name: 'Momentum',
    description: 'Buy stocks with strong price momentum',
    icon: TrendingUp,
    color: '#3b82f6',
    params: { lookback: 20 },
    indicators: []
  },
  {
    id: 'mean_reversion',
    name: 'Mean Reversion',
    description: 'Trade based on price deviation from MA',
    icon: Activity,
    color: '#10b981',
    params: { window: 20, num_std: 2 },
    indicators: [
      { key: 'moving_average', color: '#f59e0b', name: 'MA' },
      { key: 'upper_band', color: '#10b981', name: 'Upper Band' },
      { key: 'lower_band', color: '#10b981', name: 'Lower Band' }
    ]
  },
  {
    id: 'ema_crossover',
    name: 'EMA Cross',
    description: 'Golden/Death cross using EMAs',
    icon: Zap,
    color: '#f59e0b',
    params: { fast: 12, slow: 26 },
    indicators: [
      { key: 'ema_fast', color: '#10b981', name: 'Fast EMA' },
      { key: 'ema_slow', color: '#ef4444', name: 'Slow EMA' }
    ]
  },
  {
    id: 'sma_crossover',
    name: 'SMA Cross',
    description: 'Golden/Death cross using SMAs',
    icon: Layers,
    color: '#06b6d4',
    params: { short_window: 50, long_window: 200 },
    indicators: [
      { key: 'sma_short', color: '#10b981', name: 'Short SMA' },
      { key: 'sma_long', color: '#ef4444', name: 'Long SMA' }
    ]
  },
  {
    id: 'macd',
    name: 'MACD',
    description: 'Trade on MACD line crossing signal line',
    icon: Target,
    color: '#8b5cf6',
    params: { fast: 12, slow: 26, signal: 9 },
    indicators: [
      { key: 'macd', color: '#3b82f6', name: 'MACD', axis: 'right' },
      { key: 'macd_signal', color: '#f97316', name: 'Signal', axis: 'right' }
    ]
  },
  {
    id: 'rsi_reversal',
    name: 'RSI Reversal',
    description: 'Buy oversold, sell overbought',
    icon: BarChart3,
    color: '#ef4444',
    params: { window: 14, lower: 30, upper: 70 },
    indicators: [
      { key: 'rsi', color: '#f97316', name: 'RSI', axis: 'right' }
    ]
  },
  {
    id: 'rsi_momentum',
    name: 'RSI Momentum',
    description: 'RSI cross with trend filter',
    icon: ArrowUpDown,
    color: '#ec4899',
    params: { rsi_window: 14, lower: 40, upper: 60 },
    indicators: [
      { key: 'rsi', color: '#f97316', name: 'RSI', axis: 'right' }
    ]
  },
  {
    id: 'breakout',
    name: 'Breakout',
    description: 'Donchian channel breakout signals',
    icon: Crosshair,
    color: '#14b8a6',
    params: { lookback: 20 },
    indicators: [
      { key: 'donchian_high', color: '#10b981', name: 'High Channel' },
      { key: 'donchian_low', color: '#ef4444', name: 'Low Channel' }
    ]
  },
  {
    id: 'fibonacci_pullback',
    name: 'Fib Pullback',
    description: 'Buy pullbacks to Fibonacci levels',
    icon: GitBranch,
    color: '#a855f7',
    params: { lookback: 50 },
    indicators: []
  },
  {
    id: 'support_resistance',
    name: 'Sup / Res',
    description: 'Bounce off support, exit at resistance',
    icon: Shield,
    color: '#f97316',
    params: { lookback: 30, tolerance_pct: 0.01 },
    indicators: [
      { key: 'support', color: '#10b981', name: 'Support' },
      { key: 'resistance', color: '#ef4444', name: 'Resistance' }
    ]
  },
  {
    id: 'channel_trading',
    name: 'Channel',
    description: 'Donchian channel breakout trading',
    icon: BarChart3,
    color: '#64748b',
    params: { period: 20 },
    indicators: [
      { key: 'upper_channel', color: '#10b981', name: 'Upper' },
      { key: 'lower_channel', color: '#ef4444', name: 'Lower' }
    ]
  },
];

const strategyGuides: Record<string, { entry: string; exit: string; watch: string }> = {
  ema_crossover: {
    entry: 'Enter when the fast EMA crosses above the slow EMA (trend turns up).',
    exit: 'Exit or flip when the fast EMA crosses below the slow EMA.',
    watch: 'Watch the gap between EMAs. A narrowing gap means a crossover is near.',
  },
  sma_crossover: {
    entry: 'Enter when the short SMA crosses above the long SMA (Golden Cross).',
    exit: 'Exit when the short SMA crosses below the long SMA (Death Cross).',
    watch: 'SMA convergence signals upcoming crossover. Works best in trending markets.',
  },
  macd: {
    entry: 'Enter when MACD crosses above its signal line.',
    exit: 'Exit or flip when MACD crosses below its signal line.',
    watch: 'Monitor MACD histogram contraction toward zero.',
  },
  momentum: {
    entry: 'Enter when recent momentum turns positive over the lookback window.',
    exit: 'Exit when momentum turns negative.',
    watch: 'Price making higher highs with positive momentum confirms continuation.',
  },
  mean_reversion: {
    entry: 'Enter when price falls below the lower band (oversold).',
    exit: 'Exit when price reverts back to the moving average.',
    watch: 'Band width expansion signals higher volatility; be more selective.',
  },
  rsi_reversal: {
    entry: 'Enter when RSI crosses up through the lower threshold.',
    exit: 'Exit when RSI crosses down through the upper threshold.',
    watch: 'RSI hovering near thresholds suggests a signal is close.',
  },
  rsi_momentum: {
    entry: 'Enter when RSI crosses above lower bound with price above trend MA.',
    exit: 'Exit when RSI crosses down through the upper threshold.',
    watch: 'Trend MA direction confirms momentum. Works best in uptrends.',
  },
  breakout: {
    entry: 'Enter when price breaks above the Donchian high channel.',
    exit: 'Exit when price breaks below the Donchian low channel.',
    watch: 'Channel width contraction precedes breakout moves.',
  },
  fibonacci_pullback: {
    entry: 'Enter when price pulls back to 38.2% Fib level with bullish candle.',
    exit: 'Exit when price breaks above the recent swing high.',
    watch: 'Strong trends with shallow pullbacks are ideal for this strategy.',
  },
  support_resistance: {
    entry: 'Enter when price bounces off rolling support level.',
    exit: 'Exit when price approaches rolling resistance level.',
    watch: 'Multiple touches of support/resistance strengthen the level.',
  },
  channel_trading: {
    entry: 'Enter when price breaks above the upper Donchian channel.',
    exit: 'Exit when price breaks below the lower Donchian channel.',
    watch: 'Channel narrowing often precedes a breakout move.',
  },
};

export default function Backtest() {
  const [market, setMarket] = useState('US');
  const [selectedStrategies, setSelectedStrategies] = useState(['ema_crossover']);
  const [symbol, setSymbol] = useState('AAPL');
  const [initialCapital, setInitialCapital] = useState(100000);
  const [startDate, setStartDate] = useState('');
  const [endDate, setEndDate] = useState('');
  const [isRunning, setIsRunning] = useState(false);
  const [results, setResults] = useState<any>(null);
  const [heatmap, setHeatmap] = useState<any>(null);
  const [heatmapLoading, setHeatmapLoading] = useState(false);
  const [heatmapError, setHeatmapError] = useState<string | null>(null);
  const [detailStrategy, setDetailStrategy] = useState('ema_crossover');
  const [reportLink, setReportLink] = useState<string | null>(null);
  const [reportLoading, setReportLoading] = useState(false);
  const [reportError, setReportError] = useState<string | null>(null);
  const [qsLoading, setQsLoading] = useState(false);
  const [qsLink, setQsLink] = useState<string | null>(null);
  const [qsError, setQsError] = useState<string | null>(null);
  const [lastRunResult, setLastRunResult] = useState<any>(null);
  const [lastRunStrategies, setLastRunStrategies] = useState<string[]>([]);
  const currencySymbol = getCurrencySymbol(market);
  const currentGuide = strategyGuides[detailStrategy] || {
    entry: 'Entry based on signal trigger.',
    exit: 'Exit based on signal reversal.',
    watch: 'Watch indicator conditions for the next setup.',
  };

  const toggleStrategy = (strategyId: string) => {
    setSelectedStrategies(prev => {
      if (prev.includes(strategyId)) {
        if (prev.length === 1) return prev;
        return prev.filter(s => s !== strategyId);
      }
      if (prev.length >= 4) return prev;
      return [...prev, strategyId];
    });
  };

  const loadHeatmap = async (strategyId: string) => {
    setHeatmapLoading(true);
    setHeatmapError(null);
    try {
      const response = await backtestAPI.heatmap({ symbol, strategy: strategyId, range: '1y' });
      setHeatmap(response.data);
    } catch (err: any) {
      setHeatmap(null);
      setHeatmapError(err?.response?.data?.detail || 'Heatmap unavailable');
    } finally {
      setHeatmapLoading(false);
    }
  };

  const getHeatColor = (value: number | null, min: number, max: number) => {
    if (value === null || value === undefined) return 'rgba(255,255,255,0.05)';
    const span = max - min || 1;
    const t = Math.max(0, Math.min(1, (value - min) / span));
    const r = Math.round(239 + (34 - 239) * t);
    const g = Math.round(68 + (197 - 68) * t);
    const b = Math.round(68 + (94 - 68) * t);
    return `rgb(${r}, ${g}, ${b})`;
  };

  const handleGenerateReport = async (format: 'pdf' | 'html') => {
    if (!lastRunResult) return;
    setReportLoading(true);
    setReportError(null);
    try {
      const response = await backtestAPI.generateReport({
        symbol,
        strategies: lastRunStrategies,
        results: lastRunResult,
        format,
      });
      const downloadUrl = response.data?.downloadUrl;
      if (downloadUrl) {
        const filename = downloadUrl.split('/').pop() || '';
        const fullUrl = filename ? backtestAPI.downloadReport(filename) : downloadUrl;
        setReportLink(fullUrl);
      } else {
        setReportError('Report generation failed.');
      }
    } catch (err: any) {
      setReportError(err?.response?.data?.detail || 'Report generation failed.');
    } finally {
      setReportLoading(false);
    }
  };

  const handleRunBacktest = async () => {
    setIsRunning(true);
    try {
      const paramsDict: any = {};
      selectedStrategies.forEach(stratId => {
        const strat = strategies.find(s => s.id === stratId);
        if (strat?.params) paramsDict[stratId] = strat.params;
      });
      const response = await backtestAPI.run({
        symbol,
        strategies: selectedStrategies,
        range: '1y',
        params: paramsDict,
        start: startDate || undefined,
        end: endDate || undefined
      });
      setLastRunResult(response.data);
      setLastRunStrategies(selectedStrategies);
      setReportLink(null);
      if (response.data.mode === 'multi_strategy') {
        const strategyResults = response.data.strategies || {};
        const strategiesArr = Object.entries(strategyResults).map(([id, data]: any) => {
          const def = strategies.find(s => s.id === id);
          return {
            id,
            name: id,
            displayName: def?.name || data?.name || id,
            color: data?.color || def?.color,
            metrics: data?.metrics,
            error: data?.error,
            trades: data?.trades || [],
            monteCarlo: data?.monteCarlo || null,
            equityCurve: data?.equityCurve || [],
          };
        });

        const ranking = (response.data.ranking || []).map((r: any, idx: number) => {
          const strat = strategyResults[r.strategy];
          const def = strategies.find(s => s.id === r.strategy);
          return {
            name: def?.name || strat?.name || r.strategy,
            totalReturn: r.return,
            sharpe: strat?.metrics?.sharpeRatio ?? '-',
            rank: idx + 1,
          };
        });

        setResults({
          isMulti: true,
          strategies: strategiesArr,
          combinedChartData: response.data.combinedChartData || [],
          ranking,
        });
        const first = strategiesArr[0]?.id || selectedStrategies[0];
        if (first) {
          setDetailStrategy(first);
          void loadHeatmap(first);
        }
        setHeatmapError(null);
      } else {
        const equityCurve = response.data.equity_curve?.map((point: any, idx: number) => ({
          ...point,
          date: point.date || `Day ${idx + 1}`,
          portfolio: point.value || initialCapital * (1 + idx * 0.001),
          benchmark: point.benchmark || initialCapital * (1 + idx * 0.0008),
        })) || [];
        setResults({
          isMulti: false,
          equityCurve,
          metrics: response.data.metrics || {},
          trades: response.data.trades || [],
          monteCarlo: response.data.monteCarlo || null,
        });
        setDetailStrategy(selectedStrategies[0]);
        void loadHeatmap(selectedStrategies[0]);
      }
    } catch (err) {
      console.error('Backtest error:', err);
    } finally {
      setIsRunning(false);
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="font-display text-3xl font-bold text-white">Strategy Backtesting</h1>
          <p className="text-white/60">Test and compare trading strategies</p>
        </div>
        <div className="flex gap-2">
          <button onClick={() => { setMarket('IN'); setSymbol('RELIANCE.NS'); }} className={`flex items-center gap-2 px-4 py-2 rounded-lg ${market === 'IN' ? 'bg-orange-500 text-white' : 'bg-white/5 text-white/60'}`}><IndianRupee size={16} />India</button>
          <button onClick={() => { setMarket('US'); setSymbol('AAPL'); }} className={`flex items-center gap-2 px-4 py-2 rounded-lg ${market === 'US' ? 'bg-orange-500 text-white' : 'bg-white/5 text-white/60'}`}><DollarSign size={16} />US</button>
        </div>
      </div>

      <div>
        <h2 className="text-lg font-semibold text-white mb-3">Select Strategies (Max 4)</h2>
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 xl:grid-cols-6 gap-3">
          {strategies.map(strat => (
            <button key={strat.id} onClick={() => toggleStrategy(strat.id)}
              className={`p-4 rounded-lg border transition-colors ${selectedStrategies.includes(strat.id) ? 'border-orange-500 bg-orange-500/20' : 'border-white/10 bg-white/5 hover:bg-white/10'}`}>
              <strat.icon className="w-8 h-8 mx-auto mb-2" style={{ color: strat.color }} />
              <div className="text-sm font-semibold text-white">{strat.name}</div>
              <div className="text-xs text-white/60 mt-1">{strat.description}</div>
            </button>
          ))}
        </div>
      </div>

      <div className="flex gap-4">
        <div className="flex-1"><label className="block text-sm text-white/60 mb-2">Symbol</label><input value={symbol} onChange={e => setSymbol(e.target.value)} className="w-full px-4 py-2 bg-white/5 border border-white/10 rounded-lg text-white" /></div>
        <div className="flex-1"><label className="block text-sm text-white/60 mb-2">Start Date</label><input type="date" value={startDate} onChange={e => setStartDate(e.target.value)} style={{ colorScheme: 'dark' }} className="w-full px-4 py-2 bg-white/5 border border-white/10 rounded-lg text-white" /></div>
        <div className="flex-1"><label className="block text-sm text-white/60 mb-2">End Date</label><input type="date" value={endDate} onChange={e => setEndDate(e.target.value)} style={{ colorScheme: 'dark' }} className="w-full px-4 py-2 bg-white/5 border border-white/10 rounded-lg text-white" /></div>
        <div className="flex-1"><label className="block text-sm text-white/60 mb-2">Initial Capital</label><input type="number" value={initialCapital} onChange={e => setInitialCapital(Number(e.target.value))} className="w-full px-4 py-2 bg-white/5 border border-white/10 rounded-lg text-white" /></div>
        <button onClick={handleRunBacktest} disabled={isRunning} className="mt-7 flex items-center gap-2 px-6 py-2 bg-orange-500 text-white rounded-lg hover:bg-orange-600 disabled:opacity-50"><Play size={16} />{isRunning ? 'Running...' : 'Run Backtest'}</button>
      </div>

      {results && (
        <div className="space-y-4">
          <div className="flex flex-wrap items-center justify-between gap-3 bg-white/5 border border-white/10 rounded-xl p-4">
            <div>
              <div className="text-sm text-white/60">Backtest Reports</div>
              <div className="text-xs text-white/40">Generate downloadable PDF or QuantStats analytics report.</div>
            </div>
            <div className="flex items-center gap-3">
              <button
                onClick={async () => {
                  // QuantStats logic...
                  setQsLoading(true);
                  setQsError(null);
                  try {
                    const strat = selectedStrategies[0];
                    const stratDef = strategies.find(s => s.id === strat);
                    const response = await backtestAPI.quantstatsReport({
                      symbol,
                      strategy: strat,
                      range: '1y',
                      params: stratDef?.params || {},
                      benchmark: market === 'IN' ? '^NSEI' : 'SPY',
                    });
                    const downloadUrl = response.data?.downloadUrl;
                    if (downloadUrl) {
                      const filename = downloadUrl.split('/').pop() || '';
                      const fullUrl = filename ? backtestAPI.downloadReport(filename) : downloadUrl;
                      setQsLink(fullUrl);
                      window.open(fullUrl, '_blank');
                    } else {
                      setQsError('QuantStats report generation failed.');
                    }
                  } catch (err: any) {
                    setQsError(err?.response?.data?.detail || 'QuantStats report failed.');
                  } finally {
                    setQsLoading(false);
                  }
                }}
                disabled={qsLoading || !lastRunResult}
                className="flex items-center gap-2 px-4 py-2 rounded-lg bg-purple-600 text-white text-sm hover:bg-purple-700 disabled:opacity-50"
              >
                <BarChart3 size={14} />
                {qsLoading ? 'Generating…' : 'QuantStats Report'}
              </button>
              {qsLink && (
                <a className="text-xs text-purple-300 hover:text-purple-200" href={qsLink} target="_blank" rel="noreferrer">
                  Open QuantStats
                </a>
              )}
            </div>
            {qsError && <div className="text-xs text-red-400">{qsError}</div>}
          </div>

          {results.isMulti ? (
            <div className="space-y-4">
              <div className="bg-white/5 border border-white/10 rounded-xl p-4">
                <h3 className="text-lg font-semibold text-white mb-4">Strategy Comparison</h3>
                <ResponsiveContainer width="100%" height={300}>
                  <LineChart data={results.combinedChartData}>
                    <XAxis dataKey="date" stroke="#71717a" />
                    <YAxis stroke="#71717a" />
                    <Tooltip contentStyle={{ backgroundColor: '#18181b', border: '1px solid rgba(255,255,255,0.1)' }} />
                    <Legend />
                    {results.strategies?.map((s: any) => (
                      <Line
                        key={s.name}
                        type="monotone"
                        dataKey={s.name}
                        stroke={s.color || '#3b82f6'}
                      />
                    ))}
                  </LineChart>
                </ResponsiveContainer>
              </div>
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
                {results.ranking?.map((s: any, i: number) => (
                  <div key={i} className="p-4 bg-white/5 border border-white/10 rounded-lg">
                    <div className="flex items-center justify-between mb-2">
                      <span className="font-semibold text-white">{s.name}</span><span className="text-sm text-white/60">#{i + 1}</span>
                    </div>
                    <div className="text-2xl font-bold text-white">{s.totalReturn > 0 ? '+' : ''}{s.totalReturn}%</div>
                    <div className="text-xs text-white/40 mt-1">Sharpe: {s.sharpe}</div>
                  </div>
                ))}
              </div>

              <div className="bg-white/5 border border-white/10 rounded-xl p-4 space-y-4">
                <div className="flex flex-wrap gap-2">
                  {results.strategies?.map((s: any) => (
                    <button
                      key={s.id}
                      onClick={() => { setDetailStrategy(s.id); void loadHeatmap(s.id); }}
                      className={`px-3 py-1.5 rounded-full text-xs border transition-colors ${detailStrategy === s.id ? 'border-orange-500 bg-orange-500/20 text-white' : 'border-white/10 bg-white/5 text-white/60 hover:text-white'}`}
                    >
                      {s.displayName}
                    </button>
                  ))}
                </div>

                {results.strategies?.filter((s: any) => s.id === detailStrategy).map((s: any) => {
                  const guide = strategyGuides[s.id] || { entry: 'Entry based on signal trigger.', exit: 'Exit based on signal reversal.', watch: 'Watch indicator conditions for the next setup.' };
                  const equityByDate: Record<string, number> = {};
                  (s.equityCurve || []).forEach((p: any) => { equityByDate[p.date] = p.value; });
                  const entryMarkers = (s.trades || []).map((t: any) => ({ date: t.entryDate, value: equityByDate[t.entryDate] }));
                  const exitMarkers = (s.trades || []).map((t: any) => ({ date: t.exitDate, value: equityByDate[t.exitDate] }));

                  return (
                    <div key={s.id} className="space-y-4">
                      <div>
                        <div className="text-sm text-white/60 mb-2">Signal Playbook</div>
                        <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                          <div className="p-3 rounded-lg bg-white/5 border border-white/10 text-sm text-white/80">Entry: {guide.entry}</div>
                          <div className="p-3 rounded-lg bg-white/5 border border-white/10 text-sm text-white/80">Exit: {guide.exit}</div>
                          <div className="p-3 rounded-lg bg-white/5 border border-white/10 text-sm text-white/80">Next trade: {guide.watch}</div>
                        </div>
                      </div>

                      <div className="bg-white/5 border border-white/10 rounded-xl p-4">
                        <div className="text-sm text-white/60 mb-3">Equity Curve with Trade Markers</div>
                        <ResponsiveContainer width="100%" height={260}>
                          <ComposedChart data={s.equityCurve || []}>
                            <XAxis dataKey="date" stroke="#71717a" />
                            <YAxis stroke="#71717a" />
                            <Tooltip contentStyle={{ backgroundColor: '#18181b', border: '1px solid rgba(255,255,255,0.1)' }} />
                            <Line type="monotone" dataKey="value" stroke={s.color || '#22c55e'} strokeWidth={2} dot={false} />
                            <Scatter name="Entries" data={entryMarkers} dataKey="value" fill="#22c55e" />
                            <Scatter name="Exits" data={exitMarkers} dataKey="value" fill="#ef4444" />
                          </ComposedChart>
                        </ResponsiveContainer>
                      </div>

                      <div className="space-y-3">
                        <div className="text-sm text-white/60">Core Metrics</div>
                        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                          <div className="p-4 bg-white/5 rounded-lg"><div className="text-xs text-white/40">Total Return</div><div className="text-xl font-bold text-white">{s.metrics?.totalReturn}%</div></div>
                          <div className="p-4 bg-white/5 rounded-lg"><div className="text-xs text-white/40">Sharpe</div><div className="text-xl font-bold text-white">{s.metrics?.sharpeRatio}</div></div>
                          <div className="p-4 bg-white/5 rounded-lg"><div className="text-xs text-white/40">Sortino</div><div className="text-xl font-bold text-white">{s.metrics?.sortinoRatio}</div></div>
                          <div className="p-4 bg-white/5 rounded-lg"><div className="text-xs text-white/40">Calmar</div><div className="text-xl font-bold text-white">{s.metrics?.calmarRatio}</div></div>
                          <div className="p-4 bg-white/5 rounded-lg"><div className="text-xs text-white/40">Max Drawdown</div><div className="text-xl font-bold text-red-500">{s.metrics?.maxDrawdown}%</div></div>
                          <div className="p-4 bg-white/5 rounded-lg"><div className="text-xs text-white/40">Max DD Duration</div><div className="text-xl font-bold text-white">{s.metrics?.maxDrawdownDuration}</div></div>
                          <div className="p-4 bg-white/5 rounded-lg"><div className="text-xs text-white/40">Win Rate</div><div className="text-xl font-bold text-white">{s.metrics?.winRate}%</div></div>
                          <div className="p-4 bg-white/5 rounded-lg"><div className="text-xs text-white/40">Total Trades</div><div className="text-xl font-bold text-white">{s.metrics?.totalTrades}</div></div>
                        </div>
                      </div>

                      <div className="space-y-3">
                        <div className="text-sm text-white/60">Advanced Metrics</div>
                        <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-5 gap-4">
                          <div className="p-4 bg-white/5 rounded-lg"><div className="text-xs text-white/40">Profit Factor</div><div className="text-xl font-bold text-white">{s.metrics?.profitFactor ?? '-'}</div></div>
                          <div className="p-4 bg-white/5 rounded-lg"><div className="text-xs text-white/40">Expectancy</div><div className="text-xl font-bold text-white">{s.metrics?.expectancy != null ? `${s.metrics.expectancy}%` : '-'}</div></div>
                          <div className="p-4 bg-white/5 rounded-lg"><div className="text-xs text-white/40">SQN</div><div className="text-xl font-bold text-white">{s.metrics?.sqn ?? '-'}</div></div>
                          <div className="p-4 bg-white/5 rounded-lg"><div className="text-xs text-white/40">Volatility (Ann.)</div><div className="text-xl font-bold text-white">{s.metrics?.annualVolatility != null ? `${s.metrics.annualVolatility}%` : '-'}</div></div>
                          <div className="p-4 bg-white/5 rounded-lg"><div className="text-xs text-white/40">Time in Market</div><div className="text-xl font-bold text-white">{s.metrics?.timeInMarket != null ? `${s.metrics.timeInMarket}%` : '-'}</div></div>
                          <div className="p-4 bg-white/5 rounded-lg"><div className="text-xs text-white/40">Avg Win</div><div className="text-xl font-bold text-emerald-400">{s.metrics?.avgWin != null ? `${s.metrics.avgWin}%` : '-'}</div></div>
                          <div className="p-4 bg-white/5 rounded-lg"><div className="text-xs text-white/40">Avg Loss</div><div className="text-xl font-bold text-red-400">{s.metrics?.avgLoss != null ? `${s.metrics.avgLoss}%` : '-'}</div></div>
                          <div className="p-4 bg-white/5 rounded-lg"><div className="text-xs text-white/40">Best Trade</div><div className="text-xl font-bold text-emerald-400">{s.metrics?.bestTrade != null ? `${s.metrics.bestTrade}%` : '-'}</div></div>
                          <div className="p-4 bg-white/5 rounded-lg"><div className="text-xs text-white/40">Worst Trade</div><div className="text-xl font-bold text-red-400">{s.metrics?.worstTrade != null ? `${s.metrics.worstTrade}%` : '-'}</div></div>
                          <div className="p-4 bg-white/5 rounded-lg"><div className="text-xs text-white/40">Max Consec. Wins</div><div className="text-xl font-bold text-white">{s.metrics?.maxConsecutiveWins ?? '-'}</div></div>
                        </div>
                      </div>

                      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
                        <div className="bg-white/5 border border-white/10 rounded-xl p-4">
                          <div className="flex items-center justify-between mb-3">
                            <h3 className="text-lg font-semibold text-white">Trades</h3>
                            <div className="text-xs text-white/40">{(s.trades || []).length} closed trades</div>
                          </div>
                          <div className="overflow-x-auto">
                            <table className="w-full text-sm">
                              <thead>
                                <tr className="text-white/50">
                                  <th className="text-left py-2">Entry</th>
                                  <th className="text-left py-2">Exit</th>
                                  <th className="text-left py-2">Side</th>
                                  <th className="text-right py-2">Entry Px</th>
                                  <th className="text-right py-2">Exit Px</th>
                                  <th className="text-right py-2">P&amp;L</th>
                                  <th className="text-right py-2">Duration</th>
                                </tr>
                              </thead>
                              <tbody>
                                {(s.trades || []).slice(0, 8).map((t: any, i: number) => (
                                  <tr key={i} className="border-t border-white/10 text-white/80">
                                    <td className="py-2">{t.entryDate}</td>
                                    <td className="py-2">{t.exitDate}</td>
                                    <td className="py-2 capitalize">{t.side}</td>
                                    <td className="py-2 text-right">{t.entryPrice?.toFixed ? t.entryPrice.toFixed(2) : t.entryPrice}</td>
                                    <td className="py-2 text-right">{t.exitPrice?.toFixed ? t.exitPrice.toFixed(2) : t.exitPrice}</td>
                                    <td className={`py-2 text-right ${t.pnl >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>{t.pnlPct?.toFixed ? `${t.pnlPct.toFixed(2)}%` : '-'}</td>
                                    <td className="py-2 text-right">{t.duration}</td>
                                  </tr>
                                ))}
                              </tbody>
                            </table>
                            {(s.trades || []).length === 0 && (
                              <div className="text-white/40 text-sm py-4">No closed trades found for this period.</div>
                            )}
                          </div>
                        </div>

                        <div className="bg-white/5 border border-white/10 rounded-xl p-4">
                          <h3 className="text-lg font-semibold text-white mb-3">Why This Trade</h3>
                          <div className="space-y-3">
                            {(s.trades || []).slice(0, 6).map((t: any, i: number) => (
                              <div key={i} className="p-3 rounded-lg bg-white/5 border border-white/10">
                                <div className="text-sm text-white/80">Trade #{i + 1} • {t.side}</div>
                                <div className="text-xs text-white/50 mt-1">Entry: {t.entryReason || 'Signal triggered'} ({t.entryDate})</div>
                                <div className="text-xs text-white/50">Exit: {t.exitReason || 'Signal triggered'} ({t.exitDate})</div>
                              </div>
                            ))}
                            {(s.trades || []).length === 0 && (
                              <div className="text-white/40 text-sm">No trade explanations available.</div>
                            )}
                          </div>
                        </div>
                      </div>

                      <div className="grid grid-cols-1 gap-4">
                        <div className="bg-white/5 border border-white/10 rounded-xl p-4">
                          <h3 className="text-lg font-semibold text-white mb-3">Monte Carlo Simulation Paths <span className="text-xs font-normal text-white/40">({s.monteCarlo?.simulations || 0} paths)</span></h3>
                          <MonteCarloCanvas monteCarlo={s.monteCarlo} />
                        </div>
                      </div>

                      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
                        <div className="bg-white/5 border border-white/10 rounded-xl p-4">
                          <h3 className="text-lg font-semibold text-white mb-3">Monte Carlo Robustness <span className="text-xs font-normal text-white/40">({s.monteCarlo?.simulations || 0} simulations)</span></h3>
                          {s.monteCarlo?.histogram?.length ? (
                            <div>
                              <ResponsiveContainer width="100%" height={220}>
                                <BarChart data={s.monteCarlo.histogram}>
                                  <CartesianGrid stroke="rgba(255,255,255,0.06)" />
                                  <XAxis dataKey="return" stroke="#71717a" tickFormatter={(v) => `${v.toFixed(0)}%`} />
                                  <YAxis stroke="#71717a" />
                                  <Tooltip contentStyle={{ backgroundColor: '#18181b', border: '1px solid rgba(255,255,255,0.1)' }} />
                                  <Bar dataKey="count" fill="#f59e0b" />
                                </BarChart>
                              </ResponsiveContainer>
                              <div className="flex flex-wrap items-center gap-4 text-xs text-white/60 mt-3">
                                <div>P5: {s.monteCarlo.percentiles?.p5?.toFixed ? `${s.monteCarlo.percentiles.p5.toFixed(2)}%` : '-'}</div>
                                <div>P25: {s.monteCarlo.percentiles?.p25?.toFixed ? `${s.monteCarlo.percentiles.p25.toFixed(2)}%` : '-'}</div>
                                <div className="font-semibold text-white/80">P50: {s.monteCarlo.percentiles?.p50?.toFixed ? `${s.monteCarlo.percentiles.p50.toFixed(2)}%` : '-'}</div>
                                <div>P75: {s.monteCarlo.percentiles?.p75?.toFixed ? `${s.monteCarlo.percentiles.p75.toFixed(2)}%` : '-'}</div>
                                <div>P95: {s.monteCarlo.percentiles?.p95?.toFixed ? `${s.monteCarlo.percentiles.p95.toFixed(2)}%` : '-'}</div>
                              </div>
                              {s.monteCarlo.riskMetrics && (
                                <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mt-4 pt-4 border-t border-white/10">
                                  <div><div className="text-xs text-white/40">VaR (95%)</div><div className="text-sm font-bold text-red-400">{s.monteCarlo.riskMetrics.var95}%</div></div>
                                  <div><div className="text-xs text-white/40">CVaR (95%)</div><div className="text-sm font-bold text-red-400">{s.monteCarlo.riskMetrics.cvar95}%</div></div>
                                  <div><div className="text-xs text-white/40">Ruin Prob.</div><div className="text-sm font-bold text-red-400">{s.monteCarlo.riskMetrics.ruinProbability}%</div></div>
                                  <div><div className="text-xs text-white/40">Median Max DD</div><div className="text-sm font-bold text-white">{s.monteCarlo.riskMetrics.medianMaxDrawdown}%</div></div>
                                  <div><div className="text-xs text-white/40">Best Case</div><div className="text-sm font-bold text-emerald-400">{s.monteCarlo.riskMetrics.bestCase}%</div></div>
                                  <div><div className="text-xs text-white/40">Worst Case</div><div className="text-sm font-bold text-red-400">{s.monteCarlo.riskMetrics.worstCase}%</div></div>
                                  <div><div className="text-xs text-white/40">Mean Return</div><div className="text-sm font-bold text-white">{s.monteCarlo.riskMetrics.meanReturn}%</div></div>
                                </div>
                              )}
                            </div>
                          ) : (
                            <div className="text-white/40 text-sm">Monte Carlo simulation unavailable.</div>
                          )}
                        </div>

                        <div className="bg-white/5 border border-white/10 rounded-xl p-4">
                          <h3 className="text-lg font-semibold text-white mb-3">Strategy Heatmap</h3>
                          {heatmapLoading && <div className="text-white/40 text-sm">Generating heatmap…</div>}
                          {heatmapError && <div className="text-white/40 text-sm">{heatmapError}</div>}
                          {!heatmapLoading && heatmap && (
                            (() => {
                              const allValues = heatmap.values.flat().filter((v: any) => typeof v === 'number');
                              const min = allValues.length ? Math.min(...allValues) : 0;
                              const max = allValues.length ? Math.max(...allValues) : 1;
                              return (
                                <div className="space-y-2">
                                  <div className="text-xs text-white/50">Total Return % vs {heatmap.paramX} × {heatmap.paramY}</div>
                                  <div className="grid gap-1" style={{ gridTemplateColumns: `120px repeat(${heatmap.xValues.length}, minmax(0, 1fr))` }}>
                                    <div></div>
                                    {heatmap.xValues.map((x: any, i: number) => (
                                      <div key={`x-${i}`} className="text-xs text-white/50 text-center">{heatmap.paramX} {x}</div>
                                    ))}
                                    {heatmap.yValues.map((y: any, yi: number) => (
                                      <div key={`row-${yi}`} className="contents">
                                        <div className="text-xs text-white/50 pr-2">{heatmap.paramY} {y}</div>
                                        {heatmap.values[yi].map((val: any, xi: number) => (
                                          <div
                                            key={`cell-${yi}-${xi}`}
                                            className="text-xs text-white text-center rounded-md py-2"
                                            style={{ backgroundColor: getHeatColor(val, min, max) }}
                                          >
                                            {val === null || val === undefined ? '-' : `${val.toFixed(1)}%`}
                                          </div>
                                        ))}
                                      </div>
                                    ))}
                                  </div>
                                </div>
                              );
                            })()
                          )}
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          ) : (
            <div className="space-y-4">
              <div className="bg-white/5 border border-white/10 rounded-xl p-4">
                <ResponsiveContainer width="100%" height={300}>
                  <ComposedChart data={results.equityCurve}>
                    <XAxis dataKey="date" stroke="#71717a" />
                    <YAxis stroke="#71717a" />
                    <Tooltip contentStyle={{ backgroundColor: '#18181b', border: '1px solid rgba(255,255,255,0.1)' }} />
                    <Legend />
                    <Line type="monotone" dataKey="portfolio" stroke="#22c55e" strokeWidth={2} name="Portfolio" dot={false} />
                    <Line type="monotone" dataKey="benchmark" stroke="#71717a" strokeDasharray="5 5" name="Benchmark" dot={false} />

                    {/* Strategy Indicators */}
                    {(() => {
                      const strat = strategies.find(s => s.id === selectedStrategies[0]);
                      if (!strat?.indicators) return null;
                      return strat.indicators.map((ind: any) => {
                        const lineProps: any = {
                          key: ind.key,
                          type: "monotone",
                          dataKey: ind.key,
                          stroke: ind.color,
                          strokeWidth: 1,
                          dot: false,
                          name: ind.name
                        };
                        if (ind.axis === 'right') lineProps.yAxisId = 'right';
                        return <Line {...lineProps} />;
                      });
                    })()}

                    {/* Right Axis if needed */}
                    {strategies.find(s => s.id === selectedStrategies[0])?.indicators?.some((ind: any) => ind.axis === 'right') && (
                      <YAxis yAxisId="right" orientation="right" stroke="#71717a" />
                    )}

                    <Scatter name="Entries" data={(results.trades || []).map((t: any) => ({ date: t.entryDate, price: t.entryPrice }))} dataKey="price" fill="#22c55e" />
                    <Scatter name="Exits" data={(results.trades || []).map((t: any) => ({ date: t.exitDate, price: t.exitPrice }))} dataKey="price" fill="#ef4444" />
                  </ComposedChart>
                </ResponsiveContainer>
              </div>

              <div className="bg-white/5 border border-white/10 rounded-xl p-4">
                <div className="text-sm text-white/60 mb-2">Signal Playbook</div>
                <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                  <div className="p-3 rounded-lg bg-white/5 border border-white/10 text-sm text-white/80">Entry: {currentGuide.entry}</div>
                  <div className="p-3 rounded-lg bg-white/5 border border-white/10 text-sm text-white/80">Exit: {currentGuide.exit}</div>
                  <div className="p-3 rounded-lg bg-white/5 border border-white/10 text-sm text-white/80">Next trade: {currentGuide.watch}</div>
                </div>
              </div>

              <div className="space-y-3">
                <div className="text-sm text-white/60">Core Metrics</div>
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                  <div className="p-4 bg-white/5 rounded-lg"><div className="text-xs text-white/40">Total Return</div><div className="text-xl font-bold text-white">{results.metrics.totalReturn}%</div></div>
                  <div className="p-4 bg-white/5 rounded-lg"><div className="text-xs text-white/40">Sharpe</div><div className="text-xl font-bold text-white">{results.metrics.sharpeRatio}</div></div>
                  <div className="p-4 bg-white/5 rounded-lg"><div className="text-xs text-white/40">Sortino</div><div className="text-xl font-bold text-white">{results.metrics.sortinoRatio}</div></div>
                  <div className="p-4 bg-white/5 rounded-lg"><div className="text-xs text-white/40">Calmar</div><div className="text-xl font-bold text-white">{results.metrics.calmarRatio}</div></div>
                  <div className="p-4 bg-white/5 rounded-lg"><div className="text-xs text-white/40">Max Drawdown</div><div className="text-xl font-bold text-red-500">{results.metrics.maxDrawdown}%</div></div>
                  <div className="p-4 bg-white/5 rounded-lg"><div className="text-xs text-white/40">Max DD Duration</div><div className="text-xl font-bold text-white">{results.metrics.maxDrawdownDuration}</div></div>
                  <div className="p-4 bg-white/5 rounded-lg"><div className="text-xs text-white/40">Win Rate</div><div className="text-xl font-bold text-white">{results.metrics.winRate}%</div></div>
                  <div className="p-4 bg-white/5 rounded-lg"><div className="text-xs text-white/40">Total Trades</div><div className="text-xl font-bold text-white">{results.metrics.totalTrades}</div></div>
                </div>
              </div>

              <div className="space-y-3">
                <div className="text-sm text-white/60">Advanced Metrics</div>
                <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-5 gap-4">
                  <div className="p-4 bg-white/5 rounded-lg"><div className="text-xs text-white/40">Profit Factor</div><div className="text-xl font-bold text-white">{results.metrics.profitFactor ?? '-'}</div></div>
                  <div className="p-4 bg-white/5 rounded-lg"><div className="text-xs text-white/40">Expectancy</div><div className="text-xl font-bold text-white">{results.metrics.expectancy != null ? `${results.metrics.expectancy}%` : '-'}</div></div>
                  <div className="p-4 bg-white/5 rounded-lg"><div className="text-xs text-white/40">SQN</div><div className="text-xl font-bold text-white">{results.metrics.sqn ?? '-'}</div></div>
                  <div className="p-4 bg-white/5 rounded-lg"><div className="text-xs text-white/40">Volatility (Ann.)</div><div className="text-xl font-bold text-white">{results.metrics.annualVolatility != null ? `${results.metrics.annualVolatility}%` : '-'}</div></div>
                  <div className="p-4 bg-white/5 rounded-lg"><div className="text-xs text-white/40">Time in Market</div><div className="text-xl font-bold text-white">{results.metrics.timeInMarket != null ? `${results.metrics.timeInMarket}%` : '-'}</div></div>
                  <div className="p-4 bg-white/5 rounded-lg"><div className="text-xs text-white/40">Avg Win</div><div className="text-xl font-bold text-emerald-400">{results.metrics.avgWin != null ? `${results.metrics.avgWin}%` : '-'}</div></div>
                  <div className="p-4 bg-white/5 rounded-lg"><div className="text-xs text-white/40">Avg Loss</div><div className="text-xl font-bold text-red-400">{results.metrics.avgLoss != null ? `${results.metrics.avgLoss}%` : '-'}</div></div>
                  <div className="p-4 bg-white/5 rounded-lg"><div className="text-xs text-white/40">Best Trade</div><div className="text-xl font-bold text-emerald-400">{results.metrics.bestTrade != null ? `${results.metrics.bestTrade}%` : '-'}</div></div>
                  <div className="p-4 bg-white/5 rounded-lg"><div className="text-xs text-white/40">Worst Trade</div><div className="text-xl font-bold text-red-400">{results.metrics.worstTrade != null ? `${results.metrics.worstTrade}%` : '-'}</div></div>
                  <div className="p-4 bg-white/5 rounded-lg"><div className="text-xs text-white/40">Max Consec. Wins</div><div className="text-xl font-bold text-white">{results.metrics.maxConsecutiveWins ?? '-'}</div></div>
                </div>
              </div>

              <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
                <div className="bg-white/5 border border-white/10 rounded-xl p-4">
                  <div className="flex items-center justify-between mb-3">
                    <h3 className="text-lg font-semibold text-white">Trades</h3>
                    <div className="text-xs text-white/40">{(results.trades || []).length} closed trades</div>
                  </div>
                  <div className="overflow-x-auto">
                    <table className="w-full text-sm">
                      <thead>
                        <tr className="text-white/50">
                          <th className="text-left py-2">Entry</th>
                          <th className="text-left py-2">Exit</th>
                          <th className="text-left py-2">Side</th>
                          <th className="text-right py-2">Entry Px</th>
                          <th className="text-right py-2">Exit Px</th>
                          <th className="text-right py-2">P&amp;L</th>
                          <th className="text-right py-2">Duration</th>
                        </tr>
                      </thead>
                      <tbody>
                        {(results.trades || []).slice(0, 8).map((t: any, i: number) => (
                          <tr key={i} className="border-t border-white/10 text-white/80">
                            <td className="py-2">{t.entryDate}</td>
                            <td className="py-2">{t.exitDate}</td>
                            <td className="py-2 capitalize">{t.side}</td>
                            <td className="py-2 text-right">{t.entryPrice?.toFixed ? t.entryPrice.toFixed(2) : t.entryPrice}</td>
                            <td className="py-2 text-right">{t.exitPrice?.toFixed ? t.exitPrice.toFixed(2) : t.exitPrice}</td>
                            <td className={`py-2 text-right ${t.pnl >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>{t.pnlPct?.toFixed ? `${t.pnlPct.toFixed(2)}%` : '-'}</td>
                            <td className="py-2 text-right">{t.duration}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                    {(results.trades || []).length === 0 && (
                      <div className="text-white/40 text-sm py-4">No closed trades found for this period.</div>
                    )}
                  </div>
                </div>

                <div className="bg-white/5 border border-white/10 rounded-xl p-4">
                  <h3 className="text-lg font-semibold text-white mb-3">Why This Trade</h3>
                  <div className="space-y-3">
                    {(results.trades || []).slice(0, 6).map((t: any, i: number) => (
                      <div key={i} className="p-3 rounded-lg bg-white/5 border border-white/10">
                        <div className="text-sm text-white/80">Trade #{i + 1} • {t.side}</div>
                        <div className="text-xs text-white/50 mt-1">Entry: {t.entryReason || 'Signal triggered'} ({t.entryDate})</div>
                        <div className="text-xs text-white/50">Exit: {t.exitReason || 'Signal triggered'} ({t.exitDate})</div>
                      </div>
                    ))}
                    {(results.trades || []).length === 0 && (
                      <div className="text-white/40 text-sm">No trade explanations available.</div>
                    )}
                  </div>
                </div>
              </div>

              <div className="bg-white/5 border border-white/10 rounded-xl p-4">
                <h3 className="text-lg font-semibold text-white mb-3">Monte Carlo Simulation Paths <span className="text-xs font-normal text-white/40">({results.monteCarlo?.simulations || 0} paths)</span></h3>
                <MonteCarloCanvas monteCarlo={results.monteCarlo} />
              </div>

              <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
                <div className="bg-white/5 border border-white/10 rounded-xl p-4">
                  <h3 className="text-lg font-semibold text-white mb-3">Monte Carlo Robustness <span className="text-xs font-normal text-white/40">({results.monteCarlo?.simulations || 0} simulations)</span></h3>
                  {results.monteCarlo?.histogram?.length ? (
                    <div>
                      <ResponsiveContainer width="100%" height={220}>
                        <BarChart data={results.monteCarlo.histogram}>
                          <CartesianGrid stroke="rgba(255,255,255,0.06)" />
                          <XAxis dataKey="return" stroke="#71717a" tickFormatter={(v) => `${v.toFixed(0)}%`} />
                          <YAxis stroke="#71717a" />
                          <Tooltip contentStyle={{ backgroundColor: '#18181b', border: '1px solid rgba(255,255,255,0.1)' }} />
                          <Bar dataKey="count" fill="#f59e0b" />
                        </BarChart>
                      </ResponsiveContainer>
                      <div className="flex flex-wrap items-center gap-4 text-xs text-white/60 mt-3">
                        <div>P5: {results.monteCarlo.percentiles?.p5?.toFixed ? `${results.monteCarlo.percentiles.p5.toFixed(2)}%` : '-'}</div>
                        <div>P25: {results.monteCarlo.percentiles?.p25?.toFixed ? `${results.monteCarlo.percentiles.p25.toFixed(2)}%` : '-'}</div>
                        <div className="font-semibold text-white/80">P50: {results.monteCarlo.percentiles?.p50?.toFixed ? `${results.monteCarlo.percentiles.p50.toFixed(2)}%` : '-'}</div>
                        <div>P75: {results.monteCarlo.percentiles?.p75?.toFixed ? `${results.monteCarlo.percentiles.p75.toFixed(2)}%` : '-'}</div>
                        <div>P95: {results.monteCarlo.percentiles?.p95?.toFixed ? `${results.monteCarlo.percentiles.p95.toFixed(2)}%` : '-'}</div>
                      </div>
                      {results.monteCarlo.riskMetrics && (
                        <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mt-4 pt-4 border-t border-white/10">
                          <div><div className="text-xs text-white/40">VaR (95%)</div><div className="text-sm font-bold text-red-400">{results.monteCarlo.riskMetrics.var95}%</div></div>
                          <div><div className="text-xs text-white/40">CVaR (95%)</div><div className="text-sm font-bold text-red-400">{results.monteCarlo.riskMetrics.cvar95}%</div></div>
                          <div><div className="text-xs text-white/40">Ruin Prob.</div><div className="text-sm font-bold text-red-400">{results.monteCarlo.riskMetrics.ruinProbability}%</div></div>
                          <div><div className="text-xs text-white/40">Median Max DD</div><div className="text-sm font-bold text-white">{results.monteCarlo.riskMetrics.medianMaxDrawdown}%</div></div>
                          <div><div className="text-xs text-white/40">Best Case</div><div className="text-sm font-bold text-emerald-400">{results.monteCarlo.riskMetrics.bestCase}%</div></div>
                          <div><div className="text-xs text-white/40">Worst Case</div><div className="text-sm font-bold text-red-400">{results.monteCarlo.riskMetrics.worstCase}%</div></div>
                          <div><div className="text-xs text-white/40">Mean Return</div><div className="text-sm font-bold text-white">{results.monteCarlo.riskMetrics.meanReturn}%</div></div>
                        </div>
                      )}
                    </div>
                  ) : (
                    <div className="text-white/40 text-sm">Monte Carlo simulation unavailable.</div>
                  )}
                </div>

                <div className="bg-white/5 border border-white/10 rounded-xl p-4">
                  <h3 className="text-lg font-semibold text-white mb-3">Strategy Heatmap</h3>
                  {heatmapLoading && <div className="text-white/40 text-sm">Generating heatmap…</div>}
                  {heatmapError && <div className="text-white/40 text-sm">{heatmapError}</div>}
                  {!heatmapLoading && heatmap && (
                    (() => {
                      const allValues = heatmap.values.flat().filter((v: any) => typeof v === 'number');
                      const min = allValues.length ? Math.min(...allValues) : 0;
                      const max = allValues.length ? Math.max(...allValues) : 1;
                      return (
                        <div className="space-y-2">
                          <div className="text-xs text-white/50">Total Return % vs {heatmap.paramX} × {heatmap.paramY}</div>
                          <div className="grid gap-1" style={{ gridTemplateColumns: `120px repeat(${heatmap.xValues.length}, minmax(0, 1fr))` }}>
                            <div></div>
                            {heatmap.xValues.map((x: any, i: number) => (
                              <div key={`x-${i}`} className="text-xs text-white/50 text-center">{heatmap.paramX} {x}</div>
                            ))}
                            {heatmap.yValues.map((y: any, yi: number) => (
                              <div key={`row-${yi}`} className="contents">
                                <div className="text-xs text-white/50 pr-2">{heatmap.paramY} {y}</div>
                                {heatmap.values[yi].map((val: any, xi: number) => (
                                  <div
                                    key={`cell-${yi}-${xi}`}
                                    className="text-xs text-white text-center rounded-md py-2"
                                    style={{ backgroundColor: getHeatColor(val, min, max) }}
                                  >
                                    {val === null || val === undefined ? '-' : `${val.toFixed(1)}%`}
                                  </div>
                                ))}
                              </div>
                            ))}
                          </div>
                        </div>
                      );
                    })()
                  )}
                </div>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
