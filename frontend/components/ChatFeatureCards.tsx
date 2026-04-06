'use client'

import { Play, ShieldAlert, Cpu, ChevronRight } from 'lucide-react'
import { motion } from 'framer-motion'

interface FeatureCardProps {
  icon: any
  title: string
  description: string
  query: string
  delay?: number
  onSelect: (query: string) => void
}

function FeatureCard({ icon: Icon, title, description, query, delay = 0, onSelect }: FeatureCardProps) {
  return (
    <motion.div 
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: 0.8 + delay, duration: 0.6, ease: [0.23, 1, 0.32, 1] }}
      whileHover={{ y: -5, scale: 1.02 }}
      onClick={() => onSelect(query)}
      className="group relative h-48 bg-[#1a1a1c]/40 border border-white/5 hover:border-white/10 rounded-[2rem] p-8 flex flex-col justify-between transition-all cursor-pointer overflow-hidden backdrop-blur-2xl"
    >
      <div className="flex items-start justify-between">
         <div className="w-12 h-12 rounded-2xl bg-white/5 flex items-center justify-center text-white/30 group-hover:bg-white/10 transition-colors">
            <Icon size={24} />
         </div>
         <ChevronRight size={18} className="text-white/10 group-hover:translate-x-1 group-hover:text-white/40 transition-all" />
      </div>
      
      <div>
         <h4 className="text-base font-bold text-white/90 mb-1 group-hover:text-white transition-colors">{title}</h4>
         <p className="text-[13px] text-white/20 group-hover:text-white/40 transition-colors leading-relaxed font-medium line-clamp-2">{description}</p>
      </div>

      {/* Decorative gradient */}
      <div className="absolute -bottom-10 -right-10 w-24 h-24 bg-white/5 blur-3xl rounded-full opacity-0 group-hover:opacity-100 transition-opacity" />
    </motion.div>
  )
}

interface ChatFeatureCardsProps {
  onSelect: (query: string) => void
}

export function ChatFeatureCards({ onSelect }: ChatFeatureCardsProps) {
  return (
    <div className="grid grid-cols-1 md:grid-cols-3 gap-6 w-full max-w-5xl mx-auto px-6">
      <FeatureCard 
        icon={Play}
        title="Backtest Portfolio"
        description="Run high-precision backtests on your equity holdings and strategies."
        query="Run a backtest for NVDA"
        onSelect={onSelect}
        delay={0}
      />
      <FeatureCard 
        icon={ShieldAlert}
        title="Risk Simulation"
        description="Stress test your portfolio against global market regimes and volatility."
        query="Show me a risk simulation for my portfolio"
        onSelect={onSelect}
        delay={0.1}
      />
      <FeatureCard 
        icon={Cpu}
        title="Alpha Discovery"
        description="Identify non-correlated alpha sources using Multi-Agent AI consensus."
        query="Discover new alpha sources in the tech sector"
        onSelect={onSelect}
        delay={0.2}
      />
    </div>
  )
}
