'use client'

import { useState, useRef, useEffect, useCallback } from 'react'
import {
  Terminal, Cpu, Send, Loader2, Copy, Check, X,
  TrendingUp, BarChart3, AlertTriangle, Activity,
  Zap, Globe, Maximize2, Minimize2, GripVertical
} from 'lucide-react'
import {
  LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer,
  AreaChart, Area, CartesianGrid
} from 'recharts'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { getWsUrl, superAgentAPI, type SuperAgentResponse } from '@/lib/api'

const WS_URL = getWsUrl('/ws/live')

// ─── Types ───────────────────────────────────────────────────────────────────
interface Message {
  id: string
  role: 'user' | 'assistant'
  content: string
  timestamp: Date
  isStreaming?: boolean
}

type ChartPoint = { x: number; v: number }

interface RackSnapshot {
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

const uid = () => Math.random().toString(36).slice(2)

const DEFAULT_RACK_SNAPSHOT: RackSnapshot = {
  ticker: 'N/A',
  strategyName: 'Strategy',
  equityData: Array.from({ length: 40 }, (_, i) => ({
    x: i,
    v: 10000 + Math.sin(i / 5) * 1000 + i * 150,
  })),
  totalReturn: 53.1,
  sharpe: 1.82,
  winRate: 61.4,
  monteData: Array.from({ length: 50 }, (_, i) => {
    const x = (i - 25) / 10
    return { x: i, v: Math.exp(-(x * x) / 2) * 100 }
  }),
  var95: -5.0,
  expected: 8.0,
  best95: 18.0,
  riskVar99: 5.0,
  riskCvar: 8.0,
  riskMaxDd: 12.0,
}

const toNum = (value: unknown): number | null => {
  if (typeof value === 'number' && Number.isFinite(value)) return value
  if (typeof value === 'string') {
    const n = Number(value)
    if (Number.isFinite(n)) return n
  }
  return null
}

const pctFromRatioOrPercent = (value: unknown): number | null => {
  const n = toNum(value)
  if (n === null) return null
  if (Math.abs(n) <= 1) return n * 100
  return n
}

const parseTickerFromQuery = (query: string): string | null => {
  const m = /\b\w*backtest\b\s+([A-Za-z][A-Za-z0-9.\-]{0,19})/i.exec(query || '')
  if (m?.[1]) return m[1].toUpperCase()
  const words = (query || '').match(/\b[A-Za-z][A-Za-z0-9.]{1,19}\b/g) || []
  const candidate = words.find(w => /\.|^[A-Z]{2,12}$/i.test(w))
  return candidate ? candidate.toUpperCase() : null
}

const buildMonteCurve = (samples: unknown): ChartPoint[] => {
  if (!Array.isArray(samples)) return DEFAULT_RACK_SNAPSHOT.monteData
  const numeric = samples.map(toNum).filter((n): n is number => n !== null)
  if (numeric.length < 6) return DEFAULT_RACK_SNAPSHOT.monteData

  const min = Math.min(...numeric)
  const max = Math.max(...numeric)
  if (!Number.isFinite(min) || !Number.isFinite(max) || max <= min) {
    return DEFAULT_RACK_SNAPSHOT.monteData
  }

  const bins = 24
  const width = (max - min) / bins
  const hist = Array.from({ length: bins }, () => 0)
  for (const n of numeric) {
    const idx = Math.max(0, Math.min(bins - 1, Math.floor((n - min) / width)))
    hist[idx] += 1
  }
  const peak = Math.max(...hist, 1)
  return hist.map((count, i) => ({ x: i, v: (count / peak) * 100 }))
}

const extractRackSnapshot = (data: SuperAgentResponse, query: string): RackSnapshot | null => {
  const rawStrategy = (data.strategy && typeof data.strategy === 'object') ? data.strategy as Record<string, unknown> : null
  const rawBest = (rawStrategy?.best_strategy && typeof rawStrategy.best_strategy === 'object')
    ? rawStrategy.best_strategy as Record<string, unknown>
    : null
  const rawMonte = (rawStrategy?.monte_carlo && typeof rawStrategy.monte_carlo === 'object')
    ? rawStrategy.monte_carlo as Record<string, unknown>
    : null
  const rawRisk = (data.risk_engine && typeof data.risk_engine === 'object')
    ? data.risk_engine as Record<string, unknown>
    : null
  const rawFinancial = (data.financial && typeof data.financial === 'object')
    ? data.financial as Record<string, unknown>
    : null

  const rawCurve = Array.isArray(rawBest?.equity_curve) ? rawBest.equity_curve : []
  const equityData = rawCurve
    .map((p, idx) => {
      if (!p || typeof p !== 'object') return null
      const point = p as Record<string, unknown>
      const v = toNum(point.value)
      if (v === null) return null
      return { x: idx, v }
    })
    .filter((p): p is ChartPoint => p !== null)

  const ticker =
    (typeof rawFinancial?.formatted_ticker === 'string' && rawFinancial.formatted_ticker) ||
    (typeof rawFinancial?.ticker === 'string' && rawFinancial.ticker) ||
    parseTickerFromQuery(query) ||
    'N/A'

  const strategyName =
    (typeof rawBest?.strategy === 'string' && rawBest.strategy) ||
    (typeof rawStrategy?.regime === 'object' ? 'AI Selected' : 'Strategy')

  const totalReturn = pctFromRatioOrPercent(rawBest?.return)
  const winRate = pctFromRatioOrPercent(rawBest?.win_rate)
  const sharpe = toNum(rawBest?.sharpe) ?? toNum(rawBest?.sharpe_ratio)

  const var95 = pctFromRatioOrPercent(rawRisk?.VaR)
  const cvar = pctFromRatioOrPercent(rawRisk?.CVaR)
  const maxDd = pctFromRatioOrPercent(rawRisk?.Max_Drawdown)
  const best95 = pctFromRatioOrPercent(rawMonte?.best_case)
  const expected = pctFromRatioOrPercent(rawMonte?.expected_price)
  const monteData = buildMonteCurve(rawMonte?.simulation_paths)

  const hasAnyLiveData =
    equityData.length > 0 ||
    totalReturn !== null ||
    winRate !== null ||
    sharpe !== null ||
    var95 !== null ||
    cvar !== null ||
    maxDd !== null

  if (!hasAnyLiveData) return null

  return {
    ticker,
    strategyName,
    equityData: equityData.length ? equityData : DEFAULT_RACK_SNAPSHOT.equityData,
    totalReturn,
    sharpe,
    winRate,
    monteData,
    var95,
    expected,
    best95,
    riskVar99: var95,
    riskCvar: cvar,
    riskMaxDd: maxDd,
  }
}

const extractAssistantContent = (data: SuperAgentResponse) => {
  const pick = (
    data.report ||
    data.response ||
    (typeof data.content === 'string' ? data.content : null) ||
    (typeof data.analysis === 'string' ? data.analysis : null) ||
    (typeof data.message === 'string' ? data.message : null) ||
    (typeof data.summary === 'string' ? data.summary : null)
  )
  if (pick && String(pick).trim()) return String(pick)

  const result = data.result as unknown
  if (typeof result === 'string' && result.trim()) return result
  if (result && typeof result === 'object') {
    const r = result as Record<string, unknown>
    const nested =
      (typeof r.report === 'string' ? r.report : null) ||
      (typeof r.response === 'string' ? r.response : null) ||
      (typeof r.content === 'string' ? r.content : null) ||
      (typeof r.analysis === 'string' ? r.analysis : null) ||
      (typeof r.message === 'string' ? r.message : null)
    if (nested && nested.trim()) return nested
  }

  if (typeof data.error === 'string' && data.error.trim()) {
    return `⚠️ ${data.error}`
  }

  try {
    return `Analysis complete.\n\n\`\`\`json\n${JSON.stringify(data, null, 2).slice(0, 3500)}\n\`\`\``
  } catch {
    return 'Analysis complete.'
  }
}

// ─── Analytics Components ────────────────────────────────────────────────────
function AnalysisRack({ snapshot }: { snapshot: RackSnapshot }) {
  const equityData = snapshot.equityData
  const monteCarloData = snapshot.monteData

  const fmtPercent = (v: number | null, digits = 1) => (v === null ? 'N/A' : `${v.toFixed(digits)}%`)
  const fmtSignedPercent = (v: number | null, digits = 1) => {
    if (v === null) return 'N/A'
    return `${v >= 0 ? '+' : ''}${v.toFixed(digits)}%`
  }
  const fmtNumber = (v: number | null, digits = 2) => (v === null ? 'N/A' : v.toFixed(digits))

  const riskRows = [
    { label: 'VaR_99', val: snapshot.riskVar99 },
    { label: 'CVaR_EXPECTED', val: snapshot.riskCvar },
    { label: 'MAX_HISTORICAL_DD', val: snapshot.riskMaxDd },
  ]

  const maxRiskAbs = Math.max(
    1,
    ...riskRows.map(r => Math.abs(r.val ?? 0)),
  )

  const riskFillWidth = (v: number | null) => {
    if (v === null) return 2
    const scaled = (Math.abs(v) / maxRiskAbs) * 100
    return Math.max(6, Math.min(100, scaled))
  }

  const riskFillClass = (v: number | null) => {
    const a = Math.abs(v ?? 0)
    if (a >= 25) return 'bg-red-500/55 shadow-[0_0_14px_rgba(239,68,68,0.35)]'
    if (a >= 10) return 'bg-amber-400/55 shadow-[0_0_12px_rgba(251,191,36,0.3)]'
    return 'bg-indigo-500/55 shadow-[0_0_10px_rgba(99,102,241,0.3)]'
  }

  return (
    <div className="flex flex-col gap-4 h-full overflow-y-auto pr-2 custom-scrollbar pb-10">
      {/* Equity Curve */}
      <div className="chart-reflect p-5 pb-6 min-h-[min-content] rounded-2xl border border-white/20 bg-white/[0.03] backdrop-blur-xl">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-2">
            <TrendingUp size={14} className="text-indigo-400" />
            <span className="font-dm-mono text-[11px] text-white/40 uppercase tracking-[0.2em]">{snapshot.ticker} {snapshot.strategyName}</span>
          </div>
          <Maximize2 size={12} className="text-white/20" />
        </div>
        <div className="h-44 w-full">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={equityData}>
              <CartesianGrid strokeDasharray="3 3" stroke="#ffffff05" vertical={false} />
              <XAxis dataKey="x" hide />
              <YAxis hide domain={['auto', 'auto']} />
              <Tooltip content={({ active, payload }) => {
                if (active && payload?.[0]) return (
                  <div className="bg-black/90 border border-white/20 p-2 rounded text-[10px] font-dm-mono text-white tracking-widest uppercase shadow-2xl">
                    ${Number(payload[0].value).toFixed(2)}
                  </div>
                )
                return null
              }} />
              <Line type="monotone" dataKey="v" stroke="#6366f1" strokeWidth={2.5} dot={false} />
            </LineChart>
          </ResponsiveContainer>
        </div>
        <div className="grid grid-cols-3 gap-2 mt-4 pt-4 border-t border-white/10">
          <div>
            <div className="text-[9px] font-dm-mono text-white/20 uppercase tracking-widest mb-1">TOTAL RETURN</div>
            <div className="text-[14px] font-dm-mono text-indigo-400 font-bold leading-relaxed pb-1">{fmtSignedPercent(snapshot.totalReturn)}</div>
          </div>
          <div>
            <div className="text-[9px] font-dm-mono text-white/20 uppercase tracking-widest mb-1">SHARPE</div>
            <div className="text-[14px] font-dm-mono text-white font-bold leading-relaxed pb-1">{fmtNumber(snapshot.sharpe)}</div>
          </div>
          <div>
            <div className="text-[9px] font-dm-mono text-white/20 uppercase tracking-widest mb-1">WIN RATE</div>
            <div className="text-[14px] font-dm-mono text-indigo-300 font-bold leading-relaxed pb-1">{fmtPercent(snapshot.winRate)}</div>
          </div>
        </div>
      </div>

      {/* Monte Carlo */}
      <div className="chart-reflect p-5 pb-6 min-h-[min-content] rounded-2xl border border-white/20 bg-white/[0.03] backdrop-blur-xl">
        <div className="flex items-center gap-2 mb-4">
          <BarChart3 size={14} className="text-indigo-400" />
          <span className="font-dm-mono text-[11px] text-white/40 uppercase tracking-[0.2em]">Monte Carlo Simulation</span>
        </div>
        <div className="h-44 w-full mb-4">
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={monteCarloData}>
              <XAxis hide />
              <YAxis hide />
              <Area type="monotone" dataKey="v" stroke="#6366f1" fill="#6366f120" strokeWidth={2.5} dot={false} />
            </AreaChart>
          </ResponsiveContainer>
        </div>
        <div className="grid grid-cols-3 gap-2 mt-4 pt-4 border-t border-white/10">
          {[
            { l: '5% VaR', v: fmtPercent(snapshot.var95), c: 'text-red-400' },
            { l: 'EXPECTED', v: fmtPercent(snapshot.expected), c: 'text-indigo-400' },
            { l: '95% BEST', v: fmtPercent(snapshot.best95), c: 'text-indigo-400' },
          ].map(s => (
            <div key={s.l}>
              <div className="text-[9px] font-dm-mono text-white/20 uppercase tracking-widest mb-1">{s.l}</div>
              <div className={`text-[12px] font-dm-mono font-bold leading-relaxed pb-1 ${s.c}`}>{s.v}</div>
            </div>
          ))}
        </div>
      </div>

      {/* Risk Analysis */}
      <div className="chart-reflect p-5 pb-6 min-h-[min-content] rounded-2xl border border-white/20 bg-white/[0.03] backdrop-blur-xl">
        <div className="flex items-center gap-2 mb-5">
           <AlertTriangle size={14} className="text-indigo-400" />
           <span className="font-dm-mono text-[11px] text-white/40 uppercase tracking-[0.2em]">Risk Analysis Rack</span>
        </div>
        <div className="space-y-6">
          {riskRows.map(r => (
            <div key={r.label} className="flex flex-col gap-2">
              <div className="flex justify-between items-center text-[10px] uppercase font-dm-mono tracking-widest font-semibold">
                <span className="text-white/30">{r.label}</span>
                <span className="text-white">{fmtPercent(r.val, 2)}</span>
              </div>
              <div className="h-2 bg-white/5 rounded-full overflow-hidden border border-white/10 p-[1.5px]">
                <div
                  className={`h-full rounded-full transition-all duration-1000 ${riskFillClass(r.val)}`}
                  style={{ width: `${riskFillWidth(r.val)}%` }}
                />
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}

function MessageBubble({ msg }: { msg: Message }) {
  const isUser = msg.role === 'user'
  const [copied, setCopied] = useState(false)

  const handleCopy = () => {
    navigator.clipboard.writeText(msg.content)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  return (
    <div className={`flex gap-3 mb-6 group ${isUser ? 'flex-row-reverse' : ''}`}>
      <div className={`w-8 h-8 rounded-lg flex items-center justify-center shrink-0 border ${
        isUser ? 'bg-white/[0.04] border-white/20' : 'bg-indigo-500/10 border-indigo-500/20'
      }`}>
        {isUser ? <Terminal size={14} className="text-white/50" /> : <Cpu size={14} className="text-indigo-400 animate-pulse" />}
      </div>

      <div className={`flex-1 min-w-0 ${isUser ? 'max-w-[70%]' : 'max-w-[90%]'}`}>
        <div className={`flex items-center gap-2 mb-1.5 ${isUser ? 'justify-end' : ''}`}>
          <span className="text-[10px] font-dm-mono text-white/25 tracking-[0.15em] font-bold uppercase truncate">
            {isUser ? 'DEPLOYER' : 'NEURAL_UNIT@BQ'}
          </span>
          <span className="text-[9px] font-dm-mono text-white/15">
            {msg.timestamp.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })}
          </span>
          {!isUser && (
            <button onClick={handleCopy} className="opacity-0 group-hover:opacity-60 hover:opacity-100 transition-opacity ml-auto">
              {copied ? <Check size={10} className="text-emerald-400" /> : <Copy size={10} className="text-white/40" />}
            </button>
          )}
        </div>

        <div className={`rounded-2xl px-5 py-4 text-[13px] border backdrop-blur-3xl shadow-2xl ${
          isUser
            ? 'bg-white/[0.03] border-white/20 text-white/80 font-dm-mono tracking-tight leading-relaxed shadow-white/[0.01]'
            : 'bg-black/60 border-white/10 text-white/90 leading-relaxed'
        }`}>
          {msg.isStreaming ? (
            <div className="flex items-center gap-2 text-indigo-400">
              <div className="flex gap-1">
                {[0, 1, 2].map(i => (
                  <div key={i} className="w-1.5 h-1.5 bg-indigo-400 rounded-full animate-pulse" style={{ animationDelay: `${i * 200}ms` }} />
                ))}
              </div>
              <span className="text-[11px] font-dm-mono uppercase tracking-widest">Processing...</span>
            </div>
          ) : (
            <div className="prose prose-invert prose-sm max-w-none prose-p:text-white/70">
              <ReactMarkdown remarkPlugins={[remarkGfm]}>{msg.content}</ReactMarkdown>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

const QUICK_COMMANDS = [
  { cmd: 'analyze NVDA', icon: TrendingUp, label: 'Analyze NVDA' },
  { cmd: 'backtest TSLA momentum strategy', icon: BarChart3, label: 'Backtest TSLA' },
  { cmd: 'risk analysis for my portfolio', icon: AlertTriangle, label: 'Risk Analysis' },
  { cmd: 'detect current market regime', icon: Activity, label: 'Market Regime' },
  { cmd: 'optimal portfolio AI tech sector', icon: Globe, label: 'Optimizer' },
]

export default function ChatPage() {
  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [wsConnected, setWsConnected] = useState(false)
  const [rackWidth, setRackWidth] = useState(500)
  const [isResizing, setIsResizing] = useState(false)
  const [rackSnapshot, setRackSnapshot] = useState<RackSnapshot>(DEFAULT_RACK_SNAPSHOT)

  const scrollRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLInputElement>(null)
  const wsRef = useRef<WebSocket | null>(null)
  const containerRef = useRef<HTMLDivElement>(null)
  const lastQueryRef = useRef('')

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: 'smooth' })
  }, [messages])

  useEffect(() => { inputRef.current?.focus() }, [])

  // Resizer logic - improved to handle mouse events more reliably
  const handleMouseDown = (e: React.MouseEvent) => {
    setIsResizing(true)
    document.body.style.cursor = 'col-resize'
    e.preventDefault()
  };

  useEffect(() => {
    const handleMouseMove = (e: MouseEvent) => {
      if (!isResizing) return;
      const newWidth = window.innerWidth - e.clientX - 40; // Subtract padding/sidebar offset
      if (newWidth > 300 && newWidth < 900) {
        setRackWidth(newWidth);
      }
    };

    const handleMouseUp = () => {
      setIsResizing(false);
      document.body.style.cursor = 'default';
    };

    if (isResizing) {
      window.addEventListener('mousemove', handleMouseMove);
      window.addEventListener('mouseup', handleMouseUp);
    }

    return () => {
      window.removeEventListener('mousemove', handleMouseMove);
      window.removeEventListener('mouseup', handleMouseUp);
    };
  }, [isResizing]);

  useEffect(() => {
    try {
      const ws = new WebSocket(WS_URL)
      wsRef.current = ws
      ws.onopen = () => setWsConnected(true)
      ws.onclose = () => {
        setWsConnected(false)
        setIsLoading(false)
      }
      ws.onerror = () => setWsConnected(false)
      ws.onmessage = (event) => {
        try {
          const parsed: unknown = JSON.parse(event.data)
          const data: SuperAgentResponse =
            parsed && typeof parsed === 'object' ? (parsed as SuperAgentResponse) : {}
          const content = extractAssistantContent(data)
          const snapshot = extractRackSnapshot(data, lastQueryRef.current)
          if (snapshot) setRackSnapshot(snapshot)
          setMessages(prev => {
            const filtered = prev.filter(m => !m.isStreaming)
            return [...filtered, { id: uid(), role: 'assistant', content, timestamp: new Date() }]
          })
          setIsLoading(false)
        } catch {
          setIsLoading(false)
        }
      }
      return () => { ws.readyState === WebSocket.OPEN && ws.close() }
    } catch {
      setWsConnected(false)
    }
  }, [])

  const sendMessage = useCallback(async (query: string) => {
    if (!query.trim() || isLoading) return
    const userMsg: Message = { id: uid(), role: 'user', content: query.trim(), timestamp: new Date() }
    const streamMsg: Message = { id: uid(), role: 'assistant', content: '', timestamp: new Date(), isStreaming: true }
    lastQueryRef.current = query.trim()
    setMessages(prev => [...prev, userMsg, streamMsg])
    setInput('')
    setIsLoading(true)

    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ query: query.trim() }))
    } else {
      try {
        const data = await superAgentAPI.run({ query: query.trim() })
        const content = extractAssistantContent(data)
        const snapshot = extractRackSnapshot(data, query.trim())
        if (snapshot) setRackSnapshot(snapshot)
        setMessages(prev => {
            const filtered = prev.filter(m => !m.isStreaming)
            return [...filtered, { id: uid(), role: 'assistant', content, timestamp: new Date() }]
        })
      } catch (err) {
        const reason = err instanceof Error && err.message ? err.message : 'Request failed'
        setMessages(prev => {
          const filtered = prev.filter(m => !m.isStreaming)
          return [...filtered, {
            id: uid(), role: 'assistant',
            content: `⚠️ **Pipeline Error** — ${reason}`,
            timestamp: new Date()
          }]
        })
      } finally {
        setIsLoading(false)
      }
    }
  }, [isLoading])

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    sendMessage(input)
  }

  return (
    <div ref={containerRef} className="flex flex-col h-[calc(100vh-40px)] font-inter">
      {/* Header Removed as per user request */}

      <div className="flex-1 flex min-h-0 relative z-10 overflow-hidden">
        {/* Messages Pane */}
        <div className="flex-1 min-w-0 flex flex-col pr-0 overflow-hidden">
          <div ref={scrollRef} className="flex-1 overflow-y-auto pr-6 custom-scrollbar scroll-smooth">
            {messages.length === 0 ? (
              <div className="flex flex-col items-center justify-center h-full max-w-md mx-auto">
                <div className="flex flex-col items-center gap-4 mb-10">
                  <div className="relative">
                    <div className="w-16 h-16 rounded-2xl bg-indigo-500/5 border border-white/20 flex items-center justify-center backdrop-blur-3xl">
                      <Terminal size={24} className="text-indigo-400" />
                    </div>
                    <div className="absolute -inset-2 bg-indigo-500/10 blur-2xl rounded-full -z-10" />
                  </div>
                  <div className="text-center">
                    <h2 className="text-[14px] font-dm-mono text-white/60 tracking-[0.25em] uppercase mb-1">Awaiting_Instructions</h2>
                    <p className="text-[11px] font-inter text-white/20 tracking-tight uppercase">Quant Analytics Core v2.1.0_Stable</p>
                  </div>
                </div>
                
                <div className="grid grid-cols-1 gap-2 w-full">
                  {QUICK_COMMANDS.map(qc => {
                    const Icon = qc.icon
                    return (
                      <button
                        key={qc.cmd}
                        onClick={() => sendMessage(qc.cmd)}
                        className="flex items-center justify-between p-4 bg-white/[0.01] hover:bg-indigo-500/5 border border-white/10 hover:border-indigo-500/30 rounded-2xl transition-all group backdrop-blur-sm"
                      >
                        <div className="flex items-center gap-3">
                          <Icon size={13} className="text-indigo-400/50 group-hover:text-indigo-400 transition-colors" />
                          <span className="text-[11px] font-dm-mono text-white/30 group-hover:text-white/70 transition-colors uppercase tracking-widest">{qc.label}</span>
                        </div>
                        <span className="text-[10px] font-dm-mono text-white/5 opacity-0 group-hover:opacity-100 transition-all tracking-tighter">RUN_CMD</span>
                      </button>
                    )
                  })}
                </div>
              </div>
            ) : (
              <div className="py-2 space-y-4 max-w-5xl mx-auto">
                {messages.map(msg => <MessageBubble key={msg.id} msg={msg} />)}
              </div>
            )}
          </div>

          {/* Input Area */}
          <div className="pt-6 border-t border-white/20 mt-4 mr-6">
            <form onSubmit={handleSubmit}>
              <div className="flex items-center gap-3 bg-black/60 border border-white/20 focus-within:border-indigo-500/40 rounded-2xl px-5 py-4 transition-all backdrop-blur-3xl shadow-[0_0_50px_rgba(0,0,0,0.6)]">
                <span className="text-indigo-500 font-dm-mono text-sm shrink-0 tracking-widest font-bold">&gt;_</span>
                <input
                  ref={inputRef}
                  type="text"
                  value={input}
                  onChange={e => setInput(e.target.value)}
                  placeholder="DEPLOY COMMAND..."
                  className="flex-1 bg-transparent text-white placeholder:text-white/10 font-dm-mono text-[13px] focus:outline-none tracking-widest uppercase"
                  disabled={isLoading}
                />
                <button
                  type="submit"
                  disabled={!input.trim() || isLoading}
                  className="shrink-0 w-10 h-10 rounded-xl bg-indigo-500/10 hover:bg-indigo-500/20 disabled:opacity-20 flex items-center justify-center border border-indigo-500/30 transition-all shadow-indigo-500/10"
                >
                  {isLoading
                    ? <Loader2 size={15} className="text-indigo-400 animate-spin" />
                    : <Send size={15} className="text-indigo-400" />}
                </button>
              </div>
                <span className="text-[9px] font-dm-mono text-white/10 tracking-[0.2em] uppercase">{messages.length} ELEMENTS_IN_BUFFER</span>
            </form>
          </div>
        </div>

        {/* Dynamic Resizer Handle - Functional Splitter */}
        <div 
          onMouseDown={handleMouseDown}
          className={`group relative w-1.5 hover:w-2 bg-transparent hover:bg-indigo-500/30 cursor-col-resize transition-all shrink-0 flex items-center justify-center z-20 ${isResizing ? 'bg-indigo-500/50 w-2' : ''}`}
        >
          <div className="absolute h-full w-full flex items-center justify-center pointer-events-none opacity-0 group-hover:opacity-100">
             <div className="w-[1px] h-full bg-indigo-500/50" />
             <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-4 h-8 bg-indigo-500/20 border border-indigo-500/40 rounded flex items-center justify-center">
                <GripVertical size={10} className="text-indigo-400/50" />
             </div>
          </div>
        </div>

        {/* Right Panel: Rack */}
        <div 
          className="hidden xl:block shrink-0 h-full border-l border-white/10 pl-6 bg-black/20 overflow-hidden"
          style={{ width: `${rackWidth}px` }}
        >
          <AnalysisRack snapshot={rackSnapshot} />
        </div>
      </div>
      
      <style jsx global>{`
        .custom-scrollbar::-webkit-scrollbar {
          width: 4px;
        }
        .custom-scrollbar::-webkit-scrollbar-track {
          background: transparent;
        }
        .custom-scrollbar::-webkit-scrollbar-thumb {
          background: rgba(255, 255, 255, 0.05);
          border-radius: 20px;
        }
        .custom-scrollbar::-webkit-scrollbar-thumb:hover {
          background: rgba(99, 102, 241, 0.2);
        }

        .chart-reflect {
          position: relative;
          overflow: hidden;
        }

        .chart-reflect > * {
          position: relative;
          z-index: 1;
        }

        .chart-reflect::before {
          content: '';
          position: absolute;
          inset: 0;
          pointer-events: none;
          background:
            linear-gradient(164deg, rgba(255,255,255,0.16) 0%, rgba(255,255,255,0.03) 30%, rgba(99,102,241,0.1) 100%),
            radial-gradient(120% 70% at 18% -12%, rgba(255,255,255,0.14) 0%, rgba(255,255,255,0) 62%);
          opacity: 0.8;
          z-index: 0;
        }

        .chart-reflect::after {
          content: '';
          position: absolute;
          top: -35%;
          left: -25%;
          width: 65%;
          height: 140%;
          pointer-events: none;
          background: linear-gradient(112deg, transparent 0%, rgba(255,255,255,0.14) 48%, transparent 100%);
          transform: rotate(8deg);
          opacity: 0.45;
          z-index: 0;
        }
      `}</style>
    </div>
  )
}
