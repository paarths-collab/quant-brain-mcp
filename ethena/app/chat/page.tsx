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
import { getWsUrl, superAgentAPI } from '@/lib/api'

const WS_URL = getWsUrl('/ws/live')

// ─── Types ───────────────────────────────────────────────────────────────────
interface Message {
  id: string
  role: 'user' | 'assistant'
  content: string
  timestamp: Date
  isStreaming?: boolean
}

const uid = () => Math.random().toString(36).slice(2)

// ─── Analytics Components ────────────────────────────────────────────────────
function AnalysisRack() {
  const equityData = Array.from({ length: 40 }, (_, i) => ({ 
    x: i, v: 10000 + Math.sin(i/5) * 1000 + i * 150 + Math.random() * 500 
  }))
  const monteCarloData = Array.from({ length: 50 }, (_, i) => {
    const x = (i - 25) / 10
    return { x: i, v: Math.exp(-(x * x) / 2) * 100 }
  })

  return (
    <div className="flex flex-col gap-4 h-full overflow-y-auto pr-2 custom-scrollbar pb-10">
      {/* Equity Curve */}
      <div className="p-5 rounded-2xl border border-white/20 bg-white/[0.03] backdrop-blur-xl">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-2">
            <TrendingUp size={14} className="text-indigo-400" />
            <span className="font-dm-mono text-[11px] text-white/40 uppercase tracking-[0.2em]">Backtest Equity Curve</span>
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
            <div className="text-[14px] font-dm-mono text-indigo-400 font-bold">+53.1%</div>
          </div>
          <div>
            <div className="text-[9px] font-dm-mono text-white/20 uppercase tracking-widest mb-1">SHARPE</div>
            <div className="text-[14px] font-dm-mono text-white font-bold">1.82</div>
          </div>
          <div>
            <div className="text-[9px] font-dm-mono text-white/20 uppercase tracking-widest mb-1">WIN RATE</div>
            <div className="text-[14px] font-dm-mono text-white/40">—%</div>
          </div>
        </div>
      </div>

      {/* Monte Carlo */}
      <div className="p-5 rounded-2xl border border-white/20 bg-white/[0.03] backdrop-blur-xl">
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
            { l: '5% VaR', v: '-5.0%', c: 'text-red-400' },
            { l: 'EXPECTED', v: '8.0%', c: 'text-indigo-400' },
            { l: '95% BEST', v: '18.0%', c: 'text-indigo-400' },
          ].map(s => (
            <div key={s.l}>
              <div className="text-[9px] font-dm-mono text-white/20 uppercase tracking-widest mb-1">{s.l}</div>
              <div className={`text-[12px] font-dm-mono font-bold ${s.c}`}>{s.v}</div>
            </div>
          ))}
        </div>
      </div>

      {/* Risk Analysis */}
      <div className="p-5 rounded-2xl border border-white/20 bg-white/[0.03] backdrop-blur-xl">
        <div className="flex items-center gap-2 mb-5">
           <AlertTriangle size={14} className="text-indigo-400" />
           <span className="font-dm-mono text-[11px] text-white/40 uppercase tracking-[0.2em]">Risk Analysis Rack</span>
        </div>
        <div className="space-y-6">
          {[
            { label: 'VaR_99', val: '5.00%' },
            { label: 'CVaR_EXPECTED', val: '8.00%' },
            { label: 'MAX_HISTORICAL_DD', val: '12.00%' },
          ].map(r => (
            <div key={r.label} className="flex flex-col gap-2">
              <div className="flex justify-between items-center text-[10px] uppercase font-dm-mono tracking-widest font-semibold">
                <span className="text-white/30">{r.label}</span>
                <span className="text-white">{r.val}</span>
              </div>
              <div className="h-2 bg-white/5 rounded-full overflow-hidden border border-white/10 p-[1.5px]">
                <div className="h-full bg-indigo-500/50 rounded-full shadow-[0_0_10px_rgba(99,102,241,0.3)] transition-all duration-1000" style={{ width: r.val }} />
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

  const scrollRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLInputElement>(null)
  const wsRef = useRef<WebSocket | null>(null)
  const containerRef = useRef<HTMLDivElement>(null)

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
      ws.onclose = () => setWsConnected(false)
      ws.onerror = () => setWsConnected(false)
      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data)
          const content = data.report || data.response || 'Analysis complete.'
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
    setMessages(prev => [...prev, userMsg, streamMsg])
    setInput('')
    setIsLoading(true)

    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ query: query.trim() }))
    } else {
      try {
        const data = await superAgentAPI.run({ query: query.trim() })
        const content = data.report || data.response || JSON.stringify(data)
        setMessages(prev => {
            const filtered = prev.filter(m => !m.isStreaming)
            return [...filtered, { id: uid(), role: 'assistant', content, timestamp: new Date() }]
        })
      } catch {
        setMessages(prev => {
          const filtered = prev.filter(m => !m.isStreaming)
          return [...filtered, {
            id: uid(), role: 'assistant',
            content: '⚠️ **Link_Lost** — Neural Bridge offline.',
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
          <AnalysisRack />
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
      `}</style>
    </div>
  )
}
