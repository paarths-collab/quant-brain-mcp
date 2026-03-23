'use client'

import { useState, useEffect } from 'react'
import {
  LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, AreaChart, Area
} from 'recharts'

// ─── Constants ────────────────────────────────────────────────────────────────
const INDIGO_ACCENT = '#6366f1' // Unified indigo accent
const SILVER = '#c4c4cc'

const CARD = "group relative p-6 rounded-2xl border border-white/20 bg-white/[0.03] backdrop-blur-xl hover:border-indigo-400/40 hover:bg-white/5 transition-all duration-500 overflow-hidden"
const CARD_GLOW = "group relative p-6 rounded-2xl border border-white/25 bg-white/[0.035] backdrop-blur-xl shadow-[0_0_24px_rgba(99,102,241,0.06)] hover:shadow-[0_0_32px_rgba(99,102,241,0.12)] hover:border-indigo-400/50 hover:bg-white/8 transition-all duration-500 overflow-hidden"

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
  return <span className="text-indigo-400 font-dm-mono tabular-nums">{time}</span>
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
            labelFormatter={() => id}
            formatter={(v: any) => [`${Number(v).toFixed(2)}${unit}`, '']}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  )
}

function IndexCard({ idx, symbol }: { idx: typeof INDICES_US[0]; symbol: string }) {
  const isUp = idx.pct >= 0
  const spark = makeSpark(24, isUp)

  return (
    <div className={CARD_GLOW}>
      <div className="flex items-start justify-between mb-4">
        <div>
          <div className="font-dm-mono text-[11px] tracking-[0.28em] text-white/30 uppercase mb-0.5">{idx.symbol}</div>
          <div className="font-inter text-[13px] text-white/45 font-light">{idx.name}</div>
        </div>
        <div className={`font-dm-mono text-[11px] font-medium px-2 py-1 rounded border ${isUp ? 'border-indigo-500/25 bg-indigo-500/8 text-indigo-400' : 'border-white/8 bg-white/3 text-white/35'}`}>
          {isUp ? '+' : ''}{idx.pct.toFixed(2)}%
        </div>
      </div>

      <div className="font-dm-mono text-[32px] font-medium text-white tabular-nums tracking-tight mb-5 leading-none">
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
        <span className="font-dm-mono text-[10px] text-white/25 tracking-[0.28em] uppercase">{m.id}</span>
        <span className="font-dm-mono text-[9px] text-indigo-400/60">SYNC_OK</span>
      </div>
      <div className="font-inter text-[13px] text-white/40 mb-2 font-light">{m.title}</div>
      <div className="font-dm-mono text-[28px] font-medium text-white mb-4 tabular-nums tracking-tight leading-none">
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

  const isUS = market === 'us'
  const sym = isUS ? '$' : '₹'
  const INDICES = isUS ? INDICES_US : INDICES_IN
  const HOLDINGS = isUS ? HOLDINGS_US : HOLDINGS_IN
  const WATCHLIST = isUS ? WATCHLIST_US : WATCHLIST_IN
  const MACRO = isUS ? FRED : RBI

  const portfolioVal = HOLDINGS.reduce((a, h) => a + h.value, 0)
  const portfolioPL = HOLDINGS.reduce((a, h) => a + h.pl, 0)
  const portfolioPct = ((portfolioPL / (portfolioVal - portfolioPL)) * 100).toFixed(2)

  const doRefresh = async () => {
    setRefreshing(true)
    await new Promise(r => setTimeout(r, 800))
    setRefreshing(false)
  }

  const fmtVal = (n: number) =>
    isUS
      ? `$${n.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`
      : `₹${n.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`

  return (
    <div className="space-y-8 relative font-inter">
      {/* ── Dimmed Nebula Orbs ── */}
      {/* Background gradients removed as requested */}

      {/* ── Header ── */}
      <div className="flex items-center justify-between relative z-10">
        <div>
          <h1 className="font-dm-mono text-[30px] font-medium text-silver tracking-tight flex items-center gap-4">
            Analytics Terminal
            <span className="inline-flex items-center gap-2 px-2.5 py-1 text-[10px] border border-indigo-400/40 rounded-full text-indigo-300/80 bg-indigo-500/10">
              <span className="w-1.5 h-1.5 rounded-full bg-indigo-400 animate-pulse" />
              LIVE FEED
            </span>
          </h1>
          <p className="font-dm-mono text-[12px] text-white/25 mt-2 tracking-wider">
            <TimeDisplay /> · SERVER: NYC_DC_01 · STREAM: {isUS ? 'FRED' : 'RBI/NSE'}
          </p>
        </div>

        {/* Controls */}
        <div className="flex items-center gap-3">
          {/* Market Toggle */}
          <div className="flex items-center border border-white/20 rounded-lg overflow-hidden font-dm-mono text-[11px] tracking-widest">
            <button
              onClick={() => setMarket('us')}
              className={`px-4 py-2 transition-all ${isUS ? 'bg-indigo-500/15 text-white shadow-lg' : 'text-white/40 hover:text-white hover:bg-white/5'}`}
            >
              $ US
            </button>
            <div className="w-px h-5 bg-white/20" />
            <button
              onClick={() => setMarket('india')}
              className={`px-4 py-2 transition-all ${!isUS ? 'bg-indigo-500/15 text-white shadow-lg' : 'text-white/40 hover:text-white hover:bg-white/5'}`}
            >
              ₹ INDIA
            </button>
          </div>

          <button
            onClick={doRefresh}
            className="px-4 py-2 rounded-lg border border-indigo-400/30 bg-indigo-500/10 backdrop-blur-xl text-indigo-300 hover:text-white hover:bg-indigo-500/20 transition-all font-dm-mono text-[11px] uppercase tracking-widest"
          >
            {refreshing ? 'REFRESHING...' : 'REFRESH'}
          </button>
        </div>
      </div>

      {/* ── Key Stats ── */}
      <div className="grid grid-cols-1 sm:grid-cols-4 gap-4 relative z-10">
        {[
          { label: 'Portfolio Value', val: fmtVal(portfolioVal), sub: `+${portfolioPct}% TOTAL`, glow: true },
          { label: 'Unrealized P&L', val: `${portfolioPL >= 0 ? '+' : ''}${fmtVal(portfolioPL)}`, sub: 'ESTIMATED_VALUE', glow: false },
          { label: 'Exposure Index', val: '1.12', sub: 'SYSTEM_CALCULATED', glow: false },
          { label: 'Risk Efficiency', val: '1.87', sub: 'SHARPE_ANNUAL', glow: false },
        ].map(card => (
          <div key={card.label} className={card.glow ? CARD_GLOW : CARD}>
            <div className="font-inter text-[11px] text-silver/60 uppercase tracking-[0.2em] mb-3 font-medium">{card.label}</div>
            <div className="font-dm-mono text-[28px] font-medium text-white mb-1.5 tabular-nums tracking-tight leading-none">{card.val}</div>
            <div className="font-dm-mono text-[10px] text-white/40 tracking-widest">{card.sub}</div>
          </div>
        ))}
      </div>

      {/* ── Market Indices ── */}
      <section className="relative z-10">
        <div className="flex items-center gap-3 mb-5">
          <div className="w-6 h-[1px] bg-indigo-400/40" />
          <span className="font-dm-mono text-[10px] text-silver/40 uppercase tracking-[0.35em]">Market Indices · {isUS ? 'US' : 'INDIA'}</span>
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
            <span className="font-inter text-[11px] text-white/35 uppercase tracking-[0.2em] font-medium">Live Holdings</span>
            <span className="font-dm-mono text-[15px] font-medium text-white tabular-nums">{fmtVal(portfolioVal)}</span>
          </div>
          <div className="p-4 space-y-1.5">
            {HOLDINGS.map(h => (
              <div key={h.symbol} className="flex items-center justify-between px-4 py-3 rounded-xl border border-white/[0.03] hover:border-white/[0.1] hover:bg-white/[0.03] transition-all cursor-default">
                <div>
                  <div className="font-dm-mono text-[14px] font-medium text-white tracking-wide">{h.symbol}</div>
                  <div className="font-inter text-[11px] text-white/22 mt-0.5">{h.qty} × {sym}{h.avg.toFixed(0)}</div>
                </div>
                <div className="text-right">
                  <div className="font-dm-mono text-[14px] text-white tabular-nums">{fmtVal(h.value)}</div>
                  <div className={`font-dm-mono text-[11px] font-medium mt-0.5 ${h.pct >= 0 ? 'text-indigo-400' : 'text-white/30'}`}>
                    {h.pct >= 0 ? '+' : ''}{h.pct.toFixed(2)}%
                  </div>
                </div>
              </div>
            ))}
          </div>
          <div className="px-6 py-3.5 border-t border-white/[0.05] flex justify-between font-dm-mono text-[12px]">
            <span className="text-white/25 uppercase tracking-wider">TOTAL P&L</span>
            <span className={`font-medium tabular-nums ${portfolioPL >= 0 ? 'text-indigo-400' : 'text-white/35'}`}>
              {portfolioPL >= 0 ? '+' : ''}{fmtVal(portfolioPL)} ({portfolioPct}%)
            </span>
          </div>
        </div>

        {/* Watchlist */}
        <div className="lg:col-span-3 rounded-2xl border border-white/[0.07] bg-white/[0.03] backdrop-blur-xl overflow-hidden">
          <div className="px-6 py-4 border-b border-white/[0.05]">
            <span className="font-inter text-[11px] text-white/35 uppercase tracking-[0.2em] font-medium">System Watchlist · {isUS ? 'NYSE / NASDAQ' : 'NSE / BSE'}</span>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="border-b border-white/[0.03]">
                  {['Symbol', 'Price', 'Change', '% Chg', 'Volume'].map(h => (
                    <th key={h} className="px-6 py-3 text-left font-inter text-[10px] text-white/18 uppercase tracking-[0.2em] font-medium">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {WATCHLIST.map(row => {
                  const up = row.pct >= 0
                  return (
                    <tr key={row.symbol} className="border-b border-white/[0.025] hover:bg-white/[0.025] transition-colors cursor-default">
                      <td className="px-6 py-3.5">
                        <span className="font-dm-mono text-[14px] font-medium text-white tracking-wide">{row.symbol}</span>
                      </td>
                      <td className="px-6 py-3.5 font-dm-mono text-[13px] text-white tabular-nums">{sym}{row.price.toFixed(2)}</td>
                      <td className={`px-6 py-3.5 font-dm-mono text-[12px] tabular-nums ${up ? 'text-indigo-400' : 'text-white/30'}`}>
                        {up ? '+' : ''}{row.change.toFixed(2)}
                      </td>
                      <td className="px-6 py-3.5">
                        <span className={`font-dm-mono text-[12px] font-medium ${up ? 'text-indigo-400' : 'text-white/30'}`}>
                          {up ? '+' : ''}{row.pct.toFixed(2)}%
                        </span>
                      </td>
                      <td className="px-6 py-3.5 font-dm-mono text-[11px] text-white/22">{row.vol}</td>
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
          <span className="font-dm-mono text-[10px] text-white/25 uppercase tracking-[0.35em]">
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
            <span className="font-inter text-[10px] text-white/50 uppercase tracking-widest font-medium">{s.label}</span>
            <span className="font-dm-mono text-[11px] text-white font-medium">{s.status}</span>
          </div>
        ))}
      </div>
    </div>
  )
}
