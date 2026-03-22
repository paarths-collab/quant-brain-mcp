'use client'

import { useState, useEffect } from 'react'
import { RefreshCw, Briefcase, ArrowUpRight, ArrowDownRight, TrendingUp, TrendingDown, PieChart } from 'lucide-react'
import { PieChart as RechartsPie, Pie, Cell, Tooltip, ResponsiveContainer, Legend } from 'recharts'

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000'

// Mock data for UI — real app fetches from backend's investorProfileAPI
const MOCK = {
  total_value: 124830.55,
  total_invested: 100000,
  total_pl: 24830.55,
  total_pl_pct: 24.83,
  holdings: [
    { symbol: 'NVDA', quantity: 50, avg_price: 420.0, current_price: 897.5, current_value: 44875, pl: 23875, pl_pct: 113.69 },
    { symbol: 'MSFT', quantity: 30, avg_price: 310.0, current_price: 415.8, current_value: 12474, pl: 3174, pl_pct: 34.13 },
    { symbol: 'AAPL', quantity: 40, avg_price: 155.0, current_price: 189.4, current_value: 7576, pl: 1376, pl_pct: 22.19 },
    { symbol: 'TSLA', quantity: 20, avg_price: 200.0, current_price: 171.0, current_value: 3420, pl: -580, pl_pct: -14.5 },
    { symbol: 'META', quantity: 15, avg_price: 400.0, current_price: 502.3, current_value: 7534.5, pl: 1534.5, pl_pct: 25.58 },
  ],
}

const COLORS = ['#f59e0b', '#3b82f6', '#22c55e', '#8b5cf6', '#ef4444', '#06b6d4']

export default function PortfolioPage() {
  const [portfolio, setPortfolio] = useState<any>(null)
  const [loading, setLoading] = useState(true)

  const fetchPortfolio = async () => {
    setLoading(true)
    try {
      const res = await fetch(`${API_BASE}/api/portfolio`)
      if (!res.ok) throw new Error('Not found')
      const data = await res.json()
      setPortfolio(data)
    } catch {
      setPortfolio(MOCK) // fallback to mock
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { fetchPortfolio() }, [])

  const holdings = portfolio?.holdings ?? []
  const totalValue = portfolio?.total_value ?? 0

  // Pie chart data
  const pieData = holdings.map((h: any) => ({
    name: h.symbol,
    value: h.current_value,
    pct: ((h.current_value / totalValue) * 100).toFixed(1),
  }))

  if (loading) return (
    <div className="flex items-center justify-center h-[400px]">
      <div className="flex flex-col items-center gap-3">
        <RefreshCw className="animate-spin text-orange-400" size={28} />
        <span className="text-[12px] font-mono text-white/30">Loading portfolio…</span>
      </div>
    </div>
  )

  const isUp = (portfolio?.total_pl ?? 0) >= 0

  return (
    <div className="space-y-6 max-w-6xl mx-auto">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-mono font-bold text-white">Portfolio</h1>
          <p className="text-[12px] font-mono text-white/30 mt-0.5">Holdings · Performance Attribution · Risk Exposure</p>
        </div>
        <button onClick={fetchPortfolio}
          className="flex items-center gap-2 px-4 py-2 bg-white/[0.03] border border-white/[0.08] rounded-xl text-white/40 hover:text-white hover:bg-white/[0.06] transition-all text-[12px] font-mono">
          <RefreshCw size={13} />
          Refresh
        </button>
      </div>

      {!holdings.length ? (
        <div className="flex flex-col items-center justify-center py-24 border border-white/[0.07] rounded-2xl text-white/25">
          <Briefcase size={48} strokeWidth={1} className="mb-4 opacity-40" />
          <h3 className="text-lg font-mono font-semibold text-white/30">No Positions Yet</h3>
          <p className="text-[12px] font-mono mt-1">Use the AI Command or Backtest pages to initiate positions.</p>
        </div>
      ) : (
        <>
          {/* Summary Cards */}
          <div className="grid grid-cols-3 gap-4">
            <div className="p-5 rounded-xl border border-white/[0.07] bg-white/[0.02]">
              <div className="text-[10px] font-mono text-white/25 uppercase tracking-widest mb-2">Total Value</div>
              <div className="text-3xl font-mono font-bold text-white">${totalValue.toLocaleString('en-US', { minimumFractionDigits: 2 })}</div>
            </div>
            <div className="p-5 rounded-xl border border-white/[0.07] bg-white/[0.02]">
              <div className="text-[10px] font-mono text-white/25 uppercase tracking-widest mb-2">Total Invested</div>
              <div className="text-3xl font-mono font-bold text-white">${(portfolio?.total_invested ?? 0).toLocaleString()}</div>
            </div>
            <div className={`p-5 rounded-xl border ${isUp ? 'border-emerald-400/20 bg-emerald-400/5' : 'border-red-400/20 bg-red-400/5'}`}>
              <div className="text-[10px] font-mono text-white/25 uppercase tracking-widest mb-2">Total P&L</div>
              <div className={`text-3xl font-mono font-bold ${isUp ? 'text-emerald-400' : 'text-red-400'}`}>
                {isUp ? '+' : ''}${portfolio?.total_pl?.toLocaleString('en-US', { minimumFractionDigits: 2 })}
                <span className="text-lg ml-2">({portfolio?.total_pl_pct?.toFixed(2)}%)</span>
              </div>
            </div>
          </div>

          {/* Holdings Table + Allocation Pie */}
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-5">
            {/* Table */}
            <div className="lg:col-span-2 rounded-xl border border-white/[0.07] bg-white/[0.02] overflow-hidden">
              <div className="px-5 py-4 border-b border-white/[0.06]">
                <div className="text-[11px] font-mono text-white/30 uppercase tracking-widest">Holdings</div>
              </div>
              <div className="overflow-x-auto">
                <table className="w-full">
                  <thead>
                    <tr className="border-b border-white/[0.05]">
                      {['Symbol', 'Qty', 'Avg Price', 'LTP', 'Value', 'P&L'].map(h => (
                        <th key={h} className="px-4 py-3 text-left text-[10px] font-mono text-white/25 uppercase tracking-widest font-normal">{h}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {holdings.map((h: any) => {
                      const hUp = h.pl >= 0
                      return (
                        <tr key={h.symbol} className="border-b border-white/[0.04] hover:bg-white/[0.03] transition-colors">
                          <td className="px-4 py-3.5">
                            <div className="flex items-center gap-2">
                              <div className="w-7 h-7 rounded-lg bg-white/[0.06] flex items-center justify-center text-[10px] font-mono font-bold text-white/50">
                                {h.symbol.slice(0, 2)}
                              </div>
                              <span className="font-mono text-[13px] font-semibold text-white">{h.symbol}</span>
                            </div>
                          </td>
                          <td className="px-4 py-3.5 font-mono text-[12px] text-white/60">{h.quantity}</td>
                          <td className="px-4 py-3.5 font-mono text-[12px] text-white/60">${h.avg_price.toFixed(2)}</td>
                          <td className="px-4 py-3.5 font-mono text-[13px] font-semibold text-white">${h.current_price.toFixed(2)}</td>
                          <td className="px-4 py-3.5 font-mono text-[13px] text-white">${h.current_value.toLocaleString()}</td>
                          <td className="px-4 py-3.5">
                            <div className={`inline-flex flex-col items-end`}>
                              <div className={`font-mono text-[13px] font-bold flex items-center gap-1 ${hUp ? 'text-emerald-400' : 'text-red-400'}`}>
                                {hUp ? <ArrowUpRight size={12} /> : <ArrowDownRight size={12} />}
                                {hUp ? '+' : ''}${Math.abs(h.pl).toLocaleString()}
                              </div>
                              <span className={`text-[10px] font-mono ${hUp ? 'text-emerald-400/70' : 'text-red-400/70'}`}>
                                ({hUp ? '+' : ''}{h.pl_pct.toFixed(2)}%)
                              </span>
                            </div>
                          </td>
                        </tr>
                      )
                    })}
                  </tbody>
                </table>
              </div>
            </div>

            {/* Allocation Pie */}
            <div className="p-5 rounded-xl border border-white/[0.07] bg-white/[0.02]">
              <div className="text-[11px] font-mono text-white/30 uppercase tracking-widest mb-4 flex items-center gap-2">
                <PieChart size={13} className="text-orange-400" />
                Allocation
              </div>
              <ResponsiveContainer width="100%" height={200}>
                <RechartsPie>
                  <Pie data={pieData} cx="50%" cy="50%" innerRadius={50} outerRadius={85} dataKey="value" paddingAngle={2}>
                    {pieData.map((_: any, i: number) => <Cell key={i} fill={COLORS[i % COLORS.length]} />)}
                  </Pie>
                  <Tooltip
                    contentStyle={{ background: '#0a0a0a', border: '1px solid rgba(255,255,255,0.1)', borderRadius: 8, fontSize: 11, fontFamily: 'monospace' }}
                    formatter={(value: any, name: any, props: any) => [`$${value.toLocaleString()} (${props.payload.pct}%)`, props.payload.name]}
                  />
                </RechartsPie>
              </ResponsiveContainer>
              <div className="mt-4 space-y-2">
                {pieData.map((d: any, i: number) => (
                  <div key={d.name} className="flex items-center justify-between text-[11px] font-mono">
                    <div className="flex items-center gap-2">
                      <div className="w-2.5 h-2.5 rounded-sm" style={{ backgroundColor: COLORS[i % COLORS.length] }} />
                      <span className="text-white/60">{d.name}</span>
                    </div>
                    <span className="text-white/40">{d.pct}%</span>
                  </div>
                ))}
              </div>
            </div>
          </div>

          {/* Risk & Attribution */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            {[
              { label: 'Portfolio Beta', value: '1.12', note: 'vs S&P 500' },
              { label: 'Sharpe Ratio', value: '1.87', note: 'Annualized' },
              { label: 'Max Drawdown', value: '-18.3%', note: 'Last 12m', color: 'text-red-400' },
              { label: 'Volatility', value: '24.1%', note: 'Annualized' },
            ].map(card => (
              <div key={card.label} className="p-4 rounded-xl border border-white/[0.07] bg-white/[0.02]">
                <div className="text-[10px] font-mono text-white/25 uppercase tracking-widest mb-2">{card.label}</div>
                <div className={`text-xl font-mono font-bold ${card.color ?? 'text-white'}`}>{card.value}</div>
                <div className="text-[10px] font-mono text-white/25 mt-0.5">{card.note}</div>
              </div>
            ))}
          </div>
        </>
      )}
    </div>
  )
}
