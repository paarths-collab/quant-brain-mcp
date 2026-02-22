import { useEffect, useMemo, useState } from 'react';
import { ArrowUpRight, RefreshCw, Search } from 'lucide-react';
import { peersAPI } from '@/api';
import { Link } from 'react-router-dom';

type PeerRow = {
  symbol: string;
  name: string;
  price: number | null;
  pe: number | null;
  market_cap: number | null;
  div_yield: number | null;
  net_profit_q: number | null;
  profit_q_var: number | null;
  sales_q: number | null;
  sales_q_var: number | null;
  roce: number | null;
};

export default function Relationships() {
  const [market, setMarket] = useState<'US' | 'IN'>('US');
  const [symbol, setSymbol] = useState('AAPL');
  const [query, setQuery] = useState('AAPL');
  const [rows, setRows] = useState<PeerRow[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchPeers = async (sym: string) => {
    setLoading(true);
    setError(null);
    try {
      const response = await peersAPI.compare(sym, 10);
      setRows(response.data?.rows || []);
      setSymbol(sym.toUpperCase());
    } catch (err: any) {
      setRows([]);
      setError(err?.response?.data?.detail || 'Failed to load peer comparison.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchPeers(symbol);
  }, []);

  const handleMarketChange = (newMarket: 'US' | 'IN') => {
    if (newMarket === market) return;
    setMarket(newMarket);
    if (newMarket === 'IN') {
      setSymbol('RELIANCE.NS');
      setQuery('RELIANCE.NS');
      fetchPeers('RELIANCE.NS');
    } else {
      setSymbol('AAPL');
      setQuery('AAPL');
      fetchPeers('AAPL');
    }
  };

  const formatNumber = (value: number | null, digits = 2) => {
    if (value === null || value === undefined || Number.isNaN(value)) return '—';
    return value.toLocaleString('en-US', { maximumFractionDigits: digits });
  };

  const formatPercent = (value: number | null, digits = 2) => {
    if (value === null || value === undefined || Number.isNaN(value)) return '—';
    return `${value.toFixed(digits)}%`;
  };

  const formatCompact = (value: number | null) => {
    if (value === null || value === undefined || Number.isNaN(value)) return '—';
    const abs = Math.abs(value);
    if (abs >= 1e12) return `${(value / 1e12).toFixed(2)}T`;
    if (abs >= 1e9) return `${(value / 1e9).toFixed(2)}B`;
    if (abs >= 1e6) return `${(value / 1e6).toFixed(2)}M`;
    if (abs >= 1e3) return `${(value / 1e3).toFixed(2)}K`;
    return value.toFixed(2);
  };

  const sortedRows = useMemo(() => {
    const copy = [...rows];
    return copy;
  }, [rows]);

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    if (!query.trim()) return;

    let searchTicker = query.trim().toUpperCase();
    if (market === 'IN' && !searchTicker.endsWith('.NS') && !searchTicker.endsWith('.BO')) {
      searchTicker += '.NS';
    }

    fetchPeers(searchTicker);
  };

  return (
    <div className="space-y-6">
      <div className="rounded-2xl border border-white/10 bg-gradient-to-br from-white/10 via-white/[0.02] to-transparent p-6">
        <div className="flex items-start justify-between gap-6">
          <div>
            <h1 className="font-display text-3xl font-bold text-white">Peer Comparison</h1>
            <p className="text-white/60 mt-1">Compare valuation, growth, and efficiency across peers.</p>
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={() => fetchPeers(symbol)}
              className="p-2 bg-white/5 border border-white/10 rounded-lg hover:bg-white/10"
            >
              <RefreshCw size={16} className={`text-white ${loading ? 'animate-spin' : ''}`} />
            </button>
          </div>
        </div>

        <div className="mt-6 flex flex-col md:flex-row gap-4 items-start md:items-center">
          {/* Market Toggle */}
          <div className="flex p-1 bg-black/40 border border-white/10 rounded-xl">
            <button
              onClick={() => handleMarketChange('US')}
              className={`px-4 py-2 text-sm font-medium rounded-lg transition-all ${market === 'US'
                ? 'bg-orange-500 text-white shadow-lg'
                : 'text-white/60 hover:text-white hover:bg-white/5'
                }`}
            >
              US Market
            </button>
            <button
              onClick={() => handleMarketChange('IN')}
              className={`px-4 py-2 text-sm font-medium rounded-lg transition-all ${market === 'IN'
                ? 'bg-orange-500 text-white shadow-lg'
                : 'text-white/60 hover:text-white hover:bg-white/5'
                }`}
            >
              Indian Market
            </button>
          </div>

          <form onSubmit={handleSearch} className="flex flex-wrap items-center gap-3 flex-1 w-full">
            <div className="flex items-center gap-2 rounded-xl border border-white/10 bg-black/40 px-4 py-3 flex-1 min-w-[260px]">
              <Search size={18} className="text-white/40" />
              <input
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder={market === 'IN' ? "Enter ticker (e.g., RELIANCE, TCS, INFY)" : "Enter ticker (e.g., AAPL, MSFT, TSLA)"}
                className="flex-1 bg-transparent text-white outline-none"
              />
            </div>
            <button type="submit" className="rounded-lg bg-orange-500 px-4 py-2 text-sm font-medium text-white hover:bg-orange-400">
              Compare
            </button>
          </form>
        </div>
      </div>

      {error && <div className="p-4 bg-red-500/20 border border-red-500/50 rounded-lg text-red-400">{error}</div>}

      <div className="bg-white/5 border border-white/10 rounded-2xl overflow-hidden">
        <div className="px-6 py-4 border-b border-white/10 flex items-center justify-between">
          <div className="text-sm text-white/60">Showing peers for <span className="text-white font-semibold">{symbol}</span></div>
          <div className="text-xs text-white/40">{rows.length} companies</div>
        </div>

        {loading ? (
          <div className="p-12 text-center text-white/60">Loading comparison...</div>
        ) : rows.length === 0 ? (
          <div className="p-12 text-center text-white/60">No peer data available.</div>
        ) : (
          <div className="overflow-x-auto">
            <table className="min-w-[980px] w-full text-sm">
              <thead className="bg-black/40 text-white/60">
                <tr>
                  <th className="px-4 py-3 text-left">S.No.</th>
                  <th className="px-4 py-3 text-left">Name</th>
                  <th className="px-4 py-3 text-right">CMP</th>
                  <th className="px-4 py-3 text-right">P/E</th>
                  <th className="px-4 py-3 text-right">Market Cap</th>
                  <th className="px-4 py-3 text-right">Div Yield %</th>
                  <th className="px-4 py-3 text-right">NP Qtr</th>
                  <th className="px-4 py-3 text-right">Qtr Profit Var %</th>
                  <th className="px-4 py-3 text-right">Sales Qtr</th>
                  <th className="px-4 py-3 text-right">Qtr Sales Var %</th>
                  <th className="px-4 py-3 text-right">ROCE %</th>
                  <th className="px-4 py-3 text-right">Details</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-white/5">
                {sortedRows.map((row, idx) => (
                  <tr key={row.symbol} className="hover:bg-white/5">
                    <td className="px-4 py-3 text-white/70">{idx + 1}</td>
                    <td className="px-4 py-3">
                      <div className="text-white font-semibold">{row.name}</div>
                      <div className="text-xs text-white/40">{row.symbol}</div>
                    </td>
                    <td className="px-4 py-3 text-right text-white">{formatNumber(row.price)}</td>
                    <td className="px-4 py-3 text-right text-white">{formatNumber(row.pe)}</td>
                    <td className="px-4 py-3 text-right text-white">{formatCompact(row.market_cap)}</td>
                    <td className="px-4 py-3 text-right text-white">{formatPercent(row.div_yield)}</td>
                    <td className="px-4 py-3 text-right text-white">{formatCompact(row.net_profit_q)}</td>
                    <td className={`px-4 py-3 text-right ${row.profit_q_var !== null && row.profit_q_var >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                      {formatPercent(row.profit_q_var)}
                    </td>
                    <td className="px-4 py-3 text-right text-white">{formatCompact(row.sales_q)}</td>
                    <td className={`px-4 py-3 text-right ${row.sales_q_var !== null && row.sales_q_var >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                      {formatPercent(row.sales_q_var)}
                    </td>
                    <td className="px-4 py-3 text-right text-white">{formatPercent(row.roce)}</td>
                    <td className="px-4 py-3 text-right">
                      <Link
                        to={`/research?symbol=${row.symbol}`}
                        className="inline-flex items-center gap-1 text-orange-300 hover:text-orange-200"
                      >
                        View <ArrowUpRight size={14} />
                      </Link>
                    </td>
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
