'use client'

import { useMemo, useState } from 'react'
import { usePathname } from 'next/navigation'
import html2canvas from 'html2canvas'
import ReactMarkdown from 'react-markdown'
import { Camera, Loader2, Sparkles, X } from 'lucide-react'
import { researchAPI } from '@/lib/api'

const BTN_BASE =
  'fixed bottom-6 right-6 z-[90] flex items-center gap-2 px-4 py-2 rounded-xl border border-indigo-400/35 bg-indigo-500/12 text-indigo-200 text-[11px] font-dm-mono tracking-widest uppercase backdrop-blur-xl shadow-[0_0_20px_rgba(99,102,241,0.25)] hover:bg-indigo-500/20 hover:border-indigo-300/55 transition-all duration-300'

const PANEL_BASE =
  'fixed inset-0 z-[100] bg-black/70 backdrop-blur-sm flex items-center justify-center p-4'

const CARD_BASE =
  'relative w-full max-w-4xl max-h-[88vh] overflow-auto rounded-2xl border border-white/15 bg-[#060b17]/95 shadow-[0_20px_80px_rgba(0,0,0,0.65)] p-6'

const inferSymbol = (pathname: string) => {
  const fromPath = pathname
    .split('/')
    .map((s) => s.trim())
    .filter(Boolean)
    .find((s) => /^[A-Za-z][A-Za-z0-9.]{1,14}$/.test(s))

  if (fromPath) return fromPath.toUpperCase()
  return 'SPY'
}

const inferMarket = (symbol: string) => {
  const s = symbol.toUpperCase()
  if (s.endsWith('.NS') || s.endsWith('.BO')) return 'india' as const
  return 'us' as const
}

export default function GlobalPageAnalyzer() {
  const pathname = usePathname() || '/'

  const isExcludedPage =
    pathname.startsWith('/chat') ||
    pathname.startsWith('/backtest') ||
    pathname.startsWith('/research') ||
    pathname.startsWith('/technical')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [report, setReport] = useState<string | null>(null)
  const [open, setOpen] = useState(false)

  const fallbackSymbol = useMemo(() => inferSymbol(pathname), [pathname])

  if (isExcludedPage) return null

  const capturePage = async () => {
    const root = (document.querySelector('main') as HTMLElement | null) || document.body
    const canvas = await html2canvas(root, {
      backgroundColor: '#05070c',
      useCORS: true,
      scale: 1.2,
      logging: false,
      windowWidth: window.innerWidth,
      windowHeight: window.innerHeight,
    })
    return canvas.toDataURL('image/jpeg', 0.84)
  }

  const runAnalyze = async () => {
    if (loading) return
    setLoading(true)
    setError(null)

    try {
      const imageDataUrl = await capturePage()
      const symbol = fallbackSymbol
      const market = inferMarket(symbol)

      const res = await researchAPI.interpretImage({
        symbol,
        market,
        imageDataUrl,
        context: {
          path: pathname,
          title: document.title,
          source: 'global_page_analyzer',
          note: 'Analyze this page screenshot in the same style as backtest/research visual interpretation.',
        },
      })

      setReport(res.analysis || 'Analysis complete.')
      setOpen(true)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Screenshot analysis failed')
      setOpen(true)
    } finally {
      setLoading(false)
    }
  }

  return (
    <>
      <button type="button" onClick={runAnalyze} className={BTN_BASE}>
        {loading ? <Loader2 size={14} className="animate-spin" /> : <Camera size={14} />}
        <span>{loading ? 'ANALYZING_THIS_PAGE...' : 'ANALYZE_THIS_PAGE'}</span>
      </button>

      {open && (
        <div className={PANEL_BASE}>
          <div className={CARD_BASE}>
            <button
              type="button"
              onClick={() => setOpen(false)}
              className="absolute top-4 right-4 p-2 rounded-lg border border-white/15 bg-white/5 text-white/60 hover:text-white hover:bg-white/10 transition-colors"
            >
              <X size={16} />
            </button>

            <div className="flex items-center gap-2 mb-4">
              <Sparkles size={16} className="text-indigo-300" />
              <div className="text-[12px] font-dm-mono uppercase tracking-widest text-indigo-200">Page Screenshot Analysis</div>
            </div>

            <div className="text-[11px] font-dm-mono text-white/35 uppercase tracking-widest mb-4">
              Path: {pathname} | Symbol Context: {fallbackSymbol}
            </div>

            {error ? (
              <div className="rounded-xl border border-red-400/25 bg-red-400/10 text-red-200 text-sm p-4">{error}</div>
            ) : (
              <div className="prose prose-invert max-w-none prose-p:text-white/75 prose-headings:text-white prose-strong:text-white">
                <ReactMarkdown>{report || 'No analysis output available.'}</ReactMarkdown>
              </div>
            )}
          </div>
        </div>
      )}
    </>
  )
}
