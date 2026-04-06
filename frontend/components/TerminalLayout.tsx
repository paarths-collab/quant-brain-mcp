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
        className={`relative flex flex-col shrink-0 border-r border-white/20 bg-black transition-all duration-300 [transform-style:preserve-3d] ${collapsed ? 'w-[60px]' : 'w-[240px]'
          }`}
        style={{ perspective: '1200px' }}
      >
        {/* 3D lighting layers removed for pure black */}

        {/* Logo */}
        <div className="relative z-10 flex items-center gap-3 px-4 py-5 border-b border-white/20 h-[70px] shrink-0">
          <div className="w-8 h-8 rounded-lg bg-white/[0.08] border border-white/[0.2] shadow-[0_10px_20px_rgba(0,0,0,0.45),inset_0_1px_0_rgba(255,255,255,0.25)] [transform:translateZ(18px)] flex items-center justify-center shrink-0 backdrop-blur-sm">
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
        <nav className="relative z-10 flex flex-col gap-1.5 p-3 flex-1 overflow-y-auto">
          {navItems.map((item) => {
            const isActive = pathname === item.href
            return (
              <Link
                key={item.href}
                href={item.href}
                className={`group relative flex items-center gap-4 px-4 py-3 rounded-md text-[14px] font-medium transition-all duration-200 will-change-transform ${isActive
                  ? 'text-white bg-white/[0.14] border border-white/[0.2] shadow-[0_8px_24px_rgba(0,0,0,0.45),inset_0_1px_0_rgba(255,255,255,0.2)] [transform:translateZ(16px)]'
                  : 'text-white/35 border border-transparent hover:text-white hover:bg-white/[0.08] hover:border-white/[0.12] hover:shadow-[0_6px_18px_rgba(0,0,0,0.3)] hover:[transform:translateZ(10px)]'
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
          <div className="relative z-10 p-5 border-t border-white/20 space-y-2.5 bg-transparent [transform:translateZ(12px)]">
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
            className="absolute -right-3 top-[80px] w-6 h-6 rounded-sm bg-black border border-white/20 shadow-[0_8px_16px_rgba(0,0,0,0.5)] [transform:translateZ(20px)] flex items-center justify-center hover:bg-white/10 transition-colors z-10 text-[10px] font-bold"
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

        <div className={`min-h-[calc(100vh-70px)] flex flex-col ${['/technical', '/chat'].includes(pathname) ? '' : 'px-8 pt-4 pb-8'}`}>
          {children}
        </div>
      </main>
    </div>
  )
}
