'use client'

import { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { 
  Terminal, Cpu, Check, Copy, TrendingUp, BarChart3, 
  AlertTriangle, Maximize2, Send, Loader2 
} from 'lucide-react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import {
  LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer,
  AreaChart, Area, CartesianGrid
} from 'recharts'

// ─── Types ───────────────────────────────────────────────────────────────────
export interface Message {
  id: string
  role: 'user' | 'assistant'
  content: string
  timestamp: Date
  isStreaming?: boolean
}

export type ChartPoint = { x: number; v: number }

export interface RackSnapshot {
  ticker: string
  strategyName: string
  equityData: ChartPoint[]
  totalReturn: number | null
  sharpe: number | null
  winRate: number | null
  monteData: ChartPoint[]
  var95: number | null
  expected: number | null
  best95: number | null
  riskVar99: number | null
  riskCvar: number | null
  riskMaxDd: number | null
}

// ─── Components ──────────────────────────────────────────────────────────────

export function MessageBubble({ msg }: { msg: Message }) {
  const isUser = msg.role === 'user'
  const [copied, setCopied] = useState(false)

  const handleCopy = () => {
    navigator.clipboard.writeText(msg.content)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  return (
    <motion.div 
      initial={{ opacity: 0, y: 10, scale: 0.98 }}
      animate={{ opacity: 1, y: 0, scale: 1 }}
      transition={{ duration: 0.4, ease: [0.23, 1, 0.32, 1] }}
      className={`flex gap-4 mb-8 group ${isUser ? 'flex-row-reverse' : ''}`}
    >
      {/* Avatar / Icon */}
      <div className={`w-10 h-10 rounded-xl flex items-center justify-center shrink-0 border shadow-lg transition-transform duration-300 group-hover:scale-110 ${
        isUser 
          ? 'bg-white/[0.03] border-white/10 text-white/40' 
          : 'bg-indigo-500/10 border-indigo-500/20 text-indigo-400 shadow-indigo-500/5'
      }`}>
        {isUser ? <Terminal size={16} /> : <Cpu size={16} className={msg.isStreaming ? 'animate-spin' : 'animate-pulse'} />}
      </div>

      {/* Message Content */}
      <div className={`flex flex-col ${isUser ? 'items-end max-w-[80%]' : 'items-start max-w-[90%]'}`}>
        <div className={`flex items-center gap-3 mb-2 px-1 ${isUser ? 'flex-row-reverse' : ''}`}>
          <span className="text-[10px] font-mono text-white/30 tracking-[0.2em] font-bold uppercase">
            {isUser ? 'AUTHORIZED_USER' : 'QUANT_CORE_v2'}
          </span>
          <span className="text-[9px] font-mono text-white/15">
            {msg.timestamp.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })}
          </span>
          {!isUser && !msg.isStreaming && (
            <button 
              onClick={handleCopy} 
              className="opacity-0 group-hover:opacity-100 transition-all p-1 hover:bg-white/5 rounded-md"
              title="Copy analysis"
            >
              {copied ? <Check size={11} className="text-emerald-400" /> : <Copy size={11} className="text-white/30" />}
            </button>
          )}
        </div>

        <div className={`
          relative rounded-2xl px-6 py-5 text-[14px] leading-relaxed border backdrop-blur-2xl transition-all duration-500
          ${isUser
            ? 'bg-white/[0.04] border-white/10 text-white/90 font-sans shadow-xl'
            : 'bg-black/40 border-white/5 text-white/90 shadow-2xl group-hover:border-indigo-500/20'
          }
        `}>
          {/* Subtle Glow for assistant messages */}
          {!isUser && (
            <div className="absolute -inset-1 bg-indigo-500/5 blur-xl rounded-3xl -z-10 opacity-0 group-hover:opacity-100 transition-opacity duration-700" />
          )}

          {msg.isStreaming ? (
            <div className="flex items-center gap-3 text-indigo-400/80">
              <div className="flex gap-1.5">
                {[0, 1, 2].map(i => (
                  <motion.div 
                    key={i}
                    animate={{ scale: [1, 1.4, 1], opacity: [0.3, 1, 0.3] }}
                    transition={{ repeat: Infinity, duration: 1, delay: i * 0.2 }}
                    className="w-1.5 h-1.5 bg-indigo-400 rounded-full"
                  />
                ))}
              </div>
              <span className="text-[11px] font-mono uppercase tracking-[0.2em]">Neural Processing...</span>
            </div>
          ) : (
            <div className="prose prose-invert prose-sm max-w-none prose-p:text-white/80 prose-headings:text-indigo-300 prose-headings:font-syne prose-strong:text-white prose-code:text-indigo-200">
              <ReactMarkdown remarkPlugins={[remarkGfm]}>{msg.content}</ReactMarkdown>
            </div>
          )}
        </div>
      </div>
    </motion.div>
  )
}

export function AnalysisRack({ snapshot }: { snapshot: RackSnapshot }) {
  const equityData = snapshot.equityData
  const monteCarloData = snapshot.monteData

  const fmtPercent = (v: number | null, digits = 1) => (v === null ? 'N/A' : `${v.toFixed(digits)}%`)
  const fmtSignedPercent = (v: number | null, digits = 1) => {
    if (v === null) return 'N/A'
    return `${v >= 0 ? '+' : ''}${v.toFixed(digits)}%`
  }
  const fmtNumber = (v: number | null, digits = 2) => (v === null ? 'N/A' : v.toFixed(digits))

  const riskRows = [
    { label: 'VaR 99%', val: snapshot.riskVar99, desc: 'Value at Risk' },
    { label: 'Expected CVaR', val: snapshot.riskCvar, desc: 'Conditional VaR' },
    { label: 'Max Historcial Drawdown', val: snapshot.riskMaxDd, desc: 'Peak to Trough' },
  ]

  return (
    <div className="flex flex-col gap-6 h-full overflow-y-auto pr-3 custom-scrollbar pb-24 pt-4">
      {/* Header Info Removed at User Request */}

      {/* Equity Curve */}
      <motion.div 
        initial={{ opacity: 0, x: 20 }}
        animate={{ opacity: 1, x: 0 }}
        transition={{ delay: 0.1 }}
        className="relative group p-6 rounded-3xl border border-white/10 bg-white/[0.02] backdrop-blur-3xl overflow-visible"
      >
        <div className="absolute top-0 right-0 p-4 opacity-20 group-hover:opacity-100 transition-opacity">
           <Maximize2 size={12} className="cursor-pointer hover:text-indigo-400" />
        </div>
        
        <div className="flex items-center gap-2 mb-6">
          <div className="p-1.5 rounded-lg bg-indigo-500/10 border border-indigo-500/20">
            <TrendingUp size={12} className="text-indigo-400" />
          </div>
          <span className="font-mono text-[10px] text-white/40 uppercase tracking-[0.2em]">Equity Performance</span>
        </div>

        <div className="h-72 w-full overflow-visible">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={equityData} margin={{ top: 24, right: 32, left: 12, bottom: 16 }}>
              <defs>
                <linearGradient id="equityGradient" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#6366f1" stopOpacity={0.3}/>
                  <stop offset="95%" stopColor="#6366f1" stopOpacity={0}/>
                </linearGradient>
              </defs>
              <XAxis dataKey="x" hide />
              <YAxis hide domain={['auto', 'auto']} />
              <Tooltip content={({ active, payload }) => {
                if (active && payload?.[0]) return (
                  <div className="bg-black/90 backdrop-blur-xl border border-white/10 px-3 py-2 rounded-xl text-[10px] font-mono text-white/90 shadow-2xl">
                    <div className="text-white/40 mb-1">EQUITY_MARK</div>
                    <div className="text-indigo-400 font-bold">${Number(payload[0].value).toLocaleString(undefined, { minimumFractionDigits: 2 })}</div>
                  </div>
                )
                return null
              }} />
              <Line 
                type="monotone" 
                dataKey="v" 
                stroke="#818cf8" 
                strokeWidth={4} 
                dot={false} 
                animationDuration={1500}
                strokeLinecap="round"
              />
            </LineChart>
          </ResponsiveContainer>
        </div>

        <div className="grid grid-cols-3 gap-4 mt-6 pt-6 border-t border-white/5">
          <div>
            <div className="text-[9px] font-mono text-white/20 uppercase tracking-widest mb-1.5">RETURN</div>
            <div className="text-base font-syne text-indigo-400 font-bold">{fmtSignedPercent(snapshot.totalReturn)}</div>
          </div>
          <div>
            <div className="text-[9px] font-mono text-white/20 uppercase tracking-widest mb-1.5">SHARPE</div>
            <div className="text-base font-syne text-white font-bold">{fmtNumber(snapshot.sharpe)}</div>
          </div>
          <div>
            <div className="text-[9px] font-mono text-white/20 uppercase tracking-widest mb-1.5">WIN_RT</div>
            <div className="text-base font-syne text-indigo-300 font-bold">{fmtPercent(snapshot.winRate)}</div>
          </div>
        </div>
      </motion.div>

      {/* Monte Carlo */}
      <motion.div 
        initial={{ opacity: 0, x: 20 }}
        animate={{ opacity: 1, x: 0 }}
        transition={{ delay: 0.2 }}
        className="p-6 rounded-3xl border border-white/10 bg-white/[0.02] backdrop-blur-3xl overflow-visible"
      >
        <div className="flex items-center gap-2 mb-6">
          <div className="p-1.5 rounded-lg bg-indigo-500/10 border border-indigo-500/20">
            <BarChart3 size={12} className="text-indigo-400" />
          </div>
          <span className="font-mono text-[10px] text-white/40 uppercase tracking-[0.2em]">Predictive Monte Carlo</span>
        </div>

        <div className="h-64 w-full mb-6 overflow-visible">
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={monteCarloData} margin={{ top: 20, right: 18, left: 12, bottom: 20 }}>
              <defs>
                <linearGradient id="monteGradient" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#6366f1" stopOpacity={0.4}/>
                  <stop offset="95%" stopColor="#6366f1" stopOpacity={0}/>
                </linearGradient>
              </defs>
              <XAxis hide />
              <YAxis hide domain={['auto', 'auto']} />
              <Area 
                type="monotone" 
                dataKey="v" 
                stroke="#818cf8" 
                fill="url(#monteGradient)" 
                strokeWidth={3} 
                animationDuration={2000}
                strokeLinecap="round"
              />
            </AreaChart>
          </ResponsiveContainer>
        </div>

        <div className="flex flex-col gap-3 pt-6 border-t border-white/5">
           {[
             { l: 'VAR (95%)', v: fmtPercent(snapshot.var95), c: 'text-red-400/80' },
             { l: 'EXP. PRICE', v: fmtPercent(snapshot.expected), c: 'text-indigo-400' },
             { l: 'BULL (95%)', v: fmtPercent(snapshot.best95), c: 'text-emerald-400/80' },
           ].map(s => (
             <div key={s.l} className="flex justify-between items-center group/item hover:bg-white/[0.02] p-1 rounded-lg transition-colors">
               <span className="text-[10px] font-mono text-white/20 uppercase tracking-widest">{s.l}</span>
               <span className={`text-[12px] font-syne font-bold ${s.c}`}>{s.v}</span>
             </div>
           ))}
        </div>
      </motion.div>

      {/* Risk Rack */}
      <motion.div 
        initial={{ opacity: 0, x: 20 }}
        animate={{ opacity: 1, x: 0 }}
        transition={{ delay: 0.3 }}
        className="p-6 rounded-3xl border border-white/10 bg-white/[0.02] backdrop-blur-3xl"
      >
        <div className="flex items-center gap-2 mb-8">
           <div className="p-1.5 rounded-lg bg-amber-500/10 border border-amber-500/20">
             <AlertTriangle size={12} className="text-amber-400" />
           </div>
           <span className="font-mono text-[10px] text-white/40 uppercase tracking-[0.2em]">Institutional Risk Exposure</span>
        </div>
        
        <div className="space-y-8">
          {riskRows.map((r, i) => {
            const val = Math.abs(r.val ?? 0)
            const percentage = Math.min(100, (val / 30) * 100) // Scale to 30% for visual impact
            
            return (
              <div key={r.label} className="relative">
                <div className="flex justify-between items-end mb-2.5">
                  <div className="flex flex-col">
                    <span className="text-[10px] font-mono text-white/50 uppercase tracking-widest font-bold mb-0.5">{r.label}</span>
                    <span className="text-[9px] font-sans text-white/15 lowercase italic">{r.desc}</span>
                  </div>
                  <span className="text-sm font-syne font-bold text-white/90">{fmtPercent(r.val, 2)}</span>
                </div>
                <div className="h-1.5 w-full bg-white/5 rounded-full overflow-hidden">
                  <motion.div 
                    initial={{ width: 0 }}
                    animate={{ width: `${percentage}%` }}
                    transition={{ duration: 1.5, delay: 0.5 + (i * 0.1), ease: "easeOut" }}
                    className={`h-full rounded-full ${
                      val > 20 ? 'bg-gradient-to-r from-red-600 to-red-400 shadow-[0_0_15px_rgba(220,38,38,0.4)]' : 
                      val > 10 ? 'bg-gradient-to-r from-amber-600 to-amber-400 shadow-[0_0_12px_rgba(245,158,11,0.3)]' : 
                      'bg-gradient-to-r from-indigo-600 to-indigo-400 shadow-[0_0_10px_rgba(79,70,229,0.2)]'
                    }`}
                  />
                </div>
              </div>
            )
          })}
        </div>
      </motion.div>
    </div>
  )
}
