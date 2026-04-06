interface SectionLabelProps {
  children: React.ReactNode
  className?: string
}

export default function SectionLabel({ children, className = '' }: SectionLabelProps) {
  return (
    <span
      className={`inline-flex items-center gap-2 font-mono text-[10px] uppercase tracking-[0.12em] text-[#555566] border border-white/[0.07] px-3.5 py-1.5 rounded-full ${className}`}
    >
      {children}
    </span>
  )
}
