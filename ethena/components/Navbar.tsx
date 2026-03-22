'use client'

import { useState, useEffect } from 'react'
import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { ChevronDown, Box, Info } from 'lucide-react'
import { motion, AnimatePresence } from 'framer-motion'

export default function Navbar() {
  const pathname = usePathname()
  const [scrolled, setScrolled] = useState(false)
  const [hoveredLink, setHoveredLink] = useState<string | null>(null)

  // Hide Navbar on Terminal routes
  const terminalRoutes = ['/dashboard', '/chat', '/research', '/backtest', '/technical', '/portfolio']
  if (terminalRoutes.some(route => pathname?.startsWith(route))) return null

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 20)
    window.addEventListener('scroll', onScroll)
    return () => window.removeEventListener('scroll', onScroll)
  }, [])

  return (
    <div className="fixed top-6 left-0 right-0 z-50 flex justify-center px-4 w-full pointer-events-none">
      <nav
        className={`pointer-events-auto flex items-center justify-between h-[52px] rounded-full px-2 pl-4 pr-2 transition-all duration-300 w-full max-w-[1200px] border border-white/[0.08] ${scrolled
            ? 'bg-[#000000]/80 backdrop-blur-2xl shadow-[0_4px_30px_rgba(0,0,0,0.5)]'
            : 'bg-[#000000]/40 backdrop-blur-md'
          }`}
      >
        {/* Left: Logo */}
        <Link
          href="/"
          className="flex items-center gap-2 mr-8 hover:opacity-80 transition-opacity"
        >
          <div className="w-[22px] h-[22px] rounded bg-white/[0.1] text-white flex items-center justify-center text-[10px] border border-white/[0.1]">
            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M12 2L2 12l10 10 10-10L12 2z" /><path d="M12 12l-5-5" /></svg>
          </div>
          <span className="font-sans text-[15px] font-medium tracking-wide text-white uppercase">Bloomberg Quant</span>
        </Link>

        {/* Center: Nav links */}
        <div className="hidden lg:flex items-center h-full relative">
          {[
            { label: 'Agentic OS', hasDrop: false, href: '/' },
            { label: 'Quant Lab', hasDrop: true, href: '/backtest' },
            { label: 'Intelligence', hasDrop: false, href: '/research' },
            { label: 'Terminal', hasDrop: false, href: '/dashboard' },
            { label: 'Reports', hasDrop: false, href: '/portfolio' },
          ].map((link) => {
            const isActive = pathname === link.href
            return (
              <Link
                key={link.label}
                href={link.href}
                className="relative flex items-center h-full px-3.5 group"
                onMouseEnter={() => setHoveredLink(link.label)}
                onMouseLeave={() => setHoveredLink(null)}
              >
                <div className={`flex items-center gap-1.5 text-[13px] font-sans font-medium transition-colors duration-200 z-10 ${isActive ? 'text-white' : 'text-white/60 group-hover:text-white/90'
                  }`}>
                  {link.label}
                  {link.hasDrop && <ChevronDown className="w-3.5 h-3.5 opacity-50" />}
                </div>

                {isActive && (
                  <div className="absolute -bottom-[6px] left-1/2 -translate-x-1/2 w-8 h-[2px] bg-white/30 rounded-full blur-[2px]" />
                )}
              </Link>
            )
          })}
        </div>

        {/* Right: Data Pills & CTA */}
        <div className="flex items-center gap-2.5 ml-auto">
          {/* Data Pill */}
          <div className="hidden md:flex items-center h-[36px] rounded-full border border-white/[0.08] bg-white/[0.02] px-3 gap-3 text-[12px] font-mono text-white/70">

            <div className="flex items-center gap-1.5 hover:text-white transition-colors cursor-pointer">
              <span className="opacity-60 text-[10px] uppercase tracking-wider">Conf:</span>
              <span className="text-white">87.5%</span>
              <Info className="w-3.5 h-3.5 opacity-40 ml-0.5" />
            </div>

            <div className="w-px h-3.5 bg-white/10" />

            <div className="flex items-center gap-1.5 hover:text-white transition-colors cursor-pointer">
              <span className="opacity-60 text-[10px] uppercase tracking-wider">Lat:</span>
              <span className="text-white">&lt;150ms</span>
              <Info className="w-3.5 h-3.5 opacity-40 ml-0.5" />
            </div>

          </div>

          {/* Launch App Button */}
          <button className="h-[36px] px-5 rounded-full border border-white/[0.12] bg-transparent text-white text-[13px] font-medium hover:bg-white/[0.04] transition-colors ml-1">
            Launch App
          </button>
        </div>
      </nav>
    </div>
  )
}
