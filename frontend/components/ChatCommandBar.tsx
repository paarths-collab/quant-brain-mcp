'use client'

import { Plus, Activity, ShieldAlert, Users, ArrowRight, Loader2, PieChart, Globe, MessageSquare } from 'lucide-react'
import { motion } from 'framer-motion'

interface ChatCommandBarProps {
  input: string
  setInput: (v: string) => void
  onSubmit: (e: React.FormEvent) => void
  onAction?: (query: string) => void
  isLoading?: boolean
}

export function ChatCommandBar({ input, setInput, onSubmit, onAction, isLoading }: ChatCommandBarProps) {
  
  const actions = [
    { label: 'Backtest Strategy', icon: Activity, query: 'Run a backtest for NVDA' },
    { label: 'Risk Simulation', icon: ShieldAlert, query: 'Show me a risk simulation for my portfolio' },
    { label: 'Agent Consensus', icon: Users, query: 'What is the agent consensus on TSLA?' },
    { label: 'Sector Analysis', icon: PieChart, query: 'Analyze the current performance of the Tech sector' },
    { label: 'Macro Intel', icon: Globe, query: 'Show me the latest macro economic indicators' },
    { label: 'Sentiment Audit', icon: MessageSquare, query: 'What is the Reddit and News sentiment for AAPL?' },
  ]

  const handleActionClick = (query: string) => {
    if (onAction) {
      onAction(query)
    } else {
      setInput(query)
    }
  }

  return (
    <form onSubmit={onSubmit} className="relative w-full max-w-4xl mx-auto group">
      <div className="relative flex flex-col items-center gap-4 bg-black/80 border border-white/10 focus-within:border-white/20 rounded-[2.5rem] px-8 py-6 transition-all backdrop-blur-3xl shadow-[0_30px_70px_rgba(0,0,0,0.4)]">
        
        {/* Placeholder / Input Area */}
        <div className="w-full relative">
          <input 
            type="text"
            value={input}
            onChange={e => setInput(e.target.value)}
            placeholder="Ask anything about markets, strategies, or risk..."
            className="w-full bg-transparent text-white placeholder:text-white/20 text-lg font-medium focus:outline-none tracking-tight py-2"
          />
        </div>

        {/* Action Buttons Row - Scrollable for more functionality */}
        <div className="w-full flex items-center justify-between mt-2 pt-2 border-t border-white/5 overflow-hidden">
          <div className="flex items-center gap-3 overflow-x-auto no-scrollbar pb-1 max-w-[calc(100%-60px)]">
             <button type="button" className="shrink-0 w-8 h-8 rounded-full border border-white/10 flex items-center justify-center text-white/40 hover:bg-white/5 transition-all">
                <Plus size={16} />
             </button>
             
             {actions.map((action, idx) => (
               <button 
                key={idx}
                type="button" 
                onClick={() => handleActionClick(action.query)}
                className="shrink-0 flex items-center gap-2 px-3 py-1.5 rounded-full border border-white/10 text-white/40 hover:bg-white/5 hover:text-white/60 transition-all text-xs font-semibold"
               >
                  <action.icon size={14} />
                  <span>{action.label}</span>
               </button>
             ))}
          </div>

          <div className="flex items-center gap-3 ml-4">
             <button 
               type="submit" 
               disabled={!input.trim() || isLoading}
               className="w-10 h-10 rounded-full bg-white text-black flex items-center justify-center hover:bg-white/90 disabled:opacity-30 disabled:hover:bg-white transition-all shadow-[0_0_20px_rgba(255,255,255,0.2)]"
             >
                {isLoading 
                  ? <Loader2 size={18} className="animate-spin text-black/50" /> 
                  : <ArrowRight size={18} strokeWidth={3} />}
             </button>
          </div>
        </div>

        {/* Inner Glow effect */}
        <div className="absolute inset-0 rounded-[2.5rem] bg-white/[0.01] pointer-events-none group-focus-within:bg-white/[0.02] transition-colors" />
      </div>

      {/* Floating Indicators */}
      <div className="mt-6 flex justify-center gap-8 px-6 opacity-0 group-focus-within:opacity-100 transition-opacity">
         <span className="text-[10px] font-mono text-white/10 uppercase tracking-widest font-bold">⌘ K COMMAND_MENU</span>
         <span className="text-[10px] font-mono text-white/10 uppercase tracking-widest font-bold">ALT 2 INTEGRATE_SOURCE</span>
      </div>
    </form>
  )
}
