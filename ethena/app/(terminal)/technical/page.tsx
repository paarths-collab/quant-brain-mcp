'use client'

import { useState, useEffect } from 'react'
import { Search, Activity, RefreshCw, AlertTriangle, BarChart2, TrendingUp, TrendingDown, Clock, Settings, Zap } from 'lucide-react'
import {
  ComposedChart, LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer,
  CartesianGrid, Area, AreaChart
} from 'recharts'

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000'

// ─── Strategies (fetched from backend or fallback) ───────────────────────────
const FALLBACK_STRATEGIES = [
  { id: 'ema_crossover', name: 'EMA Crossover', parameters: { fast: 12, slow: 26 } },
  { id: 'rsi_reversal', name: 'RSI Reversal', parameters: { window: 14, lower: 30, upper: 70 } },
  { id: 'macd', name: 'MACD', parameters: { fast: 12, slow: 26, signal: 9 } },
  { id: 'mean_reversion', name: 'Mean Reversion', parameters: { window: 20, num_std: 2 } },
  { id: 'breakout', name: 'Breakout', parameters: { lookback: 20 } },
]

// ─── Custom Tooltip ─────────────────────────────────────────────────────────
function ChartTooltip({ active, payload, label }: any) {
  if (!active || !payload?.length) return null
  return (
    <div className="bg-[#0a0a0a] border border-white/10 rounded-xl px-3 py-2 text-[11px] font-mono shadow-xl">
      <div className="text-white/40 mb-1">{label}</div>
      {payload.map((p: any) => (
        <div key={p.dataKey} style={{ color: p.color }}>{p.name || p.dataKey}: {p.value?.toFixed(2)}</div>
      ))}
    </div>
  )
}

// ─── Main Page ────────────────────────────────────────────────────────────────
export default function TechnicalPage() {
  const [symbol, setSymbol] = useState('AAPL')
  const [market, setMarket] = useState<'US' | 'IN'>('US')
  const [searchInput, setSearchInput] = useState('')
  const [activeStrategy, setActiveStrategy] = useState('')
  const [strategies, setStrategies] = useState(FALLBACK_STRATEGIES)
  const [strategyParams, setStrategyParams] = useState<Record<string, any>>({})
  const [timeRange, setTimeRange] = useState('1Y')
  const [chartType, setChartType] = useState<'candle' | 'area' | 'line'>('area')
  const [candleData, setCandleData] = useState<any[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [meta, setMeta] = useState<any>(null)

  // Fetch strategies from backend
  useEffect(() => {
    fetch(`${API_BASE}/api/technical/strategies`)
      .then(r => r.json())
      .then(d => { if (d.strategies) setStrategies(d.strategies) })
      .catch(() => {/* use fallback */})
  }, [])

  // Switch default symbol on market change
  useEffect(() => {
    setSymbol(market === 'US' ? 'AAPL' : 'RELIANCE')
  }, [market])

  // Fetch candle data + strategy analysis
  useEffect(() => {
    if (!symbol) return
    const rangeMap: Record<string, { range: string; interval: string }> = {
      '1M': { range: '1mo', interval: '1d' },
      '3M': { range: '3mo', interval: '1d' },
      '6M': { range: '6mo', interval: '1d' },
      '1Y': { range: '1y', interval: '1d' },
      '2Y': { range: '2y', interval: '1d' },
      '5Y': { range: '5y', interval: '1d' },
    }
    const { range, interval } = rangeMap[timeRange] ?? { range: '1y', interval: '1d' }

    const controller = new AbortController()
    const timer = setTimeout(async () => {
      setLoading(true)
      setError(null)
      try {
        const candleRes = await fetch(`${API_BASE}/api/market/candles?symbol=${symbol}&interval=${interval}&range=${range}&market=${market}`, { signal: controller.signal })
        const candleJson = await candleRes.json()
        if (!candleJson?.data?.length) throw new Error(`No data for ${symbol} in ${market} market`)

        const cData = candleJson.data.map((d: any) => ({
          time: (d.date || d.timestamp || '').split('T')[0],
          open: d.open, high: d.high, low: d.low, close: d.close, volume: d.volume,
        }))
        setCandleData(cData)

        if (activeStrategy) {
          const stratRes = await fetch(`${API_BASE}/api/technical/analyze`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ symbol, strategy: activeStrategy, params: JSON.stringify(strategyParams), period: timeRange, interval, market }),
            signal: controller.signal,
          })
          const stratJson = await stratRes.json()
          setMeta(stratJson.meta)
        } else {
          setMeta(null)
        }
      } catch (err: any) {
        if (err.name !== 'AbortError') setError(err.message || 'Failed to load data')
      } finally {
        setLoading(false)
      }
    }, 500)

    return () => { controller.abort(); clearTimeout(timer) }
  }, [symbol, market, timeRange, activeStrategy, strategyParams])

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault()
    if (searchInput.trim()) { setSymbol(searchInput.toUpperCase().trim()); setSearchInput('') }
  }

  const handleStrategyChange = (id: string) => {
    setActiveStrategy(id)
    const s = strategies.find(x => x.id === id)
    setStrategyParams(s?.parameters ?? {})
  }

  function TimeDisplay() {
    const [time, setTime] = useState<string | null>(null)
    useEffect(() => {
      const fmt = () => {
        const now = new Date()
        return [now.getHours(), now.getMinutes(), now.getSeconds()]
          .map(n => String(n).padStart(2, '0')).join(':')
      }
      setTime(fmt())
      const id = setInterval(() => setTime(fmt()), 1000)
      return () => clearInterval(id)
    }, [])
    if (!time) return null
    return <span className="text-indigo-400 font-dm-mono tabular-nums">{time}</span>
  }



  // Latest candle for display
  const latest = candleData[candleData.length - 1]
  const prev = candleData[candleData.length - 2]
  const priceChange = latest && prev ? ((latest.close - prev.close) / prev.close) * 100 : null

  // Chart colors
  const upColor = '#22c55e'; const downColor = '#ef4444'

  return (
    <div className="flex flex-col gap-4 relative font-inter w-full h-[calc(100vh-102px)] overflow-hidden">
      {/* ── Nebula Glow ── */}
      <div className="pointer-events-none fixed inset-0 overflow-hidden z-0">
        <div className="absolute top-[-10%] left-[-5%] w-[500px] h-[500px] rounded-full bg-indigo-700/8 blur-[150px]" />
        <div className="absolute bottom-[10%] right-[-5%] w-[400px] h-[400px] rounded-full bg-blue-800/6 blur-[130px]" />
      </div>

      {/* Header + Controls */}
      <div className="flex items-center gap-8 relative z-10 w-full shrink-0 h-[48px]">
        <div className="flex items-center gap-3">
          <span className="inline-flex items-center gap-2 px-3 py-1.5 text-[11px] border border-indigo-500/15 rounded-full text-indigo-400/80 bg-indigo-500/5">
            <span className="w-1.5 h-1.5 rounded-full bg-indigo-400 animate-pulse" />
            LIVE
          </span>
          <div className="w-px h-4 bg-white/10" />
          <p className="font-dm-mono text-[14px] text-white/30 tracking-widest uppercase">
            <TimeDisplay />
          </p>
        </div>

        <div className="flex items-center gap-3">
          {/* Market Toggle */}
          <div className="flex items-center border border-white/[0.08] bg-white/[0.03] rounded-lg overflow-hidden font-dm-mono text-[12px] tracking-widest backdrop-blur-xl hover:border-white/[0.13] transition-all duration-300">
            <button
              onClick={() => setMarket('US')}
              className={`px-4 py-2 transition-all ${market === 'US' ? 'bg-indigo-500/15 text-white' : 'text-white/20 hover:text-white/50 hover:bg-white/5'}`}
            >
              $ US
            </button>
            <div className="w-px h-4 bg-white/[0.08]" />
            <button
              onClick={() => setMarket('IN')}
              className={`px-4 py-2 transition-all ${market === 'IN' ? 'bg-indigo-500/15 text-white' : 'text-white/20 hover:text-white/50 hover:bg-white/5'}`}
            >
              ₹ INDIA
            </button>
          </div>

          {/* Search form */}
          <form onSubmit={handleSearch} className="flex items-center border border-white/[0.08] bg-white/[0.03] backdrop-blur-xl rounded-lg overflow-hidden h-[36px] focus-within:border-white/[0.2] transition-all duration-300 group">
            <input value={searchInput} onChange={e => setSearchInput(e.target.value)}
              placeholder="SYMBOL"
              className="bg-transparent border-none outline-none text-white w-28 px-4 placeholder:text-white/20 font-dm-mono text-[12px] tracking-widest uppercase" />
            <button type="submit" className="pr-4"><Search size={14} className="text-white/20 group-hover:text-white/50 transition-colors" /></button>
          </form>

          {/* Time Range Toggle */}
          <div className="flex items-center border border-white/[0.08] bg-white/[0.03] rounded-lg overflow-hidden font-dm-mono text-[11px] tracking-widest backdrop-blur-xl hover:border-white/[0.13] transition-all duration-300">
            {['1M', '3M', '6M', '1Y', '2Y', '5Y'].map((r, i) => (
              <div key={r} className="flex items-center">
                {i > 0 && <div className="w-px h-4 bg-white/[0.08]" />}
                <button
                  onClick={() => setTimeRange(r)}
                  className={`px-3 py-2 transition-all ${timeRange === r ? 'bg-indigo-500/15 text-white' : 'text-white/20 hover:text-white/50 hover:bg-white/5'}`}
                >
                  {r}
                </button>
              </div>
            ))}
          </div>

          {/* Chart Type */}
          <div className="flex items-center border border-white/[0.08] bg-white/[0.03] rounded-lg overflow-hidden font-dm-mono text-[11px] tracking-widest backdrop-blur-xl hover:border-white/[0.13] transition-all duration-300">
            {(['area', 'line', 'candle'] as const).map((t, i) => (
              <div key={t} className="flex items-center">
                {i > 0 && <div className="w-px h-4 bg-white/[0.08]" />}
                <button
                  onClick={() => setChartType(t)}
                  className={`px-3 py-2 transition-all uppercase ${chartType === t ? 'bg-indigo-500/15 text-white' : 'text-white/20 hover:text-white/50 hover:bg-white/5'}`}
                >
                  {t}
                </button>
              </div>
            ))}
          </div>

          {/* Strategy Selector */}
          <div className="relative group h-[36px]">
            <select value={activeStrategy} onChange={e => handleStrategyChange(e.target.value)}
              className="h-full border border-white/[0.08] bg-white/[0.03] backdrop-blur-xl rounded-lg px-4 hover:border-white/[0.13] text-white/40 text-[11px] font-dm-mono tracking-widest uppercase outline-none appearance-none transition-all duration-300 cursor-pointer min-w-[140px]">
              <option value="" className="bg-[#050507] text-white/40">NO STRATEGY</option>
              {strategies.map(s => <option key={s.id} value={s.id} className="bg-[#050507] text-white">{s.name}</option>)}
            </select>
          </div>
        </div>
      </div>

      {/* Error */}
      {error && (
        <div className="p-4 bg-red-500/5 border border-red-500/20 rounded-xl flex items-center gap-3 backdrop-blur-md shrink-0 transition-all">
          <AlertTriangle size={16} className="text-red-400 shrink-0" />
          <span className="font-dm-mono text-[12px] text-red-400 tracking-wider font-light">{error}</span>
        </div>
      )}

      {/* Main Content Floor */}
      <div className="flex-1 grid grid-cols-1 lg:grid-cols-4 gap-4 relative z-10 min-h-0 pt-2">
        
        {/* Left Sidebar: Signal Status + Params */}
        <div className="lg:col-span-1 flex flex-col gap-4 min-h-0">
          
          {/* Signal Meta Card */}
          <div className="shrink-0 group relative p-6 rounded-2xl border border-white/[0.07] bg-white/[0.03] backdrop-blur-xl hover:border-white/[0.13] hover:bg-white/[0.05] transition-all duration-500 overflow-hidden">
            <div className="absolute -top-4 -right-4 p-4 opacity-[0.03] group-hover:opacity-10 transition-opacity">
              <Zap size={110} />
            </div>
            <div className="flex items-center justify-between mb-5">
              <span className="font-inter text-[12px] text-white/30 uppercase tracking-[0.2em] font-medium">Signal Mood</span>
              <span className={`px-2.5 py-1 rounded border font-dm-mono text-[10px] tracking-widest font-medium flex items-center gap-1.5 ${
                meta?.current_mood === 'BULLISH' ? 'border-indigo-500/25 bg-indigo-500/8 text-indigo-400' :
                meta?.current_mood === 'BEARISH' ? 'border-red-500/20 bg-red-500/5 text-red-400' : 'border-white/8 bg-white/3 text-white/35'
              }`}>
                {meta?.current_mood === 'BULLISH' && <TrendingUp size={12} />}
                {meta?.current_mood === 'BEARISH' && <TrendingDown size={12} />}
                {meta?.current_mood ?? 'NEUTRAL'}
              </span>
            </div>
            <div className="mb-6 relative z-10 flex flex-col items-start gap-1">
              <div className="font-dm-mono text-[32px] font-medium text-white tabular-nums tracking-tight leading-none">{symbol}</div>
              {latest && (
                <div className={`font-dm-mono text-[15px] mt-1 tabular-nums flex items-center ${(priceChange ?? 0) >= 0 ? 'text-indigo-400' : 'text-white/40'}`}>
                  ${latest.close.toFixed(2)}
                  <span className="text-xs ml-2 font-medium">{(priceChange ?? 0) >= 0 ? '+' : ''}{(priceChange ?? 0).toFixed(2)}%</span>
                </div>
              )}
            </div>
            <div className="grid grid-cols-2 gap-3 relative z-10">
              <div className="bg-white/[0.02] rounded-xl p-3 border border-white/[0.04]">
                <div className="font-inter text-[10px] text-white/25 uppercase tracking-widest mb-1.5 font-medium">SIGNALS</div>
                <div className="font-dm-mono text-[22px] font-medium text-white tabular-nums leading-none tracking-tight">{meta?.signal_count ?? 0}</div>
              </div>
              <div className="bg-white/[0.02] rounded-xl p-3 border border-white/[0.04]">
                <div className="font-inter text-[10px] text-white/25 uppercase tracking-widest mb-1.5 font-medium">INTERVAL</div>
                <div className="font-dm-mono text-[22px] font-medium text-white tabular-nums leading-none tracking-tight">1D</div>
              </div>
            </div>
          </div>

          {/* Strategy Parameters Card */}
          <div className="flex-1 min-h-0 overflow-y-auto group relative p-6 rounded-2xl border border-white/[0.07] bg-white/[0.03] backdrop-blur-xl hover:border-white/[0.13] hover:bg-white/[0.05] transition-all duration-500">
            <div className="flex items-center gap-2 mb-5 border-b border-white/[0.05] pb-3">
              <Settings size={14} className="text-white/40 group-hover:text-indigo-400 transition-colors" />
              <span className="font-inter text-[12px] text-white/30 uppercase tracking-[0.2em] font-medium">Parameters</span>
            </div>
            <div className="space-y-6 flex flex-col pt-1">
              {Object.keys(strategyParams).length > 0 ? Object.entries(strategyParams).map(([key, val]) => (
                <div key={key}>
                  <div className="flex justify-between items-center mb-3">
                    <label className="font-dm-mono text-[11px] text-white/30 uppercase tracking-[0.28em]">{key.replace(/_/g, ' ')}</label>
                    <span className="font-dm-mono text-[12px] font-medium px-2 py-0.5 rounded border border-indigo-500/25 bg-indigo-500/8 text-indigo-400 tabular-nums">
                      {val}
                    </span>
                  </div>
                  <input
                    type="range" min="2" max="250" step="1" value={Number(val)}
                    onChange={e => setStrategyParams(prev => ({ ...prev, [key]: Number(e.target.value) }))}
                    className="w-full h-1 bg-white/10 rounded-full appearance-none cursor-pointer accent-indigo-500 hover:accent-indigo-400 transition-colors mt-2"
                  />
                </div>
              )) : (
                <div className="font-inter text-[12px] text-white/30 font-light italic text-center py-6">
                  {activeStrategy ? 'No parameters required' : 'SELECT A STRATEGY'}
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Right Panel: Chart */}
        <div className="lg:col-span-3 flex-1 min-h-0 group relative p-6 rounded-2xl border border-white/[0.07] bg-white/[0.03] backdrop-blur-xl hover:border-white/[0.13] hover:bg-white/[0.05] transition-all duration-500 overflow-hidden flex flex-col">
          {loading && (
            <div className="absolute inset-0 bg-black/40 z-20 flex items-center justify-center backdrop-blur-sm">
              <div className="flex flex-col items-center gap-4">
                <Activity className="text-indigo-400/60 animate-pulse" size={28} />
                <span className="font-dm-mono text-[12px] uppercase tracking-[0.28em] text-white/40 animate-pulse">Running Analysis</span>
              </div>
            </div>
          )}
          
          <div className="flex-1 w-full min-h-0">
            {candleData.length > 0 ? (
              <ResponsiveContainer width="100%" height="100%" className="-ml-3 mt-2">
                <AreaChart data={candleData} margin={{ top: 10, right: 0, bottom: 0, left: 0 }}>
                  <defs>
                    <linearGradient id="neonGlowIndigo" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="0%" stopColor="#4f46e5" stopOpacity={0.14} />
                      <stop offset="100%" stopColor="#4f46e5" stopOpacity={0} />
                    </linearGradient>
                    <filter id="neonShadowIndigo" x="-20%" y="-20%" width="140%" height="140%">
                      <feDropShadow dx="0" dy="0" stdDeviation="5" floodColor="#4f46e5" floodOpacity="0.6" />
                    </filter>
                  </defs>
                  <CartesianGrid stroke="rgba(255,255,255,0.03)" vertical={false} />
                  <XAxis dataKey="time" stroke="#ffffff1a" tick={{ fill: '#ffffff66', fontSize: 11, fontFamily: 'var(--font-mono)' }} axisLine={false} tickLine={false} dy={12} minTickGap={40} />
                  <YAxis stroke="#ffffff1a" tick={{ fill: '#ffffff66', fontSize: 11, fontFamily: 'var(--font-mono)' }} domain={['auto', 'auto']} axisLine={false} tickLine={false} dx={-10} />
                  <Tooltip content={<ChartTooltip />} cursor={{ stroke: 'rgba(255,255,255,0.07)', strokeWidth: 1, strokeDasharray: '4 4' }} />
                  <Area type="monotone" dataKey="close" stroke="#4f46e5" strokeWidth={1.5} fill="url(#neonGlowIndigo)" dot={false} style={{ filter: 'url(#neonShadowIndigo)' }} />
                </AreaChart>
              </ResponsiveContainer>
            ) : (
              <div className="h-full flex flex-col items-center justify-center text-white/20 gap-4">
                <Activity size={24} strokeWidth={1} className="text-white/20" />
                <div className="font-dm-mono text-[10px] uppercase tracking-[0.28em] text-white/30">
                  {loading ? 'Initializing Analysis...' : 'Awaiting Parameters'}
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
