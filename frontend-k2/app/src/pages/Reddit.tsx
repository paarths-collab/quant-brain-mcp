import { useEffect, useState } from 'react';
import { Search, RefreshCw, ArrowUpRight, Newspaper, Sparkles } from 'lucide-react';
import { socialAPI } from '@/api';

const quickQueries = [
  'stock market news',
  'earnings',
  'AI stocks',
  'banking sector',
  'energy stocks',
  'gold price',
  'oil prices',
  'CPI inflation',
  'NIFTY 50',
  'SENSEX',
  'AAPL',
  'TSLA',
];

const categoryPresets: Record<string, string> = {
  Stocks: 'stock market news',
  Commodities: 'gold price OR oil prices OR silver',
  Macro: 'CPI inflation OR unemployment OR GDP',
  Crypto: 'bitcoin OR ethereum OR crypto market',
};

export default function Reddit() {
  const [query, setQuery] = useState('');
  const [activeQuery, setActiveQuery] = useState('stock market news');
  const [category, setCategory] = useState('Stocks');
  const [isLoading, setIsLoading] = useState(false);
  const [articles, setArticles] = useState<any[]>([]);
  const [error, setError] = useState<string | null>(null);

  const fetchNews = async (search?: string) => {
    setIsLoading(true);
    setError(null);
    try {
      const baseQuery = (search ?? query).trim();
      const q = baseQuery || categoryPresets[category] || 'stock market news';
      setActiveQuery(q);
      const response = await socialAPI.getNews(q, 12);
      setArticles(response.data?.articles || []);
    } catch (err: any) {
      setError(err?.response?.data?.detail || 'Failed to load news.');
      setArticles([]);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchNews('stock market news');
  }, []);

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    fetchNews(query);
  };

  return (
    <div className="space-y-6">
      <div className="rounded-2xl border border-white/10 bg-gradient-to-br from-white/10 via-white/[0.02] to-transparent p-6">
        <div className="flex items-start justify-between gap-6">
          <div>
            <div className="inline-flex items-center gap-2 rounded-full border border-white/10 bg-white/5 px-3 py-1 text-xs text-white/70">
              <Sparkles size={14} className="text-orange-400" />
              News box
            </div>
            <h1 className="font-display text-3xl font-bold text-white mt-3">Market News</h1>
            <p className="text-white/60 mt-1">Latest headlines across stocks, indices, commodities, and macro topics.</p>
          </div>
          <button onClick={() => fetchNews(activeQuery)} className="p-2 bg-white/5 border border-white/10 rounded-lg hover:bg-white/10">
            <RefreshCw size={16} className={`text-white ${isLoading ? 'animate-spin' : ''}`} />
          </button>
        </div>

        <form onSubmit={handleSearch} className="mt-6 flex items-center gap-3 rounded-xl border border-white/10 bg-black/40 px-4 py-3">
          <Search size={18} className="text-white/40" />
          <input
            type="text"
            placeholder="Search anything (stocks, commodities, macro, themes)"
            value={query}
            onChange={e => setQuery(e.target.value)}
            className="flex-1 bg-transparent text-white outline-none"
          />
          <button type="submit" className="rounded-lg bg-orange-500 px-4 py-2 text-sm font-medium text-white hover:bg-orange-400">
            Search
          </button>
        </form>

        <div className="mt-4 flex flex-wrap gap-2">
          {Object.keys(categoryPresets).map((item) => (
            <button
              key={item}
              onClick={() => { setCategory(item); fetchNews(''); }}
              className={`rounded-full border px-3 py-1 text-xs ${
                category === item ? 'border-orange-500/60 bg-orange-500/20 text-orange-200' : 'border-white/10 bg-white/5 text-white/70 hover:bg-white/10'
              }`}
            >
              {item}
            </button>
          ))}
        </div>

        <div className="mt-4 flex flex-wrap gap-2">
          {quickQueries.map((item) => (
            <button
              key={item}
              onClick={() => { setQuery(item); fetchNews(item); }}
              className="rounded-full border border-white/10 bg-white/5 px-3 py-1 text-xs text-white/70 hover:bg-white/10"
            >
              {item}
            </button>
          ))}
        </div>
      </div>

      <div className="flex items-center justify-between">
        <div className="text-sm text-white/60">
          Showing {articles.length} headlines for <span className="text-white">{activeQuery}</span>
        </div>
        <div className="flex items-center gap-2 text-xs text-white/40">
          <Newspaper size={14} />
          Live updates
        </div>
      </div>

      {error && <div className="p-4 bg-red-500/20 border border-red-500/40 rounded-lg text-red-400">{error}</div>}

      {isLoading ? (
        <div className="p-12 text-center text-white/60">Loading headlines...</div>
      ) : articles.length === 0 ? (
        <div className="p-12 text-center text-white/60">No news found.</div>
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          {articles.map((article: any, idx: number) => (
            <a
              key={`${article.url}-${idx}`}
              href={article.url}
              target="_blank"
              rel="noreferrer"
              className="group rounded-xl border border-white/10 bg-white/5 p-4 hover:bg-white/10 transition-colors"
            >
              <div className="flex items-start justify-between gap-4">
                <div>
                  <div className="text-xs text-white/40">{article.date || 'Today'}</div>
                  <div className="mt-2 text-lg font-semibold text-white group-hover:text-orange-200">
                    {article.title}
                  </div>
                </div>
                <ArrowUpRight size={18} className="text-white/40 group-hover:text-white" />
              </div>
              {article.summary && (
                <p className="mt-3 text-sm text-white/60 line-clamp-3">
                  {article.summary}
                </p>
              )}
            </a>
          ))}
        </div>
      )}
    </div>
  );
}
