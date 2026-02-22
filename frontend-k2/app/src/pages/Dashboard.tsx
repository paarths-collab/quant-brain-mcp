import { useState, useEffect } from 'react';
import { TrendingUp, TrendingDown, RefreshCw, DollarSign, IndianRupee, Activity, Globe2, Briefcase } from 'lucide-react';
import { AreaChart, Area, XAxis, YAxis, Tooltip, ResponsiveContainer } from 'recharts';
import { formatCurrency, getCurrencySymbol, treemapAPI, fredAPI, investorProfileAPI } from '@/api';

const watchlistSymbols = {
  IN: ['RELIANCE.NS', 'TCS.NS', 'HDFCBANK.NS', 'INFY.NS'],
  US: ['AAPL', 'MSFT', 'GOOGL', 'NVDA']
};

const indexSymbols = {
  IN: ['^NSEI', '^BSESN', '^NSEBANK'],
  US: ['^GSPC', '^IXIC', '^DJI']
};

const indexNames: Record<string, string> = {
  '^NSEI': 'NIFTY 50',
  '^BSESN': 'SENSEX',
  '^NSEBANK': 'NIFTY BANK',
  '^GSPC': 'S&P 500',
  '^IXIC': 'NASDAQ',
  '^DJI': 'DOW JONES'
};

const globalSeries = [
  { id: 'SP500', label: 'S&P 500' },
  { id: 'NASDAQ100', label: 'NASDAQ 100' },
  { id: 'DJIA', label: 'Dow Jones' },
  { id: 'VIXCLS', label: 'VIX' },
  { id: 'DCOILWTICO', label: 'WTI Crude' },
  { id: 'DCOILBRENTEU', label: 'Brent Crude' },
  { id: 'GOLDPMGBD228NLBM', label: 'Gold' },
  { id: 'DEXUSEU', label: 'USD/EUR' },
  { id: 'DEXJPUS', label: 'JPY/USD' },
  { id: 'DEXUSUK', label: 'USD/GBP' },
];

type Market = 'IN' | 'US';

interface Holding {
  symbol: string;
  name: string;
  price: number;
  change: number;
  value: number;
}

interface Index {
  name: string;
  value: number;
  change: number;
}

interface GlobalMarketPoint {
  id: string;
  name: string;
  value: number | null;
  changePct: number | null;
  date?: string | null;
  updatedAt?: string | null;
}

export default function Dashboard() {
  const [market, setMarket] = useState<Market>('IN');
  const [holdings, setHoldings] = useState<Holding[]>([]);
  const [indices, setIndices] = useState<Index[]>([]);
  const [globalMarkets, setGlobalMarkets] = useState<GlobalMarketPoint[]>([]);
  const [portfolioData, setPortfolioData] = useState<any[]>([]);
  const [realPortfolio, setRealPortfolio] = useState<any>(null); // New state for real portfolio
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [globalError, setGlobalError] = useState<string | null>(null);

  const symbol = getCurrencySymbol(market);

  const fetchHoldings = async () => {
    try {
      const symbols = watchlistSymbols[market];
      const promises = symbols.map(sym =>
        treemapAPI.getStockDetails(sym, market === 'IN' ? 'india' : 'us')
          .catch(() => null)
      );

      const results = await Promise.all(promises);
      const validResults = results
        .filter(r => r?.data && !r.data.error)
        .map(r => ({
          symbol: r.data.symbol,
          name: r.data.name || r.data.symbol,
          price: r.data.price?.current || 0,
          change: r.data.price?.change_percent || 0,
          value: (r.data.price?.current || 0) * 100, // Dummy value calculation for watchlist
        }));

      setHoldings(validResults);
    } catch (err) {
      console.error('Holdings fetch error:', err);
    }
  };

  const fetchRealPortfolio = async () => {
    try {
      const { data } = await investorProfileAPI.getPortfolio();
      setRealPortfolio(data);
    } catch (e) {
      console.error('Failed to fetch portfolio', e);
    }
  };

  const fetchIndices = async () => {
    try {
      const symbols = indexSymbols[market];
      const promises = symbols.map(idx =>
        treemapAPI.getStockDetails(idx, market === 'IN' ? 'india' : 'us')
          .then(r => {
            // Handle case where price is a nested object (from get_stock_details)
            const priceData = r.data?.price;
            const priceVal = typeof priceData === 'object' ? priceData?.current : priceData;
            const changeVal = typeof priceData === 'object' ? priceData?.change_percent : r.data?.change_percent;

            return {
              name: indexNames[idx] || idx,
              value: priceVal || 0,
              change: changeVal || 0,
            };
          })
          .catch(() => ({ name: indexNames[idx] || idx, value: 0, change: 0 }))
      );

      const results = await Promise.all(promises);
      setIndices(results);
    } catch (err) {
      console.error('Indices fetch error:', err);
    }
  };

  const fetchGlobalMarkets = async () => {
    try {
      setGlobalError(null);
      const response = await fredAPI.getLatestCached(globalSeries.map(s => s.id), 12);
      const data = response.data?.data || {};
      const mapped: GlobalMarketPoint[] = globalSeries.map((series) => {
        const item = data[series.id];
        return {
          id: series.id,
          name: series.label,
          value: item?.value ?? null,
          changePct: item?.change_pct ?? null,
          date: item?.date ?? null,
          updatedAt: item?.updated_at ?? null,
        };
      });
      setGlobalMarkets(mapped);
    } catch (err: any) {
      console.error('Global markets fetch error:', err);
      setGlobalError(err?.response?.data?.detail || 'Failed to load FRED data.');
      setGlobalMarkets([]);
    }
  };

  const generatePortfolioData = () => {
    const months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
    let baseValue = market === 'IN' ? 1000000 : 100000;
    const prand = (n: number) => {
      const x = Math.sin(n * 9999.123) * 10000;
      return x - Math.floor(x);
    };
    const data = months.map((month, i) => {
      const change = 1 + (prand(i) * 0.08 - 0.02);
      baseValue = baseValue * change;
      return { date: month, value: Math.round(baseValue) };
    });
    setPortfolioData(data);
  };

  const fetchData = async () => {
    setLoading(true);
    setError(null);
    try {
      await Promise.all([fetchHoldings(), fetchIndices(), fetchGlobalMarkets(), fetchRealPortfolio()]);
      generatePortfolioData();
    } catch (err) {
      setError('Failed to load data. Make sure backend is running on port 8000.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, [market]);

  // Use Real Portfolio Data if available, else fallbacks
  const totalValue = realPortfolio ? realPortfolio.total_value : 0;
  const totalPL = realPortfolio ? realPortfolio.total_pl : 0;
  const totalPLPct = realPortfolio ? realPortfolio.total_pl_pct : 0;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="font-display text-3xl font-bold text-white">Dashboard</h1>
          <p className="text-white/60">Portfolio Overview</p>
        </div>
        <div className="flex items-center gap-3">
          <button onClick={fetchData} disabled={loading} className="p-2 bg-white/5 border border-white/10 rounded-lg hover:bg-white/10 disabled:opacity-50">
            <RefreshCw className={`w-4 h-4 text-white ${loading ? 'animate-spin' : ''}`} />
          </button>
          <div className="flex gap-2">
            <button onClick={() => setMarket('IN')} className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium ${market === 'IN' ? 'bg-orange-500 text-white' : 'bg-white/5 text-white/60 hover:text-white'}`}>
              <IndianRupee size={16} />India
            </button>
            <button onClick={() => setMarket('US')} className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium ${market === 'US' ? 'bg-orange-500 text-white' : 'bg-white/5 text-white/60 hover:text-white'}`}>
              <DollarSign size={16} />US
            </button>
          </div>
        </div>
      </div>

      {error && <div className="p-4 bg-red-500/20 border border-red-500/50 rounded-lg text-red-400">{error}</div>}

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {/* Total Value Card */}
        <div className="p-6 bg-white/5 border border-white/10 rounded-xl">
          <div className="flex items-center gap-3 mb-3">
            <div className="p-2 bg-orange-500/20 rounded-lg">
              <Briefcase className="text-orange-400" size={20} />
            </div>
            <span className="text-sm text-white/60">Portfolio Value</span>
          </div>
          <div className="text-3xl font-bold text-white mb-1">{formatCurrency(totalValue, market)}</div>
        </div>

        {/* Total P&L Card (Replaces Daily Change) */}
        <div className="p-6 bg-white/5 border border-white/10 rounded-xl">
          <div className="flex items-center gap-3 mb-3">
            <div className={`p-2 rounded-lg ${totalPL >= 0 ? 'bg-green-500/20' : 'bg-red-500/20'}`}>
              {totalPL >= 0 ? <TrendingUp className="text-green-500" size={20} /> : <TrendingDown className="text-red-500" size={20} />}
            </div>
            <span className="text-sm text-white/60">Total P&L</span>
          </div>
          <div className={`text-3xl font-bold ${totalPL >= 0 ? 'text-green-500' : 'text-red-500'}`}>
            {totalPL >= 0 ? '+' : ''}{formatCurrency(Math.abs(totalPL), market)}
          </div>
        </div>

        {/* Total Return % Card */}
        <div className="p-6 bg-white/5 border border-white/10 rounded-xl">
          <div className="flex items-center gap-3 mb-3">
            <div className={`p-2 rounded-lg ${totalPLPct >= 0 ? 'bg-green-500/20' : 'bg-red-500/20'}`}>
              <Activity className={totalPLPct >= 0 ? 'text-green-500' : 'text-red-500'} size={20} />
            </div>
            <span className="text-sm text-white/60">Return %</span>
          </div>
          <div className={`text-3xl font-bold ${totalPLPct >= 0 ? 'text-green-500' : 'text-red-500'}`}>
            {totalPLPct >= 0 ? '+' : ''}{totalPLPct.toFixed(2)}%
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2 bg-white/5 border border-white/10 rounded-xl p-6">
          <h3 className="text-lg font-semibold text-white mb-4">Portfolio Performance</h3>
          <ResponsiveContainer width="100%" height={300}>
            <AreaChart data={portfolioData}>
              <defs>
                <linearGradient id="colorValue" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#FF9500" stopOpacity={0.3} />
                  <stop offset="95%" stopColor="#FF9500" stopOpacity={0} />
                </linearGradient>
              </defs>
              <XAxis dataKey="date" axisLine={false} tickLine={false} tick={{ fill: '#71717a', fontSize: 11 }} />
              <YAxis axisLine={false} tickLine={false} tick={{ fill: '#71717a', fontSize: 11 }} tickFormatter={(v) => `${symbol}${(v / 1000).toFixed(0)}K`} />
              <Tooltip
                contentStyle={{ background: '#18181b', border: '1px solid rgba(255,255,255,0.1)', borderRadius: 8 }}
                formatter={(value: any) => [formatCurrency(value, market), 'Value']}
              />
              <Area type="monotone" dataKey="value" stroke="#FF9500" strokeWidth={2} fill="url(#colorValue)" />
            </AreaChart>
          </ResponsiveContainer>
        </div>

        <div className="bg-white/5 border border-white/10 rounded-xl p-6">
          <h3 className="text-lg font-semibold text-white mb-4">Market Indices</h3>
          <div className="space-y-3">
            {loading && indices.length === 0 ? (
              <div className="text-center py-8 text-white/60 text-sm">Loading indices...</div>
            ) : (
              indices.map((index) => (
                <div key={index.name} className="flex items-center justify-between p-3 bg-white/5 rounded-lg hover:bg-white/10 transition-colors">
                  <div>
                    <div className="text-xs text-white/60">{index.name}</div>
                    <div className="text-lg font-semibold text-white">{index.value.toLocaleString('en-US', { maximumFractionDigits: 2 })}</div>
                  </div>
                  <div className={`text-sm font-medium ${index.change >= 0 ? 'text-green-500' : 'text-red-500'}`}>
                    {index.change >= 0 ? '+' : ''}{(index.change || 0).toFixed(2)}%
                  </div>
                </div>
              ))
            )}
          </div>
        </div>
      </div>

      <div className="bg-white/5 border border-white/10 rounded-xl p-6">
        <div className="flex items-center gap-2 mb-4">
          <div className="p-2 rounded-lg bg-white/5 border border-white/10">
            <Globe2 className="text-orange-400" size={18} />
          </div>
          <div>
            <h3 className="text-lg font-semibold text-white">Global Markets (FRED)</h3>
            <p className="text-xs text-white/50">Live macro & cross‑market signals</p>
          </div>
        </div>
        {globalError && <div className="text-xs text-red-400 mb-3">{globalError}</div>}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          {globalMarkets.length === 0 ? (
            <div className="text-white/60 text-sm col-span-full">No global market data available.</div>
          ) : (
            globalMarkets.map((item) => (
              <div key={item.id} className="p-4 bg-white/5 border border-white/10 rounded-lg hover:bg-white/10 transition-colors">
                <div className="text-xs text-white/50">{item.name}</div>
                <div className="text-xl font-semibold text-white">
                  {item.value !== null ? item.value.toLocaleString('en-US', { maximumFractionDigits: 2 }) : '—'}
                </div>
                <div className={`text-sm ${item.changePct !== null && item.changePct >= 0 ? 'text-green-500' : 'text-red-500'}`}>
                  {item.changePct === null ? '—' : `${item.changePct >= 0 ? '+' : ''}${item.changePct.toFixed(2)}%`}
                </div>
                {item.updatedAt && <div className="text-xs text-white/40 mt-1">Cached: {item.updatedAt.split('T')[0]}</div>}
                {!item.updatedAt && item.date && <div className="text-xs text-white/40 mt-1">{item.date}</div>}
              </div>
            ))
          )}
        </div>
      </div>

      <div className="bg-white/5 border border-white/10 rounded-xl p-6">
        <h3 className="text-lg font-semibold text-white mb-4">Watchlist</h3>
        {loading && holdings.length === 0 ? (
          <div className="text-center py-12 text-white/60">Loading watchlist...</div>
        ) : holdings.length === 0 ? (
          <div className="text-center py-12 text-white/60">No holdings data available</div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="border-b border-white/10">
                  <th className="text-left p-4 text-white/60 font-medium text-sm">Symbol</th>
                  <th className="text-left p-4 text-white/60 font-medium text-sm">Name</th>
                  <th className="text-right p-4 text-white/60 font-medium text-sm">Price</th>
                  <th className="text-right p-4 text-white/60 font-medium text-sm">Change</th>
                  <th className="text-right p-4 text-white/60 font-medium text-sm">Value</th>
                </tr>
              </thead>
              <tbody>
                {holdings.map((holding) => (
                  <tr key={holding.symbol} className="border-b border-white/5 hover:bg-white/[0.02] transition-colors">
                    <td className="p-4 text-white font-medium">{holding.symbol}</td>
                    <td className="p-4 text-white/80">{holding.name}</td>
                    <td className="p-4 text-right text-white">{formatCurrency(holding.price, market)}</td>
                    <td className={`p-4 text-right font-medium ${holding.change >= 0 ? 'text-green-500' : 'text-red-500'}`}>
                      {holding.change >= 0 ? '+' : ''}{holding.change.toFixed(2)}%
                    </td>
                    <td className="p-4 text-right text-white font-medium">{formatCurrency(holding.value, market)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
