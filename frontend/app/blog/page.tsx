import { ArrowRight } from 'lucide-react'
import { FadeIn, GlassCard, StaggerContainer, StaggerItem } from '@/components/MotionComponents'
import SectionLabel from '@/components/SectionLabel'
import { blogData } from '@/lib/data'

export default function BlogPage() {
  const [featured, ...rest] = blogData

  return (
    <div>
      {/* Header */}
      <div className="max-w-[1400px] mx-auto px-6 lg:px-10 pt-16 pb-10">
        <FadeIn>
          <SectionLabel>Research & Updates</SectionLabel>
          <h1 className="font-syne text-[clamp(32px,4vw,64px)] font-bold tracking-tight mt-5 mb-3 leading-tight">
            Ethena Lab Notes
          </h1>
          <p className="text-[#888899] text-[15px] font-light max-w-[480px]">
            Deep dives into protocol mechanics, yield strategies, and the internet-native dollar thesis.
          </p>
        </FadeIn>
      </div>

      <div className="max-w-[1400px] mx-auto px-6 lg:px-10 pb-24">
        {/* Featured article */}
        <FadeIn className="mb-4">
          <GlassCard className="p-0 overflow-hidden cursor-pointer group/card">
            <div className="grid grid-cols-1 md:grid-cols-2">
              <div
                className="h-56 md:h-full min-h-[240px] flex items-center justify-center text-6xl"
                style={{ background: featured.color }}
              >
                {featured.emoji}
              </div>
              <div className="p-8 md:p-10 flex flex-col">
                <span className="font-mono text-[10px] uppercase tracking-[0.1em] text-accent2 mb-3">
                  {featured.tag} · Featured
                </span>
                <h2 className="font-syne text-2xl md:text-3xl font-bold tracking-tight leading-tight mb-4">
                  {featured.title}
                </h2>
                <p className="text-[14px] text-[#888899] font-light leading-relaxed flex-1">
                  {featured.excerpt}
                </p>
                <div className="flex items-center justify-between mt-8 pt-6 border-t border-white/[0.07]">
                  <div>
                    <p className="font-mono text-[10px] uppercase tracking-[0.08em] text-[#555566]">{featured.date}</p>
                    <p className="font-mono text-[10px] uppercase tracking-[0.08em] text-[#555566] mt-0.5">{featured.readTime} read</p>
                  </div>
                  <div className="flex items-center gap-2 text-[13px] text-[#888899] group-hover/card:text-white transition-colors">
                    Read article
                    <ArrowRight className="w-4 h-4 group-hover/card:translate-x-0.5 transition-transform" />
                  </div>
                </div>
              </div>
            </div>
          </GlassCard>
        </FadeIn>

        {/* Rest grid */}
        <StaggerContainer className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {rest.map((post) => (
            <StaggerItem key={post.title}>
              <GlassCard className="p-0 overflow-hidden flex flex-col cursor-pointer group/card h-full">
                {/* Cover */}
                <div
                  className="h-40 flex items-center justify-center text-4xl flex-shrink-0"
                  style={{ background: post.color }}
                >
                  {post.emoji}
                </div>
                <div className="p-6 flex flex-col flex-1">
                  <span className="font-mono text-[10px] uppercase tracking-[0.1em] text-accent2 mb-2.5">
                    {post.tag}
                  </span>
                  <h3 className="font-syne text-[16px] font-bold tracking-tight leading-snug mb-3">
                    {post.title}
                  </h3>
                  <p className="text-[13px] text-[#888899] font-light leading-relaxed flex-1">
                    {post.excerpt}
                  </p>
                  <div className="flex items-center justify-between mt-5 pt-4 border-t border-white/[0.06]">
                    <span className="font-mono text-[10px] text-[#555566] uppercase tracking-[0.08em]">{post.date}</span>
                    <span className="flex items-center gap-1.5 text-[12px] text-[#888899] group-hover/card:text-white transition-colors">
                      {post.readTime} <ArrowRight className="w-3 h-3" />
                    </span>
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
