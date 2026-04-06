'use client'

import { useState, useRef, useCallback, useEffect } from 'react'
import ReactMarkdown from 'react-markdown'
import html2canvas from 'html2canvas'
import { animate, motion, useMotionValue, useSpring } from 'framer-motion'
import {
  Play, TrendingUp, Activity, Zap, Target, BarChart3,
  Layers, ArrowUpDown, Crosshair, GitBranch, Shield, DollarSign, X, Check
} from 'lucide-react'
import {
  LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer,
  Legend, ComposedChart, BarChart, Bar, CartesianGrid
} from 'recharts'
import {
  backtestAPI,
  API_BASE,
  extractErrorMessage,
  isLikelyNetworkError,
  type BacktestInterpretImageRequest,
  type BacktestInterpretRequest,
  type BacktestMultiStrategyDetail,
  type BacktestMultiStrategyResponse,
  type BacktestSingleResponse,
} from '@/lib/api'

// Unified card styles from dashboard/sectors/technical
const CARD = "shine-surface group relative p-6 rounded-2xl border border-white/10 bg-white/[0.03] backdrop-blur-xl hover:border-indigo-400/25 hover:bg-white/[0.05] transition-all duration-500 overflow-hidden"
const CARD_GLOW = "shine-surface group relative p-6 rounded-2xl border border-white/10 bg-white/[0.03] backdrop-blur-xl shadow-[0_0_24px_rgba(79,70,229,0.06)] hover:shadow-[0_0_32px_rgba(79,70,229,0.14)] hover:border-indigo-400/30 hover:bg-white/[0.05] transition-all duration-500 overflow-hidden"
const CONTROL_BTN = "shine-btn relative overflow-hidden px-4 py-2 rounded-lg text-[12px] font-dm-mono uppercase tracking-widest transition-all duration-300 border border-white/20"

function StrategyCard({
  strat,
  active,
  selectionOrder,
  onToggle,
}: {
  strat: { id: string; name: string; color: string; description: string }
  active: boolean
  selectionOrder: number | null
  onToggle: (id: string) => void
}) {
  const rotateX = useMotionValue(0)
  const rotateY = useMotionValue(0)
  const smoothX = useSpring(rotateX, { stiffness: 180, damping: 18 })
  const smoothY = useSpring(rotateY, { stiffness: 180, damping: 18 })

  return (
    <motion.button
      key={strat.id}
      onClick={() => onToggle(strat.id)}
      whileHover={{ scale: 1.03 }}
      whileTap={{ scale: 0.97 }}
      onMouseMove={(e) => {
        const rect = e.currentTarget.getBoundingClientRect()
        const x = e.clientX - rect.left
        const y = e.clientY - rect.top
        const cx = rect.width / 2
        const cy = rect.height / 2
        rotateX.set(((cy - y) / cy) * 4)
        rotateY.set(((x - cx) / cx) * 5)
      }}
      onMouseLeave={() => {
        rotateX.set(0)
        rotateY.set(0)
      }}
      style={{
        rotateX: smoothX,
        rotateY: smoothY,
        transformPerspective: 900,
        boxShadow: active
          ? `0 14px 44px -8px ${selectionOrder === 1 ? '#3b82f6' : strat.color}66, inset 0 1px 0 rgba(255,255,255,0.18)`
          : '0 0 0 rgba(0,0,0,0)',
      }}
      className={`${CARD} flex flex-col items-start gap-1.5 text-left border-2 transition-all duration-500 ${active ? 'bg-gradient-to-br from-indigo-900/30 to-slate-900/40 relative z-20' : 'border-transparent'}`}
    >
      <div 
        className="absolute inset-0 transition-opacity duration-500" 
        style={{ 
          borderColor: active ? (selectionOrder === 1 ? '#3b82f6' : strat.color) : 'transparent',
          borderWidth: '2px',
          opacity: active ? 0.65 : 0,
          borderRadius: '1rem',
          boxShadow: active ? `inset 0 0 15px ${selectionOrder === 1 ? '#3b82f6' : strat.color}25` : 'none'
        }} 
      />
      
      {active && (
        <motion.div 
          initial={{ scale: 0, opacity: 0 }}
          animate={{ scale: 1, opacity: 1 }}
          className="absolute top-2.5 right-2.5 z-20 flex items-center justify-center"
        >
          <div className={`flex items-center gap-1.5 backdrop-blur-md px-1.5 py-0.5 rounded-md border ${selectionOrder === 1 ? 'bg-blue-600/30 border-blue-400/40 shadow-[0_0_10px_rgba(37,99,235,0.2)]' : 'bg-white/10 border-white/20'}`}>
             <Check className={`w-3 h-3 ${selectionOrder === 1 ? 'text-blue-200' : 'text-white'}`} strokeWidth={3} />
             {selectionOrder && <span className={`text-[9px] font-dm-mono leading-none ${selectionOrder === 1 ? 'text-blue-100 font-bold' : 'text-white/90'}`}>{selectionOrder}</span>}
          </div>
        </motion.div>
      )}

      <div className="pointer-events-none absolute inset-0 rounded-2xl bg-[radial-gradient(circle_at_20%_10%,rgba(99,102,241,0.15),transparent_45%)] opacity-0 group-hover:opacity-100 transition-opacity" />
      <div className="flex items-center gap-2 mb-1.5 relative z-10">
        <div className="w-1.5 h-1.5 rounded-full" style={{ backgroundColor: strat.color }} />
        <div className={`text-[13px] font-dm-mono font-semibold transition-colors ${active ? 'text-white' : 'text-white/80'}`}>{strat.name}</div>
      </div>
      <div className={`text-[11px] leading-tight font-inter relative z-10 transition-colors ${active ? 'text-white/90 font-medium' : 'text-white/60'}`}>{strat.description}</div>
    </motion.button>
  )
}

function AnimatedMetricValue({ value }: { value: any }) {
  const [display, setDisplay] = useState('—')

  useEffect(() => {
    if (value === null || value === undefined || value === '—') {
      setDisplay('—')
      return
    }

    const raw = String(value)
    const match = raw.match(/-?\d+(?:\.\d+)?/)
    if (!match || match.index === undefined) {
      setDisplay(raw)
      return
    }

    const n = Number(match[0])
    if (!Number.isFinite(n)) {
      setDisplay(raw)
      return
    }

    const prefix = raw.slice(0, match.index)
    const suffix = raw.slice(match.index + match[0].length)
    const decimals = match[0].includes('.') ? 2 : 0

    const controls = animate(0, n, {
      duration: 1,
      ease: 'easeOut',
      onUpdate: (latest) => setDisplay(`${prefix}${latest.toFixed(decimals)}${suffix}`),
    })

    return () => controls.stop()
  }, [value])

  return <>{display}</>
}

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
function MonteCarloCanvas({ monteCarlo, market }: { monteCarlo: any; market: 'US' | 'IN' }) {
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const [hoverIndex, setHoverIndex] = useState<number | null>(null)
  const [hoverPos, setHoverPos] = useState<{ x: number; y: number } | null>(null)
  const currency = market === 'IN' ? '₹' : '$'

  const pp = monteCarlo?.percentilePaths || {}
  const p5 = pp.p5 as number[] | undefined
  const p25 = pp.p25 as number[] | undefined
  const p50 = pp.p50 as number[] | undefined
  const p75 = pp.p75 as number[] | undefined
  const p95 = pp.p95 as number[] | undefined
  const points = p50?.length || monteCarlo?.simulationPaths?.[0]?.length || 0

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
    const fmtD = (v: number) => Math.abs(v) >= 1e6 ? `${currency}${(v / 1e6).toFixed(1)}M` : Math.abs(v) >= 1e3 ? `${currency}${(v / 1e3).toFixed(0)}K` : `${currency}${v.toFixed(0)}`

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

    if (hoverIndex !== null && pp?.p50?.length) {
      const i = Math.max(0, Math.min(pp.p50.length - 1, hoverIndex))
      const x = xS(i)
      ctx.strokeStyle = 'rgba(255,255,255,0.35)'
      ctx.lineWidth = 1
      ctx.beginPath()
      ctx.moveTo(x, pad.top)
      ctx.lineTo(x, pad.top + plotH)
      ctx.stroke()

      const dots: [number[] | undefined, string][] = [
        [pp.p5, '#ef4444'],
        [pp.p25, '#f97316'],
        [pp.p50, '#22c55e'],
        [pp.p75, '#3b82f6'],
        [pp.p95, '#8b5cf6'],
      ]
      for (const [curve, color] of dots) {
        if (!curve || curve[i] === undefined) continue
        ctx.fillStyle = color
        ctx.beginPath()
        ctx.arc(x, yS(curve[i]), 3, 0, Math.PI * 2)
        ctx.fill()
      }
    }

    ctx.fillStyle = 'rgba(255,255,255,0.4)'; ctx.font = '10px monospace'; ctx.textAlign = 'right'
    for (let i = 0; i <= 5; i++) {
      const val = yMax - (i / 5) * (yMax - yMin)
      ctx.fillText(fmtD(val), pad.left - 4, pad.top + (i / 5) * plotH + 4)
    }
  }, [monteCarlo, hoverIndex])

  useEffect(() => {
    draw()
    window.addEventListener('resize', draw)
    return () => window.removeEventListener('resize', draw)
  }, [draw])

  if (!monteCarlo?.simulationPaths?.length) return <div className="text-[11px] font-mono text-white/25 py-4">Monte Carlo simulation unavailable.</div>

  const formatCurrency = (v?: number) => (typeof v === 'number' ? `${currency}${v.toLocaleString(undefined, { maximumFractionDigits: 0 })}` : '—')

  const hoverValues = hoverIndex !== null ? {
    p5: p5?.[hoverIndex],
    p25: p25?.[hoverIndex],
    p50: p50?.[hoverIndex],
    p75: p75?.[hoverIndex],
    p95: p95?.[hoverIndex],
  } : null

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      transition={{ duration: 0.5 }}
      className="space-y-2 relative"
    >
      <canvas
        ref={canvasRef}
        className="w-full rounded-xl cursor-crosshair"
        style={{ height: 260 }}
        onMouseMove={(e) => {
          const rect = e.currentTarget.getBoundingClientRect()
          const x = e.clientX - rect.left
          const y = e.clientY - rect.top
          const padLeft = 60
          const padRight = 16
          const usable = rect.width - padLeft - padRight
          if (usable <= 0 || points < 2) return
          const ratio = Math.max(0, Math.min(1, (x - padLeft) / usable))
          setHoverIndex(Math.round(ratio * (points - 1)))
          setHoverPos({ x, y })
        }}
        onMouseLeave={() => {
          setHoverIndex(null)
          setHoverPos(null)
        }}
      />

      {hoverValues && hoverPos && (
        <div
          className="absolute z-20 pointer-events-none rounded-lg border border-white/20 bg-black/85 px-3 py-2 text-[10px] font-mono shadow-2xl"
          style={{
            left: Math.min(hoverPos.x + 12, 620),
            top: Math.max(hoverPos.y - 90, 8),
          }}
        >
          <div className="text-white/60 mb-1">Step {hoverIndex! + 1}</div>
          <div className="text-[#ef4444]">P5: {formatCurrency(hoverValues.p5)}</div>
          <div className="text-[#f97316]">P25: {formatCurrency(hoverValues.p25)}</div>
          <div className="text-[#22c55e]">P50: {formatCurrency(hoverValues.p50)}</div>
          <div className="text-[#3b82f6]">P75: {formatCurrency(hoverValues.p75)}</div>
          <div className="text-[#8b5cf6]">P95: {formatCurrency(hoverValues.p95)}</div>
        </div>
      )}

      {hoverValues && (
        <div className="grid grid-cols-2 md:grid-cols-6 gap-2 text-[10px] font-mono rounded-lg border border-white/10 bg-white/[0.02] p-2">
          <span className="text-white/50">Step {hoverIndex! + 1}</span>
          <span className="text-[#ef4444]">P5: {formatCurrency(hoverValues.p5)}</span>
          <span className="text-[#f97316]">P25: {formatCurrency(hoverValues.p25)}</span>
          <span className="text-[#22c55e]">P50: {formatCurrency(hoverValues.p50)}</span>
          <span className="text-[#3b82f6]">P75: {formatCurrency(hoverValues.p75)}</span>
          <span className="text-[#8b5cf6]">P95: {formatCurrency(hoverValues.p95)}</span>
        </div>
      )}

      <div className="flex items-center gap-4 text-[10px] font-mono">
        {[['P5', '#ef4444'], ['P25', '#f97316'], ['P50 (Median)', '#22c55e'], ['P75', '#3b82f6'], ['P95', '#8b5cf6']].map(([l, c]) => (
          <span key={l} style={{ color: c }}>{l}</span>
        ))}
      </div>
      <div className="text-[10px] font-mono text-white/35 uppercase tracking-wider">
        Monte Carlo fan chart: P5 = worst-case tail, P50 = median path, P95 = strong upside tail. Hover chart to inspect exact values.
      </div>
    </motion.div>
  )
}

// ─── Metric Chip ──────────────────────────────────────────────────────────────
function MetricChip({ label, value, color = 'text-white' }: { label: string; value: any; color?: string }) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 24 }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true, amount: 0.5 }}
      transition={{ duration: 0.45 }}
      className="p-4 rounded-2xl border border-white/[0.06] bg-white/[0.03] backdrop-blur-xl shadow-[0_10px_30px_rgba(0,0,0,0.18)] flex flex-col gap-1"
    >
      <div className="text-[10px] font-dm-mono text-white/30 uppercase tracking-widest mb-0.5">{label}</div>
      <div className={`text-xl font-dm-mono font-bold tabular-nums ${color}`}><AnimatedMetricValue value={value} /></div>
    </motion.div>
  )
}

// ─── Main Page ─────────────────────────────────────────────────────────────────
export default function BacktestPage() {
  const resultsRef = useRef<HTMLDivElement>(null)
  const [market, setMarket] = useState('US')
  const [selectedStrategies, setSelectedStrategies] = useState(['ema_crossover'])
  const [symbol, setSymbol] = useState('AAPL')
  const [initialCapital, setInitialCapital] = useState(100000)
  const [rangePeriod, setRangePeriod] = useState('1y')
  const [candleInterval, setCandleInterval] = useState<'1d' | '1wk' | '1mo'>('1d')
  const [startDate, setStartDate] = useState('')
  const [endDate, setEndDate] = useState('')
  const [isRunning, setIsRunning] = useState(false)
  const [runError, setRunError] = useState<string | null>(null)
  const [results, setResults] = useState<any>(null)
  const [aiLoading, setAiLoading] = useState(false)
  const [aiVisionLoading, setAiVisionLoading] = useState(false)
  const [aiError, setAiError] = useState<string | null>(null)
  const [aiExplanation, setAiExplanation] = useState<string | null>(null)
  const [aiVisionError, setAiVisionError] = useState<string | null>(null)
  const [aiVisionExplanation, setAiVisionExplanation] = useState<string | null>(null)
  const [expandedModalContent, setExpandedModalContent] = useState<string | null>(null)
  const [modalTitle, setModalTitle] = useState<string>('')
  const [detailStrategy, setDetailStrategy] = useState('ema_crossover')
  const [typedAiExplanation, setTypedAiExplanation] = useState('')
  const [typedAiVisionExplanation, setTypedAiVisionExplanation] = useState('')
  const [quantReportLoading, setQuantReportLoading] = useState(false)
  const [quantReportError, setQuantReportError] = useState<string | null>(null)
  const [quantReportLink, setQuantReportLink] = useState<string | null>(null)
  const currencySymbol = market === 'IN' ? '₹' : '$'
  const intervalLabel = candleInterval === '1d' ? '1D' : candleInterval === '1wk' ? '1W' : '1M'
  const rangeLabel = rangePeriod.toUpperCase()

  const resolveDownloadUrl = (downloadUrl: string) => {
    if (/^https?:\/\//i.test(downloadUrl)) return downloadUrl
    if (downloadUrl.startsWith('/api/')) return downloadUrl
    if (downloadUrl.startsWith('/')) return `${API_BASE}${downloadUrl}`
    return `${API_BASE}/${downloadUrl}`
  }

  useEffect(() => {
    if (!aiExplanation) {
      setTypedAiExplanation('')
      return
    }
    let i = 0
    setTypedAiExplanation('')
    const timer = window.setInterval(() => {
      i += 4
      setTypedAiExplanation(aiExplanation.slice(0, i))
      if (i >= aiExplanation.length) window.clearInterval(timer)
    }, 14)
    return () => window.clearInterval(timer)
  }, [aiExplanation])

  useEffect(() => {
    if (!aiVisionExplanation) {
      setTypedAiVisionExplanation('')
      return
    }
    let i = 0
    setTypedAiVisionExplanation('')
    const timer = window.setInterval(() => {
      i += 4
      setTypedAiVisionExplanation(aiVisionExplanation.slice(0, i))
      if (i >= aiVisionExplanation.length) window.clearInterval(timer)
    }, 14)
    return () => window.clearInterval(timer)
  }, [aiVisionExplanation])

  const buildInterpretPayload = (): BacktestInterpretRequest | null => {
    if (!results) return null

    // Calculate equity curve statistics for analysis
    const calculateEquityStats = (curve: any[]) => {
      if (!curve || curve.length === 0) return {}
      const values = curve.map((c: any) => c.portfolio || c.value || 0)
      const returns = []
      for (let i = 1; i < values.length; i++) {
        returns.push(((values[i] - values[i-1]) / values[i-1]) * 100)
      }
      const maxDrawdown = values.reduce((maxDD, v, i) => {
        let dd = 0
        const peak = Math.max(...values.slice(0, i+1))
        if (peak > 0) dd = ((peak - v) / peak) * 100
        return Math.max(maxDD, dd)
      }, 0)
      return {
        initialCapital: values[0],
        finalCapital: values[values.length - 1],
        totalReturn: ((values[values.length - 1] - values[0]) / values[0]) * 100,
        maxDrawdownRealized: maxDrawdown.toFixed(2),
        avgDailyReturn: (returns.reduce((a, b) => a + b, 0) / returns.length).toFixed(3),
        volatility: (Math.sqrt(returns.reduce((sum, r) => sum + r*r, 0) / returns.length)).toFixed(2),
        equityCurveLength: values.length,
      }
    }

    // Analyze trade distribution
    const analyzeTrades = (trades: any[]) => {
      if (!trades || trades.length === 0) return {}
      const winners = trades.filter((t: any) => (t.pnl || 0) > 0).length
      const losers = trades.filter((t: any) => (t.pnl || 0) < 0).length
      const avgWinTrade = trades.filter((t: any) => (t.pnl || 0) > 0).reduce((sum, t: any) => sum + (t.pnl || 0), 0) / (winners || 1)
      const avgLoseTrade = trades.filter((t: any) => (t.pnl || 0) < 0).reduce((sum, t: any) => sum + Math.abs(t.pnl || 0), 0) / (losers || 1)
      return {
        totalTrades: trades.length,
        winners,
        losers,
        winRate: ((winners / trades.length) * 100).toFixed(1),
        avgWin: avgWinTrade.toFixed(2),
        avgLoss: avgLoseTrade.toFixed(2),
        expectancy: ((avgWinTrade * (winners/trades.length)) - (avgLoseTrade * (losers/trades.length))).toFixed(2),
      }
    }

    if (results.isMulti) {
      const compactStrategies = (results.strategies || []).map((s: any) => ({
        id: s.id,
        name: s.displayName,
        metrics: s.metrics || {},
        mcRisk: s.monteCarlo?.riskMetrics || {},
        mcPct: s.monteCarlo?.percentiles || {},
        equityStats: calculateEquityStats(s.equityCurve),
        tradeAnalysis: analyzeTrades(s.trades),
      }))
      return {
        symbol,
        market: market as 'US' | 'IN',
        selectedStrategies,
        summary: {
          mode: 'multi_strategy',
          interval: candleInterval,
          range: rangePeriod,
          ranking: results.ranking || [],
          strategies: compactStrategies,
          note: 'Combined chart contains multiple strategy equity paths.',
        },
      }
    }

    const equityStats = calculateEquityStats(results.equityCurve)
    const tradeAnalysis = analyzeTrades(results.trades)

    return {
      symbol,
      market: market as 'US' | 'IN',
      selectedStrategies,
      summary: {
        mode: 'single_strategy',
        interval: candleInterval,
        range: rangePeriod,
        metrics: results.metrics || {},
        equityStats,
        tradeAnalysis,
        monteCarlo: {
          riskMetrics: results.monteCarlo?.riskMetrics || {},
          percentiles: results.monteCarlo?.percentiles || {},
          simulations: results.monteCarlo?.simulations || 0,
        },
        latestEquity: results.equityCurve?.[results.equityCurve.length - 1] || null,
        equityCurveLength: results.equityCurve?.length || 0,
      },
    }
  }

  const captureResultsImage = async (): Promise<string> => {
    if (!resultsRef.current) throw new Error('No results panel found to capture')
    const canvas = await html2canvas(resultsRef.current, {
      backgroundColor: '#05070c',
      useCORS: true,
      scale: 1.2,
      logging: false,
    })
    return canvas.toDataURL('image/jpeg', 0.78)
  }

  const handleCombinedAnalysis = async () => {
    if (!results || aiLoading || aiVisionLoading) return
    
    // Set both to loading
    setAiLoading(true)
    setAiVisionLoading(true)
    setAiError(null)
    setAiVisionError(null)
    
    try {
      // Run data-driven analysis
      const payload = buildInterpretPayload()
      if (payload) {
        try {
          const res = await backtestAPI.interpret(payload)
          setAiExplanation(res.analysis)
        } catch (err) {
          setAiError(extractErrorMessage(err, 'AI explanation failed'))
        } finally {
          setAiLoading(false)
        }
      } else {
        setAiLoading(false)
      }
      
      // Run vision analysis
      try {
        const imageDataUrl = await captureResultsImage()
        const payload: BacktestInterpretImageRequest = {
          symbol,
          market: market as 'US' | 'IN',
          selectedStrategies,
          imageDataUrl,
          context: {
            interval: candleInterval,
            range: rangePeriod,
            mode: results?.isMulti ? 'multi_strategy' : 'single_strategy',
          },
        }
        const res = await backtestAPI.interpretImage(payload)
        setAiVisionExplanation(res.analysis)
      } catch (err) {
        setAiVisionError(extractErrorMessage(err, 'AI screenshot interpretation failed'))
      } finally {
        setAiVisionLoading(false)
      }
    } catch (err) {
      const reason = extractErrorMessage(err, 'Combined analysis failed')
      setAiError(reason)
      setAiVisionError(reason)
      setAiLoading(false)
      setAiVisionLoading(false)
    }
  }

  const toggleStrategy = (id: string) => {
    setSelectedStrategies(prev => {
      if (prev.includes(id)) return prev.length === 1 ? prev : prev.filter(s => s !== id)
      if (prev.length >= 4) return [...prev.slice(1), id]
      return [...prev, id]
    })
  }

  const handleRun = async () => {
    if (isRunning) return
    setIsRunning(true)
    setRunError(null)
    setAiError(null)
    setAiVisionError(null)
    setAiExplanation(null)
    setAiVisionExplanation(null)
    setQuantReportError(null)
    setQuantReportLink(null)
    const timeoutId = window.setTimeout(() => {
      setIsRunning(false)
      setRunError('Request timed out. Check backend server and try again.')
    }, 45000)
    try {
      const params: any = {}
      selectedStrategies.forEach(id => {
        const strat = STRATEGIES.find(s => s.id === id)
        if (strat?.params) params[id] = strat.params
      })
      const normalized = symbol.trim().toUpperCase()
      const inferredMarket = normalized.endsWith('.NS') || normalized.endsWith('.BO') ? 'india' : 'us'
      const data = await backtestAPI.run({
        symbol: normalized,
        market: market === 'IN' ? 'india' : inferredMarket,
        strategies: selectedStrategies,
        range: rangePeriod,
        interval: candleInterval,
        params,
        start: startDate || undefined,
        end: endDate || undefined,
      })

      if (data.mode === 'multi_strategy') {
        const multiData = data as BacktestMultiStrategyResponse
        const stratResults = multiData.strategies || {}
        
        // Preserve selection order and apply blue theme to selection 1
        const strategies = selectedStrategies.map((id, index) => {
          const d = stratResults[id] as BacktestMultiStrategyDetail
          const def = STRATEGIES.find(s => s.id === id)
          const isFirst = index === 0
          
          return {
            id,
            displayName: def?.name || id,
            // Override first strategy to be blue-themed per user request
            color: isFirst ? '#3b82f6' : (d?.color || def?.color || '#f59e0b'),
            metrics: d?.metrics,
            trades: d?.trades || [],
            monteCarlo: d?.monteCarlo,
            equityCurve: d?.equityCurve || [],
          }
        })

        const ranking = (multiData.ranking || []).map((r) => {
          const def = STRATEGIES.find(s => s.id === r.strategy)
          return { name: def?.name || r.strategy, totalReturn: r.return, sharpe: stratResults[r.strategy]?.metrics?.sharpeRatio ?? '—' }
        })
        setResults({ isMulti: true, strategies, combinedChartData: multiData.combinedChartData || [], ranking })
        const firstWithMonteCarlo = strategies.find((s: any) => s?.monteCarlo?.simulationPaths?.length)
        setDetailStrategy(firstWithMonteCarlo?.id ?? strategies[0]?.id ?? selectedStrategies[0])
      } else {
        const singleData = data as BacktestSingleResponse
        const equityCurve = (singleData.equity_curve || []).map((p: any, i: number) => ({
          ...p, date: p.date || `Day ${i + 1}`, portfolio: p.value || initialCapital, benchmark: p.benchmark || initialCapital,
        }))
        setResults({
          isMulti: false,
          equityCurve,
          metrics: singleData.metrics || {},
          trades: singleData.trades || [],
          monteCarlo: singleData.monteCarlo || null,
          color: '#3b82f6' // Single strategy also defaults to blue theme
        })
        setDetailStrategy(selectedStrategies[0])
      }
    } catch (err) {
      console.error('Backtest error:', err)
      const message = extractErrorMessage(err, 'Backtest failed')
      setRunError(isLikelyNetworkError(err) ? 'Backend is unreachable. Start FastAPI on port 8001 and try again.' : message)
      setResults(null)
    } finally {
      window.clearTimeout(timeoutId)
      setIsRunning(false)
    }
  }

  const handleQuantstatsReport = async () => {
    if (!results || quantReportLoading) return

    setQuantReportLoading(true)
    setQuantReportError(null)

    try {
      const strategy = results?.isMulti ? detailStrategy : selectedStrategies[0]
      if (!strategy) throw new Error('No strategy selected')

      const strategyConfig = STRATEGIES.find((s) => s.id === strategy)
      const normalized = symbol.trim().toUpperCase()
      const normalizedSymbol = market === 'IN' && !normalized.endsWith('.NS') && !normalized.endsWith('.BO')
        ? `${normalized}.NS`
        : normalized

      const res = await backtestAPI.quantstatsReport({
        symbol: normalizedSymbol,
        strategy,
        range: rangePeriod,
        params: strategyConfig?.params || {},
        benchmark: market === 'IN' ? '^NSEI' : 'SPY',
      })

      const downloadUrl = typeof res?.downloadUrl === 'string' ? String(res.downloadUrl) : ''
      const filename = typeof res?.filename === 'string'
        ? String(res.filename)
        : (downloadUrl ? downloadUrl.split('/').pop() || '' : '')

      if (!downloadUrl && !filename) throw new Error('QuantStats report URL missing')

      const fullUrl = filename
        ? backtestAPI.downloadReport(filename)
        : resolveDownloadUrl(downloadUrl)
      setQuantReportLink(fullUrl)
      window.open(fullUrl, '_blank', 'noopener,noreferrer')
    } catch (err) {
      const message = extractErrorMessage(err, 'QuantStats report generation failed')
      if (isLikelyNetworkError(err)) {
        setQuantReportError('Backend is unreachable. Start FastAPI on port 8001 and try again.')
      } else {
        setQuantReportError(message)
      }
    } finally {
      setQuantReportLoading(false)
    }
  }

  const detailStrat = results?.isMulti ? results.strategies?.find((s: any) => s.id === detailStrategy) : null

  return (
    <motion.div
      initial={{ opacity: 0, y: 18 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.55 }}
      className="relative space-y-8 max-w-7xl mx-auto py-8"
    >
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
      <motion.div
        initial={{ opacity: 0, y: 28 }}
        whileInView={{ opacity: 1, y: 0 }}
        viewport={{ once: true, amount: 0.25 }}
        transition={{ duration: 0.5 }}
      >
        <div className="text-[11px] font-dm-mono text-white/60 uppercase tracking-widest mb-3">Select Strategies (Max 4 · 5th click replaces oldest)</div>
        <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
          {STRATEGIES.map(strat => {
            const index = selectedStrategies.indexOf(strat.id)
            const active = index !== -1
            return (
              <StrategyCard 
                key={strat.id} 
                strat={strat} 
                active={active} 
                selectionOrder={active ? index + 1 : null}
                onToggle={toggleStrategy} 
              />
            )
          })}
        </div>
      </motion.div>

      {/* Config Row */}
      <motion.div
        initial={{ opacity: 0, y: 22 }}
        whileInView={{ opacity: 1, y: 0 }}
        viewport={{ once: true, amount: 0.2 }}
        transition={{ duration: 0.5, delay: 0.06 }}
        className="flex flex-wrap gap-4 items-end"
      >
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
        <div className="flex-1 min-w-[140px]">
          <label className="block text-[10px] font-dm-mono text-white/30 uppercase tracking-widest mb-2">Data Interval</label>
          <select
            value={candleInterval}
            onChange={e => setCandleInterval(e.target.value as '1d' | '1wk' | '1mo')}
            className="backtest-select w-full px-3 py-2.5 bg-white/[0.03] border border-white/[0.08] rounded-xl text-white font-dm-mono text-[13px] focus:outline-none focus:border-indigo-500/30 transition-colors"
            style={{ colorScheme: 'dark' }}
          >
            <option value="1d">1 Day</option>
            <option value="1wk">1 Week</option>
            <option value="1mo">1 Month</option>
          </select>
        </div>
        <motion.button
          type="button"
          onClick={handleRun}
          disabled={isRunning}
          whileHover={{ scale: 1.05 }}
          whileTap={{ scale: 0.95 }}
          animate={!isRunning ? { boxShadow: ['0 0 18px rgba(37,99,235,0.30)', '0 0 34px rgba(37,99,235,0.45)', '0 0 18px rgba(37,99,235,0.30)'] } : { boxShadow: '0 0 0 rgba(0,0,0,0)' }}
          transition={{ repeat: !isRunning ? Infinity : 0, duration: 2.2, ease: 'easeInOut' }}
          className="shine-btn relative z-10 overflow-hidden pointer-events-auto flex items-center gap-2 px-8 py-3 rounded-2xl text-[14px] font-dm-mono font-bold tracking-widest text-white bg-gradient-to-r from-blue-900 to-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {isRunning ? 'RUNNING_SIMULATION...' : 'RUN_BACKTEST'}
        </motion.button>
      </motion.div>

      {/* Results */}
      {runError && (
        <div className="p-3 rounded-xl border border-red-500/40 bg-red-500/10 text-red-300 text-[12px] font-dm-mono uppercase tracking-wider">
          {runError}
        </div>
      )}

      {results && (
        <div className="space-y-5" ref={resultsRef}>
          <div className="flex items-center gap-3 flex-wrap">
            <motion.button
              onClick={handleCombinedAnalysis}
              disabled={aiLoading || aiVisionLoading}
              whileHover={{ scale: 1.04 }}
              whileTap={{ scale: 0.95 }}
              className="shine-btn relative overflow-hidden px-6 py-2.5 rounded-xl text-[12px] font-dm-mono uppercase tracking-widest text-white bg-gradient-to-r from-blue-900 to-blue-700 shadow-[0_0_30px_rgba(37,99,235,0.30)] disabled:opacity-50"
            >
              {aiLoading || aiVisionLoading ? 'ANALYZING_THIS_PAGE...' : 'ANALYZE_THIS_PAGE'}
            </motion.button>
            <motion.button
              onClick={handleQuantstatsReport}
              disabled={quantReportLoading}
              whileHover={{ scale: 1.04 }}
              whileTap={{ scale: 0.95 }}
              className="shine-btn relative overflow-hidden px-6 py-2.5 rounded-xl text-[12px] font-dm-mono uppercase tracking-widest text-white bg-gradient-to-r from-indigo-900 to-indigo-700 shadow-[0_0_30px_rgba(79,70,229,0.30)] disabled:opacity-50"
            >
              {quantReportLoading ? 'GENERATING_QUANTSTATS...' : 'GENERATE_QUANTSTATS_REPORT'}
            </motion.button>
            <span className="text-[10px] font-dm-mono text-white/35 uppercase tracking-wider">Groq-powered chart + data analysis</span>
            <div className="flex items-center gap-2 px-3 py-1 rounded-full border border-emerald-400/20 bg-emerald-400/10">
              <span className="w-2 h-2 bg-emerald-400 rounded-full animate-pulse" />
              <span className="text-[10px] font-dm-mono text-emerald-300 uppercase tracking-wider">Live Analysis</span>
            </div>
            {quantReportLink && (
              <a
                href={quantReportLink}
                target="_blank"
                rel="noreferrer"
                className="text-[10px] font-dm-mono uppercase tracking-wider text-indigo-300 hover:text-indigo-200"
              >
                OPEN_QUANTSTATS_REPORT
              </a>
            )}
          </div>

          {quantReportError && (
            <div className="p-3 rounded-xl border border-red-500/40 bg-red-500/10 text-red-300 text-[12px] font-dm-mono">
              {quantReportError}
            </div>
          )}

          {aiError && (
            <div className="p-3 rounded-xl border border-red-500/40 bg-red-500/10 text-red-300 text-[12px] font-dm-mono">
              {aiError}
            </div>
          )}

          {aiExplanation && (
            <motion.div
              initial={{ opacity: 0, y: 24 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.45 }}
              className="p-4 rounded-xl border border-emerald-500/20 bg-emerald-500/5 backdrop-blur-xl text-[13px] text-white/85 leading-relaxed shadow-[0_0_40px_rgba(16,185,129,0.08)]"
            >
              <div className="flex items-center justify-between mb-2">
                <div className="text-[11px] font-dm-mono text-emerald-300 uppercase tracking-widest">AI Backtest Interpretation</div>
                <button
                  onClick={() => {
                    setExpandedModalContent(aiExplanation)
                    setModalTitle('AI Analysis - Full View')
                  }}
                  className="px-3 py-1 text-[10px] font-dm-mono uppercase tracking-widest rounded-lg border border-emerald-500/30 text-emerald-300 hover:bg-emerald-500/10 transition-all"
                >
                  Expand → Full
                </button>
              </div>
              <div className="prose prose-invert prose-sm max-w-none prose-p:text-white/80 line-clamp-6">
                <ReactMarkdown>{typedAiExplanation || aiExplanation}</ReactMarkdown>
              </div>
            </motion.div>
          )}

          {aiVisionError && (
            <div className="p-3 rounded-xl border border-red-500/40 bg-red-500/10 text-red-300 text-[12px] font-dm-mono">
              {aiVisionError}
            </div>
          )}

          {aiVisionExplanation && (
            <motion.div
              initial={{ opacity: 0, y: 24 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.45, delay: 0.05 }}
              className="p-4 rounded-xl border border-cyan-500/20 bg-cyan-500/5 backdrop-blur-xl text-[13px] text-white/85 leading-relaxed shadow-[0_0_40px_rgba(34,211,238,0.08)]"
            >
              <div className="flex items-center justify-between mb-2">
                <div className="text-[11px] font-dm-mono text-cyan-300 uppercase tracking-widest">AI Screenshot Interpretation</div>
                <button
                  onClick={() => {
                    setExpandedModalContent(aiVisionExplanation)
                    setModalTitle('AI Screenshot Analysis - Full View')
                  }}
                  className="px-3 py-1 text-[10px] font-dm-mono uppercase tracking-widest rounded-lg border border-cyan-500/30 text-cyan-300 hover:bg-cyan-500/10 transition-all"
                >
                  Expand → Full
                </button>
              </div>
              <div className="prose prose-invert prose-sm max-w-none prose-p:text-white/80 line-clamp-6">
                <ReactMarkdown>{typedAiVisionExplanation || aiVisionExplanation}</ReactMarkdown>
              </div>
            </motion.div>
          )}

          {results.isMulti ? (
            <>
              {/* Multi-strategy comparison */}
              <motion.div
                initial={{ opacity: 0, y: 38 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true, amount: 0.2 }}
                transition={{ duration: 0.6 }}
                className={CARD_GLOW + ' shadow-[inset_0_0_100px_rgba(16,185,129,0.06)]'}
              >
                <div className="text-[11px] font-mono text-white/30 uppercase tracking-widest mb-4">Strategy Comparison · Based on {intervalLabel} candles · Range {rangeLabel}</div>
                <ResponsiveContainer width="100%" height={280}>
                  <LineChart data={results.combinedChartData}>
                    <XAxis dataKey="date" stroke="#3f3f46" tick={{ fill: '#52525b', fontSize: 10, fontFamily: 'monospace' }} />
                    <YAxis stroke="#3f3f46" tick={{ fill: '#52525b', fontSize: 10, fontFamily: 'monospace' }} />
                    <Tooltip contentStyle={{ background: '#0a0a0a', border: '1px solid rgba(255,255,255,0.1)', borderRadius: 8, fontSize: 11, fontFamily: 'monospace' }} />
                    <Legend wrapperStyle={{ fontSize: 11, fontFamily: 'monospace' }} />
                    {results.strategies?.map((s: any) => <Line key={s.id} type="monotone" dataKey={s.id} stroke={s.color || '#f59e0b'} strokeWidth={2} dot={false} name={s.displayName} />)}
                  </LineChart>
                </ResponsiveContainer>
              </motion.div>

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
              <motion.div
                initial={{ opacity: 0, y: 28 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true, amount: 0.25 }}
                transition={{ duration: 0.5 }}
                className={CARD_GLOW + ' space-y-5'}
              >
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
                    <MonteCarloCanvas monteCarlo={detailStrat.monteCarlo} market={market as 'US' | 'IN'} />
                  </>
                )}
              </motion.div>
            </>
          ) : (
            <>
              {/* Single strategy equity curve */}
              <motion.div
                initial={{ opacity: 0, y: 38 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true, amount: 0.2 }}
                transition={{ duration: 0.6 }}
                className={CARD_GLOW + ' shadow-[inset_0_0_100px_rgba(16,185,129,0.06)]'}
              >
                <div className="text-[11px] font-mono text-white/30 uppercase tracking-widest mb-4">Equity Curve · Based on {intervalLabel} candles · Range {rangeLabel}</div>
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
              </motion.div>

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
                <motion.div
                  initial={{ opacity: 0, y: 24 }}
                  whileInView={{ opacity: 1, y: 0 }}
                  viewport={{ once: true, amount: 0.25 }}
                  transition={{ duration: 0.5 }}
                  className={CARD_GLOW + ' overflow-x-auto'}
                >
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
                          <td className="py-2.5 pr-4 font-mono text-[12px] text-white">{currencySymbol}{t.entryPrice?.toFixed(2)}</td>
                          <td className="py-2.5 pr-4 font-mono text-[12px] text-white">{currencySymbol}{t.exitPrice?.toFixed(2)}</td>
                          <td className={`py-2.5 pr-4 font-mono text-[12px] ${t.pnl >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>
                            {t.pnlPct?.toFixed ? `${t.pnlPct.toFixed(2)}%` : '—'}
                          </td>
                          <td className="py-2.5 font-mono text-[12px] text-white/40">{t.duration}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </motion.div>
              )}

              {/* Monte Carlo */}
              <motion.div
                initial={{ opacity: 0, y: 24 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true, amount: 0.25 }}
                transition={{ duration: 0.5 }}
                className={CARD_GLOW}
              >
                <div className="text-[11px] font-mono text-white/30 uppercase tracking-widest mb-4">
                  Monte Carlo Simulation ({results.monteCarlo?.simulations ?? 0} paths) · Based on {intervalLabel} candles · Range {rangeLabel}
                </div>
                <MonteCarloCanvas monteCarlo={results.monteCarlo} market={market as 'US' | 'IN'} />
              </motion.div>
            </>
          )}
        </div>
      )}

      <style jsx global>{`
        .shine-btn,
        .shine-surface {
          isolation: isolate;
        }

        .shine-btn::after {
          content: '';
          position: absolute;
          top: -120%;
          left: -20%;
          width: 34%;
          height: 340%;
          background: linear-gradient(120deg, transparent 0%, rgba(255,255,255,0.58) 48%, transparent 100%);
          transform: translateX(-260%) rotate(18deg);
          animation: none;
          pointer-events: none;
          z-index: 2;
          opacity: 0;
          transition: opacity 0.25s ease;
          mix-blend-mode: screen;
        }

        .shine-btn:hover::after {
          animation: sheenSweep 0.9s ease-out 1;
          opacity: 0.62;
        }

        .shine-surface::before {
          content: '';
          position: absolute;
          inset: 0;
          border-radius: inherit;
          background: linear-gradient(165deg, rgba(255,255,255,0.14) 0%, rgba(255,255,255,0.02) 35%, rgba(99,102,241,0.07) 100%);
          opacity: 0.7;
          pointer-events: none;
          z-index: 0;
        }

        .shine-surface::after {
          content: '';
          position: absolute;
          top: -160%;
          left: -14%;
          width: 28%;
          height: 390%;
          background: linear-gradient(120deg, transparent 0%, rgba(255,255,255,0.24) 50%, transparent 100%);
          transform: translateX(-250%) rotate(14deg);
          animation: none;
          pointer-events: none;
          z-index: 1;
          opacity: 0;
          transition: opacity 0.25s ease;
        }

        .shine-surface:hover::after {
          animation: sheenSweep 1.1s ease-out 1;
          opacity: 0.45;
        }

        @keyframes sheenSweep {
          0% { transform: translateX(-260%) rotate(16deg); }
          100% { transform: translateX(430%) rotate(16deg); }
        }

        .backtest-select,
        .backtest-select:focus,
        .backtest-select:active {
          background-color: #05070c;
          color: #ffffff;
        }

        .backtest-select option {
          background-color: #05070c;
          color: #ffffff;
        }

        .prose {
          text-wrap: pretty;
        }
      `}</style>

      {/* Full Screen Modal for Expanded Analysis */}
      {expandedModalContent && (
        <div 
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm p-4"
          onClick={() => setExpandedModalContent(null)}
        >
          <div 
            className="relative w-full max-w-4xl max-h-[90vh] bg-gray-900/95 border border-white/20 rounded-2xl p-8 overflow-y-auto"
            onClick={(e) => e.stopPropagation()}
          >
            {/* Close Button */}
            <button
              onClick={() => setExpandedModalContent(null)}
              className="absolute top-6 right-6 w-8 h-8 flex items-center justify-center rounded-lg border border-white/20 text-white/60 hover:text-white hover:bg-white/10 transition-all"
              aria-label="Close modal"
            >
              <X size={20} />
            </button>

            {/* Title */}
            <h2 className="text-2xl font-dm-mono font-bold text-white mb-6 pr-12">{modalTitle}</h2>

            {/* Content */}
            <div className="prose prose-invert max-w-none">
              <ReactMarkdown>{expandedModalContent}</ReactMarkdown>
            </div>
          </div>
        </div>
      )}
    </motion.div>
  )
}
