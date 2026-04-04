'use client'

import { 
  Plus, MessageSquare, LayoutDashboard, Terminal, 
  User, Settings, Puzzle, CreditCard, HelpCircle, 
  ChevronRight, Bookmark
} from 'lucide-react'
import { motion } from 'framer-motion'

interface SidebarItemProps {
  icon: any
  label: string
  active?: boolean
  onClick?: () => void
}

function SidebarItem({ icon: Icon, label, active, onClick }: SidebarItemProps) {
  return (
    <button 
      onClick={onClick}
      className={`w-full flex items-center justify-between px-3 py-2 rounded-xl transition-all group ${
        active 
          ? 'bg-white/5 text-white' 
          : 'text-white/40 hover:bg-white/[0.03] hover:text-white/70'
      }`}
    >
      <div className="flex items-center gap-3">
        <Icon size={18} className={active ? 'text-indigo-400' : 'text-current'} />
        <span className="text-sm font-medium tracking-tight font-inter">{label}</span>
      </div>
      {active && <div className="w-1.5 h-1.5 rounded-full bg-indigo-500 shadow-[0_0_8px_rgba(99,102,241,0.6)]" />}
    </button>
  )
}

export function ChatSidebar() {
  return (
    <aside className="w-64 h-full bg-[#0d0d10] border-r border-white/5 flex flex-col p-4 select-none">
      {/* Brand */}
      <div className="px-3 mb-8">
        <div className="flex items-center gap-2 mb-1">
          <div className="w-8 h-8 rounded-lg bg-indigo-600 flex items-center justify-center">
             <Terminal size={18} className="text-white" />
          </div>
          <span className="text-lg font-syne font-bold tracking-tight text-white/90">Starbot.ai</span>
        </div>
        <p className="text-[10px] font-mono text-white/20 uppercase tracking-[0.2em] ml-1">HERE FOR DATA</p>
      </div>

      {/* Primary Actions */}
      <div className="space-y-1 mb-10">
        <button className="w-full flex items-center gap-2 bg-indigo-600/10 hover:bg-indigo-600/20 text-indigo-400 border border-indigo-500/20 px-3 py-2.5 rounded-xl transition-all mb-4 group shadow-sm">
          <Plus size={18} className="transition-transform group-hover:rotate-90" />
          <span className="text-sm font-bold tracking-tight">New chat</span>
        </button>

        <SidebarItem icon={MessageSquare} label="Team chats" />
        <SidebarItem icon={LayoutDashboard} label="Dashboards" />
        <SidebarItem icon={Terminal} label="Prompt lab" />
        <SidebarItem icon={User} label="My Assistant" active />
      </div>

      {/* History Sections */}
      <div className="flex-1 overflow-y-auto space-y-8 pr-2 custom-scrollbar">
        {/* Pinned */}
        <div>
          <div className="px-3 mb-2 flex items-center gap-2 text-[10px] font-mono text-white/20 uppercase tracking-[0.2em] font-bold">
            <Bookmark size={10} />
            <span>Pinned chats</span>
          </div>
          <div className="space-y-0.5">
            {['Weekly Performance Sum...', 'Units sold last month', 'Trends Summary'].map(chat => (
              <button key={chat} className="w-full text-left px-3 py-1.5 rounded-lg text-[13px] text-white/30 hover:bg-white/[0.02] hover:text-white/60 transition-colors truncate">
                {chat}
              </button>
            ))}
          </div>
        </div>

        {/* Today */}
        <div>
           <div className="px-3 mb-2 text-[10px] font-mono text-white/20 uppercase tracking-[0.2em] font-bold">Today</div>
           <div className="space-y-0.5">
            {['Weekly Performance Sum...', 'APAC and EMEA sales', '2023 revenue'].map(chat => (
              <button key={chat} className="w-full text-left px-3 py-1.5 rounded-lg text-[13px] text-white/30 hover:bg-white/[0.02] hover:text-white/60 transition-colors truncate">
                {chat}
              </button>
            ))}
          </div>
        </div>

        {/* Yesterday */}
        <div>
           <div className="px-3 mb-2 text-[10px] font-mono text-white/20 uppercase tracking-[0.2em] font-bold">Yesterday</div>
           <div className="space-y-0.5">
            {['Operational Efficiency Rep...', 'Sales trend for Q2 this year', 'June summary', 'Forecast – July 2025'].map(chat => (
              <button key={chat} className="w-full text-left px-3 py-1.5 rounded-lg text-[13px] text-white/30 hover:bg-white/[0.02] hover:text-white/60 transition-colors truncate">
                {chat}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Footer Nav */}
      <div className="pt-4 mt-4 border-t border-white/5 space-y-1">
        <SidebarItem icon={Settings} label="Settings" />
        <SidebarItem icon={Puzzle} label="Integrations" />
        <SidebarItem icon={CreditCard} label="Subscription" />
        <SidebarItem icon={HelpCircle} label="Help & support" />
        
        <div className="px-3 mt-4 flex items-center justify-between">
           <span className="text-[10px] font-mono text-white/10 uppercase tracking-widest">ver. 1.1.2</span>
           <div className="w-1.5 h-1.5 rounded-full bg-emerald-500/50" />
        </div>
      </div>
    </aside>
  )
}
