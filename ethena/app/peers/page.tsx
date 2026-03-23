'use client'

import { useEffect, useState } from 'react';
import { Search, RefreshCw, ArrowUpRight } from 'lucide-react';
import { peersAPI } from '@/lib/api';

// Mock peer data for both markets (structure for future API integration)
const PEERS_US = [
  { symbol: 'AAPL', name: 'Apple Inc.', price: 175.24, pe: 28.5, market_cap: 2.71e12, div_yield: 0.005, net_profit_q: 33900000000, profit_q_var: 0.13, sales_q: 119575000000, sales_q_var: 0.02, roce: 0.52 },
  { symbol: 'MSFT', name: 'Microsoft Corp.', price: 415.50, pe: 35.2, market_cap: 3.12e12, div_yield: 0.007, net_profit_q: 21900000000, profit_q_var: 0.27, sales_q: 62020000000, sales_q_var: 0.18, roce: 0.38 },
  { symbol: 'GOOGL', name: 'Alphabet Inc.', price: 147.60, pe: 24.8, market_cap: 1.84e12, div_yield: 0, net_profit_q: 20687000000, profit_q_var: 0.52, sales_q: 86310000000, sales_q_var: 0.13, roce: 0.26 },
  { symbol: 'NVDA', name: 'NVIDIA', price: 897.50, pe: 72.4, market_cap: 2.21e12, div_yield: 0.003, net_profit_q: 12285000000, profit_q_var: 8.43, sales_q: 22103000000, sales_q_var: 2.65, roce: 1.15 },
  { symbol: 'AMD', name: 'Advanced Micro', price: 165.30, pe: 310.2, market_cap: 2.67e11, div_yield: 0.01, net_profit_q: 800000000, profit_q_var: -0.08, sales_q: 5500000000, sales_q_var: 0.03, roce: 0.12 },
  { symbol: 'INTC', name: 'Intel', price: 44.20, pe: 29.8, market_cap: 1.87e11, div_yield: 0.125, net_profit_q: 1200000000, profit_q_var: -0.15, sales_q: 18000000000, sales_q_var: -0.04, roce: 0.09 },
  { symbol: 'TSLA', name: 'Tesla Inc.', price: 172.63, pe: 41.2, market_cap: 5.50e11, div_yield: 0, net_profit_q: 7928000000, profit_q_var: -0.35, sales_q: 25167000000, sales_q_var: 0.03, roce: 0.18 },
  { symbol: 'META', name: 'Meta Platforms', price: 505.50, pe: 32.1, market_cap: 1.29e12, div_yield: 0.003, net_profit_q: 14000000000, profit_q_var: 2.01, sales_q: 40111000000, sales_q_var: 0.25, roce: 0.28 },
];
const PEERS_IN = [
  { symbol: 'RELIANCE', name: 'Reliance Ind.', price: 2975.30, pe: 28.4, market_cap: 2.01e14, div_yield: 0.003, net_profit_q: 172650000000, profit_q_var: 0.09, sales_q: 2279700000000, sales_q_var: 0.12, roce: 0.10 },
  { symbol: 'TCS', name: 'Tata Consultancy', price: 4012.30, pe: 32.4, market_cap: 1.46e13, div_yield: 0.015, net_profit_q: 11000000000, profit_q_var: 0.07, sales_q: 60000000000, sales_q_var: 0.05, roce: 0.41 },
  { symbol: 'INFY', name: 'Infosys', price: 1389.40, pe: 26.2, market_cap: 5.8e12, div_yield: 0.032, net_profit_q: 8000000000, profit_q_var: -0.03, sales_q: 35000000000, sales_q_var: 0.01, roce: 0.31 },
  { symbol: 'WIPRO', name: 'Wipro', price: 480.15, pe: 22.8, market_cap: 2.5e12, div_yield: 0.011, net_profit_q: 27000000000, profit_q_var: 0.02, sales_q: 223000000000, sales_q_var: -0.01, roce: 0.18 },
  { symbol: 'HDFCBANK', name: 'HDFC Bank', price: 1445.60, pe: 18.5, market_cap: 1.12e13, div_yield: 0.013, net_profit_q: 163720000000, profit_q_var: 1.33, sales_q: 784000000000, sales_q_var: 0.26, roce: 0.08 },
  { symbol: 'ICICIBANK', name: 'ICICI Bank', price: 1089.40, pe: 17.2, market_cap: 7.6e12, div_yield: 0.009, net_profit_q: 102710000000, profit_q_var: 0.23, sales_q: 489000000000, sales_q_var: 0.21, roce: 0.08 },
  { symbol: 'ADANIENT', name: 'Adani Enterprises', price: 3145.20, pe: 142.5, market_cap: 3.5e12, div_yield: 0.001, net_profit_q: 18880000000, profit_q_var: 1.30, sales_q: 283500000000, sales_q_var: -0.07, roce: 0.11 },
];

function formatNumber(n: number | null | undefined) {
  if (n == null) return '-';
  return n.toLocaleString(undefined, { maximumFractionDigits: 2 });
}
function formatCompact(n: number | null | undefined) {
  if (n == null) return '-';
  if (n >= 1e12) return (n / 1e12).toFixed(2) + 'T';
  if (n >= 1e9) return (n / 1e9).toFixed(2) + 'B';
  if (n >= 1e6) return (n / 1e6).toFixed(2) + 'M';
  if (n >= 1e3) return (n / 1e3).toFixed(2) + 'K';
  return n.toString();
}
function formatPercent(n: number | null | undefined) {
  if (n == null) return '-';
  const val = Math.abs(n) <= 1 ? n * 100 : n;
  return val.toFixed(2) + '%';
}

export default function PeerComparisonPage() {
  const [market, setMarket] = useState<'us' | 'india'>('us');
  const [query, setQuery] = useState('');
  const [symbol, setSymbol] = useState('AAPL');
  const [rows, setRows] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fallbackPeers = (market === 'us' ? PEERS_US : PEERS_IN).filter(p =>
    !query.trim() || p.symbol.toLowerCase().includes(query.trim().toLowerCase())
  );

  const peers = rows.length ? rows : fallbackPeers;
  const sym = market === 'us' ? '$' : '₹';

  const fetchPeers = async (symInput: string) => {
    setLoading(true);
    setError(null);
    try {
      const response = await peersAPI.compare(symInput, 12);
      setRows(response?.rows || []);
      setSymbol(symInput.toUpperCase());
    } catch (err: any) {
      setRows(fallbackPeers);
      setError(err?.message || 'Failed to load peer comparison.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    const defaultSymbol = market === 'india' ? 'RELIANCE.NS' : 'AAPL';
    setSymbol(defaultSymbol);
    setQuery(defaultSymbol.replace('.NS', ''));
    fetchPeers(defaultSymbol);
  }, [market]);

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    if (!query.trim()) return;

    let searchTicker = query.trim().toUpperCase();
    if (market === 'india' && !searchTicker.endsWith('.NS') && !searchTicker.endsWith('.BO')) {
      searchTicker += '.NS';
    }
    fetchPeers(searchTicker);
  };

  return (
    <div className="space-y-8 font-inter">
      <div className="rounded-2xl border border-white/20 bg-white/5 backdrop-blur-xl p-6">
        <div className="flex items-start justify-between gap-6">
          <div>
            <div className="flex items-center gap-2 mb-1">
              <div className="w-1.5 h-1.5 rounded-full bg-indigo-500 shadow-[0_0_8px_rgba(99,102,241,0.6)]" />
              <span className="font-dm-mono text-[11px] text-white/50 tracking-[0.2em] uppercase font-semibold">Discovery / Comparison Mode</span>
            </div>
            <p className="font-inter text-[13px] text-white/30">Select a primary asset to identify industry competitors and fundamental deviations.</p>
          </div>
          <button
            onClick={() => fetchPeers(symbol)}
            className="p-2 bg-white/5 border border-white/20 rounded-lg hover:bg-white/10"
            aria-label="Refresh"
          >
            <RefreshCw size={18} className={`text-white ${loading ? 'animate-spin' : ''}`} />
          </button>
        </div>

        <div className="mt-6 flex flex-col md:flex-row gap-4 items-start md:items-center">
          {/* Market Toggle */}
          <div className="flex p-1 bg-black/60 border border-white/20 rounded-xl">
            <button
              onClick={() => setMarket('us')}
              className={`px-4 py-2 text-sm font-medium rounded-lg transition-all ${market === 'us'
                ? 'bg-indigo-500/15 text-white shadow-lg'
                : 'text-white/60 hover:text-white hover:bg-white/5'
                }`}
            >
              $ US
            </button>
            <button
              onClick={() => setMarket('india')}
              className={`px-4 py-2 text-sm font-medium rounded-lg transition-all ${market === 'india'
                ? 'bg-indigo-500/15 text-white shadow-lg'
                : 'text-white/60 hover:text-white hover:bg-white/5'
                }`}
            >
              ₹ INDIA
            </button>
          </div>

          <form onSubmit={handleSearch} className="flex flex-wrap items-center gap-3 flex-1 w-full">
            <div className="flex items-center gap-2 rounded-xl border border-white/10 bg-black/40 px-4 py-3 flex-1 min-w-[220px]">
              <Search size={18} className="text-white/40" />
              <input
                value={query}
                onChange={e => setQuery(e.target.value)}
                placeholder={market === 'india' ? "Enter ticker (e.g., TCS, INFY)" : "Enter ticker (e.g., NVDA, AMD)"}
                className="flex-1 bg-transparent text-white outline-none"
              />
            </div>
            <button
              type="submit"
              className="px-8 py-2.5 bg-indigo-500/10 backdrop-blur-xl border border-indigo-500/30 text-indigo-400 hover:bg-indigo-500/20 hover:border-indigo-500/50 rounded-2xl text-[14px] font-dm-mono font-bold transition-all duration-300 shadow-[0_0_15px_rgba(99,102,241,0.1)] tracking-widest uppercase"
            >
              DISCOVER_PEERS
            </button>
          </form>
        </div>
      </div>

      {error && <div className="p-4 bg-red-500/20 border border-red-500/50 rounded-lg text-red-400">{error}</div>}

      <div className="bg-white/5 border border-white/20 rounded-2xl overflow-hidden backdrop-blur-xl">
        <div className="px-6 py-4 border-b border-white/20 flex items-center justify-between">
          <div className="text-sm text-white/60">Showing peers for <span className="text-white font-semibold">{symbol || (market === 'us' ? 'US Market' : 'India Market')}</span></div>
          <div className="text-xs text-white/40">{peers.length} companies</div>
        </div>

        {loading ? (
          <div className="p-12 text-center text-white/60">Loading comparison...</div>
        ) : peers.length === 0 ? (
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
                {peers.map((row, idx) => (
                  <tr key={row.symbol} 
                      onClick={() => { setQuery(row.symbol); fetchPeers(row.symbol); }}
                      className={`hover:bg-white/5 cursor-pointer group/row transition-colors ${query.toUpperCase() === row.symbol ? 'bg-indigo-500/5' : ''}`}>
                    <td className="px-4 py-3 text-white/50 group-hover/row:text-white transition-colors">{idx + 1}</td>
                    <td className="px-4 py-3">
                      <div className="text-white font-semibold group-hover/row:text-indigo-400 transition-colors">{row.name}</div>
                      <div className="text-xs text-white/40 tracking-wider font-mono">{row.symbol}</div>
                    </td>
                    <td className="px-4 py-3 text-right text-white">{sym}{formatNumber(row.price)}</td>
                    <td className="px-4 py-3 text-right text-white">{formatNumber(row.pe)}</td>
                    <td className="px-4 py-3 text-right text-white">{formatCompact(row.market_cap)}</td>
                    <td className="px-4 py-3 text-right text-white">{formatPercent(row.div_yield)}</td>
                    <td className="px-4 py-3 text-right text-white">{formatCompact(row.net_profit_q)}</td>
                    <td className={`px-4 py-3 text-right ${row.profit_q_var !== null && row.profit_q_var >= 0 ? 'text-indigo-400' : 'text-red-400'}`}>{formatPercent(row.profit_q_var)}</td>
                    <td className="px-4 py-3 text-right text-white">{formatCompact(row.sales_q)}</td>
                    <td className={`px-4 py-3 text-right ${row.sales_q_var !== null && row.sales_q_var >= 0 ? 'text-indigo-400' : 'text-red-400'}`}>{formatPercent(row.sales_q_var)}</td>
                    <td className="px-4 py-3 text-right text-white">{formatPercent(row.roce)}</td>
                    <td className="px-4 py-3 text-right">
                      <a
                        href={`#`}
                        className="inline-flex items-center gap-1 text-indigo-300 hover:text-indigo-200"
                        tabIndex={-1}
                        aria-label={`View details for ${row.symbol}`}
                      >
                        View <ArrowUpRight size={14} />
                      </a>
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
