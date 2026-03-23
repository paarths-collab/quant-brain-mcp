'use client'

import { useState } from 'react'
import Link from 'next/link'
import { usePathname } from 'next/navigation'

const navItems = [
  { label: 'Dashboard', href: '/dashboard' },
  { label: 'Global Markets', href: '/markets' },
  { label: 'Sectors', href: '/sectors' },
  { label: 'Technical Analysis', href: '/technical' },
  { label: 'Backtest', href: '/backtest' },
  { label: 'Peer Comparison', href: '/peers' },
  { label: 'News Box', href: '/news' },
  { label: 'Research', href: '/research' },
  { label: 'AI Chat', href: '/chat' },
  { label: 'Profile', href: '/profile' },
  { label: 'Settings', href: '/settings' },
]

export default function TerminalLayout({ children }: { children: React.ReactNode }) {
  const pathname = usePathname()
  const [collapsed, setCollapsed] = useState(false)

  return (
    <div className="flex h-screen bg-black text-white overflow-hidden font-mono">
      {/* Sidebar */}
      <aside
        className={`relative flex flex-col shrink-0 border-r border-white/20 bg-white/[0.03] backdrop-blur-2xl transition-all duration-300 ${collapsed ? 'w-[60px]' : 'w-[240px]'
          }`}
      >
        {/* Logo */}
        <div className="flex items-center gap-3 px-4 py-5 border-b border-white/20 h-[70px] shrink-0">
          <div className="w-8 h-8 rounded-lg bg-white/[0.06] border border-white/[0.12] flex items-center justify-center shrink-0 backdrop-blur-sm">
            <span className="font-dm-mono text-[12px] font-medium tracking-tight text-white/80">BQ</span>
          </div>
          {!collapsed && (
            <>
              <span className="font-dm-mono text-[11px] font-medium tracking-[0.22em] text-white/40 uppercase whitespace-nowrap overflow-hidden flex-1">
                Terminal
              </span>
              <button
                onClick={() => setCollapsed(true)}
                className="w-5 h-5 flex items-center justify-center text-white/25 hover:text-white/70 transition-colors text-[14px] font-light shrink-0"
                title="Collapse sidebar"
              >
                ×
              </button>
            </>
          )}
        </div>

        {/* Nav Items */}
        <nav className="flex flex-col gap-1 p-3 flex-1 overflow-y-auto">
          {navItems.map((item) => {
            const isActive = pathname === item.href
            return (
              <Link
                key={item.href}
                href={item.href}
                className={`group flex items-center gap-4 px-4 py-3 rounded-sm text-[14px] font-medium transition-all duration-150 ${isActive
                  ? 'bg-white/10 text-white'
                  : 'text-white/30 hover:text-white hover:bg-white/5'
                  }`}
                title={collapsed ? item.label : undefined}
              >
                {isActive && <div className="w-1.5 h-1.5 rounded-full bg-indigo-500 shrink-0" />}
                {!collapsed && <span className="truncate tracking-wider">{item.label.toUpperCase()}</span>}
                {collapsed && !isActive && <span className="w-1.5 h-1.5 rounded-full bg-white/10 shrink-0" />}
              </Link>
            )
          })}
        </nav>

        {/* System Status */}
        {!collapsed && (
          <div className="p-5 border-t border-white/20 space-y-2.5 bg-transparent">
            {[
              { label: 'System', value: 'ONLINE', highlight: true },
              { label: 'Risk Engine', value: 'READY', highlight: false },
              { label: 'Latency', value: '<24ms', highlight: true },
            ].map(s => (
              <div key={s.label} className="flex items-center justify-between">
                <span className="font-mono text-[9px] text-white/20 tracking-[0.2em] uppercase">{s.label}</span>
                <span className={`font-mono text-[9px] tracking-wider font-medium ${s.highlight ? 'text-indigo-400/70' : 'text-white/35'}`}>{s.value}</span>
              </div>
            ))}
          </div>
        )}

        {/* Expand button — only shown when collapsed */}
        {collapsed && (
          <button
            onClick={() => setCollapsed(false)}
            className="absolute -right-3 top-[80px] w-6 h-6 rounded-sm bg-black border border-white/20 flex items-center justify-center hover:bg-white/10 transition-colors z-10 text-[10px] font-bold"
          >
            &gt;
          </button>
        )}
      </aside>

      {/* Main Content */}
      <main className="flex-1 overflow-auto relative bg-black">
        {/* Top bar */}
        <header className="sticky top-0 z-20 flex items-center justify-between h-[70px] px-8 border-b border-white/20 bg-black/60 backdrop-blur-xl shrink-0">
          <div className="flex items-center gap-4">
            <div className="w-1 h-6 bg-indigo-500/50 rounded-full" />
            <span className="font-dm-mono text-[30px] font-medium text-white tracking-widest uppercase">
              {navItems.find(n => n.href === pathname)?.label ?? 'Intelligence Hub'}
            </span>
          </div>
          <div className="flex items-center gap-5 font-mono text-[10px] text-white/40 tracking-[0.2em] font-medium uppercase">
            <span>BQ_v2.0</span>
            <div className="w-px h-3 bg-white/10" />
            <div className="flex items-center gap-2">
              <div className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-[pulse_2s_ease-in-out_infinite] shadow-[0_0_8px_rgba(16,185,129,0.6)]" />
              <span className="text-white/30">LIVE_SECURE</span>
            </div>
          </div>
        </header>

        <div className="px-8 pt-4 pb-8 min-h-[calc(100vh-70px)]">
          {children}
        </div>
      </main>
    </div>
  )
}
