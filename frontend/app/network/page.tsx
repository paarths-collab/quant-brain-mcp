import { ArrowRight } from 'lucide-react'
import { FadeIn, GlassCard, StaggerContainer, StaggerItem } from '@/components/MotionComponents'
import SectionLabel from '@/components/SectionLabel'
import { networkData } from '@/lib/data'

const oeSteps = [
  { label: 'User Deposits', icon: '⬇', desc: 'Collateral sent to custodians' },
  { label: 'Custodians', icon: '🔐', desc: 'Off-exchange settlement' },
  { label: 'Mirror Positions', icon: '↔', desc: 'Delta-neutral hedging' },
  { label: 'Perp Exchanges', icon: '📊', desc: 'Funding rate capture' },
  { label: 'Yield to sUSDe', icon: '💰', desc: 'Distributed to stakers' },
]

export default function NetworkPage() {
  return (
    <div>
      {/* Header */}
      <div className="max-w-[1400px] mx-auto px-6 lg:px-10 pt-16 pb-16">
        <FadeIn>
          <SectionLabel>Network</SectionLabel>
          <h1 className="font-syne text-[clamp(32px,4vw,64px)] font-bold tracking-tight mt-5 mb-4 leading-tight">
            Institutional-grade<br />custody infrastructure
          </h1>
          <p className="text-[#888899] text-[15px] font-light max-w-[560px]">
            Ethena's security model uses off-exchange settlement via regulated custodians, eliminating counterparty risk entirely.
          </p>
        </FadeIn>

        {/* OES Architecture */}
        <FadeIn delay={0.1} className="mt-16">
          <GlassCard className="p-8 md:p-10">
            <h3 className="font-syne text-xl font-bold tracking-tight mb-2">How Off-Exchange Settlement Works</h3>
            <p className="text-[13px] text-[#888899] font-light mb-10 max-w-[480px]">
              Collateral is held with regulated custodians. Only net P&amp;L flows to exchanges — user funds are never at exchange risk.
            </p>
            <div className="flex flex-wrap items-center gap-3 lg:gap-4">
              {oeSteps.map((step, i) => (
                <div key={i} className="flex items-center gap-3 lg:gap-4">
                  <div className="text-center">
                    <div className="w-14 h-14 lg:w-16 lg:h-16 rounded-xl bg-accent/8 border border-accent/20 flex flex-col items-center justify-center mb-2 mx-auto">
                      <span className="text-xl">{step.icon}</span>
                    </div>
                    <p className="font-mono text-[9px] uppercase tracking-[0.08em] text-[#888899] max-w-[80px] text-center leading-tight">{step.label}</p>
                  </div>
                  {i < oeSteps.length - 1 && (
                    <ArrowRight className="w-4 h-4 text-[#333344] flex-shrink-0" />
                  )}
                </div>
              ))}
            </div>
          </GlassCard>
        </FadeIn>
      </div>

      {/* Custodian cards — horizontal scroll */}
      <div className="max-w-[1400px] mx-auto px-6 lg:px-10 pb-10">
        <FadeIn>
          <h2 className="font-syne text-2xl font-bold tracking-tight mb-6">Custodian Partners</h2>
        </FadeIn>
      </div>
      <div className="overflow-x-auto no-scrollbar pb-12 px-6 lg:px-10">
        <StaggerContainer className="flex gap-4 min-w-max">
          {networkData.map((custodian: any, i: number) => (
            <StaggerItem key={custodian.name}>
              <GlassCard className="p-7 w-[320px] flex-shrink-0 flex flex-col">
                <div className="flex items-center gap-3.5 mb-4">
                  <div className="w-10 h-10 rounded-xl bg-accent/10 border border-accent/20 flex items-center justify-center flex-shrink-0">
                    <span className="font-syne font-black text-sm text-accent2">{custodian.name[0]}</span>
                  </div>
                  <div>
                    <p className="font-syne font-bold text-base tracking-tight">{custodian.name}</p>
                    <span className="font-mono text-[10px] uppercase tracking-[0.08em] text-accent2 bg-accent/10 px-2 py-0.5 rounded-full">
                      {custodian.type}
                    </span>
                  </div>
                </div>
                <p className="text-[13px] text-[#888899] font-light leading-relaxed flex-1">{custodian.desc}</p>
                <div className="grid grid-cols-2 gap-2.5 mt-5">
                  {[
                    { v: custodian.tvl, l: 'AUM' },
                    { v: custodian.chains.toString(), l: 'Chains' },
                  ].map(({ v, l }: any) => (
                    <div key={l} className="bg-black/30 border border-white/[0.07] rounded-xl p-3.5">
                      <p className="font-mono text-lg font-medium">{v}</p>
                      <p className="font-mono text-[10px] uppercase tracking-[0.08em] text-[#555566] mt-0.5">{l}</p>
                    </div>
                  ))}
                </div>
                <div className="flex items-center gap-2 mt-4 font-mono text-[11px] text-[#4ade80]">
                  <span className="w-1.5 h-1.5 rounded-full bg-[#4ade80] animate-pulse" />
                  Uptime: {custodian.uptime}
                </div>
              </GlassCard>
            </StaggerItem>
          ))}
        </StaggerContainer>
      </div>

      {/* Risk section */}
      <div className="max-w-[1400px] mx-auto px-6 lg:px-10 pb-24">
        <FadeIn>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {[
              { title: 'No Exchange Counterparty Risk', desc: 'Collateral never sits on a centralized exchange. OES architecture eliminates the FTX-style risk entirely.', icon: '🛡' },
              { title: 'Multi-Custodian Redundancy', desc: 'Assets are distributed across 6+ regulated custodians. No single point of failure in the custody stack.', icon: '🔀' },
              { title: 'Real-Time On-Chain Proof', desc: 'All positions and collateral are verifiable on-chain at any time. Full transparency, no trust required.', icon: '🔍' },
            ].map((item) => (
              <GlassCard key={item.title} className="p-7">
                <span className="text-2xl mb-4 block">{item.icon}</span>
                <h4 className="font-syne text-base font-bold tracking-tight mb-2">{item.title}</h4>
                <p className="text-[13px] text-[#888899] font-light leading-relaxed">{item.desc}</p>
              </GlassCard>
            ))}
          </div>
        </FadeIn>
      </div>
    </div>
  )
}
