'use client'

import { useRef, useState } from 'react'
import html2canvas from 'html2canvas'
import ReactMarkdown from 'react-markdown'
import { motion } from 'framer-motion'
import {
  Search, Brain, TrendingUp, TrendingDown, DollarSign,
  RefreshCw, AlertTriangle, ExternalLink, Download, FileText,
  BarChart3, Shield, Activity, Camera, X
} from 'lucide-react'
import { API_BASE, researchAPI, sentimentAPI, extractErrorMessage, isLikelyNetworkError, type SentimentAnalysisResponse } from '@/lib/api'

// ─── Helpers ─────────────────────────────────────────────────────────────────
const sentimentColor = (score: number) =>
  score >= 0.6 ? 'text-indigo-400' : score >= 0.4 ? 'text-white/50' : 'text-red-400'

const sentimentBg = (score: number) =>
  score >= 0.6 ? 'bg-indigo-400/10 border-indigo-400/20' : score >= 0.4 ? 'bg-white/5 border-white/10' : 'bg-red-400/10 border-red-400/20'

const CARD = 'shine-surface group relative rounded-2xl border border-white/10 bg-white/[0.03] backdrop-blur-xl transition-all duration-500 overflow-hidden'
const CARD_GLOW = 'shine-surface group relative rounded-2xl border border-white/10 bg-white/[0.03] backdrop-blur-xl shadow-[0_0_24px_rgba(79,70,229,0.08)] hover:shadow-[0_0_32px_rgba(79,70,229,0.16)] transition-all duration-500 overflow-hidden'
const CONTROL_BTN = 'shine-btn relative overflow-hidden rounded-xl text-[12px] font-dm-mono font-bold tracking-widest uppercase transition-all duration-300'

const clamp = (value: number, min = 0, max = 100) => Math.min(max, Math.max(min, value))

const riskTone = (value: number) => {
  if (value >= 70) return { label: 'HIGH', cls: 'text-red-400 border-red-500/30 bg-red-500/10' }
  if (value >= 40) return { label: 'MEDIUM', cls: 'text-amber-300 border-amber-400/30 bg-amber-400/10' }
  return { label: 'LOW', cls: 'text-emerald-300 border-emerald-400/30 bg-emerald-400/10' }
}

const formatDate = (raw: unknown) => {
  if (!raw || typeof raw !== 'string') return 'TBD'
  const d = new Date(raw)
  if (Number.isNaN(d.getTime())) return 'TBD'
  return d.toLocaleDateString('en-US', { month: 'short', day: '2-digit', year: 'numeric' })
}

const normalizeSentimentResponse = (raw: any): SentimentAnalysisResponse => {
  const sentimentOverall =
    typeof raw?.sentiment?.overall === 'number'
      ? raw.sentiment.overall
      : typeof raw?.sentiment === 'number'
        ? raw.sentiment
        : typeof raw?.score === 'number'
          ? raw.score
          : 0.5

  const sentimentSummary =
    typeof raw?.sentiment?.summary === 'string'
      ? raw.sentiment.summary
      : typeof raw?.outlook === 'string'
        ? raw.outlook
        : typeof raw?.label === 'string'
          ? raw.label
          : 'Neutral'

  const redditMentions =
    typeof raw?.reddit_sentiment?.mentions === 'number'
      ? raw.reddit_sentiment.mentions
      : typeof raw?.reddit_posts_count === 'number'
        ? raw.reddit_posts_count
        : 0

  const redditScore =
    typeof raw?.reddit_sentiment?.score === 'number'
      ? raw.reddit_sentiment.score
      : sentimentOverall

  const marketData =
    raw?.market_data && typeof raw.market_data === 'object'
      ? raw.market_data
      : {}

  const normalized: SentimentAnalysisResponse = {
    ...raw,
    symbol: raw?.symbol || raw?.ticker,
    sentiment: {
      overall: sentimentOverall,
      summary: sentimentSummary,
    },
    reddit_sentiment: {
      score: redditScore,
      mentions: redditMentions,
    },
    market_data: marketData,
    recommendation: raw?.recommendation || 'HOLD',
    outlook: raw?.outlook || sentimentSummary || 'Neutral',
    news: raw?.news && typeof raw.news === 'object'
      ? raw.news
      : { articles: [] },
    supply_chain: raw?.supply_chain && typeof raw.supply_chain === 'object'
      ? raw.supply_chain
      : { customers: [], suppliers: [] },
  }

  return normalized
}

// ─── Stat Card ────────────────────────────────────────────────────────────────
function StatBox({ label, value, sub, color = 'white' }: { label: string; value: string; sub?: string; color?: string }) {
  return (
    <div className="p-4 rounded-xl border border-white/[0.07] bg-white/[0.02]">
      <div className="text-[10px] font-mono text-white/30 uppercase tracking-widest mb-2">{label}</div>
      <div className={`text-2xl font-mono font-bold text-${color}`}>{value}</div>
      {sub && <div className="text-[11px] text-white/30 mt-0.5">{sub}</div>}
    </div>
  )
}

// ─── Main Page ────────────────────────────────────────────────────────────────
export default function ResearchPage() {
  const researchPageRef = useRef<HTMLDivElement>(null)
  const [searchInput, setSearchInput] = useState('')
  const [symbol, setSymbol] = useState('')
  const [market, setMarket] = useState('us')
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [data, setData] = useState<SentimentAnalysisResponse | null>(null)
  const [reportLoading, setReportLoading] = useState(false)
  const [reportLink, setReportLink] = useState<string | null>(null)
  const [reportFilename, setReportFilename] = useState<string | null>(null)
  const [reportError, setReportError] = useState<string | null>(null)
  const [pageAnalyzeLoading, setPageAnalyzeLoading] = useState(false)
  const [pageAnalyzeError, setPageAnalyzeError] = useState<string | null>(null)
  const [pageAnalyzeReport, setPageAnalyzeReport] = useState<string | null>(null)
  const [expandedModalContent, setExpandedModalContent] = useState<string | null>(null)

  const marketData = data?.market_data || {}
  const currentPrice = marketData.current_price ?? data?.price ?? 0
  const dayChangePct = marketData.day_change_pct ?? data?.day_change_pct ?? 0
  const dayChange = marketData.day_change ?? data?.day_change ?? 0
  const companyName = data?.name || marketData.company_name || data?.symbol || ''
  const sym = market === 'us' ? '$' : '₹'

  const fmt = (v: any, suffix = '') => {
    if (v === null || v === undefined || v === '') return '—'
    const n = Number(v)
    if (isNaN(n)) return String(v)
    return n.toFixed(2) + suffix
  }
  const fmtLarge = (v: any) => {
    const n = Number(v)
    if (!v || isNaN(n)) return '—'
    const currency = sym
    if (n >= 1e12) return `${currency}${(n / 1e12).toFixed(2)}T`
    if (n >= 1e9) return `${currency}${(n / 1e9).toFixed(2)}B`
    if (n >= 1e6) return `${currency}${(n / 1e6).toFixed(2)}M`
    return `${currency}${n.toLocaleString()}`
  }
  const numOrNull = (v: unknown) => {
    const n = Number(v)
    return Number.isFinite(n) ? n : null
  }

  const targetPrice = numOrNull(marketData.target_mean_price)
  const wkHigh = numOrNull(marketData['52w_high'] || marketData.fiftyTwoWeekHigh)
  const wkLow = numOrNull(marketData['52w_low'] || marketData.fiftyTwoWeekLow)

  const valuationGapPct = targetPrice && currentPrice
    ? ((targetPrice - currentPrice) / currentPrice) * 100
    : null

  const valuationState =
    valuationGapPct === null
      ? 'No target data'
      : valuationGapPct >= 12
        ? 'Undervalued vs target'
        : valuationGapPct <= -12
          ? 'Overvalued vs target'
          : 'Near fair value'

  const rangeProgress = (wkHigh && wkLow && wkHigh > wkLow && currentPrice)
    ? clamp(((currentPrice - wkLow) / (wkHigh - wkLow)) * 100)
    : null

  const beta = numOrNull(marketData.beta)
  const debtToEq = numOrNull(marketData.debt_to_equity)
  const currentRatio = numOrNull(marketData.current_ratio)
  const dayMoveAbs = Math.abs(dayChangePct || 0)

  const riskScore = clamp(
    (beta !== null ? Math.min(40, Math.abs(beta - 1) * 35) : 10) +
    (debtToEq !== null ? Math.min(30, debtToEq / 8) : 8) +
    (currentRatio !== null ? (currentRatio < 1 ? 18 : 6) : 10) +
    Math.min(20, dayMoveAbs * 2)
  )
  const riskMeta = riskTone(riskScore)

  const earningsDate = typeof marketData.earnings_date === 'string' ? marketData.earnings_date : null
  const daysToEarnings = numOrNull(marketData.days_to_earnings)
  const exDividendDate = typeof marketData.ex_dividend_date === 'string' ? marketData.ex_dividend_date : null
  const volatility30d = numOrNull(marketData.volatility_30d)
  const fiftyDayAvg = numOrNull(marketData.fifty_day_avg)
  const twoHundredDayAvg = numOrNull(marketData.two_hundred_day_avg)

  const revenueGrowthPct = numOrNull(marketData.revenue_growth)
  const epsGrowthPct = numOrNull(marketData.eps_growth)
  const operatingMarginPct = numOrNull(marketData.operating_margins)
  const fcf = numOrNull(marketData.free_cashflow)

  const earningsQualityScore = clamp(
    (revenueGrowthPct !== null ? Math.max(0, Math.min(35, revenueGrowthPct * 120)) : 12) +
    (epsGrowthPct !== null ? Math.max(0, Math.min(30, epsGrowthPct * 100)) : 10) +
    (operatingMarginPct !== null ? Math.max(0, Math.min(20, operatingMarginPct * 90)) : 8) +
    (fcf !== null ? (fcf > 0 ? 15 : 4) : 8)
  )
  const earningsQualityTier = earningsQualityScore >= 70 ? 'STRONG' : earningsQualityScore >= 45 ? 'MODERATE' : 'WEAK'

  const trendTag = (() => {
    if (!currentPrice || fiftyDayAvg === null || twoHundredDayAvg === null) return 'Insufficient trend data'
    if (currentPrice > fiftyDayAvg && fiftyDayAvg > twoHundredDayAvg) return 'Strong Uptrend'
    if (currentPrice < fiftyDayAvg && fiftyDayAvg < twoHundredDayAvg) return 'Downtrend'
    return 'Range / Transition'
  })()

  const analystCount = numOrNull(marketData.analyst_count)
  const targetHigh = numOrNull(marketData.target_high_price)
  const targetLow = numOrNull(marketData.target_low_price)
  const targetMedian = numOrNull(marketData.target_median_price)
  const targetSpreadPct =
    targetHigh !== null && targetLow !== null && currentPrice
      ? ((targetHigh - targetLow) / currentPrice) * 100
      : null
  const analystConfidence = clamp(
    (analystCount !== null ? Math.min(60, analystCount * 4) : 12) +
    (targetSpreadPct !== null ? Math.max(0, 40 - targetSpreadPct) : 12)
  )

  const quickRatio = numOrNull(marketData.quick_ratio)
  const interestCoverage = numOrNull(marketData.interest_coverage)
  const balanceSheetSafety = clamp(
    (currentRatio !== null ? Math.min(35, currentRatio * 18) : 12) +
    (quickRatio !== null ? Math.min(25, quickRatio * 14) : 10) +
    (debtToEq !== null ? Math.max(0, 30 - debtToEq / 6) : 12) +
    (interestCoverage !== null ? Math.min(10, Math.max(0, interestCoverage)) : 6)
  )
  const balanceSheetTier = balanceSheetSafety >= 70 ? 'SAFE' : balanceSheetSafety >= 45 ? 'WATCH' : 'FRAGILE'

  const eventRiskLevel = (() => {
    if (daysToEarnings === null) return 'MEDIUM'
    if (daysToEarnings >= 0 && daysToEarnings <= 7) return 'HIGH'
    if (daysToEarnings >= 8 && daysToEarnings <= 21) return 'MEDIUM'
    return 'LOW'
  })()
  const eventRiskCls =
    eventRiskLevel === 'HIGH'
      ? 'text-red-300 border-red-500/40 bg-red-500/10'
      : eventRiskLevel === 'MEDIUM'
        ? 'text-amber-300 border-amber-400/40 bg-amber-400/10'
        : 'text-emerald-300 border-emerald-400/40 bg-emerald-400/10'

  const catalysts = [
    {
      label: 'Earnings',
      date: formatDate(earningsDate),
      sub: daysToEarnings === null
        ? 'Date unavailable'
        : daysToEarnings === 0
          ? 'Today'
        : daysToEarnings < 0
          ? `Occurred ${Math.abs(daysToEarnings)} days ago`
          : `In ${daysToEarnings} days`,
    },
    {
      label: 'Ex-Dividend',
      date: formatDate(exDividendDate),
      sub: exDividendDate ? 'Dividend eligibility cutoff' : 'Not announced',
    },
  ]

  const fetchSentiment = async (sym: string, mkt: string) => {
    setIsLoading(true)
    setError(null)
    setReportLink(null)
    setReportFilename(null)
    setReportError(null)
    try {
      const json = await sentimentAPI.analyze(sym, mkt)
      const normalized = normalizeSentimentResponse(json)
      setData(normalized)
      setSymbol(normalized?.symbol ?? sym)
    } catch (err: unknown) {
      setError(extractErrorMessage(err, 'Failed to fetch analysis'))
      setData(null)
    } finally {
      setIsLoading(false)
    }
  }

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault()
    const sym = searchInput.toUpperCase().trim()
    if (sym) { fetchSentiment(sym, market); setSearchInput('') }
  }

  const handleDownloadReport = async () => {
    setReportLoading(true)
    setReportError(null)
    try {
      if (!symbol) throw new Error('Select a symbol first')
      const report = (await researchAPI.generateReport({
        symbol,
        market,
        format: 'quantstats',
        range: '1y',
        benchmark: market === 'india' ? '^NSEI' : 'SPY',
      }))
      const downloadUrl = typeof report?.downloadUrl === 'string' ? String(report.downloadUrl) : ''
      const filename = typeof report?.filename === 'string'
        ? String(report.filename)
        : (downloadUrl ? downloadUrl.split('/').pop() || '' : '')

      if (!downloadUrl && !filename) throw new Error('Report not available')

      const fullUrl = filename
        ? researchAPI.downloadReport(filename)
        : (downloadUrl.startsWith('/') ? `${API_BASE}${downloadUrl}` : downloadUrl)
      setReportLink(fullUrl)
      setReportFilename(filename || null)
    } catch (err: unknown) {
      const message = extractErrorMessage(err, 'Report generation failed')
      if (isLikelyNetworkError(err)) {
        setReportError('Backend is unreachable. Start FastAPI on port 8001 and try again.')
      } else {
        setReportError(message)
      }
    } finally {
      setReportLoading(false)
    }
  }

  const captureResearchImage = async () => {
    if (!researchPageRef.current) throw new Error('Research panel not available for capture')
    const canvas = await html2canvas(researchPageRef.current, {
      backgroundColor: '#05070c',
      useCORS: true,
      scale: 1.2,
      logging: false,
    })
    return canvas.toDataURL('image/jpeg', 0.82)
  }

  const handleAnalyzeThisPage = async () => {
    if (!data || !symbol || pageAnalyzeLoading) return
    setPageAnalyzeLoading(true)
    setPageAnalyzeError(null)

    try {
      const imageDataUrl = await captureResearchImage()
      const res = await researchAPI.interpretImage({
        symbol,
        market: market as 'us' | 'india',
        imageDataUrl,
        context: {
          recommendation: data.recommendation,
          outlook: data.outlook,
          sentiment: data.sentiment,
          currentPrice,
          dayChangePct,
          marketData,
        },
      })
      setPageAnalyzeReport(res.analysis)
    } catch (err) {
      setPageAnalyzeError(extractErrorMessage(err, 'Screenshot analysis failed'))
    } finally {
      setPageAnalyzeLoading(false)
    }
  }

  const suggestions = market === 'india' ? ['RELIANCE', 'TCS', 'INFY', 'HDFCBANK'] : ['AAPL', 'MSFT', 'GOOGL', 'NVDA', 'TSLA']

  return (
    <motion.div
      ref={researchPageRef}
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5 }}
      className="relative space-y-8 font-inter max-w-7xl mx-auto py-8"
    >
      {/* Header */}
      <div className="flex items-center justify-between pt-4">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <div className="w-1.5 h-1.5 rounded-full bg-indigo-500 shadow-[0_0_8px_rgba(99,102,241,0.6)]" />
            <span className="font-dm-mono text-[11px] text-white/50 tracking-[0.2em] uppercase font-semibold">Intelligence Retrieval / Synthesis</span>
          </div>
          <p className="font-inter text-[13px] text-white/30">AI-powered sentiment analysis · Reddit signals · Supply chain mapping</p>
        </div>
        {/* Market Toggle */}
        <div className="flex bg-black/60 rounded-xl p-1 border border-white/20 backdrop-blur-xl">
          {[{ id: 'us', label: 'US' }, { id: 'india', label: 'INDIA' }].map(m => (
            <button
              key={m.id}
              onClick={() => setMarket(m.id)}
              className={`px-6 py-2 rounded-lg text-[11px] font-dm-mono font-bold tracking-widest transition-all ${market === m.id ? 'bg-indigo-500/15 text-white shadow-[0_0_15px_rgba(99,102,241,0.1)]' : 'text-white/30 hover:text-white'}`}
            >
              {m.label}
            </button>
          ))}
        </div>
      </div>

      {/* Search Bar */}
      <form onSubmit={handleSearch} className={`${CARD_GLOW} flex items-center gap-3 px-5 py-3.5 focus-within:border-indigo-500/40`}>
        <Search size={18} className="text-white/30 shrink-0" />
        <input
          type="text"
          placeholder={`SEARCH ${market === 'india' ? 'NSE' : 'US'} TICKER (e.g. ${suggestions[0]})...`}
          value={searchInput}
          onChange={e => setSearchInput(e.target.value)}
          className="flex-1 bg-transparent text-white placeholder:text-white/20 font-dm-mono text-sm focus:outline-none tracking-wider"
        />
        <button type="submit" disabled={isLoading} 
          className={`${CONTROL_BTN} px-8 py-2 bg-indigo-500/10 border border-indigo-500/30 text-indigo-300 hover:bg-indigo-500/20 hover:border-indigo-500/50 shadow-[0_0_15px_rgba(99,102,241,0.14)]`}>
          {isLoading ? <RefreshCw size={13} className="animate-spin" /> : 'ANALYZE'}
        </button>
      </form>

      {/* Suggestions */}
      {!data && !isLoading && !error && (
        <div className="flex items-center gap-2 flex-wrap">
          <span className="text-[11px] font-mono text-white/25">Try:</span>
          {suggestions.map(s => (
            <button key={s} onClick={() => fetchSentiment(s, market)}
              className="px-3 py-1 bg-white/[0.03] hover:bg-white/[0.07] border border-white/[0.08] rounded-lg text-[12px] font-mono text-white/50 hover:text-white transition-all">
              {s}
            </button>
          ))}
        </div>
      )}

      {/* Error */}
      {error && (
        <div className="p-4 bg-red-500/10 border border-red-500/20 rounded-xl flex items-center gap-3">
          <AlertTriangle className="text-red-400 shrink-0" size={20} />
          <div>
            <div className="text-sm font-mono font-semibold text-white">Analysis Failed</div>
            <div className="text-[12px] text-white/50 mt-0.5">{error}</div>
          </div>
        </div>
      )}

      {/* Loading */}
      {isLoading && (
        <div className="p-12 flex flex-col items-center justify-center">
          <div className="relative mb-4">
            <Brain size={40} className="text-indigo-400" />
            <div className="absolute -inset-2 bg-indigo-500/10 blur-xl rounded-full" />
          </div>
          <h3 className="text-sm font-dm-mono text-white mb-1 uppercase tracking-widest">Analyzing {searchInput || symbol}...</h3>
          <p className="text-[11px] font-dm-mono text-white/30 animate-pulse uppercase tracking-[0.2em]">Fetching market data · Reddit sentiment · AI synthesis</p>
        </div>
      )}

      {/* Results */}
      {data && !isLoading && (
        <div className="space-y-5">
          {/* Symbol Header */}
          <div className={`${CARD_GLOW} p-5`}>
            <div className="flex items-start justify-between">
              <div>
                <h2 className="text-3xl font-mono font-bold text-white">{data.symbol}</h2>
                <p className="text-white/40 text-sm mt-0.5">{companyName}</p>
              </div>
              <div className="text-right">
                <div className="text-3xl font-mono font-bold text-white">{sym}{currentPrice.toFixed(2)}</div>
                <div className={`flex items-center justify-end gap-1 text-sm font-mono mt-0.5 ${dayChangePct >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>
                  {dayChangePct >= 0 ? <TrendingUp size={14} /> : <TrendingDown size={14} />}
                  {dayChangePct >= 0 ? '+' : ''}{dayChangePct.toFixed(2)}%
                </div>
              </div>
            </div>
            <div className="flex items-center gap-3 mt-4">
              <button onClick={handleDownloadReport} disabled={reportLoading}
                className={`${CONTROL_BTN} flex items-center gap-2 px-6 py-2.5 bg-indigo-500/10 border border-indigo-500/30 text-indigo-300 hover:bg-indigo-500/20 hover:border-indigo-500/50 shadow-[0_0_15px_rgba(99,102,241,0.14)]`}>
                <Download size={13} />
                {reportLoading ? 'GENERATING…' : 'DOWNLOAD_QUANTSTATS_REPORT'}
              </button>
              <button
                onClick={handleAnalyzeThisPage}
                disabled={pageAnalyzeLoading}
                className={`${CONTROL_BTN} flex items-center gap-2 px-6 py-2.5 bg-blue-900/80 border border-blue-500/30 text-blue-200 hover:bg-blue-800/90 hover:border-blue-400/40 shadow-[0_0_18px_rgba(59,130,246,0.2)] disabled:opacity-50`}
              >
                <Camera size={13} />
                {pageAnalyzeLoading ? 'ANALYZING_THIS_PAGE…' : 'ANALYZE_THIS_PAGE'}
              </button>
              {reportLink && (
                <div className="flex items-center gap-3">
                  <a href={reportLink} target="_blank" rel="noreferrer" className="flex items-center gap-1 text-[11px] font-dm-mono text-indigo-300 hover:text-indigo-200 uppercase tracking-widest">
                    OPEN <ExternalLink size={11} />
                  </a>
                  <a
                    href={reportLink}
                    download={reportFilename || undefined}
                    className="flex items-center gap-1 text-[11px] font-dm-mono text-emerald-300 hover:text-emerald-200 uppercase tracking-widest"
                  >
                    DOWNLOAD <Download size={11} />
                  </a>
                </div>
              )}
              {reportError && <span className="text-[11px] font-dm-mono text-red-400 uppercase tracking-widest">{reportError}</span>}
            </div>
          </div>

          {pageAnalyzeError && (
            <div className="p-3 rounded-xl border border-red-500/40 bg-red-500/10 text-red-300 text-[12px] font-dm-mono">
              {pageAnalyzeError}
            </div>
          )}

          {pageAnalyzeReport && (
            <div className={`${CARD_GLOW} p-4 border-blue-500/20 bg-blue-500/5 text-[13px] text-white/85 leading-relaxed shadow-[0_0_40px_rgba(59,130,246,0.1)]`}>
              <div className="flex items-center justify-between mb-2">
                <div className="text-[11px] font-dm-mono text-blue-300 uppercase tracking-widest">AI Screenshot Research Report</div>
                <button
                  onClick={() => setExpandedModalContent(pageAnalyzeReport)}
                  className="px-3 py-1 text-[10px] font-dm-mono uppercase tracking-widest rounded-lg border border-blue-500/30 text-blue-300 hover:bg-blue-500/10 transition-all"
                >
                  Expand → Full
                </button>
              </div>
              <div className="prose prose-invert prose-sm max-w-none prose-p:text-white/80 line-clamp-6">
                <ReactMarkdown>{pageAnalyzeReport}</ReactMarkdown>
              </div>
            </div>
          )}

          <div className={`rounded-xl border px-4 py-3 flex items-center justify-between gap-4 ${eventRiskCls}`}>
            <div>
              <div className="text-[10px] font-dm-mono uppercase tracking-[0.2em]">Event Risk Banner</div>
              <div className="text-[12px] text-white/85 mt-0.5">
                {daysToEarnings === null
                  ? 'Upcoming earnings date unavailable from yfinance.'
                  : daysToEarnings === 0
                    ? 'Earnings today. Expect elevated intraday and post-close volatility.'
                  : daysToEarnings < 0
                    ? `Earnings event passed ${Math.abs(daysToEarnings)} days ago.`
                    : `Earnings in ${daysToEarnings} days. Expect volatility expansion around event window.`}
              </div>
            </div>
            <div className="text-right">
              <div className="text-[10px] font-dm-mono uppercase tracking-widest">Risk</div>
              <div className="text-[14px] font-dm-mono font-bold">{eventRiskLevel}</div>
            </div>
          </div>

          {/* Sentiment Cards */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {[
              { label: 'AI Sentiment', score: data.sentiment?.overall ?? 0.5, sub: data.sentiment?.summary ?? 'Neutral' },
              {
                label: 'Reddit Sentiment',
                score: data.reddit_sentiment?.score ?? 0.5,
                sub: (data.reddit_sentiment?.mentions ?? 0) > 0 ? `${data.reddit_sentiment?.mentions ?? 0} mentions` : '-',
              },
            ].map(card => (
              <div key={card.label} className={`${CARD} p-4 ${sentimentBg(card.score)}`}>
                <div className="text-[10px] font-mono text-white/30 uppercase tracking-widest mb-2">{card.label}</div>
                <div className={`text-3xl font-mono font-bold ${sentimentColor(card.score)}`}>
                  {(card.score * 100).toFixed(0)}%
                </div>
                <div className="text-[11px] text-white/40 mt-0.5">{card.sub}</div>
              </div>
            ))}
            <div className={`${CARD} p-4`}>
              <div className="text-[10px] font-mono text-white/30 uppercase tracking-widest mb-2">Recommendation</div>
              <div className="text-2xl font-mono font-bold text-white uppercase">{data.recommendation ?? 'HOLD'}</div>
              <div className="text-[11px] text-white/40 mt-0.5">{data.outlook ?? 'Neutral'}</div>
            </div>
          </div>

          {/* Company Description + AI Summary */}
          {(marketData.business_summary || data.summary) && (
            <div className={`${CARD_GLOW} p-5 space-y-4`}>
              {marketData.business_summary && (
                <div>
                  <div className="text-[11px] font-mono text-white/30 uppercase tracking-widest mb-2">Company Description</div>
                  <p className="text-[13px] text-white/70 leading-relaxed">{marketData.business_summary}</p>
                </div>
              )}
              {data.summary && (
                <div>
                  <div className="text-[11px] font-mono text-white/30 uppercase tracking-widest mb-2">AI Summary</div>
                  <p className="text-[13px] text-white/70 leading-relaxed">{data.summary}</p>
                </div>
              )}
            </div>
          )}

          {/* Company Snapshot */}
            <div className={`${CARD_GLOW} p-5`}>
            <div className="text-[11px] font-dm-mono text-white/30 uppercase tracking-[0.2em] mb-4">Company Snapshot</div>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              {[
                { label: 'Market Cap', value: fmtLarge(marketData.market_cap) },
                { label: 'Sector', value: String(marketData.sector ?? '—') },
                { label: 'Industry', value: String(marketData.industry ?? '—') },
                { label: 'P/E Ratio', value: fmt(marketData.pe_ratio) },
                { label: 'Forward P/E', value: fmt(marketData.forward_pe) },
                { label: 'EPS', value: fmt(marketData.eps) },
                { label: 'Beta', value: fmt(marketData.beta) },
                { label: 'Dividend Yield', value: fmt(numOrNull(marketData.dividend_yield) !== null ? numOrNull(marketData.dividend_yield)! * 100 : null, '%') },
                { label: '52W High', value: `${sym}${fmt(marketData['52w_high'] || marketData.fiftyTwoWeekHigh)}` },
                { label: '52W Low', value: `${sym}${fmt(marketData['52w_low'] || marketData.fiftyTwoWeekLow)}` },
                { label: 'Revenue', value: fmtLarge(marketData.revenue) },
                { label: 'Profit Margin', value: fmt(numOrNull(marketData.profit_margin) !== null ? numOrNull(marketData.profit_margin)! * 100 : null, '%') },
                { label: 'ROE', value: fmt(numOrNull(marketData.roe) !== null ? numOrNull(marketData.roe)! * 100 : null, '%') },
                { label: 'Debt/Equity', value: fmt(marketData.debt_to_equity) },
                { label: 'Target Price', value: `${sym}${fmt(marketData.target_mean_price)}` },
                { label: 'Recommendation', value: String(marketData.recommendation_key ?? '—') },
              ].map(({ label, value }) => (
                <div key={label} className="shine-surface p-3.5 bg-white/[0.02] border border-white/[0.05] rounded-xl group/snap hover:bg-white/[0.04] transition-colors">
                  <div className="text-[10px] font-dm-mono text-white/20 uppercase tracking-widest mb-1 group-hover/snap:text-white/40 transition-colors uppercase">{label}</div>
                  <div className="text-[14px] font-dm-mono text-white group-hover/snap:text-indigo-400 transition-colors">{value}</div>
                </div>
              ))}
            </div>
          </div>

          {/* Valuation / Risk / Catalysts */}
          <div className="grid grid-cols-1 xl:grid-cols-3 gap-4">
            <div className={`${CARD_GLOW} p-5`}>
              <div className="text-[11px] font-dm-mono text-white/30 uppercase tracking-[0.2em] mb-4">Valuation Band</div>
              <div className="space-y-3">
                <div className="flex items-baseline justify-between">
                  <span className="text-[11px] text-white/45">Current</span>
                  <span className="font-dm-mono text-white">{sym}{fmt(currentPrice)}</span>
                </div>
                <div className="flex items-baseline justify-between">
                  <span className="text-[11px] text-white/45">Target Mean</span>
                  <span className="font-dm-mono text-indigo-300">{sym}{fmt(targetPrice)}</span>
                </div>
                <div className="flex items-baseline justify-between">
                  <span className="text-[11px] text-white/45">Gap</span>
                  <span className={`font-dm-mono ${valuationGapPct !== null && valuationGapPct >= 0 ? 'text-emerald-300' : 'text-red-300'}`}>
                    {valuationGapPct === null ? '—' : `${valuationGapPct >= 0 ? '+' : ''}${valuationGapPct.toFixed(1)}%`}
                  </span>
                </div>
                <div className="pt-2">
                  <div className="h-2 rounded-full bg-white/10 border border-white/10 overflow-hidden">
                    <div
                      className="h-full bg-gradient-to-r from-indigo-500/70 via-indigo-400/70 to-cyan-300/70"
                      style={{ width: `${rangeProgress ?? 0}%` }}
                    />
                  </div>
                  <div className="mt-2 text-[11px] text-white/45">52W Position: {rangeProgress === null ? 'N/A' : `${rangeProgress.toFixed(0)}%`}</div>
                  <div className="text-[11px] text-indigo-300 mt-1">{valuationState}</div>
                </div>
              </div>
            </div>

            <div className={`${CARD_GLOW} p-5`}>
              <div className="flex items-center justify-between mb-4">
                <div className="text-[11px] font-dm-mono text-white/30 uppercase tracking-[0.2em]">Risk Dashboard</div>
                <span className={`px-2 py-1 text-[10px] font-dm-mono rounded border uppercase tracking-widest ${riskMeta.cls}`}>{riskMeta.label}</span>
              </div>
              <div className="space-y-3">
                <div className="flex items-baseline justify-between"><span className="text-[11px] text-white/45">Risk Score</span><span className="font-dm-mono text-white">{riskScore.toFixed(0)}/100</span></div>
                <div className="flex items-baseline justify-between"><span className="text-[11px] text-white/45">Beta</span><span className="font-dm-mono text-white">{fmt(beta)}</span></div>
                <div className="flex items-baseline justify-between"><span className="text-[11px] text-white/45">Debt / Equity</span><span className="font-dm-mono text-white">{fmt(debtToEq)}</span></div>
                <div className="flex items-baseline justify-between"><span className="text-[11px] text-white/45">Current Ratio</span><span className="font-dm-mono text-white">{fmt(currentRatio)}</span></div>
                <div className="flex items-baseline justify-between"><span className="text-[11px] text-white/45">1D Volatility</span><span className="font-dm-mono text-white">{Math.abs(dayChangePct).toFixed(2)}%</span></div>
              </div>
            </div>

            <div className={`${CARD_GLOW} p-5`}>
              <div className="text-[11px] font-dm-mono text-white/30 uppercase tracking-[0.2em] mb-4">Catalyst Timeline</div>
              <div className="space-y-3">
                {catalysts.map((event) => (
                  <div key={event.label} className="rounded-xl border border-white/[0.06] bg-white/[0.02] p-3">
                    <div className="flex items-center justify-between gap-3">
                      <span className="text-[11px] text-white/55 uppercase tracking-widest font-dm-mono">{event.label}</span>
                      <span className="text-[12px] font-dm-mono text-white">{event.date}</span>
                    </div>
                    <div className="text-[11px] text-indigo-300 mt-1">{event.sub}</div>
                  </div>
                ))}
              </div>
            </div>
          </div>

          <div className="grid grid-cols-1 xl:grid-cols-2 gap-4">
            <div className={`${CARD_GLOW} p-5`}>
              <div className="flex items-center justify-between mb-4">
                <div className="text-[11px] font-dm-mono text-white/30 uppercase tracking-[0.2em]">Earnings & Quality</div>
                <span className="text-[10px] font-dm-mono uppercase tracking-widest text-indigo-300">{earningsQualityTier}</span>
              </div>
              <div className="space-y-3">
                <div className="flex items-baseline justify-between"><span className="text-[11px] text-white/45">Earnings Date</span><span className="font-dm-mono text-white">{formatDate(earningsDate)}</span></div>
                <div className="flex items-baseline justify-between"><span className="text-[11px] text-white/45">Days to Earnings</span><span className="font-dm-mono text-white">{daysToEarnings === null ? 'N/A' : daysToEarnings === 0 ? 'Today' : String(daysToEarnings)}</span></div>
                <div className="flex items-baseline justify-between"><span className="text-[11px] text-white/45">Quality Score</span><span className="font-dm-mono text-white">{earningsQualityScore.toFixed(0)}/100</span></div>
                <div className="flex items-baseline justify-between"><span className="text-[11px] text-white/45">Revenue Growth</span><span className="font-dm-mono text-white">{fmt(revenueGrowthPct !== null ? revenueGrowthPct * 100 : null, '%')}</span></div>
                <div className="flex items-baseline justify-between"><span className="text-[11px] text-white/45">EPS Growth</span><span className="font-dm-mono text-white">{fmt(epsGrowthPct !== null ? epsGrowthPct * 100 : null, '%')}</span></div>
                <div className="flex items-baseline justify-between"><span className="text-[11px] text-white/45">Operating Margin</span><span className="font-dm-mono text-white">{fmt(operatingMarginPct !== null ? operatingMarginPct * 100 : null, '%')}</span></div>
                <div className="flex items-baseline justify-between"><span className="text-[11px] text-white/45">Free Cash Flow</span><span className="font-dm-mono text-white">{fmtLarge(fcf)}</span></div>
              </div>
            </div>

            <div className={`${CARD_GLOW} p-5`}>
              <div className="flex items-center justify-between mb-4">
                <div className="text-[11px] font-dm-mono text-white/30 uppercase tracking-[0.2em]">Trend Regime Tag</div>
                <span className="text-[10px] font-dm-mono uppercase tracking-widest text-indigo-300">{trendTag}</span>
              </div>
              <div className="space-y-3">
                <div className="flex items-baseline justify-between"><span className="text-[11px] text-white/45">Current Price</span><span className="font-dm-mono text-white">{sym}{fmt(currentPrice)}</span></div>
                <div className="flex items-baseline justify-between"><span className="text-[11px] text-white/45">50D Average</span><span className="font-dm-mono text-white">{sym}{fmt(fiftyDayAvg)}</span></div>
                <div className="flex items-baseline justify-between"><span className="text-[11px] text-white/45">200D Average</span><span className="font-dm-mono text-white">{sym}{fmt(twoHundredDayAvg)}</span></div>
                <div className="flex items-baseline justify-between"><span className="text-[11px] text-white/45">30D Volatility</span><span className="font-dm-mono text-white">{fmt(volatility30d !== null ? volatility30d * 100 : null, '%')}</span></div>
              </div>
            </div>

            <div className={`${CARD_GLOW} p-5`}>
              <div className="flex items-center justify-between mb-4">
                <div className="text-[11px] font-dm-mono text-white/30 uppercase tracking-[0.2em]">Analyst Dispersion</div>
                <span className="text-[10px] font-dm-mono uppercase tracking-widest text-indigo-300">{analystConfidence.toFixed(0)}% confidence</span>
              </div>
              <div className="space-y-3">
                <div className="flex items-baseline justify-between"><span className="text-[11px] text-white/45">Analyst Count</span><span className="font-dm-mono text-white">{fmt(analystCount)}</span></div>
                <div className="flex items-baseline justify-between"><span className="text-[11px] text-white/45">Target Low</span><span className="font-dm-mono text-white">{sym}{fmt(targetLow)}</span></div>
                <div className="flex items-baseline justify-between"><span className="text-[11px] text-white/45">Target Median</span><span className="font-dm-mono text-white">{sym}{fmt(targetMedian)}</span></div>
                <div className="flex items-baseline justify-between"><span className="text-[11px] text-white/45">Target High</span><span className="font-dm-mono text-white">{sym}{fmt(targetHigh)}</span></div>
                <div className="flex items-baseline justify-between"><span className="text-[11px] text-white/45">Spread %</span><span className="font-dm-mono text-white">{fmt(targetSpreadPct, '%')}</span></div>
              </div>
            </div>

            <div className={`${CARD_GLOW} p-5`}>
              <div className="flex items-center justify-between mb-4">
                <div className="text-[11px] font-dm-mono text-white/30 uppercase tracking-[0.2em]">Balance Sheet Safety</div>
                <span className="text-[10px] font-dm-mono uppercase tracking-widest text-indigo-300">{balanceSheetTier}</span>
              </div>
              <div className="space-y-3">
                <div className="flex items-baseline justify-between"><span className="text-[11px] text-white/45">Safety Score</span><span className="font-dm-mono text-white">{balanceSheetSafety.toFixed(0)}/100</span></div>
                <div className="flex items-baseline justify-between"><span className="text-[11px] text-white/45">Debt / Equity</span><span className="font-dm-mono text-white">{fmt(debtToEq)}</span></div>
                <div className="flex items-baseline justify-between"><span className="text-[11px] text-white/45">Current Ratio</span><span className="font-dm-mono text-white">{fmt(currentRatio)}</span></div>
                <div className="flex items-baseline justify-between"><span className="text-[11px] text-white/45">Quick Ratio</span><span className="font-dm-mono text-white">{fmt(quickRatio)}</span></div>
                <div className="flex items-baseline justify-between"><span className="text-[11px] text-white/45">Interest Coverage</span><span className="font-dm-mono text-white">{fmt(interestCoverage)}</span></div>
              </div>
            </div>
          </div>

          {/* Recent News */}
          {(data.news?.articles || []).length > 0 && (
              <div className={`${CARD_GLOW} p-5`}>
              <div className="text-[11px] font-dm-mono text-white/30 uppercase tracking-[0.2em] mb-4">Recent News</div>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {(data.news?.articles || []).map((article: any, idx: number) => (
                  <a
                    key={idx}
                    href={article.url}
                    target="_blank"
                    rel="noreferrer"
                    className="block p-4 bg-white/[0.02] border border-white/[0.06] rounded-xl hover:bg-white/[0.05] hover:border-white/[0.12] transition-all group"
                  >
                    <div className="flex items-start justify-between gap-3">
                      <div className="flex-1 min-w-0">
                        <div className="text-[14px] font-semibold text-white group-hover:text-indigo-400 transition-colors line-clamp-2">{article.title || 'Untitled'}</div>
                        <div className="text-[10px] font-dm-mono text-white/25 mt-1 uppercase tracking-widest">{article.source || 'NEWS'} · {article.published || 'LIVE'}</div>
                      </div>
                      <ExternalLink size={13} className="text-white/20 shrink-0 mt-0.5" />
                    </div>
                    {article.snippet && <p className="text-[11px] text-white/40 mt-2 line-clamp-2">{article.snippet}</p>}
                  </a>
                ))}
              </div>
            </div>
          )}

        </div>
      )}
      {expandedModalContent && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm p-4"
          onClick={() => setExpandedModalContent(null)}
        >
          <div
            className="relative w-full max-w-4xl max-h-[90vh] bg-gray-900/95 border border-white/20 rounded-2xl p-8 overflow-y-auto"
            onClick={(e) => e.stopPropagation()}
          >
            <button
              onClick={() => setExpandedModalContent(null)}
              className="absolute top-6 right-6 w-8 h-8 flex items-center justify-center rounded-lg border border-white/20 text-white/60 hover:text-white hover:bg-white/10 transition-all"
              aria-label="Close modal"
            >
              <X size={20} />
            </button>

            <h2 className="text-2xl font-dm-mono font-bold text-white mb-6 pr-12">Research Screenshot Analysis</h2>

            <div className="prose prose-invert max-w-none">
              <ReactMarkdown>{expandedModalContent}</ReactMarkdown>
            </div>
          </div>
        </div>
      )}

      <style jsx global>{`
        .shine-btn,
        .shine-surface {
          isolation: isolate;
        }

        .shine-btn::after,
        .shine-surface::before,
        .shine-surface::after {
          content: none !important;
        }
      `}</style>
    </motion.div>
  )
}
