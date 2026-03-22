'use client'

import { useState } from 'react'

const PEERS_US = [
  { symbol: 'NVDA', name: 'NVIDIA', price: 897.50, mktCap: '2.21T', pe: 72.4, pb: 38.2, roe: 115.8, margin: 55.7, ytd: 82.4 },
  { symbol: 'AMD', name: 'Advanced Micro', price: 165.30, mktCap: '267B', pe: 310.2, pb: 3.8, roe: 1.2, margin: 3.6, ytd: -14.2 },
  { symbol: 'INTC', name: 'Intel', price: 44.20, mktCap: '187B', pe: 29.8, pb: 1.4, roe: 4.7, margin: 5.1, ytd: -22.8 },
  { symbol: 'QCOM', name: 'Qualcomm', price: 169.40, mktCap: '191B', pe: 21.3, pb: 7.2, roe: 33.8, margin: 26.2, ytd: 12.7 },
  { symbol: 'AVGO', name: 'Broadcom', price: 1482.10, mktCap: '695B', pe: 37.8, pb: 10.3, roe: 29.4, margin: 51.4, ytd: 18.3 },
]

const PEERS_IN = [
  { symbol: 'TCS', name: 'Tata Consultancy', price: 4012.30, mktCap: '14.6T', pe: 32.4, pb: 13.2, roe: 41.8, margin: 24.7, ytd: 8.4 },
  { symbol: 'INFY', name: 'Infosys', price: 1389.40, mktCap: '5.8T', pe: 26.2, pb: 7.8, roe: 31.2, margin: 20.6, ytd: -7.4 },
  { symbol: 'WIPRO', name: 'Wipro', price: 480.15, mktCap: '2.5T', pe: 22.8, pb: 4.1, roe: 18.4, margin: 16.2, ytd: 2.1 },
  { symbol: 'HCLTECH', name: 'HCL Technologies', price: 1621.00, mktCap: '4.4T', pe: 28.6, pb: 6.9, roe: 24.7, margin: 19.8, ytd: 14.2 },
  { symbol: 'LTIM', name: 'LTIMindtree', price: 5382.45, mktCap: '1.6T', pe: 35.1, pb: 8.3, roe: 22.1, margin: 15.4, ytd: 5.8 },
]

export default function PeerComparisonPage() {
  const [market, setMarket] = useState<'us' | 'india'>('us')
  const peers = market === 'us' ? PEERS_US : PEERS_IN
  const sym = market === 'us' ? '$' : '₹'

  const cols = ['Symbol', 'Price', 'Mkt Cap', 'P/E', 'P/B', 'ROE %', 'Net Margin %', 'YTD']

  return (
    <div className="space-y-6 font-inter">
      <div className="flex items-start justify-between">
        <div>
          <h1 className="font-dm-mono text-[28px] font-medium text-white tracking-tight">Peer Comparison</h1>
          <p className="font-inter text-[13px] text-white/30 mt-1">Side-by-side fundamental valuation analysis</p>
        </div>
        <div className="flex items-center border border-white/[0.07] rounded-lg overflow-hidden font-dm-mono text-[11px] tracking-widest">
          <button onClick={() => setMarket('us')} className={`px-4 py-2 transition-all ${market === 'us' ? 'bg-indigo-500/15 text-white' : 'text-white/30 hover:text-white/60'}`}>$ US</button>
          <div className="w-px h-5 bg-white/[0.07]" />
          <button onClick={() => setMarket('india')} className={`px-4 py-2 transition-all ${market === 'india' ? 'bg-indigo-500/15 text-white' : 'text-white/30 hover:text-white/60'}`}>₹ INDIA</button>
        </div>
      </div>

      <div className="rounded-2xl border border-white/[0.07] bg-white/[0.03] backdrop-blur-xl overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead>
              <tr className="border-b border-white/[0.04]">
                {cols.map(c => (
                  <th key={c} className="px-5 py-3.5 text-left font-inter text-[10px] text-white/20 uppercase tracking-[0.18em] font-medium whitespace-nowrap">{c}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {peers.map((p, i) => {
                const isFirst = i === 0
                return (
                  <tr key={p.symbol} className={`border-b border-white/[0.025] hover:bg-white/[0.025] transition-colors ${isFirst ? 'bg-indigo-500/[0.04]' : ''}`}>
                    <td className="px-5 py-4">
                      <div className="font-dm-mono text-[14px] font-medium text-white">{p.symbol}</div>
                      <div className="font-inter text-[11px] text-white/25 mt-0.5 truncate max-w-[120px]">{p.name}</div>
                    </td>
                    <td className="px-5 py-4 font-dm-mono text-[13px] text-white tabular-nums">{sym}{p.price.toLocaleString()}</td>
                    <td className="px-5 py-4 font-dm-mono text-[13px] text-white/60 tabular-nums">{p.mktCap}</td>
                    <td className="px-5 py-4 font-dm-mono text-[13px] text-white/70 tabular-nums">{p.pe}x</td>
                    <td className="px-5 py-4 font-dm-mono text-[13px] text-white/70 tabular-nums">{p.pb}x</td>
                    <td className="px-5 py-4 font-dm-mono text-[13px] text-indigo-400 tabular-nums">{p.roe}%</td>
                    <td className="px-5 py-4 font-dm-mono text-[13px] text-indigo-400/70 tabular-nums">{p.margin}%</td>
                    <td className={`px-5 py-4 font-dm-mono text-[13px] font-medium tabular-nums ${p.ytd >= 0 ? 'text-indigo-400' : 'text-white/30'}`}>
                      {p.ytd >= 0 ? '+' : ''}{p.ytd}%
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}
