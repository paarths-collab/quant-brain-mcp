'use client'

import { useState, useRef, useCallback, useEffect } from 'react'
import {
  Play, TrendingUp, Activity, Zap, Target, BarChart3,
  Layers, ArrowUpDown, Crosshair, GitBranch, Shield, DollarSign
} from 'lucide-react'
import {
  LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer,
  Legend, ComposedChart, BarChart, Bar, CartesianGrid
} from 'recharts'
import { backtestAPI } from '@/lib/api'

// Unified card styles from dashboard/sectors/technical
const CARD = "group relative p-6 rounded-2xl border border-white/20 bg-white/[0.03] backdrop-blur-xl hover:border-indigo-500/30 hover:bg-white/[0.05] transition-all duration-500 overflow-hidden"
const CARD_GLOW = "group relative p-6 rounded-2xl border border-white/25 bg-white/[0.03] backdrop-blur-xl shadow-[0_0_24px_rgba(79,70,229,0.06)] hover:shadow-[0_0_32px_rgba(79,70,229,0.12)] hover:border-indigo-500/40 hover:bg-white/[0.05] transition-all duration-500 overflow-hidden"
const CONTROL_BTN = "px-4 py-2 rounded-lg text-[12px] font-dm-mono uppercase tracking-widest transition-all duration-300 border border-white/20"

// ─── Strategy Definitions ─────────────────────────────────────────────────────
const STRATEGIES = [
  { id: 'momentum', name: 'Momentum', color: '#3b82f6', description: 'Price momentum signals', params: { lookback: 20 } },
  { id: 'mean_reversion', name: 'Mean Revert', color: '#10b981', description: 'Deviation from MA', params: { window: 20, num_std: 2 } },
  { id: 'ema_crossover', name: 'EMA Cross', color: '#f59e0b', description: 'Golden/Death cross EMAs', params: { fast: 12, slow: 26 } },
  { id: 'sma_crossover', name: 'SMA Cross', color: '#06b6d4', description: '50/200 SMA crossover', params: { short_window: 50, long_window: 200 } },
  { id: 'macd', name: 'MACD', color: '#8b5cf6', description: 'MACD signal crossover', params: { fast: 12, slow: 26, signal: 9 } },
  { id: 'rsi_reversal', name: 'RSI Reversal', color: '#ef4444', description: 'Oversold / overbought', params: { window: 14, lower: 30, upper: 70 } },
  { id: 'rsi_momentum', name: 'RSI Momentum', color: '#ec4899', description: 'RSI cross + trend filter', params: { rsi_window: 14, lower: 40, upper: 60 } },
  { id: 'breakout', name: 'Breakout', color: '#14b8a6', description: 'Donchian channel break', params: { lookback: 20 } },
  { id: 'fibonacci_pullback', name: 'Fib Pullback', color: '#a855f7', description: 'Fibonacci retracement', params: { lookback: 50 } },
  { id: 'support_resistance', name: 'Sup/Res', color: '#f97316', description: 'S/R bounce trading', params: { lookback: 30, tolerance_pct: 0.01 } },
]

// ─── Monte Carlo Canvas ───────────────────────────────────────────────────────
function MonteCarloCanvas({ monteCarlo }: { monteCarlo: any }) {
  const canvasRef = useRef<HTMLCanvasElement>(null)

  const draw = useCallback(() => {
    const canvas = canvasRef.current
    if (!canvas || !monteCarlo?.simulationPaths?.length) return
    const ctx = canvas.getContext('2d')
    if (!ctx) return
    const dpr = window.devicePixelRatio || 1
    const rect = canvas.getBoundingClientRect()
    canvas.width = rect.width * dpr
    canvas.height = rect.height * dpr
    ctx.scale(dpr, dpr)
    const W = rect.width, H = rect.height
    const pad = { top: 16, right: 16, bottom: 28, left: 60 }
    const plotW = W - pad.left - pad.right, plotH = H - pad.top - pad.bottom

    const paths: number[][] = monteCarlo.simulationPaths
    const steps = paths[0]?.length || 0
    if (steps < 2) return

    let yMin = Infinity, yMax = -Infinity
    for (const p of paths) for (const v of p) { if (v < yMin) yMin = v; if (v > yMax) yMax = v }
    const yPad = (yMax - yMin) * 0.05; yMin -= yPad; yMax += yPad

    const xS = (i: number) => pad.left + (i / (steps - 1)) * plotW
    const yS = (v: number) => pad.top + plotH - ((v - yMin) / (yMax - yMin)) * plotH
    const fmtD = (v: number) => Math.abs(v) >= 1e6 ? `$${(v / 1e6).toFixed(1)}M` : Math.abs(v) >= 1e3 ? `$${(v / 1e3).toFixed(0)}K` : `$${v.toFixed(0)}`

    ctx.clearRect(0, 0, W, H)
    ctx.strokeStyle = 'rgba(255,255,255,0.05)'; ctx.lineWidth = 1
    for (let i = 0; i <= 5; i++) {
      const y = pad.top + (i / 5) * plotH
      ctx.beginPath(); ctx.moveTo(pad.left, y); ctx.lineTo(W - pad.right, y); ctx.stroke()
    }

    ctx.lineWidth = 0.4; ctx.globalAlpha = 0.04; ctx.strokeStyle = '#f59e0b'
    for (const p of paths) {
      ctx.beginPath()
      for (let i = 0; i < steps; i++) { i === 0 ? ctx.moveTo(xS(i), yS(p[i])) : ctx.lineTo(xS(i), yS(p[i])) }
      ctx.stroke()
    }
    ctx.globalAlpha = 1

    const pctColors: [string, string, number][] = [
      ['p5', '#ef4444', 1.5], ['p25', '#f97316', 1.2], ['p50', '#22c55e', 2.5], ['p75', '#3b82f6', 1.2], ['p95', '#8b5cf6', 1.5]
    ]
    const pp = monteCarlo.percentilePaths
    if (pp) {
      for (const [key, color, width] of pctColors) {
        const curve = pp[key]; if (!curve) continue
        ctx.strokeStyle = color; ctx.lineWidth = width
        ctx.beginPath()
        for (let i = 0; i < curve.length; i++) { i === 0 ? ctx.moveTo(xS(i), yS(curve[i])) : ctx.lineTo(xS(i), yS(curve[i])) }
        ctx.stroke()
      }
    }

    ctx.fillStyle = 'rgba(255,255,255,0.4)'; ctx.font = '10px monospace'; ctx.textAlign = 'right'
    for (let i = 0; i <= 5; i++) {
      const val = yMax - (i / 5) * (yMax - yMin)
      ctx.fillText(fmtD(val), pad.left - 4, pad.top + (i / 5) * plotH + 4)
    }
  }, [monteCarlo])

  useEffect(() => {
    draw()
    window.addEventListener('resize', draw)
    return () => window.removeEventListener('resize', draw)
  }, [draw])

  if (!monteCarlo?.simulationPaths?.length) return <div className="text-[11px] font-mono text-white/25 py-4">Monte Carlo simulation unavailable.</div>

  return (
    <div className="space-y-2">
      <canvas ref={canvasRef} className="w-full rounded-xl" style={{ height: 260 }} />
      <div className="flex items-center gap-4 text-[10px] font-mono">
        {[['P5', '#ef4444'], ['P25', '#f97316'], ['P50 (Median)', '#22c55e'], ['P75', '#3b82f6'], ['P95', '#8b5cf6']].map(([l, c]) => (
          <span key={l} style={{ color: c }}>{l}</span>
        ))}
      </div>
    </div>
  )
}

// ─── Metric Chip ──────────────────────────────────────────────────────────────
function MetricChip({ label, value, color = 'text-white' }: { label: string; value: any; color?: string }) {
  return (
    <div className="p-4 rounded-2xl border border-white/[0.07] bg-white/[0.03] backdrop-blur-xl flex flex-col gap-1">
      <div className="text-[10px] font-dm-mono text-white/30 uppercase tracking-widest mb-0.5">{label}</div>
      <div className={`text-xl font-dm-mono font-bold tabular-nums ${color}`}>{value ?? '—'}</div>
    </div>
  )
}

// ─── Main Page ─────────────────────────────────────────────────────────────────
export default function BacktestPage() {
  const [market, setMarket] = useState('US')
  const [selectedStrategies, setSelectedStrategies] = useState(['ema_crossover'])
  const [symbol, setSymbol] = useState('AAPL')
  const [initialCapital, setInitialCapital] = useState(100000)
  const [startDate, setStartDate] = useState('')
  const [endDate, setEndDate] = useState('')
  const [isRunning, setIsRunning] = useState(false)
  const [results, setResults] = useState<any>(null)
  const [detailStrategy, setDetailStrategy] = useState('ema_crossover')

  const toggleStrategy = (id: string) => {
    setSelectedStrategies(prev => {
      if (prev.includes(id)) return prev.length === 1 ? prev : prev.filter(s => s !== id)
      if (prev.length >= 4) return prev
      return [...prev, id]
    })
  }

  const handleRun = async () => {
    setIsRunning(true)
    try {
      const params: any = {}
      selectedStrategies.forEach(id => {
        const strat = STRATEGIES.find(s => s.id === id)
        if (strat?.params) params[id] = strat.params
      })
      const data = await backtestAPI.run({
        symbol,
        strategies: selectedStrategies,
        range: '1y',
        params,
        start: startDate || undefined,
        end: endDate || undefined,
      })

      if (data.mode === 'multi_strategy') {
        const stratResults = data.strategies || {}
        const strategies = Object.entries(stratResults).map(([id, d]: any) => {
          const def = STRATEGIES.find(s => s.id === id)
          return { id, displayName: def?.name || id, color: d?.color || def?.color, metrics: d?.metrics, trades: d?.trades || [], monteCarlo: d?.monteCarlo, equityCurve: d?.equityCurve || [] }
        })
        const ranking = (data.ranking || []).map((r: any, i: number) => {
          const def = STRATEGIES.find(s => s.id === r.strategy)
          return { name: def?.name || r.strategy, totalReturn: r.return, sharpe: stratResults[r.strategy]?.metrics?.sharpeRatio ?? '—' }
        })
        setResults({ isMulti: true, strategies, combinedChartData: data.combinedChartData || [], ranking })
        setDetailStrategy(strategies[0]?.id ?? selectedStrategies[0])
      } else {
        const equityCurve = (data.equity_curve || []).map((p: any, i: number) => ({
          ...p, date: p.date || `Day ${i + 1}`, portfolio: p.value || initialCapital, benchmark: p.benchmark || initialCapital,
        }))
        setResults({ isMulti: false, equityCurve, metrics: data.metrics || {}, trades: data.trades || [], monteCarlo: data.monteCarlo || null })
        setDetailStrategy(selectedStrategies[0])
      }
    } catch (err) {
      console.error('Backtest error:', err)
    } finally {
      setIsRunning(false)
    }
  }

  const detailStrat = results?.isMulti ? results.strategies?.find((s: any) => s.id === detailStrategy) : null

  return (
    <div className="space-y-8 max-w-7xl mx-auto py-8">
      {/* Header */}
      <div className="flex items-center justify-between mb-2">
        <div>
          <p className="text-[13px] font-dm-mono text-white/50 tracking-widest uppercase">Multi-strategy backtesting · Monte Carlo simulation · Parameter optimization</p>
        </div>
        <div className="flex gap-2">
          <button onClick={() => { setMarket('US'); setSymbol('AAPL') }} className={`${CONTROL_BTN} ${market === 'US' ? 'bg-indigo-500/10 text-indigo-400 border-indigo-500/30' : 'bg-white/[0.03] text-white/30 hover:bg-white/[0.06]'}`}>US</button>
          <button onClick={() => { setMarket('IN'); setSymbol('RELIANCE.NS') }} className={`${CONTROL_BTN} ${market === 'IN' ? 'bg-indigo-500/10 text-indigo-400 border-indigo-500/30' : 'bg-white/[0.03] text-white/30 hover:bg-white/[0.06]'}`}>India</button>
        </div>
      </div>

      {/* Strategy Grid */}
      <div>
        <div className="text-[11px] font-dm-mono text-white/60 uppercase tracking-widest mb-3">Select Strategies (Max 4)</div>
        <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
          {STRATEGIES.map(strat => {
            const active = selectedStrategies.includes(strat.id)
            return (
              <button key={strat.id} onClick={() => toggleStrategy(strat.id)}
                className={`${CARD} flex flex-col items-start gap-1.5 transition-all text-left ${active ? 'border-indigo-500/40 bg-indigo-500/10' : ''}`}> 
                <div className="flex items-center gap-2 mb-1.5">
                   <div className="w-1.5 h-1.5 rounded-full" style={{ backgroundColor: strat.color }} />
                   <div className="text-[13px] font-dm-mono font-semibold text-white">{strat.name}</div>
                </div>
                <div className="text-[11px] text-white/60 leading-tight font-inter">{strat.description}</div>
              </button>
            )
          })}
        </div>
      </div>

      {/* Config Row */}
      <div className="flex flex-wrap gap-4 items-end">
        {[
          { label: 'Symbol', value: symbol, onChange: setSymbol, type: 'text' },
          { label: 'Start Date', value: startDate, onChange: setStartDate, type: 'date' },
          { label: 'End Date', value: endDate, onChange: setEndDate, type: 'date' },
        ].map(field => (
          <div key={field.label} className="flex-1 min-w-[140px]">
            <label className="block text-[10px] font-dm-mono text-white/30 uppercase tracking-widest mb-2">{field.label}</label>
            <input
              type={field.type} value={field.value} onChange={e => field.onChange(e.target.value)}
              style={{ colorScheme: 'dark' }}
              className="w-full px-3 py-2.5 bg-white/[0.03] border border-white/[0.08] rounded-xl text-white font-dm-mono text-[13px] focus:outline-none focus:border-indigo-500/30 transition-colors"
            />
          </div>
        ))}
        <div className="flex-1 min-w-[140px]">
          <label className="block text-[10px] font-dm-mono text-white/30 uppercase tracking-widest mb-2">Initial Capital</label>
          <input
            type="number" value={initialCapital} onChange={e => setInitialCapital(Number(e.target.value))}
            className="w-full px-3 py-2.5 bg-white/[0.03] border border-white/[0.08] rounded-xl text-white font-dm-mono text-[13px] focus:outline-none focus:border-indigo-500/30 transition-colors"
          />
        </div>
        <button onClick={handleRun} disabled={isRunning}
          className="flex items-center gap-2 px-8 py-2.5 bg-indigo-500/10 backdrop-blur-xl border border-indigo-500/30 text-indigo-400 hover:bg-indigo-500/20 hover:border-indigo-500/50 rounded-2xl text-[14px] font-dm-mono font-bold disabled:opacity-50 transition-all duration-300 shadow-[0_0_20px_rgba(99,102,241,0.1)] hover:shadow-[0_0_30px_rgba(99,102,241,0.25)] tracking-widest">
          {isRunning ? 'RUNNING_SIMULATION...' : 'RUN_BACKTEST'}
        </button>
      </div>

      {/* Results */}
      {results && (
        <div className="space-y-5">
          {results.isMulti ? (
            <>
              {/* Multi-strategy comparison */}
              <div className={CARD_GLOW}>
                <div className="text-[11px] font-mono text-white/30 uppercase tracking-widest mb-4">Strategy Comparison</div>
                <ResponsiveContainer width="100%" height={280}>
                  <LineChart data={results.combinedChartData}>
                    <XAxis dataKey="date" stroke="#3f3f46" tick={{ fill: '#52525b', fontSize: 10, fontFamily: 'monospace' }} />
                    <YAxis stroke="#3f3f46" tick={{ fill: '#52525b', fontSize: 10, fontFamily: 'monospace' }} />
                    <Tooltip contentStyle={{ background: '#0a0a0a', border: '1px solid rgba(255,255,255,0.1)', borderRadius: 8, fontSize: 11, fontFamily: 'monospace' }} />
                    <Legend wrapperStyle={{ fontSize: 11, fontFamily: 'monospace' }} />
                    {results.strategies?.map((s: any) => <Line key={s.id} type="monotone" dataKey={s.id} stroke={s.color || '#f59e0b'} strokeWidth={2} dot={false} name={s.displayName} />)}
                  </LineChart>
                </ResponsiveContainer>
              </div>

              {/* Rankings */}
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                {results.ranking?.map((s: any, i: number) => (
                  <div key={i} className="p-4 rounded-xl border border-white/[0.07] bg-white/[0.02]">
                    <div className="flex items-center justify-between mb-2">
                      <span className="text-[12px] font-mono font-semibold text-white">{s.name}</span>
                      <span className="text-[10px] font-mono text-white/25">#{i + 1}</span>
                    </div>
                    <div className={`text-2xl font-mono font-bold ${s.totalReturn >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>
                      {s.totalReturn >= 0 ? '+' : ''}{s.totalReturn}%
                    </div>
                    <div className="text-[10px] text-white/30 mt-0.5">Sharpe: {s.sharpe}</div>
                  </div>
                ))}
              </div>

              {/* Detail tabs */}
              <div className={CARD_GLOW + " space-y-5"}>
                <div className="flex gap-2 flex-wrap">
                  {results.strategies?.map((s: any) => (
                    <button key={s.id} onClick={() => setDetailStrategy(s.id)}
                      className={`px-3 py-1.5 rounded-full text-[11px] font-mono border transition-all ${detailStrategy === s.id ? 'border-orange-500 bg-orange-500/20 text-white' : 'border-white/[0.08] text-white/40 hover:text-white'}`}>
                      {s.displayName}
                    </button>
                  ))}
                </div>

                {detailStrat && (
                  <>
                    <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                      <MetricChip label="Total Return" value={`${detailStrat.metrics?.totalReturn ?? '—'}%`} color={detailStrat.metrics?.totalReturn >= 0 ? 'text-emerald-400' : 'text-red-400'} />
                      <MetricChip label="Sharpe" value={detailStrat.metrics?.sharpeRatio} />
                      <MetricChip label="Max Drawdown" value={`${detailStrat.metrics?.maxDrawdown ?? '—'}%`} color="text-red-400" />
                      <MetricChip label="Win Rate" value={`${detailStrat.metrics?.winRate ?? '—'}%`} />
                      <MetricChip label="Profit Factor" value={detailStrat.metrics?.profitFactor} />
                      <MetricChip label="Total Trades" value={detailStrat.metrics?.totalTrades} />
                      <MetricChip label="Avg Win" value={`${detailStrat.metrics?.avgWin ?? '—'}%`} color="text-emerald-400" />
                      <MetricChip label="Avg Loss" value={`${detailStrat.metrics?.avgLoss ?? '—'}%`} color="text-red-400" />
                    </div>
                    <MonteCarloCanvas monteCarlo={detailStrat.monteCarlo} />
                  </>
                )}
              </div>
            </>
          ) : (
            <>
              {/* Single strategy equity curve */}
              <div className={CARD_GLOW}>
                <div className="text-[11px] font-mono text-white/30 uppercase tracking-widest mb-4">Equity Curve</div>
                <ResponsiveContainer width="100%" height={280}>
                  <ComposedChart data={results.equityCurve}>
                    <XAxis dataKey="date" stroke="#3f3f46" tick={{ fill: '#52525b', fontSize: 10 }} />
                    <YAxis stroke="#3f3f46" tick={{ fill: '#52525b', fontSize: 10 }} />
                    <Tooltip contentStyle={{ background: '#0a0a0a', border: '1px solid rgba(255,255,255,0.1)', borderRadius: 8, fontSize: 11 }} />
                    <Legend wrapperStyle={{ fontSize: 11 }} />
                    <Line type="monotone" dataKey="portfolio" stroke="#22c55e" strokeWidth={2} name="Portfolio" dot={false} />
                    <Line type="monotone" dataKey="benchmark" stroke="#52525b" strokeDasharray="5 5" name="Benchmark" dot={false} />
                  </ComposedChart>
                </ResponsiveContainer>
              </div>

              {/* Core Metrics */}
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                <MetricChip label="Total Return" value={`${results.metrics.totalReturn ?? '—'}%`} color={results.metrics.totalReturn >= 0 ? 'text-emerald-400' : 'text-red-400'} />
                <MetricChip label="Sharpe Ratio" value={results.metrics.sharpeRatio} />
                <MetricChip label="Sortino" value={results.metrics.sortinoRatio} />
                <MetricChip label="Max Drawdown" value={`${results.metrics.maxDrawdown ?? '—'}%`} color="text-red-400" />
                <MetricChip label="Win Rate" value={`${results.metrics.winRate ?? '—'}%`} />
                <MetricChip label="Total Trades" value={results.metrics.totalTrades} />
                <MetricChip label="Profit Factor" value={results.metrics.profitFactor} />
                <MetricChip label="Avg Win" value={`${results.metrics.avgWin ?? '—'}%`} color="text-emerald-400" />
              </div>

              {/* Trades Table */}
              {(results.trades || []).length > 0 && (
                <div className={CARD_GLOW + " overflow-x-auto"}>
                  <div className="text-[11px] font-mono text-white/30 uppercase tracking-widest mb-4">Trade Log ({results.trades.length} trades)</div>
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="border-b border-white/[0.06]">
                        {['Entry', 'Exit', 'Side', 'Entry Px', 'Exit Px', 'P&L', 'Duration'].map(h => (
                          <th key={h} className="pb-2 pr-4 text-left text-[10px] font-mono text-white/25 uppercase tracking-widest font-normal">{h}</th>
                        ))}
                      </tr>
                    </thead>
                    <tbody>
                      {results.trades.slice(0, 10).map((t: any, i: number) => (
                        <tr key={i} className="border-b border-white/[0.04] hover:bg-white/[0.02]">
                          <td className="py-2.5 pr-4 font-mono text-[12px] text-white/50">{t.entryDate}</td>
                          <td className="py-2.5 pr-4 font-mono text-[12px] text-white/50">{t.exitDate}</td>
                          <td className="py-2.5 pr-4 font-mono text-[12px] capitalize text-white/70">{t.side}</td>
                          <td className="py-2.5 pr-4 font-mono text-[12px] text-white">${t.entryPrice?.toFixed(2)}</td>
                          <td className="py-2.5 pr-4 font-mono text-[12px] text-white">${t.exitPrice?.toFixed(2)}</td>
                          <td className={`py-2.5 pr-4 font-mono text-[12px] ${t.pnl >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>
                            {t.pnlPct?.toFixed ? `${t.pnlPct.toFixed(2)}%` : '—'}
                          </td>
                          <td className="py-2.5 font-mono text-[12px] text-white/40">{t.duration}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}

              {/* Monte Carlo */}
              <div className={CARD_GLOW}>
                <div className="text-[11px] font-mono text-white/30 uppercase tracking-widest mb-4">
                  Monte Carlo Simulation ({results.monteCarlo?.simulations ?? 0} paths)
                </div>
                <MonteCarloCanvas monteCarlo={results.monteCarlo} />
              </div>
            </>
          )}
        </div>
      )}
    </div>
  )
}
