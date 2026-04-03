'use client'

import { useState, useRef, useEffect, useCallback } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import {
  Terminal, Send, Loader2, GripVertical,
  TrendingUp, BarChart3, AlertTriangle, Activity, Globe
} from 'lucide-react'
import { getWsUrl, stockAdvisorAPI, superAgentAPI, type SuperAgentResponse } from '@/lib/api'
import { MessageBubble, AnalysisRack, type Message, type RackSnapshot, type ChartPoint } from '@/components/ChatComponents'

const WS_URL = getWsUrl('/ws/live')

// ─── Types & Constants ───────────────────────────────────────────────────────
const uid = () => Math.random().toString(36).slice(2)

const DEFAULT_RACK_SNAPSHOT: RackSnapshot = {
  ticker: 'NVDA',
  strategyName: 'Neural Momentum Strategy',
  equityData: Array.from({ length: 40 }, (_, i) => ({
    x: i,
    v: 11000 + Math.sin(i / 4) * 1200 + i * 180,
  })),
  totalReturn: 64.2,
  sharpe: 2.14,
  winRate: 68.5,
  monteData: Array.from({ length: 50 }, (_, i) => {
    const x = (i - 25) / 10
    return { x: i, v: Math.exp(-(x * x) / 2) * 100 }
  }),
  var95: -4.2,
  expected: 9.5,
  best95: 22.4,
  riskVar99: 6.2,
  riskCvar: 9.4,
  riskMaxDd: 14.8,
}

const QUICK_COMMANDS = [
  { cmd: 'analyze NVDA', icon: TrendingUp, label: 'Analyze NVDA' },
  { cmd: 'backtest TSLA momentum strategy', icon: BarChart3, label: 'Backtest TSLA' },
  { cmd: 'risk analysis for my portfolio', icon: AlertTriangle, label: 'Risk Analysis' },
  { cmd: 'detect current market regime', icon: Activity, label: 'Market Regime' },
  { cmd: 'optimal portfolio AI tech sector', icon: Globe, label: 'Optimizer' },
]

// ─── Helper Functions ────────────────────────────────────────────────────────
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

const getMarketFromTicker = (ticker: string) => {
  const clean = ticker.toUpperCase()
  if (clean.endsWith('.NS') || clean.endsWith('.BO')) return 'IN'
  return 'US'
}

const formatAgentSection = (title: string, payload: Record<string, unknown> | undefined) => {
  if (!payload) return ''
  const verdict = typeof payload.verdict === 'string' ? payload.verdict : 'HOLD'
  const confidence = typeof payload.confidence === 'number' ? payload.confidence : null
  const provider = typeof payload.provider === 'string' ? payload.provider : ''
  const reasoning = typeof payload.reasoning === 'string' ? payload.reasoning : ''
  const factors = Array.isArray(payload.key_factors) ? payload.key_factors.filter((item): item is string => typeof item === 'string') : []

  const lines = [
    `**${title}:** ${verdict}${provider ? ` from ${provider}` : ''}${confidence !== null ? ` with ${(confidence * 100).toFixed(0)}% confidence` : ''}.`,
    reasoning ? reasoning : '',
    factors.length ? `Key factors: ${factors.join('; ')}.` : '',
  ].filter(Boolean)

  return lines.join(' ')
}

const formatMultiPovContent = (data: SuperAgentResponse | Record<string, unknown>) => {
  const symbol = typeof data.symbol === 'string' ? data.symbol : 'UNKNOWN'
  const bull = data.bull && typeof data.bull === 'object' ? (data.bull as Record<string, unknown>) : undefined
  const bear = data.bear && typeof data.bear === 'object' ? (data.bear as Record<string, unknown>) : undefined
  const neutral = data.neutral && typeof data.neutral === 'object' ? (data.neutral as Record<string, unknown>) : undefined

  return [
    `## Bull / Bear / Neutral Debates`,
    `**Symbol:** ${symbol}`,
    '',
    formatAgentSection('Bull verdict', bull),
    '',
    formatAgentSection('Bear verdict', bear),
    '',
    formatAgentSection('Neutral verdict', neutral),
  ].filter(Boolean).join('\n\n')
}

const looksLikeMultiPovQuery = (query: string) => !!parseTickerFromQuery(query)

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

// ─── Main Component ──────────────────────────────────────────────────────────
export default function ChatPage() {
  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [wsConnected, setWsConnected] = useState(false)
  const [rackWidth, setRackWidth] = useState(480)
  const [isResizing, setIsResizing] = useState(false)
  const [rackSnapshot, setRackSnapshot] = useState<RackSnapshot>(DEFAULT_RACK_SNAPSHOT)

  const scrollRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLInputElement>(null)
  const wsRef = useRef<WebSocket | null>(null)
  const lastQueryRef = useRef('')

  useEffect(() => {
    if (scrollRef.current) {
        scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages])

  useEffect(() => { inputRef.current?.focus() }, [])

  // Resizer logic 
  const handleMouseDown = (e: React.MouseEvent) => {
    setIsResizing(true)
    document.body.style.cursor = 'col-resize'
    e.preventDefault()
  };

  useEffect(() => {
    const handleMouseMove = (e: MouseEvent) => {
      if (!isResizing) return;
      const newWidth = window.innerWidth - e.clientX - 40;
      if (newWidth > 320 && newWidth < 800) {
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

    const ticker = parseTickerFromQuery(query.trim())
    const shouldUseMultiPov = Boolean(ticker && looksLikeMultiPovQuery(query.trim()))

    if (shouldUseMultiPov) {
      try {
        const response = await stockAdvisorAPI.multiPov({
          symbol: ticker!,
          market: getMarketFromTicker(ticker!),
          context: query.trim(),
        })
        const content = formatMultiPovContent(response as SuperAgentResponse)
        setMessages(prev => {
          const filtered = prev.filter(m => !m.isStreaming)
          return [...filtered, { id: uid(), role: 'assistant', content, timestamp: new Date() }]
        })
      } catch (err) {
        const reason = err instanceof Error && err.message ? err.message : 'Pipeline Disruption'
        setMessages(prev => {
          const filtered = prev.filter(m => !m.isStreaming)
          return [...filtered, {
            id: uid(), role: 'assistant',
            content: `⚠️ **System Error** — ${reason}`,
            timestamp: new Date()
          }]
        })
      } finally {
        setIsLoading(false)
      }
      return
    }

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
      } catch {
        setIsLoading(false)
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
    <div className="flex flex-col h-[calc(100vh-20px)] overflow-hidden bg-transparent select-none">
      <div className="flex-1 flex min-h-0 relative z-10 overflow-hidden px-4 pt-4">
        
        {/* Messages Pane */}
        <div className="flex-1 min-w-0 flex flex-col relative overflow-hidden">
          <div ref={scrollRef} className="flex-1 overflow-y-auto pr-6 custom-scrollbar scroll-smooth">
            <AnimatePresence mode="popLayout">
              {messages.length === 0 ? (
                <motion.div 
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, scale: 0.95 }}
                  className="flex flex-col items-center justify-center h-full max-w-2xl mx-auto"
                >
                  <div className="flex flex-col items-center gap-6 mb-16 text-center">
                    <div className="relative group">
                      <div className="w-24 h-24 rounded-[2rem] bg-gradient-to-br from-indigo-600/10 to-indigo-500/5 border border-white/10 flex items-center justify-center backdrop-blur-3xl transition-transform duration-500 group-hover:scale-110">
                        <Terminal size={36} className="text-indigo-400" />
                        <div className="absolute inset-0 rounded-[2rem] bg-indigo-500/20 blur-3xl opacity-0 group-hover:opacity-100 transition-opacity" />
                      </div>
                      <div className="absolute -inset-4 bg-indigo-500/5 blur-2xl rounded-full -z-10 animate-pulse" />
                    </div>
                    <div>
                      <h2 className="text-3xl font-syne font-extrabold text-white/90 tracking-tight mb-2">NEURAL_TERMINAL</h2>
                      <p className="text-[12px] font-mono text-white/20 uppercase tracking-[0.4em]">Decentralized Quant Intelligence Unit</p>
                    </div>
                  </div>
                  
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 w-full">
                    {QUICK_COMMANDS.map((qc, i) => {
                      const Icon = qc.icon
                      return (
                        <motion.button
                          key={qc.cmd}
                          initial={{ opacity: 0, y: 10 }}
                          animate={{ opacity: 1, y: 0 }}
                          transition={{ delay: 0.4 + (i * 0.05) }}
                          onClick={() => sendMessage(qc.cmd)}
                          className="flex items-center justify-between p-5 bg-white/[0.02] hover:bg-indigo-500/10 border border-white/5 hover:border-indigo-500/30 rounded-2xl transition-all group backdrop-blur-2xl"
                        >
                          <div className="flex items-center gap-4">
                            <div className="p-2 rounded-lg bg-white/5 group-hover:bg-indigo-500/20 transition-colors">
                              <Icon size={14} className="text-white/40 group-hover:text-indigo-400" />
                            </div>
                            <span className="text-[11px] font-mono text-white/30 group-hover:text-white/80 transition-colors uppercase tracking-widest leading-relaxed text-left">{qc.label}</span>
                          </div>
                          <motion.div 
                            whileHover={{ scale: 1.1 }}
                            className="text-[10px] font-mono text-indigo-500/0 group-hover:text-indigo-400/100 transition-all font-bold tracking-tighter"
                          >
                            RUN_EXEC
                          </motion.div>
                        </motion.button>
                      )
                    })}
                  </div>
                </motion.div>
              ) : (
                <div className="py-6 space-y-2 max-w-4xl mx-auto w-full">
                  {messages.map(msg => <MessageBubble key={msg.id} msg={msg} />)}
                </div>
              )}
            </AnimatePresence>
          </div>

          {/* Premium Floating Command Bar */}
          <div className="relative pt-6 pb-8 mr-6">
            <div className="absolute inset-x-0 bottom-full h-24 bg-gradient-to-t from-background to-transparent pointer-events-none z-10" />
            
            <form onSubmit={handleSubmit} className="relative z-20">
              <motion.div 
                layout
                className="group relative flex items-center gap-4 bg-[#0d0d10]/80 border border-white/10 focus-within:border-indigo-500/40 rounded-[1.5rem] px-6 py-4 transition-all backdrop-blur-3xl shadow-[0_20px_50px_rgba(0,0,0,0.5)]"
              >
                <div className="flex items-center gap-2 shrink-0">
                  <div className={`w-2 h-2 rounded-full ${wsConnected ? 'bg-emerald-500 shadow-[0_0_8px_rgba(16,185,129,0.5)]' : 'bg-red-500 shadow-[0_0_8px_rgba(239,68,68,0.5)]'} animate-pulse`} />
                  <span className="text-indigo-500/80 font-mono text-[11px] font-bold tracking-widest hidden sm:block">SYS_PROMPT</span>
                  <span className="text-white/10 font-mono text-sm ml-1 select-none">|</span>
                </div>
                
                <input
                  ref={inputRef}
                  type="text"
                  value={input}
                  onChange={e => setInput(e.target.value)}
                  placeholder="DEPLOY INTEL COMMAND..."
                  className="flex-1 bg-transparent text-white placeholder:text-white/10 font-mono text-[13px] focus:outline-none tracking-[0.1em] placeholder:tracking-widest uppercase"
                  disabled={isLoading}
                />

                <div className="flex items-center gap-2">
                   <span className="hidden md:block text-[9px] font-mono text-white/10 uppercase tracking-widest mr-2">ENTER_TO_EXEC</span>
                   <button
                    type="submit"
                    disabled={!input.trim() || isLoading}
                    className="shrink-0 w-12 h-12 rounded-2xl bg-indigo-600/10 hover:bg-indigo-600/30 disabled:opacity-20 flex items-center justify-center border border-indigo-500/30 transition-all shadow-[0_0_15px_rgba(79,70,229,0.1)] group-hover:shadow-[0_0_20px_rgba(79,70,229,0.2)]"
                  >
                    {isLoading
                      ? <Loader2 size={18} className="text-indigo-400 animate-spin" />
                      : <Send size={18} className="text-indigo-400 group-hover:translate-x-0.5 group-hover:-translate-y-0.5 transition-transform" />}
                  </button>
                </div>

                {/* Inner Glow focus effect */}
                <div className="absolute inset-0 rounded-[1.5rem] bg-indigo-500/5 opacity-0 group-focus-within:opacity-100 pointer-events-none transition-opacity" />
              </motion.div>
              
              <div className="mt-3 px-6 flex justify-between items-center">
                <div className="flex gap-4">
                  <span className="text-[9px] font-mono text-white/5 uppercase tracking-[0.2em]">{messages.length} NODES_IN_THREAD</span>
                  <span className="text-[9px] font-mono text-white/5 uppercase tracking-[0.2em]">LATENCY: 12ms</span>
                </div>
                <div className="text-[9px] font-mono text-white/5 uppercase tracking-[0.2em]">CORE_AUTH: LEVEL_4</div>
              </div>
            </form>
          </div>
        </div>

        {/* Dynamic Resizer Handle */}
        <div 
          onMouseDown={handleMouseDown}
          className={`group relative w-2 bg-transparent hover:bg-indigo-500/30 cursor-col-resize transition-all shrink-0 flex items-center justify-center z-30 ${isResizing ? 'bg-indigo-500/50 w-3' : ''}`}
        >
          <div className="absolute h-1/2 w-px bg-white/5 group-hover:bg-indigo-500/40" />
          <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-6 h-10 bg-black/60 border border-white/10 rounded-xl flex items-center justify-center backdrop-blur-xl group-hover:border-indigo-500/40 transition-all opacity-0 group-hover:opacity-100">
             <GripVertical size={12} className="text-white/20 group-hover:text-indigo-400/50" />
          </div>
        </div>

        {/* Right Panel: Enhanced Rack */}
        <motion.div 
          layout
          className="hidden xl:block shrink-0 h-full border-l border-white/5 pl-8 bg-black/10 backdrop-blur-3xl overflow-hidden"
          style={{ width: `${rackWidth}px` }}
        >
          <AnalysisRack snapshot={rackSnapshot} />
        </motion.div>
      </div>
      
      <style jsx global>{`
        .custom-scrollbar::-webkit-scrollbar {
          width: 5px;
        }
        .custom-scrollbar::-webkit-scrollbar-track {
          background: transparent;
        }
        .custom-scrollbar::-webkit-scrollbar-thumb {
          background: rgba(255, 255, 255, 0.03);
          border-radius: 10px;
          border: 1px solid rgba(255, 255, 255, 0.05);
        }
        .custom-scrollbar::-webkit-scrollbar-thumb:hover {
          background: rgba(99, 102, 241, 0.2);
          border-color: rgba(99, 102, 241, 0.3);
        }

        /* Specific typography overrides for premium feel */
        .prose strong { color: #fff; font-weight: 700; }
        .prose h2, .prose h3 { color: #818cf8; letter-spacing: -0.02em; font-family: 'Syne', sans-serif; }
      `}</style>
    </div>
  )
}
