'use client'

import { useState, useEffect, useRef, useCallback } from 'react'
import { Zap } from 'lucide-react'
import html2canvas from 'html2canvas'
import ReactMarkdown from 'react-markdown'
import { marketAPI, researchAPI } from '@/lib/api'

// ─── TYPES ───────────────────────────────────────────────────────────────────
interface Candle { time: string; open: number; high: number; low: number; close: number; volume: number }
interface SRLevels { support: number[]; resistance: number[] }
interface MTFSignal { tf: string; trend: 'Bullish' | 'Bearish' | 'Neutral'; rsi: number }
interface MarketState {
  state: 'bullish' | 'bearish' | 'sideways'
  subtype: 'strong' | 'weak' | 'range' | 'choppy'
  confidence: number
  reason: string
}

function inferMarketFromSymbol(raw: string): 'US' | 'IN' | null {
  const s = (raw || '').trim().toUpperCase()
  if (!s) return null
  if (s.includes(':')) {
    if (s.startsWith('NSE:') || s.startsWith('BSE:')) return 'IN'
    return 'US'
  }
  if (s.endsWith('.NS') || s.endsWith('.BO') || s.endsWith('.BS')) return 'IN'
  return null
}

function normalizeSymbolInput(raw: string, market: 'US' | 'IN'): string {
  const s = (raw || '').trim().toUpperCase()
  if (!s) return market === 'IN' ? 'RELIANCE.BO' : 'AAPL'
  if (s.includes(':')) return s
  if (market === 'IN') {
    if (s.endsWith('.BO') || s.endsWith('.BS')) return s
    if (s.endsWith('.NS')) return s.replace('.NS', '.BO')
    return `${s}.BO`
  }
  return s.split('.')[0]
}

function toTradingViewSymbol(symbol: string, market: 'US' | 'IN'): string {
  const s = (symbol || '').trim().toUpperCase()
  if (!s) return market === 'IN' ? 'BSE:RELIANCE' : 'AAPL'
  if (s.includes(':')) return s
  if (market === 'IN') {
    if (s.endsWith('.NS')) return `BSE:${s.replace('.NS', '')}`
    if (s.endsWith('.BO') || s.endsWith('.BS')) return `BSE:${s.replace(/\.(BO|BS)$/, '')}`
    return `BSE:${s}`
  }
  return s.split('.')[0]
}

const TIMEFRAMES = [
  { label: '1D', range: '1d',  interval: '1d',  tv: '5'  },
  { label: '1W', range: '5d',  interval: '1d',  tv: '15' },
  { label: '1M', range: '1mo', interval: '1d',  tv: 'D'  },
  { label: '1Y', range: '1y',  interval: '1wk', tv: 'W'  },
]

// ─── QUANT ENGINE ─────────────────────────────────────────────────────────────
function computeRSI(closes: number[], period = 14): number {
  if (closes.length < period + 1) return 50
  let gains = 0, losses = 0
  for (let i = closes.length - period; i < closes.length; i++) {
    const d = closes[i] - closes[i - 1]
    d > 0 ? (gains += d) : (losses -= d)
  }
  const ag = gains / period, al = losses / period
  return al === 0 ? 100 : Math.round(100 - 100 / (1 + ag / al))
}

function computeEMA(closes: number[], period: number): number {
  if (closes.length < period) return closes.at(-1) ?? 0
  const k = 2 / (period + 1)
  let ema = closes.slice(0, period).reduce((a, b) => a + b, 0) / period
  for (let i = period; i < closes.length; i++) ema = closes[i] * k + ema * (1 - k)
  return ema
}

function detectMarketState(data: Candle[], rsi?: number): MarketState {
  if (!data.length || data.length < 6) {
    return {
      state: 'sideways',
      subtype: 'choppy',
      confidence: 40,
      reason: 'Insufficient structure data',
    }
  }

  const recent = data.slice(-5)
  const recentHighs = recent.map((c) => c.high)
  const recentLows = recent.map((c) => c.low)
  const lastClose = recent.at(-1)?.close ?? data.at(-1)?.close ?? 0

  const higherHighs = recentHighs.at(-1)! > recentHighs[0]
  const higherLows = recentLows.at(-1)! > recentLows[0]
  const lowerHighs = recentHighs.at(-1)! < recentHighs[0]
  const lowerLows = recentLows.at(-1)! < recentLows[0]

  const rangeSize = Math.max(...recentHighs) - Math.min(...recentLows)
  const rangePct = lastClose > 0 ? rangeSize / lastClose : 0

  let out: MarketState

  if (higherHighs && higherLows) {
    out = {
      state: 'bullish',
      subtype: 'strong',
      confidence: 75,
      reason: 'Higher highs and higher lows',
    }
  } else if (lowerHighs && lowerLows) {
    out = {
      state: 'bearish',
      subtype: 'strong',
      confidence: 75,
      reason: 'Lower highs and lower lows',
    }
  } else if (higherHighs || higherLows) {
    out = {
      state: 'bullish',
      subtype: 'weak',
      confidence: 62,
      reason: 'Partial bullish structure',
    }
  } else if (lowerHighs || lowerLows) {
    out = {
      state: 'bearish',
      subtype: 'weak',
      confidence: 62,
      reason: 'Partial bearish structure',
    }
  } else if (rangePct < 0.02) {
    out = {
      state: 'sideways',
      subtype: 'range',
      confidence: 60,
      reason: 'Low-volatility range',
    }
  } else {
    out = {
      state: 'sideways',
      subtype: 'choppy',
      confidence: 50,
      reason: 'No clear structure',
    }
  }

  // Indicator confirmation layer (confirmation only, not core decision).
  if (typeof rsi === 'number') {
    if (out.state === 'bearish' && rsi < 50) out.confidence += 10
    if (out.state === 'bullish' && rsi > 50) out.confidence += 10
  }

  out.confidence = Math.max(35, Math.min(95, out.confidence))
  return out
}

function getAction(ms: MarketState): string {
  if (ms.state === 'bullish') return 'Look for buy opportunities'
  if (ms.state === 'bearish') return 'Look for sell / short setups'
  if (ms.subtype === 'choppy') return 'Avoid trading'
  return 'Wait for breakout'
}

// # Quant Intelligence Upgrade
//
// - [x] Support / Resistance Detection (client-side swing detection + clustering)
// - [x] Multi-Timeframe Analysis (fetch 3 timeframes, combine signals)
// - [x] Display S/R zones + MTF panel in the AI panel right column
// - [x] Verify all renders correctly in browser
// - [x] Upgrade AI Analysis with Full Quant Context (S/R, MTF, Confidence)
// - [/] Implement 'Compare/Add' vs 'Replace' symbol logic (Bloomberg-style)
// - [ ] Final visual audit of terminal aesthetics
function computeSR(data: Candle[]): SRLevels {
  if (data.length < 10) return { support: [], resistance: [] }
  const highs: number[] = [], lows: number[] = []
  const lb = 3
  for (let i = lb; i < data.length - lb; i++) {
    let isH = true, isL = true
    for (let j = 1; j <= lb; j++) {
      if (data[i].high <= data[i - j].high || data[i].high <= data[i + j].high) isH = false
      if (data[i].low  >= data[i - j].low  || data[i].low  >= data[i + j].low)  isL = false
    }
    if (isH) highs.push(data[i].high)
    if (isL) lows.push(data[i].low)
  }
  const cluster = (levels: number[]) => {
    if (!levels.length) return []
    const sorted = [...levels].sort((a, b) => a - b)
    const out: number[] = []
    let g = [sorted[0]]
    for (let i = 1; i < sorted.length; i++) {
      if ((sorted[i] - g.at(-1)!) / g.at(-1)! < 0.008) g.push(sorted[i])
      else { out.push(g.reduce((a, b) => a + b) / g.length); g = [sorted[i]] }
    }
    out.push(g.reduce((a, b) => a + b) / g.length)
    return out
  }
  return { resistance: cluster(highs).slice(-3).reverse(), support: cluster(lows).slice(0, 3).reverse() }
}

function deriveTrend(closes: number[], rsi: number): 'Bullish' | 'Bearish' | 'Neutral' {
  if (closes.length < 30) return 'Neutral'
  const ema20 = computeEMA(closes, 20)
  const ema50 = computeEMA(closes, 50)
  const last = closes.at(-1) ?? 0
  const prev10 = closes.at(-10) ?? last
  const ret10 = prev10 ? ((last - prev10) / prev10) * 100 : 0

  if (last < ema20 && ema20 < ema50 && ret10 < -1) return 'Bearish'
  if (last > ema20 && ema20 > ema50 && ret10 > 1) return 'Bullish'
  if (last < ema20 && ret10 < -2 && rsi < 48) return 'Bearish'
  if (last > ema20 && ret10 > 2 && rsi > 52) return 'Bullish'
  return 'Neutral'
}

// ─── TRADINGVIEW CHART ────────────────────────────────────────────────────────
// FIX 1: Use textContent (not innerHTML) for the config when script has a src
// FIX 2: Add tradingview-widget-container class so TV can size itself
// FIX 3: Remove any padding from the wrapper div
function TradingViewChart({
  symbol, market, interval, studies = []
}: {
  symbol: string; market: 'US' | 'IN'; interval: string; studies?: string[]
}) {
  const containerRef = useRef<HTMLDivElement>(null)

  const tvSym = toTradingViewSymbol(symbol, market)

  useEffect(() => {
    const el = containerRef.current
    if (!el) return

    // Wipe previous widget
    el.innerHTML = ''

    // Outer wrapper — TV requires this class to autosize
    const wrapper = document.createElement('div')
    wrapper.className = 'tradingview-widget-container'
    wrapper.style.cssText = 'width:100%;height:100%;'

    // Inner widget target div
    const widgetEl = document.createElement('div')
    widgetEl.className = 'tradingview-widget-container__widget'
    widgetEl.style.cssText = 'width:100%;height:100%;'
    wrapper.appendChild(widgetEl)

    // Prepare studies: Convert overlaid symbols to TV 'Compare' studies
    const tvStudies = studies.map(s => ({
      id: "Compare@tv-basicstudies",
      inputs: { symbol: s },
      override: { "plot.color.0": "#818cf8" } // Indigo overlay
    }))

    // Script — KEY FIX: use textContent, NOT innerHTML, when src is set
    const script = document.createElement('script')
    script.type = 'text/javascript'
    script.src = 'https://s3.tradingview.com/external-embedding/embed-widget-advanced-chart.js'
    script.async = true
    script.textContent = JSON.stringify({
      autosize:            true,
      symbol:              tvSym,
      interval:            interval,
      timezone:            market === 'IN' ? 'Asia/Kolkata' : 'America/New_York',
      theme:               'dark',
      style:               '1',
      locale:              'en',
      allow_symbol_change: false,
      calendar:            false,
      save_image:          true,
      backgroundColor:     '#000000',
      gridColor:           'rgba(255,255,255,0.04)',
      hide_top_toolbar:    false,
      hide_legend:         false,
      studies:             tvStudies,
    })
    wrapper.appendChild(script)

    // Delay to ensure DOM has fully painted before TradingView attaches
    // its iframe resize listener (prevents contentWindow unavailable error)
    const timer = setTimeout(() => {
      if (el) el.appendChild(wrapper)
    }, 100)

    return () => {
      clearTimeout(timer)
      if (el) el.innerHTML = ''
    }
  }, [tvSym, interval, studies])

  // Pro Clipping: make slightly taller and hide the bottom branding
  return (
    <div className="w-full h-full overflow-hidden">
      <div 
        ref={containerRef} 
        style={{ width: '100%', height: 'calc(100% + 40px)' }} 
      />
    </div>
  )
}

// ─── MAIN PAGE ────────────────────────────────────────────────────────────────
export default function TechnicalPage() {
  const [market, setMarket]     = useState<'US' | 'IN'>('US')
  const [symbol, setSymbol]     = useState('AAPL')
  const [tf, setTf]             = useState(TIMEFRAMES[2])
  const [cmd, setCmd]           = useState('')

  const [price, setPrice]       = useState<number | null>(null)
  const [pctChange, setPct]     = useState<number | null>(null)
  const [rsi, setRsi]           = useState(50)
  const [marketState, setMarketState] = useState<MarketState>({
    state: 'sideways',
    subtype: 'choppy',
    confidence: 50,
    reason: 'Waiting for data',
  })
  const [srLevels, setSR]       = useState<SRLevels>({ support: [], resistance: [] })
  const [mtfRows, setMTF]       = useState<MTFSignal[]>([])
  const [mtfBias, setMTFBias]   = useState('—')
  const [overlays, setOverlays] = useState<string[]>([])

  const [showModal, setShowModal] = useState(false)
  const [aiLoading, setAiLoading] = useState(false)
  const [aiText, setAiText]       = useState('')

  const [clock, setClock] = useState('')
  useEffect(() => {
    const f = () => new Date().toLocaleTimeString('en-US', { hour12: false })
    setClock(f())
    const id = setInterval(() => setClock(f()), 1000)
    return () => clearInterval(id)
  }, [])

  // Primary data fetch
  useEffect(() => {
    marketAPI.getCandles(symbol, tf.interval, tf.range, market)
      .then((d: any) => {
        const raw = d?.data as any[]
        if (!raw?.length) return
        const data: Candle[] = raw.map(x => ({
          time: (x.date || '').split('T')[0],
          open: x.open, high: x.high, low: x.low, close: x.close, volume: x.volume,
        }))
        const closes = data.map(x => x.close)
        const last = closes.at(-1)!, prev = closes.at(-2) ?? last
        const pct = ((last - prev) / prev) * 100
        const r = computeRSI(closes)
        const ms = detectMarketState(data, r)
        setPrice(last); setPct(pct); setRsi(r)
        setSR(computeSR(data))
        setMarketState(ms)
      })
      .catch(() => {})
  }, [symbol, tf, market])

  // Multi-TF
  useEffect(() => {
    const configs = [
      { tf: '1D', range: '5d',  interval: '1d'  },
      { tf: '1M', range: '1mo', interval: '1d'  },
      { tf: '3M', range: '3mo', interval: '1wk' },
    ]
    Promise.allSettled(
      configs.map(c =>
        marketAPI.getCandles(symbol, c.interval, c.range, market)
          .then((d: any) => ({ ...c, data: d?.data }))
      )
    ).then(results => {
      const rows: MTFSignal[] = results.map((r, i) => {
        if (r.status !== 'fulfilled' || !r.value?.data?.length)
          return { tf: configs[i].tf, trend: 'Neutral' as const, rsi: 50 }
        const closes = r.value.data.map((x: any) => x.close)
        const rv = computeRSI(closes, 14)
        return { tf: configs[i].tf, trend: deriveTrend(closes, rv), rsi: rv }
      })
      setMTF(rows)
      const bull = rows.filter(r => r.trend === 'Bullish').length
      const bear = rows.filter(r => r.trend === 'Bearish').length
      setMTFBias(
        bull === 3 ? 'Strong Bull' : bull >= 2 ? 'Bullish'
        : bear === 3 ? 'Strong Bear' : bear >= 2 ? 'Bearish'
        : 'Neutral'
      )
    })
  }, [symbol, market])

  // Screenshot-based page analysis for this technical view
  const runPageScreenshotAnalysis = useCallback(async (sym: string) => {
    setShowModal(true)
    setAiLoading(true); setAiText('')
    try {
      const root = (document.querySelector('main') as HTMLElement | null) || document.body
      const canvas = await html2canvas(root, {
        backgroundColor: '#05070c',
        useCORS: true,
        scale: 1.2,
        logging: false,
        windowWidth: window.innerWidth,
        windowHeight: window.innerHeight,
      })
      const imageDataUrl = canvas.toDataURL('image/jpeg', 0.86)

      const res = await researchAPI.interpretImage({
        symbol: sym,
        market: market === 'IN' ? 'india' : 'us',
        imageDataUrl,
        context: {
          source: 'technical_page_screenshot',
          timeframe: tf.label,
          ticker: sym,
          price: price != null ? Number(price.toFixed(2)) : null,
          day_change_percent: pctChange != null ? Number(pctChange.toFixed(2)) : null,
          rsi14: rsi,
          market_state: marketState,
          mtfBias,
          mtf_rows: mtfRows,
          support_levels: srLevels.support,
          resistance_levels: srLevels.resistance,
          bse_only_india: market === 'IN',
          note: 'Analyze this technical page screenshot and infer trend strength, risks, and setup quality.',
        },
      })

      setAiText(res.analysis || 'Analysis complete.')
    } catch {
      setAiText('Screenshot analysis failed. Ensure backend is running on port 8001 and try again.')
    } finally {
      setAiLoading(false)
    }
  }, [market, tf.label, price, pctChange, rsi, marketState, mtfBias, mtfRows, srLevels])

  const handleCmd = (e: React.FormEvent) => {
    e.preventDefault()
    const raw = cmd.trim(); setCmd('')
    if (!raw) return
    const v = raw.toUpperCase()

    if (v.startsWith('/ANALYZE ')) {
      const raw = v.split(' ')[1]
      const inferred = inferMarketFromSymbol(raw)
      const nextMarket = inferred ?? market
      const normalized = normalizeSymbolInput(raw, nextMarket)
      if (nextMarket !== market) setMarket(nextMarket)
      setSymbol(normalized)
      runPageScreenshotAnalysis(normalized)
    } else if (v.startsWith('/COMPARE ') || v.startsWith('/ADD ')) {
      const raw = v.split(' ')[1]
      const inferred = inferMarketFromSymbol(raw)
      const nextMarket = inferred ?? market
      const normalized = normalizeSymbolInput(raw, nextMarket)
      const tvCompare = toTradingViewSymbol(normalized, nextMarket)
      setOverlays(prev => [...new Set([...prev, tvCompare])])
    } else if (v === '/CLEAR') {
      setOverlays([])
    } else if (!v.startsWith('/')) {
      const inferred = inferMarketFromSymbol(v)
      const nextMarket = inferred ?? market
      const normalized = normalizeSymbolInput(v, nextMarket)
      if (nextMarket !== market) setMarket(nextMarket)
      setSymbol(normalized)
      setOverlays([]) // Replace wipes overlays for clean view
    }
  }

  const cur       = market === 'IN' ? '₹' : '$'
  const priceUp   = (pctChange ?? 0) >= 0
  const sigColor  = marketState.state === 'bullish' ? 'text-emerald-400'
                  : marketState.state === 'bearish' ? 'text-rose-400'
                  : 'text-amber-300'
  const confColor = marketState.confidence > 70 ? '#4ade80' : marketState.confidence > 55 ? '#818cf8' : '#f87171'
  const marketHeading =
    marketState.state === 'bullish'
      ? `▲ BULLISH ${marketState.subtype === 'strong' ? 'TREND' : '(WEAK)'}`
      : marketState.state === 'bearish'
        ? `▼ BEARISH ${marketState.subtype === 'strong' ? 'TREND' : '(WEAK)'}`
        : `SIDEWAYS (${marketState.subtype === 'range' ? 'RANGE' : 'CHOPPY'})`
  const marketAction = getAction(marketState)
  const mtfStr    = mtfRows.map(r =>
    `${r.tf} ${r.trend === 'Bullish' ? '↑' : r.trend === 'Bearish' ? '↓' : '→'}`
  ).join('  ')

  return (
    // FIX 4: flex-col with fixed height, children use min-h-0 to prevent overflow
    <div
      className="flex flex-col bg-[#030305] w-full relative overflow-hidden"
      style={{ height: 'calc(100vh - 70px)' }}
    >
      {/* ── COMMAND BAR ──────────────────────────────────────────────────── */}
      <div className="flex-shrink-0 flex items-center gap-6 px-6 py-3 border-b border-white/[0.05]">
        <span className="font-mono text-[11px] text-white/25 tracking-[0.35em] uppercase flex-shrink-0">
          Terminal
        </span>

        <form onSubmit={handleCmd} className="flex-1">
          <input
            value={cmd}
            onChange={e => setCmd(e.target.value)}
            placeholder="/analyze RELIANCE.BO  or  AAPL"
            className="w-full bg-transparent text-white/90 placeholder:text-white/20 text-sm outline-none font-mono"
          />
        </form>

        <div className="flex items-center gap-0.5 flex-shrink-0">
          {(['US', 'IN'] as const).map(m => (
            <button
              key={m}
              onClick={() => { setMarket(m); setSymbol(m === 'US' ? 'AAPL' : 'RELIANCE.BO') }}
              className={`px-3 py-1 rounded font-mono text-[10px] tracking-widest transition-all ${
                market === m ? 'bg-white/10 text-white' : 'text-white/30 hover:text-white/60'
              }`}
            >
              {m}
            </button>
          ))}
        </div>

        <div className="flex items-center gap-0.5 flex-shrink-0">
          {TIMEFRAMES.map(t => (
            <button
              key={t.label}
              onClick={() => setTf(t)}
              className={`px-3 py-1 rounded font-mono text-[10px] tracking-widest transition-all ${
                tf.label === t.label ? 'bg-white/10 text-white' : 'text-white/30 hover:text-white/60'
              }`}
            >
              {t.label}
            </button>
          ))}
        </div>

        <div className="flex items-center gap-2 flex-shrink-0">
          <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
          <span className="font-mono text-[10px] text-white/25 tabular-nums">{clock}</span>
        </div>
      </div>

      <div className="flex-shrink-0 px-6 py-1.5 border-b border-white/[0.04] bg-white/[0.01]">
        <span className="font-mono text-[10px] text-indigo-300/70 uppercase tracking-[0.18em]">
          India feed: BSE only (.BO) | NSE disabled on this page
        </span>
      </div>

      {/* ── AI MODAL ─────────────────────────────────────────────────────── */}
      {showModal && (
        <div className="absolute inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-md pointer-events-auto p-4">
          <div className="w-full max-w-4xl bg-black/90 backdrop-blur-2xl border border-white/15 shadow-2xl relative flex flex-col max-h-[95vh] overflow-hidden rounded-lg">
            <button
              onClick={() => setShowModal(false)}
              className="absolute top-5 right-5 text-white/30 hover:text-white transition-colors text-2xl leading-none z-10"
            >
              ✕
            </button>

            {/* Header */}
            <div className="flex items-center justify-between gap-3 px-8 py-5 border-b border-white/10 shrink-0">
              <div className="flex items-center gap-3">
                <div className="w-8 h-8 rounded bg-indigo-500/10 border border-indigo-500/20 flex items-center justify-center">
                  <Zap size={16} className="text-indigo-400" />
                </div>
                <h2 className="text-base tracking-[0.15em] uppercase font-bold text-white/90">Technical Analysis Report</h2>
              </div>
              <div className="flex items-center gap-3 font-mono text-[11px] text-white/40">
                <span>{symbol}</span>
                <span>•</span>
                <span>{tf.label}</span>
                <span>•</span>
                <span className={priceUp ? 'text-emerald-400' : 'text-rose-400'}>{cur}{price?.toFixed(2)}</span>
              </div>
            </div>

            {/* Content Area */}
            <div className="flex-1 overflow-y-auto px-8 py-8">
              {aiLoading ? (
                <div className="h-full flex flex-col items-center justify-center gap-6">
                  <span className="w-6 h-6 border-2 border-indigo-500/20 border-t-indigo-500 rounded-full animate-spin" />
                  <span className="font-mono text-[11px] text-indigo-300 animate-pulse tracking-[0.3em]">
                    ANALYZING MARKET STRUCTURE...
                  </span>
                </div>
              ) : (
                <div className="prose prose-invert max-w-none
                  prose-headings:text-white prose-headings:font-bold prose-headings:mt-6 prose-headings:mb-4
                  prose-h2:text-lg prose-h2:tracking-[0.1em]
                  prose-p:text-white/85 prose-p:leading-relaxed prose-p:mb-4
                  prose-strong:text-white prose-strong:font-semibold
                  prose-code:text-amber-300 prose-code:bg-white/5 prose-code:px-1.5 prose-code:py-0.5 prose-code:rounded
                  prose-li:text-white/85
                  [&>h2:first-child]:mt-0
                  space-y-4">
                  <ReactMarkdown>{aiText || 'No analysis output available.'}</ReactMarkdown>
                </div>
              )}
            </div>

            {/* Footer */}
            <div className="shrink-0 px-8 py-5 border-t border-white/10 bg-white/[0.02] flex items-center justify-between">
              <div className="font-mono text-[10px] text-white/25 space-y-1">
                <div>RSI: <span className="text-amber-400">{rsi}</span> | MTF Bias: <span className="text-white/50">{mtfBias}</span></div>
                <div>Support: <span className="text-emerald-400">{cur}{srLevels.support[0]?.toFixed(2) || '—'}</span> | Resistance: <span className="text-rose-400">{cur}{srLevels.resistance[0]?.toFixed(2) || '—'}</span></div>
              </div>
              <button 
                onClick={() => setShowModal(false)}
                className="px-6 py-2 bg-white/10 hover:bg-white/15 text-white/70 hover:text-white transition-all font-mono text-[11px] tracking-[0.1em] uppercase rounded"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ── CHART — overflow-hidden clips the watermark from the child ── */}
      <div className="flex-1 min-h-0 w-full relative overflow-hidden bg-black">
        <TradingViewChart 
          symbol={symbol} 
          market={market} 
          interval={tf.tv} 
          studies={overlays}
        />
      </div>

      {/* ── INTELLIGENCE STRIP ───────────────────────────────────────────── */}
      <div className="flex-shrink-0 border-t border-white/[0.06] bg-[#030305] h-[150px]">
        <div className="grid grid-cols-4 divide-x divide-white/[0.05] h-full items-center">

          {/* Signal */}
          <div className="px-6 py-2">
            <p className="font-mono text-[10px] text-white/30 uppercase tracking-[0.3em] mb-1.5">Market State</p>
            <p className={`font-mono text-xl font-bold leading-none mb-1.5 ${sigColor}`}>{marketHeading}</p>
            <p className="font-mono text-[10px] text-white/45 uppercase tracking-widest mb-1">{marketState.reason}</p>
            <p className="font-mono text-[10px] text-indigo-300/75 uppercase tracking-widest mb-1.5">Action: {marketAction}</p>
            <div className="flex items-center gap-2">
              <div className="flex-1 h-1 rounded-full bg-white/[0.07] overflow-hidden">
                <div
                  className="h-full rounded-full transition-all duration-700"
                  style={{ width: `${marketState.confidence}%`, background: confColor }}
                />
              </div>
              <span className="font-mono text-[10px] text-white/40">{marketState.confidence}%</span>
            </div>
          </div>

          {/* Trade Setup */}
          <div className="px-6 py-2">
            <p className="font-mono text-[10px] text-white/30 uppercase tracking-[0.3em] mb-1.5">Trade Setup</p>
            <button
              onClick={() => runPageScreenshotAnalysis(symbol)}
              disabled={aiLoading}
              className="flex items-center justify-center w-full py-2 bg-indigo-500/10 hover:bg-indigo-500/20 border border-indigo-500/20 rounded-md gap-1.5 font-mono text-xs text-indigo-300 hover:text-indigo-200 transition-colors disabled:opacity-40"
            >
              <Zap size={11} />
              {aiLoading ? 'Analyzing Screenshot…' : 'Analyse Page (Screenshot)'}
            </button>
            {!!aiText && !aiLoading && (
              <div className="mt-2 font-mono text-[10px] text-white/35 uppercase tracking-widest text-center">
                Screenshot report ready
              </div>
            )}
          </div>

          {/* S/R Levels */}
          <div className="px-6 py-2">
            <p className="font-mono text-[10px] text-white/30 uppercase tracking-[0.3em] mb-1.5">S/R Levels</p>
            <div className="grid grid-cols-2 gap-x-4">
              <div className="space-y-1">
                {srLevels.resistance.slice(0, 2).map((r, i) => (
                  <div key={i} className="font-mono text-[11px]">
                    <span className="text-white/30">R{i + 1} </span>
                    <span className="text-rose-400">{cur}{r.toFixed(2)}</span>
                  </div>
                ))}
              </div>
              <div className="space-y-1">
                {srLevels.support.slice(0, 2).map((s, i) => (
                  <div key={i} className="font-mono text-[11px]">
                    <span className="text-white/30">S{i + 1} </span>
                    <span className="text-emerald-400">{cur}{s.toFixed(2)}</span>
                  </div>
                ))}
              </div>
              {!srLevels.resistance.length && !srLevels.support.length && (
                <span className="font-mono text-xs text-white/20 col-span-2">Awaiting data…</span>
              )}
            </div>
          </div>

          {/* Market Structure */}
          <div className="px-6 py-2">
            <p className="font-mono text-[10px] text-white/30 uppercase tracking-[0.3em] mb-1.5">Market Structure</p>
            <div className={`font-mono text-sm font-semibold mb-1 ${
              mtfBias === 'Strong Bull' || mtfBias === 'Bullish' ? 'text-emerald-400'
              : mtfBias === 'Strong Bear' || mtfBias === 'Bearish' ? 'text-rose-400'
              : 'text-white/40'
            }`}>
              {mtfBias}
            </div>
            <div className="font-mono text-[10px] text-white/30 tracking-wider truncate">
              {mtfStr || '—'}
            </div>
          </div>

        </div>
      </div>
    </div>
  )
}
