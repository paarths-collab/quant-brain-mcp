import { useEffect, useMemo, useState } from 'react';
import { Globe as GlobeIcon, RefreshCw, ArrowUpRight, ArrowDownRight } from 'lucide-react';
import { fredAPI, treemapAPI } from '@/api';

type GlobalItem = {
  id: string;
  label: string;
  category: string;
};

type GlobalPoint = {
  id: string;
  label: string;
  category: string;
  value: number | null;
  changePct: number | null;
  date?: string | null;
  updatedAt?: string | null;
  status?: string | null;
  message?: string | null;
};

type IndiaIndex = {
  symbol: string;
  name: string;
  price: number | null;
  changePercent: number | null;
};

const GLOBAL_SERIES: GlobalItem[] = [
  { id: 'SP500', label: 'S&P 500', category: 'Indices' },
  { id: 'NASDAQ100', label: 'NASDAQ 100', category: 'Indices' },
  { id: 'DJIA', label: 'Dow Jones', category: 'Indices' },
  { id: 'VIXCLS', label: 'VIX', category: 'Volatility' },
  { id: 'DGS10', label: 'US 10Y', category: 'Rates' },
  { id: 'DGS2', label: 'US 2Y', category: 'Rates' },
  { id: 'FEDFUNDS', label: 'Fed Funds', category: 'Rates' },
  { id: 'DGS30', label: 'US 30Y', category: 'Rates' },
  { id: 'DPRIME', label: 'Prime Rate', category: 'Rates' },
  { id: 'T10Y2Y', label: '10Y-2Y Spread', category: 'Spreads' },
  { id: 'T10YIE', label: '10Y Breakeven Inflation', category: 'Spreads' },
  { id: 'DCOILWTICO', label: 'WTI Crude', category: 'Commodities' },
  { id: 'DCOILBRENTEU', label: 'Brent Crude', category: 'Commodities' },
  { id: 'GOLDPMGBD228NLBM', label: 'Gold', category: 'Commodities' },
  { id: 'NASDAQQSLVO', label: 'Silver Index', category: 'Commodities' },
  { id: 'GASREGW', label: 'US Gasoline', category: 'Commodities' },
  { id: 'DEXUSEU', label: 'USD/EUR', category: 'FX' },
  { id: 'DEXJPUS', label: 'JPY/USD', category: 'FX' },
  { id: 'DEXUSUK', label: 'USD/GBP', category: 'FX' },
  { id: 'UNRATE', label: 'Unemployment Rate', category: 'Labor' },
  { id: 'EMRATIO', label: 'Employment-Population Ratio', category: 'Labor' },
  { id: 'PAYEMS', label: 'Nonfarm Payrolls', category: 'Labor' },
  { id: 'CPIAUCSL', label: 'CPI', category: 'Macro' },
  { id: 'GDP', label: 'GDP', category: 'Macro' },
  { id: 'INDPRO', label: 'Industrial Production', category: 'Macro' },
  { id: 'M2SL', label: 'M2 Money Stock', category: 'Liquidity' },
];

export default function Globe() {
  const [data, setData] = useState<GlobalPoint[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [lastRefresh, setLastRefresh] = useState<string | null>(null);
  const [newsLoading, setNewsLoading] = useState(false);
  const [newsError, setNewsError] = useState<string | null>(null);
  const [trending, setTrending] = useState<any | null>(null);
  const [articles, setArticles] = useState<any[]>([]);
  const [newsFilter, setNewsFilter] = useState('');
  const [seriesNews, setSeriesNews] = useState<Record<string, any>>({});
  const [seriesNewsLoading, setSeriesNewsLoading] = useState(false);
  const [seriesNewsError, setSeriesNewsError] = useState<string | null>(null);
  const [indiaIndices, setIndiaIndices] = useState<IndiaIndex[]>([]);
  const [indiaError, setIndiaError] = useState<string | null>(null);

  const normalizeSeriesData = (raw: any): Record<string, any> => {
    if (!raw) return {};
    if (Array.isArray(raw)) {
      return raw.reduce<Record<string, any>>((acc, item) => {
        const key = item?.series_id || item?.id;
        if (key) acc[key] = item;
        return acc;
      }, {});
    }
    if (typeof raw === 'object') return raw as Record<string, any>;
    return {};
  };

  const toNumber = (value: any): number | null => {
    if (value === null || value === undefined) return null;
    const parsed = typeof value === 'number' ? value : Number(value);
    return Number.isFinite(parsed) ? parsed : null;
  };

  const fetchGlobal = async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await fredAPI.getLatestCached(GLOBAL_SERIES.map(s => s.id), 12);
      const raw = normalizeSeriesData(response.data?.data);
      const mapped: GlobalPoint[] = GLOBAL_SERIES.map((item) => {
        const entry = raw[item.id];
        return {
          id: item.id,
          label: item.label,
          category: item.category,
          value: toNumber(entry?.value),
          changePct: toNumber(entry?.change_pct),
          date: entry?.date ?? null,
          updatedAt: entry?.updated_at ?? null,
          status: entry?.status ?? null,
          message: entry?.message ?? null,
        };
      });
      setData(mapped);
      const latest = mapped
        .map((item) => item.updatedAt || item.date)
        .filter(Boolean)
        .sort()
        .slice(-1)[0] as string | undefined;
      setLastRefresh(latest || null);
    } catch (err: any) {
      setError(err?.response?.data?.detail || 'Failed to load FRED data.');
      setData([]);
      setLastRefresh(null);
    } finally {
      setLoading(false);
    }
  };

  const fetchTrendingNews = async () => {
    setNewsLoading(true);
    setNewsError(null);
    try {
      const indexIds = GLOBAL_SERIES.filter(s => s.category === 'Indices').map(s => s.id);
      const response = await fredAPI.getTrendingNews(indexIds, 12, 8);
      const payload = response.data || {};
      if (payload.status === 'error') {
        setTrending(null);
        setArticles([]);
        setNewsError(payload.message || 'Unable to fetch trending news.');
      } else {
        setTrending(payload.trending || null);
        setArticles(payload.articles || []);
      }
    } catch (err: any) {
      setTrending(null);
      setArticles([]);
      setNewsError(err?.response?.data?.detail || 'Failed to load trending index news.');
    } finally {
      setNewsLoading(false);
    }
  };

  const fetchSeriesNews = async () => {
    setSeriesNewsLoading(true);
    setSeriesNewsError(null);
    try {
      const seriesIds = GLOBAL_SERIES.map(s => s.id);
      const response = await fredAPI.getSeriesNews(seriesIds, 12, 5);
      const payload = response.data?.data || {};
      setSeriesNews(payload);
    } catch (err: any) {
      setSeriesNews({});
      setSeriesNewsError(err?.response?.data?.detail || 'Failed to load series news.');
    } finally {
      setSeriesNewsLoading(false);
    }
  };

  const fetchIndiaBenchmarks = async () => {
    setIndiaError(null);
    try {
      const symbols = ['^NSEI', '^BSESN'];
      const results = await Promise.all(
        symbols.map(symbol =>
          treemapAPI
            .getStockDetails(symbol, 'india')
            .then((res) => ({
              symbol,
              name: symbol === '^NSEI' ? 'NIFTY 50' : 'SENSEX',
              price: typeof res.data?.price?.current === 'number'
                ? res.data.price.current
                : (typeof res.data?.price === 'number' ? res.data.price : null),
              changePercent: typeof res.data?.price?.change_percent === 'number'
                ? res.data.price.change_percent
                : (typeof res.data?.change_percent === 'number' ? res.data.change_percent : null),
            }))
            .catch(() => ({
              symbol,
              name: symbol === '^NSEI' ? 'NIFTY 50' : 'SENSEX',
              price: null,
              changePercent: null,
            }))
        )
      );
      setIndiaIndices(results);
    } catch (err: any) {
      setIndiaError(err?.response?.data?.detail || 'Failed to load Indian benchmarks.');
      setIndiaIndices([]);
    }
  };

  useEffect(() => {
    fetchGlobal();
    fetchTrendingNews();
    fetchSeriesNews();
    fetchIndiaBenchmarks();
  }, []);

  const categories = Array.from(new Set(GLOBAL_SERIES.map(s => s.category)));
  const hasAnyValue = data.some((item) => item.value !== null);
  const pulseStats = useMemo(() => {
    const valid = data.filter((d) => d.changePct !== null);
    const up = valid.filter((d) => (d.changePct ?? 0) > 0).length;
    const down = valid.filter((d) => (d.changePct ?? 0) < 0).length;
    const flat = valid.length - up - down;
    return { up, down, flat, total: data.length };
  }, [data]);

  const handleRefresh = () => {
    fetchGlobal();
    fetchTrendingNews();
    fetchSeriesNews();
    fetchIndiaBenchmarks();
  };

  const filteredArticles = useMemo(() => {
    const term = newsFilter.trim().toLowerCase();
    if (!term) return articles;
    return articles.filter((article) => {
      const title = String(article.title || '').toLowerCase();
      const summary = String(article.summary || '').toLowerCase();
      return title.includes(term) || summary.includes(term);
    });
  }, [articles, newsFilter]);

  const filteredSeriesNews = useMemo(() => {
    const term = newsFilter.trim().toLowerCase();
    if (!term) return seriesNews;
    const next: Record<string, any> = {};
    Object.keys(seriesNews || {}).forEach((key) => {
      const block = seriesNews[key];
      const articlesList = (block?.articles || []).filter((article: any) => {
        const title = String(article.title || '').toLowerCase();
        const summary = String(article.summary || '').toLowerCase();
        return title.includes(term) || summary.includes(term);
      });
      next[key] = { ...block, articles: articlesList };
    });
    return next;
  }, [seriesNews, newsFilter]);

  const seriesByCategory = useMemo(() => {
    const grouped: Record<string, GlobalItem[]> = {};
    GLOBAL_SERIES.forEach((item) => {
      if (!grouped[item.category]) grouped[item.category] = [];
      grouped[item.category].push(item);
    });
    return grouped;
  }, []);

  return (
    <div className="space-y-6">
      <div className="rounded-2xl border border-white/10 bg-gradient-to-br from-white/5 via-white/[0.02] to-transparent p-6">
        <div className="flex items-start justify-between gap-6">
          <div>
            <div className="inline-flex items-center gap-2 rounded-full border border-white/10 bg-white/5 px-3 py-1 text-xs text-white/70">
              <GlobeIcon size={14} className="text-orange-400" />
              Macro snapshot
            </div>
            <h1 className="font-display text-3xl font-bold text-white mt-3">Global Markets</h1>
            <p className="text-white/60 mt-1">FRED-backed macro dashboard (updates every 12 hours)</p>
            {lastRefresh && (
              <div className="text-xs text-white/40 mt-2">Latest cached update: {lastRefresh.split('T')[0]}</div>
            )}
          </div>
          <button
            onClick={handleRefresh}
            disabled={loading || newsLoading}
            className="p-2 bg-white/5 border border-white/10 rounded-lg hover:bg-white/10 disabled:opacity-50"
          >
            <RefreshCw className={`w-4 h-4 text-white ${loading ? 'animate-spin' : ''}`} />
          </button>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-4 gap-3 mt-6">
          <div className="p-4 rounded-xl border border-white/10 bg-black/30">
            <div className="text-xs text-white/50">Series tracked</div>
            <div className="text-2xl font-semibold text-white">{pulseStats.total}</div>
          </div>
          <div className="p-4 rounded-xl border border-white/10 bg-black/30">
            <div className="text-xs text-white/50">Up</div>
            <div className="text-2xl font-semibold text-green-400">{pulseStats.up}</div>
          </div>
          <div className="p-4 rounded-xl border border-white/10 bg-black/30">
            <div className="text-xs text-white/50">Down</div>
            <div className="text-2xl font-semibold text-red-400">{pulseStats.down}</div>
          </div>
          <div className="p-4 rounded-xl border border-white/10 bg-black/30">
            <div className="text-xs text-white/50">Flat</div>
            <div className="text-2xl font-semibold text-white">{pulseStats.flat}</div>
          </div>
        </div>
      </div>

      {error && <div className="p-4 bg-red-500/20 border border-red-500/50 rounded-lg text-red-400">{error}</div>}

      <div className="grid grid-cols-1 xl:grid-cols-[2.2fr,1fr] gap-6">
        <div className="space-y-6">
          <div className="bg-white/5 border border-white/10 rounded-xl p-6">
            <div className="flex items-center justify-between mb-4">
              <div>
                <h2 className="text-lg font-semibold text-white">Indian Benchmarks (Yahoo Finance)</h2>
                <p className="text-xs text-white/50">NIFTY 50 and SENSEX live snapshot</p>
              </div>
            </div>
            {indiaError && <div className="text-xs text-red-400 mb-3">{indiaError}</div>}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-px bg-white/10 rounded-xl overflow-hidden">
              {indiaIndices.map((item) => (
                <div key={item.symbol} className="p-4 bg-black/50">
                  <div className="text-xs text-white/50">{item.name}</div>
                  <div className="text-2xl font-semibold text-white">
                    {item.price !== null ? item.price.toLocaleString('en-IN', { maximumFractionDigits: 2 }) : '—'}
                  </div>
                  <div className={`text-sm flex items-center gap-1 ${item.changePercent !== null && item.changePercent >= 0 ? 'text-green-500' : 'text-red-500'}`}>
                    {item.changePercent === null ? '—' : (
                      <>
                        {item.changePercent >= 0 ? <ArrowUpRight size={14} /> : <ArrowDownRight size={14} />}
                        {item.changePercent >= 0 ? '+' : ''}{item.changePercent.toFixed(2)}%
                      </>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </div>

          {loading && data.length === 0 ? (
            <div className="p-12 bg-white/5 border border-white/10 rounded-xl text-center text-white/60">
              Loading global markets...
            </div>
          ) : !loading && !error && !hasAnyValue ? (
            <div className="p-12 bg-white/5 border border-white/10 rounded-xl text-center text-white/60">
              No cached global market data yet. Run the backend or wait for the first 12h refresh window.
            </div>
          ) : (
            categories.map((category) => (
              <div key={category} className="space-y-3">
                <div className="flex items-center gap-2">
                  <GlobeIcon className="text-orange-400" size={16} />
                  <h2 className="text-lg font-semibold text-white">{category}</h2>
                </div>
                <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-px bg-white/10 rounded-xl overflow-hidden">
                  {data.filter(d => d.category === category).map((item) => (
                    <div key={item.id} className="p-4 bg-black/40 hover:bg-white/10 transition-colors">
                      <div className="text-xs text-white/50">{item.label}</div>
                      <div className="text-xl font-semibold text-white">
                        {item.value !== null ? item.value.toLocaleString('en-US', { maximumFractionDigits: 4 }) : '—'}
                      </div>
                      <div className={`text-sm flex items-center gap-1 ${item.changePct !== null && item.changePct >= 0 ? 'text-green-500' : 'text-red-500'}`}>
                        {item.changePct === null ? '—' : (
                          <>
                            {item.changePct >= 0 ? <ArrowUpRight size={14} /> : <ArrowDownRight size={14} />}
                            {item.changePct >= 0 ? '+' : ''}{item.changePct.toFixed(2)}%
                          </>
                        )}
                      </div>
                      {item.status === 'error' && item.message && (
                        <div className="text-xs text-red-400 mt-1">{item.message}</div>
                      )}
                      {item.updatedAt && <div className="text-xs text-white/40 mt-1">Cached: {item.updatedAt.split('T')[0]}</div>}
                      {!item.updatedAt && item.date && <div className="text-xs text-white/40 mt-1">{item.date}</div>}
                    </div>
                  ))}
                </div>
              </div>
            ))
          )}
        </div>

        <div className="space-y-6">
          <div className="bg-white/5 border border-white/10 rounded-xl p-6">
            <div className="flex items-center justify-between mb-4">
              <div>
                <h2 className="text-lg font-semibold text-white">Trending Index News</h2>
                <p className="text-xs text-white/50">News for the most volatile index</p>
              </div>
              {trending?.title && (
                <div className="text-xs text-white/60 text-right">
                  <div>{trending.title}</div>
                  {typeof trending.change_pct === 'number' && (
                    <div className={trending.change_pct >= 0 ? 'text-green-400' : 'text-red-400'}>
                      {trending.change_pct >= 0 ? '+' : ''}{trending.change_pct.toFixed(2)}%
                    </div>
                  )}
                </div>
              )}
            </div>

            <div className="mb-4">
              <input
                value={newsFilter}
                onChange={(event) => setNewsFilter(event.target.value)}
                placeholder="Filter news (e.g., inflation, oil, tech)"
                className="w-full rounded-lg border border-white/10 bg-black/40 px-3 py-2 text-sm text-white/80 placeholder:text-white/30 focus:outline-none focus:ring-2 focus:ring-orange-500/50"
              />
            </div>
            {newsError && <div className="text-xs text-red-400 mb-3">{newsError}</div>}
            {newsLoading ? (
              <div className="text-white/60 text-sm">Loading trending news...</div>
            ) : filteredArticles.length === 0 ? (
              <div className="text-white/60 text-sm">No trending index news available.</div>
            ) : (
              <div className="space-y-3">
                {filteredArticles.map((article, idx) => (
                  <a
                    key={`${article.url}-${idx}`}
                    href={article.url}
                    target="_blank"
                    rel="noreferrer"
                    className="block p-4 bg-black/30 border border-white/10 rounded-lg hover:bg-white/10 transition-colors"
                  >
                    <div className="text-sm text-white font-medium">{article.title}</div>
                    <div className="text-xs text-white/50 mt-1">{article.date || ''}</div>
                    {article.summary && <div className="text-xs text-white/60 mt-2 line-clamp-2">{article.summary}</div>}
                  </a>
                ))}
              </div>
            )}
          </div>

          <div className="bg-white/5 border border-white/10 rounded-xl p-6">
            <div className="flex items-center justify-between mb-4">
              <div>
                <h2 className="text-lg font-semibold text-white">Series News (5 each)</h2>
                <p className="text-xs text-white/50">Headlines for every tracked series</p>
              </div>
            </div>

            {seriesNewsError && <div className="text-xs text-red-400 mb-3">{seriesNewsError}</div>}
            {seriesNewsLoading ? (
              <div className="text-white/60 text-sm">Loading series news...</div>
            ) : Object.keys(filteredSeriesNews || {}).length === 0 ? (
              <div className="text-white/60 text-sm">No series news available.</div>
            ) : (
              <div className="space-y-4">
        {Object.keys(seriesByCategory).map((category) => (
          <div key={category} className="border border-white/10 rounded-lg bg-black/40 overflow-hidden">
            <div className="px-4 py-2 border-b border-white/10 text-xs text-white/60">
              {category}
            </div>
            <div className="divide-y divide-white/10">
              {seriesByCategory[category].map((series) => {
                const block = filteredSeriesNews[series.id];
                const list = block?.articles || [];
                return (
                  <details key={series.id} className="px-4 py-3">
                    <summary className="cursor-pointer text-sm text-white font-medium">
                      {series.label}
                    </summary>
                    <div className="mt-3 space-y-2">
                      {block?.status === 'warming' ? (
                        <div className="text-xs text-white/50">Fetching news…</div>
                      ) : list.length === 0 ? (
                        <div className="text-xs text-white/50">No news available.</div>
                      ) : (
                        list.map((article: any, idx: number) => (
                          <a
                                    key={`${article.url}-${idx}`}
                                    href={article.url}
                                    target="_blank"
                                    rel="noreferrer"
                                    className="block p-3 rounded-lg bg-black/50 hover:bg-white/10 transition-colors"
                                  >
                                    <div className="text-sm text-white">{article.title}</div>
                                    <div className="text-xs text-white/50 mt-1">{article.date || ''}</div>
                                  </a>
                                ))
                              )}
                            </div>
                          </details>
                        );
                      })}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
