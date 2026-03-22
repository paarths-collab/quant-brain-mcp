'use client'

import { useState } from 'react'
import { ArrowUpRight } from 'lucide-react'
import { FadeIn, GlassCard, StaggerContainer, StaggerItem } from '@/components/MotionComponents'
import SectionLabel from '@/components/SectionLabel'
import { ecosystemData, ecosystemFilters } from '@/lib/data'

export default function EcosystemPage() {
  const [activeFilter, setActiveFilter] = useState('All')

  const filtered =
    activeFilter === 'All'
      ? ecosystemData
      : ecosystemData.filter((d) => d.type === activeFilter)

  return (
    <div>
      {/* Header */}
      <div className="max-w-[1400px] mx-auto px-6 lg:px-10 pt-16 pb-10">
        <FadeIn>
          <SectionLabel>Ecosystem</SectionLabel>
          <h1 className="font-syne text-[clamp(32px,4vw,64px)] font-bold tracking-tight mt-5 mb-3 leading-tight">
            Powering the on-chain economy
          </h1>
          <p className="text-[#888899] text-[15px] font-light max-w-[560px]">
            USDe and sUSDe are integrated across 200+ leading DeFi protocols, exchanges, and institutional venues.
          </p>
        </FadeIn>

        {/* Filter bar */}
        <FadeIn delay={0.1} className="mt-8">
          <div className="flex flex-wrap gap-2">
            {ecosystemFilters.map((f) => (
              <button
                key={f}
                onClick={() => setActiveFilter(f)}
                className={`px-4 py-2 rounded-lg text-[12.5px] font-medium border transition-all duration-200 ${
                  activeFilter === f
                    ? 'bg-accent/10 border-accent/40 text-accent2'
                    : 'bg-transparent border-white/[0.07] text-[#888899] hover:border-white/[0.18] hover:text-white'
                }`}
              >
                {f}
              </button>
            ))}
          </div>
        </FadeIn>
      </div>

      {/* Grid */}
      <div className="max-w-[1400px] mx-auto px-6 lg:px-10 pb-24">
        <StaggerContainer className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
          {filtered.map((item, i) => (
            <StaggerItem key={item.name}>
              <GlassCard className="p-5 cursor-pointer">
                <div className="flex items-center gap-3 mb-4">
                  <div
                    className="w-10 h-10 rounded-xl flex items-center justify-center border border-white/[0.07] flex-shrink-0"
                    style={{ background: `${item.color}18` }}
                  >
                    <span
                      className="font-syne font-black text-base"
                      style={{ color: item.color }}
                    >
                      {item.name[0]}
                    </span>
                  </div>
                  <div>
                    <p className="text-[14px] font-semibold tracking-tight">{item.name}</p>
                    <p className="font-mono text-[10px] uppercase tracking-[0.08em] text-[#555566] mt-0.5">
                      {item.type}
                    </p>
                  </div>
                </div>
                <div className="h-px bg-white/[0.06] mb-4" />
                <div className="flex items-end justify-between">
                  <div>
                    <p className="font-mono text-xl font-medium text-[#4ade80]">{item.apy}</p>
                    <p className="font-mono text-[10px] uppercase tracking-[0.08em] text-[#555566] mt-0.5">Est. APY</p>
                  </div>
                  <div className="w-7 h-7 rounded-lg bg-white/[0.04] border border-white/[0.07] flex items-center justify-center text-[#555566] hover:text-white hover:border-white/[0.2] transition-all">
                    <ArrowUpRight className="w-3.5 h-3.5" />
                  </div>
                </div>
              </GlassCard>
            </StaggerItem>
          ))}
        </StaggerContainer>
      </div>
    </div>
  )
}
