'use client'

import { useEffect, useState } from 'react'
import { socialAPI, extractErrorMessage } from '@/lib/api'

interface NewsItem {
  title: string
  url: string
  date?: string
  source?: string
}

const DEFAULT_QUERY = 'stock market news'
const HEADLINE_LIMIT = 10

const sourceLabel = (source?: string) => {
  const raw = (source || 'Live Feed').trim()
  const collapsed = raw.replace(/\s+/g, ' ')
  if (collapsed.length <= 18) return collapsed
  return `${collapsed.slice(0, 18)}...`
}

const formatDate = (iso?: string) => {
  if (!iso) return '-- ---'
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return '-- ---'
  return d.toLocaleDateString('en-US', { day: '2-digit', month: 'short' }).toUpperCase()
}

const formatTime = (iso?: string) => {
  if (!iso) return '--:--'
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return '--:--'
  return d.toLocaleTimeString('en-US', {
    hour12: false,
    hour: '2-digit',
    minute: '2-digit',
  })
}

export default function NewsBoxPage() {
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [news, setNews] = useState<NewsItem[]>([])

  const loadNews = async () => {
    setIsLoading(true)
    setError(null)
    try {
      const res: any = await socialAPI.getNews(DEFAULT_QUERY, HEADLINE_LIMIT)
      const rows = Array.isArray(res?.articles) ? res.articles : []
      setNews(rows.slice(0, HEADLINE_LIMIT))
    } catch (err: unknown) {
      try {
        const cached: any = await socialAPI.getNewsCached(DEFAULT_QUERY, HEADLINE_LIMIT)
        const rows = Array.isArray(cached?.articles) ? cached.articles : []
        setNews(rows.slice(0, HEADLINE_LIMIT))
        setError(rows.length ? 'Live feed timed out. Showing cached headlines.' : 'Live feed timed out. No cached headlines available yet.')
      } catch (cacheErr: unknown) {
        setError(
          extractErrorMessage(err, extractErrorMessage(cacheErr, 'Failed to load news'))
        )
        setNews([])
      }
    } finally {
      setIsLoading(false)
    }
  }

  useEffect(() => {
    void loadNews()
  }, [])

  return (
    <div className="space-y-5 font-inter">
      <div className="rounded-2xl border border-white/10 bg-[linear-gradient(135deg,rgba(10,10,10,0.9),rgba(5,5,5,0.86))] px-4 md:px-5 py-4">
        <div className="flex items-start justify-between gap-4">
          <div>
            <div className="flex items-center gap-2 mb-1">
              <div className="w-1.5 h-1.5 rounded-full bg-blue-400 shadow-[0_0_10px_rgba(96,165,250,0.75)]" />
              <span className="font-dm-mono text-[10px] md:text-[11px] text-white/55 tracking-[0.2em] uppercase font-semibold">
                Intelligence Stream / Top Headlines
              </span>
            </div>
            <p className="font-inter text-[12px] md:text-[13px] text-white/38 leading-relaxed">
              Live scrape feed with the latest 10 market-moving headlines.
            </p>
          </div>

          <button
            type="button"
            onClick={loadNews}
            disabled={isLoading}
            className="shrink-0 font-dm-mono text-[10px] px-3 py-1.5 rounded-lg border tracking-[0.16em] transition-all border-blue-500/35 bg-blue-500/12 text-blue-200 hover:bg-blue-500/20 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {isLoading ? 'LOADING...' : 'REFRESH'}
          </button>
        </div>

        <div className="mt-3 flex items-center gap-2 text-[10px] font-dm-mono uppercase tracking-[0.16em] text-white/35">
          <span className="px-2 py-1 rounded border border-white/12 bg-white/[0.03]">10 Headline Limit</span>
          <span className="px-2 py-1 rounded border border-white/12 bg-white/[0.03]">Live Sources</span>
        </div>
      </div>

      <div className="space-y-2.5">
        {isLoading && (
          <div className="px-5 py-10 rounded-xl border border-white/12 bg-white/[0.03] text-center font-dm-mono text-[11px] text-white/45 uppercase tracking-[0.18em]">
            Fetching live headlines...
          </div>
        )}

        {error && !isLoading && (
          <div className="px-5 py-4 rounded-xl border border-rose-400/20 bg-rose-400/10 text-rose-100 text-sm">
            {error}
          </div>
        )}

        {!isLoading && !error && news.length === 0 && (
          <div className="px-5 py-10 rounded-xl border border-white/12 bg-white/[0.03] text-center font-dm-mono text-[11px] text-white/35 uppercase tracking-[0.16em]">
            No headlines available right now.
          </div>
        )}

        {!isLoading && !error &&
          news.slice(0, HEADLINE_LIMIT).map((item, idx) => (
            <a
              key={`${item.url || item.title || 'news'}-${idx}`}
              href={item.url}
              target="_blank"
              rel="noopener noreferrer"
              className="group relative overflow-hidden rounded-xl border border-white/15 bg-[linear-gradient(125deg,rgba(9,9,9,0.92),rgba(4,4,4,0.88))] px-4 md:px-5 py-4 hover:border-blue-400/35 transition-all"
            >
              <div className="pointer-events-none absolute inset-y-0 left-0 w-1 bg-gradient-to-b from-blue-400/0 via-blue-400/45 to-cyan-300/0 opacity-0 group-hover:opacity-100 transition-opacity" />

              <div className="flex items-start gap-4">
                <div className="shrink-0 w-[68px] text-right pt-0.5">
                  <div className="font-dm-mono text-[10px] text-white/35 tabular-nums uppercase tracking-wider">
                    {formatTime(item.date)}
                  </div>
                  <div className="font-dm-mono text-[9px] text-white/25 mt-0.5 uppercase tracking-wider">
                    {formatDate(item.date)}
                  </div>
                </div>

                <div className="w-px h-12 bg-white/12 shrink-0 self-center" />

                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-1.5">
                    <span className="font-dm-mono text-[9px] uppercase tracking-[0.14em] text-blue-200/85 px-2 py-0.5 rounded border border-blue-300/25 bg-blue-300/10">
                      {sourceLabel(item.source)}
                    </span>
                    <span className="font-dm-mono text-[9px] uppercase tracking-[0.14em] text-white/28">
                      #{String(idx + 1).padStart(2, '0')}
                    </span>
                  </div>

                  <p className="font-inter text-[14px] md:text-[15px] text-white/78 leading-snug group-hover:text-white transition-colors">
                    {item.title || 'Untitled headline'}
                  </p>
                </div>
              </div>
            </a>
          ))}
      </div>
    </div>
  )
}
