'use client'

import { useState } from 'react'

const NEWS = [
  { id: 1, source: 'Reuters', time: '23:01', title: 'Fed signals potential rate cut in Q3 amid cooling inflation data', tag: 'MACRO', sentiment: 'bullish' },
  { id: 2, source: 'Bloomberg', time: '22:47', title: 'NVIDIA surpasses $2T market cap on record data center demand', tag: 'TECH', sentiment: 'bullish' },
  { id: 3, source: 'WSJ', time: '22:31', title: 'China consumer confidence falls for third consecutive month', tag: 'GLOBAL', sentiment: 'bearish' },
  { id: 4, source: 'FT', time: '22:15', title: 'Oil slides on supply glut concerns, WTI below $80/barrel', tag: 'ENERGY', sentiment: 'bearish' },
  { id: 5, source: 'CNBC', time: '21:58', title: 'Apple launches new AI features in iOS 18, analysts upgrade target', tag: 'TECH', sentiment: 'bullish' },
  { id: 6, source: 'Reuters', time: '21:42', title: 'ECB holds rates steady, Lagarde flags Q4 easing possible', tag: 'MACRO', sentiment: 'neutral' },
  { id: 7, source: 'Bloomberg', time: '21:20', title: 'Tesla Q1 deliveries miss estimates by 12%, stock drops after hours', tag: 'AUTO', sentiment: 'bearish' },
  { id: 8, source: 'CNBC', time: '20:55', title: 'Microsoft Azure revenue grows 31% YoY, beating expectations', tag: 'TECH', sentiment: 'bullish' },
  { id: 9, source: 'Reuters', time: '20:33', title: 'Gold hits all-time high above $2,300 on safe-haven demand', tag: 'COMMODITY', sentiment: 'bullish' },
  { id: 10, source: 'FT', time: '20:10', title: 'India GDP forecast raised to 7.2% by IMF for FY2025', tag: 'INDIA', sentiment: 'bullish' },
]

const TAGS = ['ALL', 'MACRO', 'TECH', 'GLOBAL', 'ENERGY', 'AUTO', 'COMMODITY', 'INDIA']

const sentimentStyle = (s: string) => {
  if (s === 'bullish') return 'text-indigo-400 border-indigo-500/25 bg-indigo-500/8'
  if (s === 'bearish') return 'text-white/35 border-white/10 bg-white/[0.03]'
  return 'text-white/40 border-white/8 bg-white/[0.02]'
}

export default function NewsBoxPage() {
  const [activeTag, setActiveTag] = useState('ALL')

  const filtered = activeTag === 'ALL' ? NEWS : NEWS.filter(n => n.tag === activeTag)

  return (
    <div className="space-y-6 font-inter">
      <div>
        <h1 className="font-dm-mono text-[28px] font-medium text-white tracking-tight">News Box</h1>
        <p className="font-inter text-[13px] text-white/30 mt-1">Real-time financial news & AI sentiment</p>
      </div>

      {/* Tag filters */}
      <div className="flex flex-wrap gap-2">
        {TAGS.map(tag => (
          <button
            key={tag}
            onClick={() => setActiveTag(tag)}
            className={`font-dm-mono text-[10px] px-3 py-1.5 rounded-lg border tracking-widest transition-all ${
              activeTag === tag
                ? 'border-indigo-500/35 bg-indigo-500/12 text-white'
                : 'border-white/[0.06] bg-transparent text-white/25 hover:text-white/50 hover:border-white/[0.12]'
            }`}
          >
            {tag}
          </button>
        ))}
      </div>

      {/* News feed */}
      <div className="space-y-2">
        {filtered.map(n => (
          <div
            key={n.id}
            className="flex items-start gap-4 px-5 py-4 rounded-xl border border-white/[0.05] bg-white/[0.02] hover:bg-white/[0.04] hover:border-white/[0.1] transition-all cursor-pointer group"
          >
            <div className="shrink-0 pt-0.5 text-right w-[52px]">
              <div className="font-dm-mono text-[10px] text-white/20 tabular-nums">{n.time}</div>
              <div className="font-inter text-[9px] text-white/18 mt-0.5 uppercase tracking-wider">{n.source}</div>
            </div>
            <div className="w-px h-10 bg-white/[0.06] shrink-0 self-center" />
            <div className="flex-1 min-w-0">
              <p className="font-inter text-[14px] text-white/75 leading-snug group-hover:text-white/90 transition-colors">{n.title}</p>
              <div className="flex items-center gap-2 mt-2">
                <span className={`font-dm-mono text-[9px] px-2 py-0.5 rounded border tracking-wider ${sentimentStyle(n.sentiment)}`}>
                  {n.sentiment.toUpperCase()}
                </span>
                <span className="font-dm-mono text-[9px] text-white/20 tracking-widest">{n.tag}</span>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
