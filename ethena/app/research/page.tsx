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
import { API_BASE, researchAPI, sentimentAPI, type SentimentAnalysisResponse } from '@/lib/api'

// ─── Helpers ─────────────────────────────────────────────────────────────────
const sentimentColor = (score: number) =>
  score >= 0.6 ? 'text-indigo-400' : score >= 0.4 ? 'text-white/50' : 'text-red-400'

const sentimentBg = (score: number) =>
  score >= 0.6 ? 'bg-indigo-400/10 border-indigo-400/20' : score >= 0.4 ? 'bg-white/5 border-white/10' : 'bg-red-400/10 border-red-400/20'

const CARD = 'shine-surface group relative rounded-2xl border border-white/10 bg-white/[0.03] backdrop-blur-xl transition-all duration-500 overflow-hidden'
const CARD_GLOW = 'shine-surface group relative rounded-2xl border border-white/10 bg-white/[0.03] backdrop-blur-xl shadow-[0_0_24px_rgba(79,70,229,0.08)] hover:shadow-[0_0_32px_rgba(79,70,229,0.16)] transition-all duration-500 overflow-hidden'
const CONTROL_BTN = 'shine-btn relative overflow-hidden rounded-xl text-[12px] font-dm-mono font-bold tracking-widest uppercase transition-all duration-300'

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
    if (n >= 1e12) return `$${(n / 1e12).toFixed(2)}T`
    if (n >= 1e9) return `$${(n / 1e9).toFixed(2)}B`
    if (n >= 1e6) return `$${(n / 1e6).toFixed(2)}M`
    return `$${n.toLocaleString()}`
  }
  const numOrNull = (v: unknown) => {
    const n = Number(v)
    return Number.isFinite(n) ? n : null
  }

  const fetchSentiment = async (sym: string, mkt: string) => {
    setIsLoading(true)
    setError(null)
    setReportLink(null)
    setReportError(null)
    try {
      const json = await sentimentAPI.analyze(sym, mkt)
      setData(json)
      setSymbol(json?.symbol ?? sym)
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to fetch analysis')
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
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : 'Report generation failed'
      if (/Failed to fetch|NetworkError|ECONNREFUSED/i.test(message)) {
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
      setPageAnalyzeError(err instanceof Error ? err.message : 'Screenshot analysis failed')
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
                <div className="text-3xl font-mono font-bold text-white">${currentPrice.toFixed(2)}</div>
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
                <a href={reportLink} target="_blank" rel="noreferrer" className="flex items-center gap-1 text-[11px] font-dm-mono text-indigo-300 hover:text-indigo-200 uppercase tracking-widest">
                  OPEN <ExternalLink size={11} />
                </a>
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

          {/* Sentiment Cards */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {[
              { label: 'AI Sentiment', score: data.sentiment?.overall ?? 0.5, sub: data.sentiment?.summary ?? 'Neutral' },
              { label: 'Reddit Sentiment', score: data.reddit_sentiment?.score ?? 0.5, sub: `${data.reddit_sentiment?.mentions ?? 0} mentions` },
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

          {/* Supply Chain */}
          {data.supply_chain && (
            <div className={`${CARD_GLOW} p-5`}>
              <div className="flex items-center gap-2 mb-1">
                <div className="text-[11px] font-dm-mono text-white/30 uppercase tracking-widest">Supply Chain Intelligence</div>
                <span className="text-[10px] font-dm-mono px-2 py-0.5 bg-indigo-500/10 border border-indigo-500/20 rounded text-indigo-400 uppercase tracking-widest">Experimental</span>
              </div>
              <p className="text-[11px] font-dm-mono text-white/20 mb-4 tracking-tight uppercase">US: SEC filings · India: public source crawler</p>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {(['customers', 'suppliers'] as const).map(type => (
                  <div key={type} className={`${CARD} p-5`}>
                    <div className="text-[10px] font-dm-mono text-white/30 uppercase tracking-[0.2em] mb-4 capitalize">{type}</div>
                    <div className="space-y-2">
                      {(data.supply_chain?.[type] || []).map((item: any, i: number) => (
                        <div key={i} className="p-2.5 bg-white/[0.02] border border-white/[0.05] rounded-lg">
                          <div className="text-[12px] font-semibold text-white">{item.name}</div>
                          {item.evidence && <div className="text-[10px] text-white/40 mt-0.5">{item.evidence}</div>}
                        </div>
                      ))}
                      {(data.supply_chain?.[type] || []).length === 0 && (
                        <div className="text-[11px] text-white/25 py-2">No {type} found.</div>
                      )}
                    </div>
                  </div>
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
