'use client'
import { useRef } from 'react'
import { ArrowRight, ExternalLink, Shield, Zap, Lock, BarChart3, TrendingUp, ArrowUpRight, PieChart, LineChart, ShieldCheck } from 'lucide-react'
import { motion, useInView, useScroll, useVelocity, useTransform, useSpring } from 'framer-motion'
import { FadeIn, GlassCard, StaggerContainer, StaggerItem } from '@/components/MotionComponents'
import SectionLabel from '@/components/SectionLabel'
import Globe from '@/components/Globe'
import { statsBar, apyData, onboardData, transparencyCards, transparencyStats, highlightsData, accessTiers } from '@/lib/data'

/* ─── SECTION GLOW ─── */
// A blue ambient glow orb at the top of each section.
// depth (0–1) controls how bright it glows — sections deeper in the page are more intense.
function SectionGlow({ depth = 0 }: { depth?: number }) {
  const ref = useRef(null)
  const isInView = useInView(ref, { once: false, margin: "-100px" })
  const baseOpacity = 0.12 + depth * 0.22   // 0.12 → 0.34 as depth increases
  const size = 600 + depth * 200             // glow gets wider deeper in page

  return (
    <motion.div
      ref={ref}
      initial={{ opacity: 0, scale: 0.7 }}
      animate={isInView ? { opacity: 1, scale: 1 } : { opacity: 0, scale: 0.7 }}
      transition={{ duration: 1.2, ease: [0.16, 1, 0.3, 1] }}
      className="pointer-events-none relative w-full flex justify-center overflow-hidden"
      style={{ height: 1, marginBottom: -1 }}
    >
      {isInView && (
        <div
          style={{
            position: 'absolute',
            top: 0,
            left: '50%',
            transform: 'translateX(-50%)',
            width: size,
            height: size * 0.55,
            background: `radial-gradient(ellipse at 50% 0%, rgba(59, 130, 246, ${baseOpacity}) 0%, rgba(99, 102, 241, ${baseOpacity * 0.5}) 35%, transparent 70%)`,
            filter: 'blur(2px)',
            pointerEvents: 'none',
          }}
        />
      )}
    </motion.div>
  )
}

/* ─── HERO ─── */

function HeroSection() {
  return (
    <section className="relative min-h-[92vh] flex items-center px-8 lg:px-16 max-w-[1400px] mx-auto overflow-hidden pt-28 pb-32">
      {/* Dot grid — defined in globals.css as .hero-grid-bg / .hero-grid-fade */}
      <div className="absolute inset-0 pointer-events-none hero-grid-bg hero-grid-fade opacity-100" />

      <div className="w-full grid grid-cols-1 lg:grid-cols-2 gap-8 items-center relative z-10">
        {/* Left */}
        <div className="relative z-20">
          <FadeIn delay={0.1}>
            <h1
              className="font-sans text-[clamp(44px,5vw,86px)] font-light tracking-[-0.02em] leading-[1.05] mb-6 text-white/90"
              style={{ fontWeight: 300 }}
            >
              The Intelligent Layer for<br />
              Quantitative Finance.
            </h1>
            <p className="text-[#888899] text-[clamp(15px,1.5vw,18px)] font-light max-w-[540px] leading-relaxed mb-10">
              Orchestrating a decentralized committee of AI Agents and institutional-grade mathematics to deliver explainable alpha and dynamic risk management.
            </p>
          </FadeIn>

          <FadeIn delay={0.2}>
            <div className="flex items-center gap-5">
              <button className="bg-white text-black px-7 py-3 rounded-full font-semibold text-sm hover:bg-gray-100 transition-all shadow-[0_0_30px_rgba(255,255,255,0.15)]">
                Deploy Agentic Pipeline
              </button>
              <button className="text-white/60 hover:text-white transition-colors text-sm font-medium">Explore Quant Models</button>
            </div>
          </FadeIn>
        </div>

        {/* Right: Globe — fills more of the right column, slightly cropped like screenshot */}
        <div className="hidden lg:flex justify-center items-center relative -top-16 z-0" style={{ marginRight: '-80px' }}>
          <Globe />
        </div>
      </div>

      {/* Stats bar pinned to bottom */}
      <div className="absolute bottom-0 left-0 right-0">
        <StatsBar />
      </div>
    </section>
  )
}

/* ─── STATS BAR ─── */
// Matching screenshot: icon + value + label layout, 6 columns
const STAT_ICONS = [
  // sUSDe APY — circular arrows
  <svg key="apy" className="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.5}><path d="M4 12a8 8 0 1 0 8-8" strokeLinecap="round" /><path d="M4 8v4h4" strokeLinecap="round" strokeLinejoin="round" /></svg>,
  // Avg sUSDe APY — scales
  <svg key="avg" className="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.5}><path d="M12 3v2m0 0L8 9m4-4 4 4M5 14l3-5 3 5H5zm8 0 3-5 3 5h-6zM3 19h18" strokeLinecap="round" strokeLinejoin="round" /></svg>,
  // USDe Supply — dollar
  <svg key="usde" className="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.5}><circle cx="12" cy="12" r="9" /><path d="M12 7v10M9.5 9.5A2.5 2.5 0 0 1 12 8h.5a2.5 2.5 0 0 1 0 5h-1a2.5 2.5 0 0 0 0 5h.5a2.5 2.5 0 0 0 2.5-2.5" strokeLinecap="round" /></svg>,
  // USDtb Supply — dollar
  <svg key="usdtb" className="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.5}><circle cx="12" cy="12" r="9" /><path d="M12 7v10M9.5 9.5A2.5 2.5 0 0 1 12 8h.5a2.5 2.5 0 0 1 0 5h-1a2.5 2.5 0 0 0 0 5h.5a2.5 2.5 0 0 0 2.5-2.5" strokeLinecap="round" /></svg>,
  // Users — person
  <svg key="users" className="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.5}><circle cx="12" cy="8" r="4" /><path d="M4 20c0-4 3.6-7 8-7s8 3 8 7" strokeLinecap="round" /></svg>,
  // Chains — link
  <svg key="chains" className="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.5}><path d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71" strokeLinecap="round" strokeLinejoin="round" /></svg>,
]

function StatsBar() {
  return (
    <div className="border-t border-white/[0.07] bg-black/30 backdrop-blur-md">
      <div className="max-w-[1400px] mx-auto">
        <div className="grid grid-cols-2 md:grid-cols-6 items-center divide-x divide-white/[0.06]">
          {statsBar.map((stat, i) => (
            <div key={stat.label} className="flex flex-col items-center gap-2 py-9 px-4 group">
              <span className="font-mono text-[32px] font-bold tracking-tight text-white/90 group-hover:text-white transition-colors leading-none">
                {stat.value}
              </span>
              <div className="flex items-center gap-1.5 text-white/30">
                <span className="w-4 h-4 flex-shrink-0 opacity-60">{STAT_ICONS[i]}</span>
                <span className="font-mono text-[10px] uppercase tracking-[0.15em] font-medium whitespace-nowrap">{stat.label}</span>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}

/* ─── MARQUEE ─── */
function Marquee() {
  const logos = ['Aave', 'GMX', 'Bybit', 'OKX', 'Copper', 'Fireblocks', 'Bitget', 'Deribit', 'Morpho', 'Binance']

  return (
    <div className="w-full border-t border-b border-white/[0.05] py-12 overflow-hidden bg-black/20">
      <div className="flex animate-marquee whitespace-nowrap min-w-full">
        {[...logos, ...logos].map((logo, i) => (
          <div key={`${logo}-${i}`} className="inline-flex items-center gap-3 mx-12">
            <div className="w-8 h-8 rounded-lg bg-white/5 flex items-center justify-center font-bold text-[10px] text-white/40">
              {logo[0]}
            </div>
            <span className="font-sans text-sm font-semibold text-white/40 tracking-widest uppercase">{logo}</span>
          </div>
        ))}
      </div>
    </div>
  )
}

/* ─── THE HOLY GRAIL ─── */
function HolyGrailSection() {
  return (
    <section className="max-w-[1400px] mx-auto px-6 lg:px-10 py-32">
      <FadeIn className="text-center mb-16">
        <div className="flex justify-center mb-6">
          <SectionLabel>QUANT OS</SectionLabel>
        </div>
        <h2 className="font-sans text-[clamp(32px,4vw,64px)] font-light tracking-tight leading-tight mb-6">
          Beyond Traditional Bots: The Agentic OS
        </h2>
      </FadeIn>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-20 items-center mt-12">
        <div>
          <h3 className="font-sans text-3xl font-light tracking-tight mb-6 max-w-[400px]">
            Institutional Rigor. AI Scale.
          </h3>
          <p className="text-[#888899] text-[15px] font-light max-w-[440px] leading-relaxed">
            Our platform doesn't just "chat." It deploys a sophisticated WealthOrchestrator that manages specialized nodes to validate every thesis through a competitive debate protocol.
          </p>
        </div>

        <div className="space-y-4">
          <div className="flex justify-end gap-2 mb-4">
            <span className="text-[10px] font-mono text-white/40 bg-white/5 px-2 py-1 rounded uppercase tracking-wider">Confidence</span>
            <span className="text-[10px] font-mono text-white/20 px-2 py-1 rounded uppercase tracking-wider">Models</span>
          </div>
          {apyData.map((item) => (
            <div key={item.name} className="card-shine card-glow card-top-edge flex items-center gap-6 p-5 rounded-2xl bg-[#0d0d10] border border-white/[0.05] group transition-all">
              <div className="w-10 h-10 rounded-full bg-white/5 flex items-center justify-center text-xs font-mono text-white/60">
                {item.abbr}
              </div>
              <div className="flex-1">
                <div className="flex justify-between items-center mb-2">
                  <span className="text-sm font-medium text-white/80">{item.name}</span>
                  <span className="font-mono text-sm text-white">{item.pct}%</span>
                </div>
                <div className="h-2 w-full bg-white/5 rounded-full overflow-hidden">
                  <motion.div
                    initial={{ width: 0 }}
                    whileInView={{ width: `${(item.pct / 20) * 100}%` }}
                    transition={{ duration: 1.5, ease: 'easeOut' }}
                    className="h-full rounded-full"
                    style={{ background: item.color }}
                  />
                </div>
              </div>
            </div>
          ))}
          <p className="text-[10px] text-white/20 mt-6 leading-relaxed max-w-[500px]">
            Confidence scores and model weighting are calculated in real-time by the WealthOrchestrator based on live market regimes.
          </p>
        </div>
      </div>
    </section>
  )
}

/* ─── BOARD OF DIRECTORS ─── */
function BoardOfDirectorsSection() {
  return (
    <section className="max-w-[1400px] mx-auto px-6 lg:px-10 pb-24">
      <FadeIn className="text-center mb-14">
        <div className="flex justify-center mb-6">
          <SectionLabel>DIRECTORS</SectionLabel>
        </div>
        <h2 className="font-sans text-[42px] font-light tracking-tight leading-tight mt-5">
          The Board of Directors
        </h2>
      </FadeIn>

      <StaggerContainer className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {onboardData.map((card) => (
          <StaggerItem key={card.title}>
            <div className="card-shine card-glow card-top-edge p-8 rounded-3xl bg-[#0d0d10] border border-white/[0.05] h-[520px] flex flex-col group transition-all relative overflow-hidden">
              <div className="absolute inset-0 opacity-[0.02] pointer-events-none" style={{ backgroundImage: `url('https://www.ethena.fi/images/grid.svg')` }} />

              <div className="flex justify-between items-start mb-6 relative z-10">
                <div className="flex gap-2">
                  <span className="text-[10px] bg-white/5 border border-white/10 px-3 py-1.5 rounded-full text-white/50 font-mono tracking-widest">{card.badge}</span>
                </div>
              </div>

              <h3 className="font-sans text-2xl font-semibold tracking-tight mb-4 relative z-10">{card.title}</h3>
              <p className="text-[14px] text-[#888899] leading-relaxed font-light mb-1 pr-4 relative z-10 flex items-start gap-2">
                <span className="text-white/40 mt-0.5">✓</span>{card.desc1}
              </p>
              <p className="text-[14px] text-[#888899] leading-relaxed font-light mb-8 pr-4 relative z-10 flex items-start gap-2">
                <span className="text-white/40 mt-0.5">✓</span>{card.desc2}
              </p>

              <div className="mt-auto space-y-1 relative z-10">
                {card.links.map((link) => (
                  <div key={link.name} className="flex items-center justify-between py-2.5 text-[13px] text-[#888899] hover:text-white cursor-pointer transition-colors group/link border-b border-white/[0.03]">
                    <div className="flex items-center gap-3">
                      <div className="w-5 h-5 rounded bg-white/5 flex items-center justify-center border border-white/10">
                        <ArrowUpRight className="w-3 h-3 opacity-60" />
                      </div>
                      <span className="font-medium tracking-wide">{link.name}</span>
                    </div>
                    {link.status !== 'Coming Soon' && <ArrowRight className="w-3.5 h-3.5 opacity-40 group-hover/link:opacity-100 group-hover/link:translate-x-0.5 transition-all text-white" />}
                    {link.status === 'Coming Soon' && <span className="text-[9px] bg-white/5 px-2 py-1 rounded text-white/50 uppercase font-mono">Coming Soon</span>}
                  </div>
                ))}
              </div>
            </div>
          </StaggerItem>
        ))}
      </StaggerContainer>
    </section>
  )
}

/* ─── TRANSPARENCY ─── */
function TransparencySection() {
  return (
    <section className="max-w-[1400px] mx-auto px-6 lg:px-10 pb-24 border-b border-white/[0.05]">
      <FadeIn className="text-center mb-14">
        <div className="flex justify-center mb-6">
          <SectionLabel>QUANT XAI</SectionLabel>
        </div>
        <h2 className="font-sans text-[42px] font-light tracking-tight leading-[1.1] mt-5 mb-3">
          Alpha Without the "Black Box"
        </h2>
      </FadeIn>

      <StaggerContainer className="grid grid-cols-1 md:grid-cols-3 gap-5 mb-0">

        {/* Card 1: Real-Time Backing Assets */}
        <StaggerItem>
          <div className="card-shine card-glow card-top-edge p-7 rounded-2xl bg-[#0d0d0f] border border-white/[0.07] flex flex-col group transition-all relative overflow-hidden" style={{ minHeight: 320 }}>
            <h3 className="font-sans text-[17px] font-semibold tracking-tight mb-3 text-white">Real-Time Backing Assets</h3>
            <p className="text-[13px] text-white/45 leading-relaxed mb-4 font-light">View real-time information about the allocation of backing assets.</p>
            <div className="flex items-center gap-1.5 text-[11px] font-mono tracking-[0.12em] text-white/60 hover:text-white cursor-pointer transition-colors uppercase mb-auto">
              LEARN MORE <ArrowRight className="w-3 h-3 ml-1" />
            </div>
            {/* Donut chart visual - Centered and proper */}
            <div className="mt-auto flex justify-center py-4 relative">
              <div className="relative flex items-center justify-center h-28 w-28">
                <svg viewBox="0 0 160 160" className="w-full h-full drop-shadow-[0_0_15px_rgba(37,99,235,0.1)]">
                  <circle cx="80" cy="80" r="65" fill="none" stroke="rgba(255,255,255,0.03)" strokeWidth="20" />
                  <circle cx="80" cy="80" r="65" fill="none" stroke="#2563eb" strokeWidth="20"
                    strokeDasharray="280 128" strokeDashoffset="0" strokeLinecap="butt"
                    transform="rotate(-90 80 80)" />
                  <circle cx="80" cy="80" r="65" fill="none" stroke="#1d4ed8" strokeWidth="20"
                    strokeDasharray="60 348" strokeDashoffset="-280" strokeLinecap="butt"
                    transform="rotate(-90 80 80)" />
                  <circle cx="80" cy="80" r="65" fill="none" stroke="#60a5fa" strokeWidth="20"
                    strokeDasharray="28 380" strokeDashoffset="-340" strokeLinecap="butt"
                    transform="rotate(-90 80 80)" />
                </svg>
                <div className="absolute inset-0 flex flex-col items-center justify-center">
                   <span className="text-[10px] font-mono text-white/30 uppercase tracking-tighter">Liquid</span>
                   <span className="text-sm font-semibold text-white">92%</span>
                </div>
              </div>
            </div>
          </div>
        </StaggerItem>

        {/* Card 2: Weekly Proof of Reserves */}
        <StaggerItem>
          <div className="card-shine card-glow card-top-edge p-7 rounded-2xl bg-[#0d0d0f] border border-white/[0.07] flex flex-col group transition-all relative overflow-hidden" style={{ minHeight: 320 }}>
            <h3 className="font-sans text-[17px] font-semibold tracking-tight mb-3 text-white">Weekly Proof of Reserves</h3>
            <p className="text-[13px] text-white/45 leading-relaxed mb-4 font-light">Independent third-party proofs of the value of the backing assets & delta neutrality.</p>
            <div className="flex items-center gap-1.5 text-[11px] font-mono tracking-[0.12em] text-white/60 hover:text-white cursor-pointer transition-colors uppercase mb-6">
              LEARN MORE <ArrowRight className="w-3 h-3 ml-1" />
            </div>
            {/* Logo Grid matching screenshot */}
            <div className="mt-auto grid grid-cols-2 gap-3">
              {[
                { name: 'ht.digital', icon: '⬡' },
                { name: 'CHAOS LABS', icon: '◈' },
                { name: 'LlamaRisk', icon: '⟁' },
                { name: 'Chainlink', icon: '⬡' },
              ].map(logo => (
                <div key={logo.name} className="flex items-center gap-2 px-3 py-2.5 rounded-lg border border-white/[0.06] bg-white/[0.02]">
                  <span className="text-white/40 text-base">{logo.icon}</span>
                  <span className="text-[12px] text-white/70 font-medium">{logo.name}</span>
                </div>
              ))}
            </div>
          </div>
        </StaggerItem>

        {/* Card 3: Monthly Custodian Attestations */}
        <StaggerItem>
          <div className="card-shine card-glow card-top-edge p-7 rounded-2xl bg-[#0d0d0f] border border-white/[0.07] flex flex-col group transition-all relative overflow-hidden" style={{ minHeight: 320 }}>
            <h3 className="font-sans text-[17px] font-semibold tracking-tight mb-3 text-white">Monthly Custodian Attestations</h3>
            <p className="text-[13px] text-white/45 leading-relaxed mb-4 font-light">Independent attestations of the value of the backing assets residing with custodians.</p>
            <div className="flex items-center gap-1.5 text-[11px] font-mono tracking-[0.12em] text-white/60 hover:text-white cursor-pointer transition-colors uppercase mb-6">
              LATEST ATTESTATION <ArrowRight className="w-3 h-3 ml-1" />
            </div>
            {/* Logo Grid matching screenshot */}
            <div className="mt-auto grid grid-cols-2 gap-3">
              {[
                { name: 'copper.co', icon: '◎' },
                { name: 'CEFFU', icon: '◇' },
              ].map(logo => (
                <div key={logo.name} className="flex items-center gap-2 px-3 py-2.5 rounded-lg border border-white/[0.06] bg-white/[0.02]">
                  <span className="text-white/40 text-base">{logo.icon}</span>
                  <span className="text-[12px] text-white/70 font-medium">{logo.name}</span>
                </div>
              ))}
            </div>
          </div>
        </StaggerItem>

      </StaggerContainer>

      {/* Stats Row */}
      <FadeIn delay={0.2}>
        <div className="grid grid-cols-1 md:grid-cols-3 border-t border-white/[0.06] mt-10">
          {[
            { value: '101.29%', label: 'PROTOCOL BACKING RATIO', icon: <PieChart className="w-3 h-3" /> },
            { value: '<0.2%', label: 'TIME BELOW $0.997', icon: <Shield className="w-3 h-3" /> },
            { value: '100%', label: '24/7 MINT/REDEEM AVAILABILITY', icon: <BarChart3 className="w-3 h-3" /> },
          ].map((stat, i) => (
            <div key={stat.label} className={`flex flex-col items-center justify-center py-10 px-6 ${i < 2 ? 'md:border-r border-white/[0.06]' : ''}`}>
              <div className="font-sans text-[46px] font-light tracking-tight text-white mb-3 leading-none">{stat.value}</div>
              <div className="flex items-center gap-1.5 text-[9px] font-mono text-white/40 tracking-[0.2em] uppercase">
                <span className="opacity-60">{stat.icon}</span>
                {stat.label}
                <span className="ml-1 opacity-40">ⓘ</span>
              </div>
            </div>
          ))}
        </div>
      </FadeIn>
    </section>
  )
}

/* ─── HIGHLIGHTS ─── */
function HighlightsSection() {
  return (
    <section className="max-w-[1400px] mx-auto px-6 lg:px-10 pb-32 pt-24">
      <FadeIn className="text-center mb-14">
        <div className="flex justify-center mb-6">
          <SectionLabel>LIVE FEED</SectionLabel>
        </div>
        <h2 className="font-sans text-[42px] font-light tracking-tight leading-tight mt-5">
          Processed Intelligence Feed
        </h2>
      </FadeIn>

      <StaggerContainer className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-12">
        {highlightsData.map((news) => (
          <StaggerItem key={news.title}>
            <div className="card-shine card-glow card-top-edge p-8 rounded-3xl bg-[#0d0d10] border border-white/[0.05] h-[360px] flex flex-col group transition-all cursor-pointer relative overflow-hidden">
              <div className="absolute inset-0 opacity-[0.02] pointer-events-none" style={{ backgroundImage: `url('https://www.ethena.fi/images/grid.svg')` }} />

              <div className="flex items-center gap-2 mb-6 relative z-10">
                <div className="w-4 h-4 rounded-full bg-white/10 flex items-center justify-center">
                  <div className="w-1.5 h-1.5 rounded-full bg-indigo-400" />
                </div>
                <span className="text-[10px] text-white/50 font-mono tracking-widest uppercase">{news.tag}</span>
              </div>

              <h3 className="font-sans text-xl font-semibold tracking-tight mb-4 pr-4 relative z-10 text-white/90 group-hover:text-white transition-colors">
                {news.title}
              </h3>
              <p className="text-[13.5px] text-[#888899] leading-relaxed font-light mb-8 pr-2 relative z-10">
                {news.desc}
              </p>

              <div className="mt-auto flex items-center text-[12px] text-white/60 group-hover:text-white transition-colors relative z-10 font-mono uppercase tracking-widest">
                {news.link} <ArrowUpRight className="w-3.5 h-3.5 ml-2 opacity-50 group-hover:opacity-100 group-hover:-translate-y-0.5 group-hover:translate-x-0.5 transition-all" />
              </div>
            </div>
          </StaggerItem>
        ))}
      </StaggerContainer>

      <FadeIn delay={0.3} className="flex justify-center mt-12">
        <button className="bg-white/5 border border-white/10 text-white text-[13px] font-medium px-8 py-3 rounded-full hover:bg-white/10 transition-colors">
          See All News
        </button>
      </FadeIn>
    </section>
  )
}
/* ─── ACCESS TIERS ─── */
function AccessTiersSection() {
  return (
    <section className="max-w-[1400px] mx-auto px-6 lg:px-10 py-32 border-t border-white/[0.05]">
      <FadeIn className="text-center mb-16">
        <div className="flex justify-center mb-6">
          <SectionLabel>SUBSCRIPTION</SectionLabel>
        </div>
        <h2 className="font-sans text-[clamp(28px,4vw,52px)] font-light tracking-tight leading-tight uppercase">
          Flexible Access Tiers
        </h2>
      </FadeIn>

      <StaggerContainer className="grid grid-cols-1 md:grid-cols-3 gap-8">
        {accessTiers.map((tier: any) => (
          <StaggerItem key={tier.tier}>
            <div className="card-shine card-glow card-top-edge p-10 rounded-[2.5rem] bg-[#0d0d10] border border-white/[0.05] h-full flex flex-col group transition-all relative overflow-hidden">
              <div className="absolute inset-0 opacity-[0.02] pointer-events-none transition-opacity group-hover:opacity-[0.05]" style={{ backgroundImage: `url('https://www.ethena.fi/images/grid.svg')` }} />
              
              <div className="flex justify-between items-start mb-10 relative z-10">
                <span className="text-[10px] bg-white/5 border border-white/10 px-3 py-1.5 rounded-full text-white/50 font-mono tracking-widest uppercase">{tier.badge}</span>
                <div className="text-right">
                  <div className="text-3xl font-light text-white">{tier.price}</div>
                  <div className="text-[11px] text-white/30 font-mono mt-1">{tier.unit}</div>
                </div>
              </div>

              <h3 className="font-sans text-3xl font-light tracking-tight mb-4 relative z-10">{tier.tier}</h3>
              <p className="text-[15px] text-[#888899] font-light mb-10 leading-relaxed relative z-10 h-12">
                {tier.desc}
              </p>

              <div className="space-y-4 mb-10 relative z-10">
                {tier.features.map((feature: any) => (
                  <div key={feature} className="flex items-center gap-3 text-[14px] text-white/70 font-light">
                    <div className="w-5 h-5 rounded-full bg-[#4ade80]/10 flex items-center justify-center text-[#4ade80] text-[10px]">✓</div>
                    {feature}
                  </div>
                ))}
              </div>

              <button className="mt-auto w-full py-4 rounded-2xl bg-white/5 border border-white/10 text-white text-[14px] font-medium hover:bg-white/10 transition-all relative z-10">
                Start with {tier.tier}
              </button>
            </div>
          </StaggerItem>
        ))}
      </StaggerContainer>
    </section>
  )
}
/* ─── FUTURE SECTION ─── */
function FutureSection() {
  return (
    <section className="max-w-[1400px] mx-auto px-6 lg:px-10 py-40 border-t border-white/[0.05]">
      <FadeIn className="text-center relative">
        <div className="absolute inset-0 -z-10 opacity-[0.03] scale-150" style={{ backgroundImage: `url('https://www.ethena.fi/images/grid.svg')` }} />
        <h2 className="font-sans text-[clamp(40px,5vw,80px)] font-light tracking-tight leading-[1.1] mb-8">
          Join the Future of <br />
          <span className="text-white/40 italic">Quantitative Finance</span>
        </h2>
        <p className="text-[#888899] text-[17px] font-light max-w-[600px] mx-auto mb-12 leading-relaxed">
          Deploy your first Agentic Pipeline or explore our institutional-grade documentation and SDKs.
        </p>
        <div className="flex items-center gap-4 justify-center flex-wrap">
          <button className="bg-white text-black px-10 py-4 rounded-full text-base font-semibold hover:bg-white/90 transition-all shadow-[0_0_40px_rgba(255,255,255,0.2)]">
            Launch Quant Terminal
          </button>
          <button className="flex items-center gap-2 text-white/60 hover:text-white transition-all text-base font-medium group">
            View Documentation <ArrowRight className="w-4 h-4 ml-1 group-hover:translate-x-1 transition-transform" />
          </button>
        </div>
      </FadeIn>
    </section>
  )
}

/* ─── PAGE ─── */
function SectionDivider() {
  return (
    <div className="w-full px-6 lg:px-16 my-0">
      <div className="h-px w-full bg-gradient-to-r from-transparent via-white/[0.12] to-transparent relative">
        <div className="absolute inset-0 bg-gradient-to-r from-transparent via-white/[0.06] to-transparent blur-[2px]" />
      </div>
    </div>
  )
}

export default function HomePage() {
  const { scrollY } = useScroll()
  const scrollVelocity = useVelocity(scrollY)
  const blurValue = useTransform(scrollVelocity, [-2000, 0, 2000], [3, 0, 3])
  const smoothBlur = useSpring(blurValue, { stiffness: 100, damping: 30 })

  return (
    <motion.div style={{ filter: useTransform(smoothBlur, (v) => `blur(${v}px)`) }}>
      <SectionGlow depth={0} />
      <HeroSection />
      <SectionDivider />
      <SectionGlow depth={0.15} />
      <Marquee />
      <SectionDivider />
      <SectionGlow depth={0.3} />
      <HolyGrailSection />
      <SectionDivider />
      <BoardOfDirectorsSection />
      <SectionDivider />
      <SectionGlow depth={0.7} />
      <TransparencySection />
      <SectionDivider />
      <SectionGlow depth={0.8} />
      <AccessTiersSection />
      <SectionDivider />
      <SectionGlow depth={0.9} />
      <HighlightsSection />
      <SectionDivider />
      <SectionGlow depth={1} />
      <FutureSection />
    </motion.div>
  )
}
