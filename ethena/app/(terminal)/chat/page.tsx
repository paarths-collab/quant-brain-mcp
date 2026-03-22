'use client'

import { useState, useRef, useEffect, useCallback } from 'react'
import {
  Terminal, Cpu, Send, Loader2, Copy, Check, X,
  TrendingUp, BarChart3, AlertTriangle, Activity,
  Zap, Globe, User, Maximize2, Minimize2
} from 'lucide-react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000'
const WS_URL = process.env.NEXT_PUBLIC_WS_URL ?? 'ws://localhost:8000/ws/agent'

// ─── Types ───────────────────────────────────────────────────────────────────
interface Message {
  id: string
  role: 'user' | 'assistant'
  content: string
  timestamp: Date
  isStreaming?: boolean
}

const uid = () => Math.random().toString(36).slice(2)

function MessageBubble({ msg }: { msg: Message }) {
  const isUser = msg.role === 'user'
  const [copied, setCopied] = useState(false)

  const handleCopy = () => {
    navigator.clipboard.writeText(msg.content)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  return (
    <div className={`flex gap-3 mb-5 group ${isUser ? 'flex-row-reverse' : ''}`}>
      {/* Avatar */}
      <div className={`w-7 h-7 rounded-lg flex items-center justify-center shrink-0 border ${
        isUser
          ? 'bg-white/[0.04] border-white/[0.08]'
          : 'bg-orange-500/10 border-orange-500/20'
      }`}>
        {isUser
          ? <Terminal size={13} className="text-white/50" />
          : <Cpu size={13} className="text-orange-400 animate-pulse" />}
      </div>

      {/* Bubble */}
      <div className={`flex-1 max-w-[78%]`}>
        <div className={`flex items-center gap-2 mb-1.5 ${isUser ? 'justify-end' : ''}`}>
          <span className="text-[10px] font-mono text-white/25 tracking-widest">
            {isUser ? 'USER' : 'AGENT@BLOOMBERG-QUANT'}
          </span>
          <span className="text-[10px] font-mono text-white/15">
            {msg.timestamp.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })}
          </span>
          {!isUser && (
            <button onClick={handleCopy} className="opacity-0 group-hover:opacity-60 hover:opacity-100 transition-opacity ml-auto">
              {copied ? <Check size={10} className="text-emerald-400" /> : <Copy size={10} className="text-white/40" />}
            </button>
          )}
        </div>

        <div className={`rounded-xl px-4 py-3 text-sm border ${
          isUser
            ? 'bg-white/[0.04] border-white/[0.08] text-white/80 font-mono'
            : 'bg-[#0d0d0d] border-white/[0.06] text-white/90'
        }`}>
          {msg.isStreaming ? (
            <div className="flex items-center gap-2 text-orange-400">
              <div className="flex gap-1">
                {[0, 1, 2].map(i => (
                  <div key={i} className="w-1.5 h-1.5 bg-orange-400 rounded-full animate-pulse" style={{ animationDelay: `${i * 200}ms` }} />
                ))}
              </div>
              <span className="text-xs font-mono">Processing...</span>
            </div>
          ) : (
            <div className="prose prose-invert prose-sm max-w-none
              prose-code:text-orange-400 prose-code:bg-orange-500/10 prose-code:px-1.5 prose-code:py-0.5 prose-code:rounded prose-code:border prose-code:border-orange-500/20
              prose-table:w-full prose-th:border prose-th:border-white/10 prose-th:bg-white/[0.04] prose-th:p-2 prose-th:text-left prose-th:text-white/60 prose-th:text-xs
              prose-td:border prose-td:border-white/[0.06] prose-td:p-2 prose-td:text-white/70 prose-td:text-xs
              prose-headings:text-white prose-strong:text-white prose-p:text-white/80">
              <ReactMarkdown remarkPlugins={[remarkGfm]}>{msg.content}</ReactMarkdown>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

// Quick commands shown on empty state
const QUICK_COMMANDS = [
  { cmd: 'analyze NVDA', icon: TrendingUp, label: 'Analyze NVDA' },
  { cmd: 'backtest TSLA momentum strategy', icon: BarChart3, label: 'Backtest TSLA' },
  { cmd: 'risk analysis for my portfolio', icon: AlertTriangle, label: 'Risk Analysis' },
  { cmd: 'detect current market regime', icon: Activity, label: 'Market Regime' },
  { cmd: 'optimal portfolio AI tech sector', icon: Globe, label: 'Portfolio Optimizer' },
]

// ─── Main Page ────────────────────────────────────────────────────────────────
export default function ChatPage() {
  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [wsConnected, setWsConnected] = useState(false)
  const scrollRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLInputElement>(null)
  const wsRef = useRef<WebSocket | null>(null)

  // Auto scroll
  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: 'smooth' })
  }, [messages])

  // Focus input
  useEffect(() => { inputRef.current?.focus() }, [])

  // WebSocket connection
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
      // HTTP fallback
      try {
        const res = await fetch(`${API_BASE}/api/super-agent`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ query: query.trim() }),
        })
        const data = await res.json()
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
            content: '⚠️ **Connection Error** — Backend unreachable. Make sure your Bloomberg Quant server is running on `localhost:8000`.',
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
    <div className="flex flex-col h-[calc(100vh-108px)]">
      {/* Header */}
      <div className="flex items-center justify-between mb-4 pb-4 border-b border-white/[0.06]">
        <div className="flex items-center gap-3">
          <div className="relative w-9 h-9 rounded-xl bg-orange-500/10 border border-orange-500/20 flex items-center justify-center">
            <Terminal size={16} className="text-orange-400" />
            <div className="absolute -inset-0.5 bg-orange-500/10 blur-md rounded-xl -z-10" />
          </div>
          <div>
            <h1 className="text-[15px] font-mono font-bold text-white tracking-wide">AI Command Interface</h1>
            <div className="flex items-center gap-2 mt-0.5">
              <div className={`w-1.5 h-1.5 rounded-full ${wsConnected ? 'bg-emerald-400 shadow-[0_0_6px_#34d399]' : 'bg-red-400'}`} />
              <span className="text-[10px] font-mono text-white/30 tracking-wider">
                {wsConnected ? 'WEBSOCKET LIVE' : 'HTTP FALLBACK'}
              </span>
            </div>
          </div>
        </div>
        {messages.length > 0 && (
          <button
            onClick={() => setMessages([])}
            className="flex items-center gap-1.5 px-3 py-1.5 text-[11px] font-mono text-white/30 hover:text-white/60 border border-white/[0.08] hover:border-white/[0.15] rounded-lg transition-all"
          >
            <X size={11} />
            Clear
          </button>
        )}
      </div>

      {/* Messages */}
      <div ref={scrollRef} className="flex-1 overflow-y-auto pr-1 scroll-smooth">
        {messages.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-full">
            <div className="relative mb-6">
              <div className="w-20 h-20 rounded-2xl bg-gradient-to-br from-orange-500/20 to-orange-900/10 border border-orange-500/20 flex items-center justify-center">
                <Terminal size={32} className="text-orange-400" />
              </div>
              <div className="absolute -inset-3 bg-orange-500/5 blur-2xl rounded-full -z-10" />
            </div>
            <h2 className="text-[15px] font-mono text-white/60 mb-2">Initiate Market Analysis</h2>
            <p className="text-[12px] font-mono text-white/25 mb-8 text-center max-w-sm">
              Ask any question about markets, request a backtest, analyze a ticker, or run a portfolio optimization.
            </p>
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-2 w-full max-w-2xl">
              {QUICK_COMMANDS.map(qc => {
                const Icon = qc.icon
                return (
                  <button
                    key={qc.cmd}
                    onClick={() => sendMessage(qc.cmd)}
                    className="flex items-center gap-2.5 p-3.5 bg-white/[0.02] hover:bg-white/[0.05] border border-white/[0.07] hover:border-orange-500/20 rounded-xl text-left transition-all group"
                  >
                    <Icon size={14} className="text-orange-400 shrink-0" />
                    <span className="text-[12px] font-mono text-white/50 group-hover:text-white/80 transition-colors">{qc.label}</span>
                  </button>
                )
              })}
            </div>
          </div>
        ) : (
          <div className="max-w-4xl mx-auto py-4">
            {messages.map(msg => <MessageBubble key={msg.id} msg={msg} />)}
          </div>
        )}
      </div>

      {/* Input */}
      <div className="pt-4 border-t border-white/[0.06]">
        <form onSubmit={handleSubmit}>
          <div className="flex items-center gap-2 bg-[#0d0d0d] border border-white/[0.08] focus-within:border-orange-500/30 rounded-xl px-4 py-3 transition-all">
            <span className="text-orange-500 font-mono text-sm shrink-0">&gt;</span>
            <input
              ref={inputRef}
              type="text"
              value={input}
              onChange={e => setInput(e.target.value)}
              placeholder="Enter ticker, command, or question..."
              className="flex-1 bg-transparent text-white placeholder:text-white/20 font-mono text-sm focus:outline-none"
              disabled={isLoading}
            />
            <button
              type="submit"
              disabled={!input.trim() || isLoading}
              className="shrink-0 w-8 h-8 rounded-lg bg-orange-500/20 hover:bg-orange-500/30 disabled:opacity-20 flex items-center justify-center border border-orange-500/20 transition-all"
            >
              {isLoading
                ? <Loader2 size={13} className="text-orange-400 animate-spin" />
                : <Send size={13} className="text-orange-400" />}
            </button>
          </div>
          <div className="flex justify-between mt-2 px-1">
            <span className="text-[10px] font-mono text-white/15">Bloomberg Quant Neural Engine v2.0</span>
            <span className="text-[10px] font-mono text-white/15">{messages.filter(m => m.role === 'user').length} queries this session</span>
          </div>
        </form>
      </div>
    </div>
  )
}
