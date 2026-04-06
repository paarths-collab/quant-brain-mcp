'use client'

import { useState, useEffect, useRef, useCallback } from 'react'
import { marketAPI, fredAPI, investorProfileAPI, extractErrorMessage } from '@/lib/api'
import {
  LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, AreaChart, Area
} from 'recharts'

// ─── Constants ────────────────────────────────────────────────────────────────
const INDIGO_ACCENT = '#6366f1' // Unified indigo accent
const SILVER = '#c4c4cc'

const CARD = "system-card group relative p-6 rounded-2xl border border-white/20 bg-white/[0.03] backdrop-blur-xl hover:border-indigo-400/40 hover:bg-white/5 transition-all duration-500 overflow-hidden hover:-translate-y-1"
const CARD_GLOW = "system-card group relative p-6 rounded-2xl border border-white/25 bg-white/[0.035] backdrop-blur-xl shadow-[0_0_24px_rgba(99,102,241,0.06)] hover:shadow-[0_0_32px_rgba(99,102,241,0.12)] hover:border-indigo-400/50 hover:bg-white/8 transition-all duration-500 overflow-hidden hover:-translate-y-1"

// ─── Market Data ──────────────────────────────────────────────────────────────
const INDICES_US = [
  { symbol: 'SPY', name: 'S&P 500', price: 5842.47, change: 23.14, pct: 0.40 },
  { symbol: 'QQQ', name: 'NASDAQ', price: 20378.92, change: 87.33, pct: 0.43 },
  { symbol: 'DJI', name: 'Dow Jones', price: 43192.05, change: -45.12, pct: -0.10 },
  { symbol: 'VIX', name: 'Volatility', price: 16.31, change: -0.82, pct: -4.78 },
]

const INDICES_IN = [
  { symbol: 'NIFTY', name: 'Nifty 50', price: 22402.40, change: 112.30, pct: 0.50 },
  { symbol: 'SENSEX', name: 'Sensex', price: 73877.30, change: -95.20, pct: -0.13 },
  { symbol: 'BANK', name: 'Bank Nifty', price: 48210.55, change: 230.10, pct: 0.48 },
  { symbol: 'MIDCAP', name: 'Midcap 100', price: 49382.10, change: -180.40, pct: -0.36 },
]

const HOLDINGS_US = [
  { symbol: 'NVDA', qty: 50, avg: 420.0, ltp: 897.5, value: 44875, pl: 23875, pct: 113.69 },
  { symbol: 'MSFT', qty: 30, avg: 310.0, ltp: 415.8, value: 12474, pl: 3174, pct: 34.13 },
  { symbol: 'AAPL', qty: 40, avg: 155.0, ltp: 189.4, value: 7576, pl: 1376, pct: 22.19 },
  { symbol: 'TSLA', qty: 20, avg: 200.0, ltp: 171.0, value: 3420, pl: -580, pct: -14.5 },
]

const HOLDINGS_IN = [
  { symbol: 'RELIANCE', qty: 100, avg: 2400.0, ltp: 2872.5, value: 287250, pl: 47250, pct: 19.69 },
  { symbol: 'TCS', qty: 50, avg: 3600.0, ltp: 4012.3, value: 200615, pl: 20615, pct: 11.43 },
  { symbol: 'INFY', qty: 80, avg: 1500.0, ltp: 1389.4, value: 111152, pl: -8848, pct: -7.37 },
  { symbol: 'HDFCBANK', qty: 120, avg: 1550.0, ltp: 1621.0, value: 194520, pl: 8520, pct: 4.58 },
]

const WATCHLIST_US = [
  { symbol: 'NVDA', price: 897.50, change: 12.40, pct: 1.40, vol: '42.3M' },
  { symbol: 'AAPL', price: 189.40, change: -1.20, pct: -0.63, vol: '55.1M' },
  { symbol: 'TSLA', price: 171.05, change: 4.32, pct: 2.59, vol: '91.2M' },
  { symbol: 'MSFT', price: 415.82, change: 2.14, pct: 0.52, vol: '18.4M' },
  { symbol: 'META', price: 502.30, change: -3.10, pct: -0.61, vol: '11.7M' },
  { symbol: 'AMZN', price: 187.90, change: 1.85, pct: 0.99, vol: '33.5M' },
]

const WATCHLIST_IN = [
  { symbol: 'RELIANCE', price: 2872.50, change: 34.20, pct: 1.21, vol: '8.4M' },
  { symbol: 'TCS', price: 4012.30, change: -22.10, pct: -0.55, vol: '2.1M' },
  { symbol: 'WIPRO', price: 480.15, change: 5.30, pct: 1.11, vol: '15.2M' },
  { symbol: 'BAJFINANCE', price: 7121.45, change: -61.30, pct: -0.85, vol: '1.8M' },
  { symbol: 'HDFCBANK', price: 1621.00, change: 12.80, pct: 0.80, vol: '9.3M' },
  { symbol: 'ICICIBANK', price: 1089.70, change: 18.40, pct: 1.72, vol: '14.1M' },
]

const FRED = [
  { id: 'FEDFUNDS', title: 'Fed Funds Rate', value: 5.33, unit: '%' },
  { id: 'CPIAUCSL', title: 'CPI Inflation', value: 3.2, unit: '%' },
  { id: 'UNRATE', title: 'Unemployment', value: 3.7, unit: '%' },
  { id: 'DGS10', title: '10Y Treasury', value: 4.71, unit: '%' },
]

const RBI = [
  { id: 'REPO', title: 'Repo Rate', value: 6.50, unit: '%' },
  { id: 'INDIA_CPI', title: 'India CPI', value: 5.1, unit: '%' },
  { id: 'INDIA_GDP', title: 'GDP Growth', value: 7.2, unit: '%' },
  { id: 'USD_INR', title: 'USD/INR', value: 83.47, unit: '' },
]

function makeSpark(n = 24, up = true) {
  const arr = []
  let v = 100
  for (let i = 0; i < n; i++) {
    v += (Math.random() - (up ? 0.35 : 0.65)) * 3
    arr.push({ v: Math.max(85, v) })
  }
  return arr
}

function makeFred(base: number, vol: number, n = 18) {
  const arr = []
  let v = base * 0.7
  for (let i = 0; i < n; i++) {
    v += (Math.random() - 0.45) * vol
    arr.push({ v: Math.max(0, +v.toFixed(2)) })
  }
  arr.push({ v: base })
  return arr
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
  return <span className="text-indigo-400 data-text tabular-nums">{time}</span>
}

function useCountUp(value: number, duration = 700) {
  const [display, setDisplay] = useState(value)
  const prev = useRef(value)
  const raf = useRef<number>()

  useEffect(() => {
    const from = prev.current
    const to = value
    const start = performance.now()
    const animate = (t: number) => {
      const elapsed = t - start
      const p = Math.min(elapsed / duration, 1)
      const eased = 1 - Math.pow(1 - p, 3)
      const next = from + (to - from) * eased
      setDisplay(next)
      if (p < 1) {
        raf.current = requestAnimationFrame(animate)
      } else {
        prev.current = to
      }
    }
    raf.current = requestAnimationFrame(animate)
    return () => {
      if (raf.current) cancelAnimationFrame(raf.current)
    }
  }, [value, duration])

  return display
}

function NeonSpark({ data, color, id }: { data: { v: number }[]; color: string; id: string }) {
  return (
    <div className="h-11" style={{ filter: `drop-shadow(0 0 5px ${color}60)` }}>
      <ResponsiveContainer width="100%" height="100%">
        <AreaChart data={data} margin={{ top: 0, right: 0, bottom: 0, left: 0 }}>
          <defs>
            <linearGradient id={`ng-${id}`} x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor={color} stopOpacity={0.14} />
              <stop offset="100%" stopColor={color} stopOpacity={0} />
            </linearGradient>
          </defs>
          <Area type="monotone" dataKey="v" stroke={color} strokeWidth={1.5} fill={`url(#ng-${id})`} dot={false} />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  )
}

function NeonLine({ data, color, id, unit }: { data: { v: number }[]; color: string; id: string; unit: string }) {
  return (
    <div className="h-12" style={{ filter: `drop-shadow(0 0 4px ${color}50)` }}>
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={data} margin={{ top: 0, right: 0, bottom: 0, left: 0 }}>
          <Line type="monotone" dataKey="v" stroke={color} strokeWidth={1.5} dot={false} />
          <Tooltip
            contentStyle={{ background: '#06060a', border: '1px solid rgba(255,255,255,0.07)', borderRadius: 8, fontSize: 11, fontFamily: 'var(--font-mono)', backdropFilter: 'blur(8px)' }}
            itemStyle={{ color }}
            formatter={(v: any) => [`${Number(v).toFixed(2)}${unit}`, '']}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  )
}

type BackendHolding = {
  symbol: string
  quantity: number
  avg_price: number
  current_price: number
  current_value: number
  pl: number
  pl_pct: number
}

function IndexCard({ idx, symbol }: { idx: typeof INDICES_US[0]; symbol: string }) {
  const isUp = idx.pct >= 0
  const spark = makeSpark(24, isUp)

  return (
    <div className={CARD_GLOW}>
      <div className="flex items-start justify-between mb-4">
        <div>
          <div className="data-text text-[11px] tracking-[0.28em] text-white/30 uppercase mb-0.5">{idx.symbol}</div>
          <div className="data-text text-[13px] tracking-[0.12em] text-white/55 uppercase">{idx.name}</div>
        </div>
        <div className={`data-text text-[11px] font-medium px-2 py-1 rounded border ${isUp ? 'border-indigo-500/25 bg-indigo-500/8 text-indigo-400' : 'border-white/8 bg-white/3 text-white/35'}`}>
          {isUp ? '+' : ''}{idx.pct.toFixed(2)}%
        </div>
      </div>

      <div className="metric-text glow-text primary-text text-[32px] tabular-nums tracking-tight mb-5 leading-none">
        {symbol}{idx.price.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
      </div>

      <NeonSpark data={spark} color={INDIGO_ACCENT} id={idx.symbol} />
    </div>
  )
}

function FredCard({ m }: { m: typeof FRED[0] }) {
  const data = makeFred(m.value, m.value * 0.08)
  return (
    <div className={CARD_GLOW}>
      <div className="flex items-center justify-between mb-1.5">
        <span className="data-text text-[10px] text-white/25 tracking-[0.28em] uppercase">{m.id}</span>
        <span className="data-text text-[9px] text-indigo-400/60">SYNC_OK</span>
      </div>
      <div className="data-text text-[13px] text-white/50 mb-2">{m.title}</div>
      <div className="metric-text glow-text primary-text text-[28px] mb-4 tabular-nums tracking-tight leading-none">
        {m.value.toFixed(2)}<span className="text-[16px] text-white/35 ml-0.5">{m.unit}</span>
      </div>
      <NeonLine data={data} color={INDIGO_ACCENT} id={m.id} unit={m.unit} />
    </div>
  )
}

type Market = 'us' | 'india'

export default function DashboardPage() {
  const [market, setMarket] = useState<Market>('us')
  const [refreshing, setRefreshing] = useState(false)
  const [indices, setIndices] = useState(market === 'us' ? INDICES_US : INDICES_IN)
  const [holdings, setHoldings] = useState(market === 'us' ? HOLDINGS_US : HOLDINGS_IN)
  const [watchlist, setWatchlist] = useState(market === 'us' ? WATCHLIST_US : WATCHLIST_IN)
  const [macro, setMacro] = useState(market === 'us' ? FRED : RBI)
  const [error, setError] = useState<string | null>(null)

  const isUS = market === 'us'
  const sym = isUS ? '$' : '₹'
  const INDICES = indices
  const HOLDINGS = holdings
  const WATCHLIST = watchlist
  const MACRO = macro

  const loadBackendData = useCallback(async () => {
    setRefreshing(true)
    setError(null)
    try {
      const [overview, portfolio, fredSnapshot]: [any, any, any] = await Promise.all([
        marketAPI.getOverview(),
        investorProfileAPI.getPortfolio(),
        fredAPI.getLatestCached(['FEDFUNDS', 'CPIAUCSL', 'UNRATE', 'DGS10']),
      ])

      const overviewIndices = overview?.indices || {}
      const fredData = fredSnapshot?.data || {}

      if (market === 'us') {
        setIndices([
          { symbol: 'SPY', name: 'S&P 500', price: Number(overviewIndices.SP500?.price ?? INDICES_US[0].price), change: Number(overviewIndices.SP500?.change_pct ?? INDICES_US[0].change), pct: Number(overviewIndices.SP500?.change_pct ?? INDICES_US[0].pct) },
          { symbol: 'QQQ', name: 'NASDAQ', price: Number(overviewIndices.NASDAQ100?.price ?? INDICES_US[1].price), change: Number(overviewIndices.NASDAQ100?.change_pct ?? INDICES_US[1].change), pct: Number(overviewIndices.NASDAQ100?.change_pct ?? INDICES_US[1].pct) },
          { symbol: 'DJI', name: 'Dow Jones', price: Number(overviewIndices.DJIA?.price ?? INDICES_US[2].price), change: Number(overviewIndices.DJIA?.change_pct ?? INDICES_US[2].change), pct: Number(overviewIndices.DJIA?.change_pct ?? INDICES_US[2].pct) },
          { symbol: 'VIX', name: 'Volatility', price: Number(overviewIndices.VIXCLS?.price ?? INDICES_US[3].price), change: Number(overviewIndices.VIXCLS?.change_pct ?? INDICES_US[3].change), pct: Number(overviewIndices.VIXCLS?.change_pct ?? INDICES_US[3].pct) },
        ])
        setHoldings(Array.isArray(portfolio?.holdings) && portfolio.holdings.length ? portfolio.holdings.map((h: BackendHolding) => ({
          symbol: h.symbol,
          qty: h.quantity,
          avg: h.avg_price,
          ltp: h.current_price,
          value: h.current_value,
          pl: h.pl,
          pct: h.pl_pct,
        })) : HOLDINGS_US)
        setWatchlist(WATCHLIST_US)
        setMacro([
          { id: 'FEDFUNDS', title: 'Fed Funds Rate', value: Number(fredData.FEDFUNDS?.value ?? FRED[0].value), unit: '%' },
          { id: 'CPIAUCSL', title: 'CPI Inflation', value: Number(fredData.CPIAUCSL?.value ?? FRED[1].value), unit: '%' },
          { id: 'UNRATE', title: 'Unemployment', value: Number(fredData.UNRATE?.value ?? FRED[2].value), unit: '%' },
          { id: 'DGS10', title: '10Y Treasury', value: Number(fredData.DGS10?.value ?? FRED[3].value), unit: '%' },
        ])
      } else {
        setIndices([
          { symbol: 'NIFTY', name: 'Nifty 50', price: Number(overviewIndices['^NSEI']?.price ?? INDICES_IN[0].price), change: Number(overviewIndices['^NSEI']?.change_pct ?? INDICES_IN[0].change), pct: Number(overviewIndices['^NSEI']?.change_pct ?? INDICES_IN[0].pct) },
          { symbol: 'SENSEX', name: 'Sensex', price: Number(overviewIndices['^BSESN']?.price ?? INDICES_IN[1].price), change: Number(overviewIndices['^BSESN']?.change_pct ?? INDICES_IN[1].change), pct: Number(overviewIndices['^BSESN']?.change_pct ?? INDICES_IN[1].pct) },
          { symbol: 'BANK', name: 'Bank Nifty', price: Number(overviewIndices['^NSEBANK']?.price ?? INDICES_IN[2].price), change: Number(overviewIndices['^NSEBANK']?.change_pct ?? INDICES_IN[2].change), pct: Number(overviewIndices['^NSEBANK']?.change_pct ?? INDICES_IN[2].pct) },
          { symbol: 'MIDCAP', name: 'Midcap 100', price: Number(overviewIndices['^NIFTYMCAP100']?.price ?? INDICES_IN[3].price), change: Number(overviewIndices['^NIFTYMCAP100']?.change_pct ?? INDICES_IN[3].change), pct: Number(overviewIndices['^NIFTYMCAP100']?.change_pct ?? INDICES_IN[3].pct) },
        ])
        setHoldings(Array.isArray(portfolio?.holdings) && portfolio.holdings.length ? portfolio.holdings.map((h: BackendHolding) => ({
          symbol: h.symbol,
          qty: h.quantity,
          avg: h.avg_price,
          ltp: h.current_price,
          value: h.current_value,
          pl: h.pl,
          pct: h.pl_pct,
        })) : HOLDINGS_IN)
        setWatchlist(WATCHLIST_IN)
        setMacro(RBI)
      }
    } catch (err) {
      setError(extractErrorMessage(err, 'Failed to load dashboard data from backend.'))
    } finally {
      setRefreshing(false)
    }
  }, [market])

  useEffect(() => {
    void loadBackendData()
  }, [loadBackendData])

  const portfolioVal = HOLDINGS.reduce((a, h) => a + h.value, 0)
  const portfolioPL = HOLDINGS.reduce((a, h) => a + h.pl, 0)
  const portfolioPct = ((portfolioPL / (portfolioVal - portfolioPL)) * 100).toFixed(2)
  const animatedPortfolioVal = useCountUp(portfolioVal, 800)
  const animatedPortfolioPL = useCountUp(portfolioPL, 800)
  const animatedExposure = useCountUp(1.12, 700)
  const animatedRisk = useCountUp(1.87, 700)

  const doRefresh = async () => {
    await loadBackendData()
  }

  const fmtVal = (n: number) =>
    isUS
      ? `$${n.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`
      : `₹${n.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`

  return (
    <div className="dashboard-bg dashboard-scope space-y-8 relative">

      {/* ── Terminal Header ── */}
      <div className="relative z-10 space-y-5">
        {error && (
          <div className="rounded-xl border border-amber-400/20 bg-amber-400/10 px-4 py-3 text-sm text-amber-100">
            {error}
          </div>
        )}
        <div className="flex items-center gap-3">
          <span className="w-1.5 h-6 rounded-full bg-indigo-400/80 shadow-[0_0_16px_rgba(129,140,248,0.6)]" />
          <span className="data-text text-[12px] text-white/65 tracking-[0.32em] uppercase">
            Terminal
          </span>
          <div className="flex-1 h-px bg-white/10" />
        </div>

        <div className="flex flex-wrap items-center gap-3">
          <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full border border-white/15 bg-white/[0.02] backdrop-blur-xl">
            <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
            <span className="data-text text-[10px] text-white/60 uppercase tracking-[0.24em]">System Status</span>
          </div>
          <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full border border-white/10 bg-white/[0.015]">
            <span className="data-text text-[10px] text-indigo-200/90 uppercase tracking-[0.22em]">AI_ACTIVE</span>
          </div>
          <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full border border-white/10 bg-white/[0.015]">
            <span className="data-text text-[10px] text-white/55 uppercase tracking-[0.22em]">CONFIDENCE 87.5%</span>
          </div>
          <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full border border-white/10 bg-white/[0.015]">
            <span className="data-text text-[10px] text-white/55 uppercase tracking-[0.22em]">
              STREAM {isUS ? 'FRED' : 'RBI/NSE'}
            </span>
          </div>
        </div>

        <div className="flex items-center justify-between gap-6">
          <div>
            <h1 className="heading-text glow-text text-[30px] text-white tracking-[-0.01em] flex items-center gap-4">
              Analytics Terminal
              <span className="inline-flex items-center gap-2 px-2.5 py-1 text-[10px] border border-indigo-400/40 rounded-full text-indigo-200/90 bg-indigo-500/10">
                <span className="w-1.5 h-1.5 rounded-full bg-indigo-300 animate-pulse" />
                LIVE FEED
              </span>
            </h1>
            <p className="data-text text-[11px] meta-text mt-2 tracking-[0.18em] uppercase">
              <TimeDisplay /> · SERVER NYC_DC_01 · STREAM {isUS ? 'FRED' : 'RBI/NSE'}
            </p>
          </div>

          {/* Controls */}
          <div className="flex items-center gap-3">
            {/* Market Toggle */}
            <div className="flex items-center border border-white/15 rounded-lg overflow-hidden data-text text-[11px] tracking-widest">
              <button
                onClick={() => setMarket('us')}
                className={`px-4 py-2 transition-all ${isUS ? 'bg-indigo-500/15 text-white shadow-lg' : 'text-white/40 hover:text-white hover:bg-white/5'}`}
              >
                $ US
              </button>
              <div className="w-px h-5 bg-white/15" />
              <button
                onClick={() => setMarket('india')}
                className={`px-4 py-2 transition-all ${!isUS ? 'bg-indigo-500/15 text-white shadow-lg' : 'text-white/40 hover:text-white hover:bg-white/5'}`}
              >
                ₹ INDIA
              </button>
            </div>

            <button
              onClick={doRefresh}
              className="px-4 py-2 rounded-lg border border-indigo-400/30 bg-indigo-500/10 backdrop-blur-xl text-indigo-200/90 hover:text-white hover:bg-indigo-500/20 transition-all data-text text-[11px] uppercase tracking-widest"
            >
              {refreshing ? 'REFRESHING...' : 'REFRESH'}
            </button>
          </div>
        </div>
      </div>

      {/* ── System Metrics ── */}
      <div className="grid grid-cols-1 sm:grid-cols-4 gap-4 relative z-10">
        {[
          { label: 'Portfolio Value', val: fmtVal(animatedPortfolioVal), sub: `+${portfolioPct}% TOTAL`, glow: true },
          { label: 'Unrealized P&L', val: `${portfolioPL >= 0 ? '+' : ''}${fmtVal(animatedPortfolioPL)}`, sub: 'ESTIMATED_VALUE', glow: false },
          { label: 'Exposure Index', val: animatedExposure.toFixed(2), sub: 'SYSTEM_CALCULATED', glow: false },
          { label: 'Risk Efficiency', val: animatedRisk.toFixed(2), sub: 'SHARPE_ANNUAL', glow: false },
        ].map(card => (
          <div key={card.label} className={card.glow ? CARD_GLOW : CARD}>
            <div className="absolute inset-0 opacity-0 group-hover:opacity-100 transition-opacity duration-300 bg-[radial-gradient(circle_at_top_right,rgba(79,107,255,0.18),transparent_60%)]" />
            <div className="section-title meta-text mb-3">{card.label}</div>
            <div className="metric-text glow-text primary-text text-[28px] mb-1.5 tabular-nums leading-none">{card.val}</div>
            <div className="data-text text-[10px] secondary-text tracking-widest">{card.sub}</div>
          </div>
        ))}
      </div>

      {/* ── Market Field ── */}
      <section className="relative z-10">
        <div className="flex items-center gap-3 mb-5">
          <div className="w-6 h-[1px] bg-indigo-400/40" />
          <span className="section-title meta-text">Market Field · {isUS ? 'US' : 'INDIA'}</span>
        </div>
        <div className="grid grid-cols-1 lg:grid-cols-4 gap-4">
          {INDICES.map(idx => <IndexCard key={idx.symbol} idx={idx} symbol={sym} />)}
        </div>
      </section>

      {/* ── Portfolio + Watchlist ── */}
      <div className="grid grid-cols-1 lg:grid-cols-5 gap-6 relative z-10">
        {/* Holdings */}
        <div className="lg:col-span-2 rounded-2xl border border-white/[0.07] bg-white/[0.03] backdrop-blur-xl overflow-hidden">
          <div className="px-6 py-4 border-b border-white/[0.05] flex items-center justify-between">
          <span className="data-text text-[11px] text-white/35 uppercase tracking-[0.2em] font-medium">Live Holdings</span>
          <span className="metric-text primary-text text-[15px] tabular-nums">{fmtVal(portfolioVal)}</span>
        </div>
        <div className="p-4 space-y-1.5">
          {HOLDINGS.map(h => (
            <div key={h.symbol} className="flex items-center justify-between px-4 py-3 rounded-xl border border-white/[0.03] hover:border-white/[0.1] hover:bg-white/[0.03] transition-all cursor-default">
              <div>
                <div className="data-text text-[14px] text-white tracking-wide">{h.symbol}</div>
                <div className="data-text text-[11px] text-white/30 mt-0.5">{h.qty} × {sym}{h.avg.toFixed(0)}</div>
              </div>
              <div className="text-right">
                <div className="metric-text primary-text text-[14px] tabular-nums">{fmtVal(h.value)}</div>
                <div className={`data-text text-[11px] font-medium mt-0.5 ${h.pct >= 0 ? 'text-indigo-400' : 'text-white/30'}`}>
                  {h.pct >= 0 ? '+' : ''}{h.pct.toFixed(2)}%
                </div>
              </div>
            </div>
          ))}
        </div>
        <div className="px-6 py-3.5 border-t border-white/[0.05] flex justify-between data-text text-[12px]">
          <span className="text-white/25 uppercase tracking-wider">TOTAL P&L</span>
          <span className={`metric-text tabular-nums ${portfolioPL >= 0 ? 'text-indigo-400' : 'text-white/35'}`}>
            {portfolioPL >= 0 ? '+' : ''}{fmtVal(portfolioPL)} ({portfolioPct}%)
          </span>
        </div>
      </div>

        {/* Watchlist */}
        <div className="lg:col-span-3 rounded-2xl border border-white/[0.07] bg-white/[0.03] backdrop-blur-xl overflow-hidden">
        <div className="px-6 py-4 border-b border-white/[0.05]">
          <span className="data-text text-[11px] text-white/35 uppercase tracking-[0.2em] font-medium">System Watchlist · {isUS ? 'NYSE / NASDAQ' : 'NSE / BSE'}</span>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead>
              <tr className="border-b border-white/[0.03]">
                {['Symbol', 'Price', 'Change', '% Chg', 'Volume'].map(h => (
                  <th key={h} className="px-6 py-3 text-left data-text text-[10px] text-white/18 uppercase tracking-[0.2em] font-medium">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {WATCHLIST.map(row => {
                const up = row.pct >= 0
                return (
                  <tr key={row.symbol} className="border-b border-white/[0.025] hover:bg-white/[0.025] transition-colors cursor-default">
                    <td className="px-6 py-3.5">
                      <span className="data-text text-[14px] text-white tracking-wide">{row.symbol}</span>
                    </td>
                    <td className="px-6 py-3.5 metric-text text-[13px] text-white tabular-nums">{sym}{row.price.toFixed(2)}</td>
                    <td className={`px-6 py-3.5 data-text text-[12px] tabular-nums ${up ? 'text-indigo-400' : 'text-white/30'}`}>
                      {up ? '+' : ''}{row.change.toFixed(2)}
                    </td>
                    <td className="px-6 py-3.5">
                      <span className={`data-text text-[12px] font-medium ${up ? 'text-indigo-400' : 'text-white/30'}`}>
                        {up ? '+' : ''}{row.pct.toFixed(2)}%
                      </span>
                    </td>
                    <td className="px-6 py-3.5 data-text text-[11px] text-white/22">{row.vol}</td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      </div>
      </div>

      {/* ── Macro Data ── */}
      <section className="relative z-10">
        <div className="flex items-center gap-3 mb-5">
          <div className="w-6 h-[1px] bg-indigo-500/40" />
          <span className="data-text text-[10px] text-white/25 uppercase tracking-[0.35em]">
            {isUS ? 'FRED Macro Data' : 'RBI / India Macro'}
          </span>
        </div>
        <div className="grid grid-cols-1 lg:grid-cols-4 gap-4">
          {MACRO.map(m => <FredCard key={m.id} m={m} />)}
        </div>
      </section>

      {/* ── System Footer ── */}
      <div className="relative z-10 flex flex-wrap items-center gap-10 py-8 border-t border-white/[0.04]">
        {[
          { label: 'Agents', status: 'ONLINE' },
          { label: 'Market Feed', status: 'STABLE' },
          { label: 'Risk Engine', status: 'ACTIVE' },
          { label: 'Latency', status: '<24ms' },
        ].map(s => (
          <div key={s.label} className="flex flex-col gap-1 opacity-25">
            <span className="data-text text-[10px] text-white/50 uppercase tracking-widest font-medium">{s.label}</span>
            <span className="data-text text-[11px] text-white font-medium">{s.status}</span>
          </div>
        ))}
      </div>
    </div>
  )
}
