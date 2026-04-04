'use client'

import { useEffect, useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Search, RefreshCw, ArrowUpRight, X, Building2, Globe, BarChart3 } from 'lucide-react';
import { peersAPI, fundamentalsAPI, type PeerRow, type FundamentalsSummaryResponse } from '@/lib/api';

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

const metricLabelMap: Record<string, string> = {
  peRatio: 'P/E',
  forwardPE: 'Forward P/E',
  pegRatio: 'PEG',
  priceToBook: 'Price / Book',
  enterpriseToEbitda: 'EV / EBITDA',
  debtToEquity: 'Debt / Equity',
  currentRatio: 'Current Ratio',
  roe: 'ROE',
  operatingMargins: 'Operating Margin',
  dividendYield: 'Dividend Yield',
  revenueGrowth: 'Revenue Growth',
  epsGrowth: 'EPS Growth',
  beta: 'Beta',
  targetMeanPrice: 'Target Mean Price',
};

function normalizeSymbolForMarket(sym: string, market: 'us' | 'india') {
  const clean = sym.trim().toUpperCase();
  if (market === 'india' && !clean.endsWith('.NS') && !clean.endsWith('.BO')) {
    return `${clean}.NS`;
  }
  return clean;
}

function formatMetricValue(key: string, value: unknown) {
  if (value == null) return '-';
  if (typeof value !== 'number') return String(value);
  if (['dividendYield', 'revenueGrowth', 'epsGrowth', 'roe', 'operatingMargins'].includes(key)) {
    return formatPercent(value);
  }
  return formatNumber(value);
}

export default function PeerComparisonPage() {
  const [market, setMarket] = useState<'us' | 'india'>('us');
  const [query, setQuery] = useState('');
  const [symbol, setSymbol] = useState('AAPL');
  const [rows, setRows] = useState<PeerRow[]>([]);
  const [hasDiscovered, setHasDiscovered] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [detailOpen, setDetailOpen] = useState(false);
  const [selectedPeer, setSelectedPeer] = useState<PeerRow | null>(null);
  const [stockDetail, setStockDetail] = useState<FundamentalsSummaryResponse | null>(null);
  const [detailLoading, setDetailLoading] = useState(false);
  const [detailError, setDetailError] = useState<string | null>(null);

  const peers = rows;
  const sym = market === 'us' ? '$' : '₹';

  const fetchPeers = async (symInput: string) => {
    setLoading(true);
    setError(null);
    try {
      const response = await peersAPI.compare(symInput, 12);
      const discoveredRows = response?.rows || [];
      const normalizedInput = symInput.toUpperCase();

      const singleFallbackRow =
        discoveredRows.length === 1 &&
        String(discoveredRows[0]?.symbol || '').toUpperCase() === normalizedInput &&
        [
          discoveredRows[0]?.price,
          discoveredRows[0]?.pe,
          discoveredRows[0]?.market_cap,
          discoveredRows[0]?.div_yield,
          discoveredRows[0]?.net_profit_q,
          discoveredRows[0]?.sales_q,
          discoveredRows[0]?.roce,
        ].every((v) => v == null);

      const backendMessage =
        (response as { message?: string; partial?: boolean; restricted?: boolean })?.message || null;

      setRows(discoveredRows);
      setSymbol(normalizedInput);

      if (backendMessage || singleFallbackRow) {
        setError(
          backendMessage ||
            `Could not discover peers for ${normalizedInput}. Check the ticker symbol (example: NVDA, AAPL, RELIANCE.NS).`
        );
      }
      setHasDiscovered(true);
    } catch (err: unknown) {
      setRows([]);
      setError(err instanceof Error ? err.message : 'Failed to load peer comparison.');
      setHasDiscovered(true);
    } finally {
      setLoading(false);
    }
  };

  const handleOpenDetails = async (row: PeerRow) => {
    const rowSymbol = String(row.symbol || '').toUpperCase();
    if (!rowSymbol) return;

    const requestSymbol = normalizeSymbolForMarket(rowSymbol, market);
    setSelectedPeer(row);
    setDetailOpen(true);
    setDetailLoading(true);
    setDetailError(null);

    try {
      const details = await fundamentalsAPI.getOverview(requestSymbol);
      setStockDetail(details || null);
    } catch (err: unknown) {
      setStockDetail(null);
      setDetailError(err instanceof Error ? err.message : 'Failed to load stock details.');
    } finally {
      setDetailLoading(false);
    }
  };

  useEffect(() => {
    const defaultSymbol = market === 'india' ? 'RELIANCE.NS' : 'AAPL';
    setSymbol(defaultSymbol);
    setQuery(defaultSymbol.replace('.NS', ''));
    setRows([]);
    setError(null);
    setHasDiscovered(false);
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
    <div className="relative space-y-8 font-inter overflow-hidden">
      <div className="pointer-events-none absolute -top-28 -left-24 h-72 w-72 rounded-full bg-black/0 blur-3xl" />
      <div className="pointer-events-none absolute -bottom-20 right-0 h-80 w-80 rounded-full bg-black/0 blur-3xl" />

      <motion.div
        initial={{ opacity: 0, y: 12 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.45 }}
        className="relative rounded-2xl border border-white/20 bg-white/5 backdrop-blur-xl p-6"
      >
        <div className="flex items-start justify-between gap-6">
          <div>
            <div className="flex items-center gap-2 mb-1">
              <div className="w-1.5 h-1.5 rounded-full bg-blue-400 shadow-[0_0_10px_rgba(96,165,250,0.8)]" />
              <span className="font-dm-mono text-[11px] text-white/50 tracking-[0.2em] uppercase font-semibold">Discovery / Comparison Mode</span>
            </div>
            <p className="font-inter text-[13px] text-white/30">Select a primary asset to identify industry competitors and fundamental deviations.</p>
          </div>
          <button
            onClick={() => fetchPeers(symbol)}
            className="p-2 bg-white/5 border border-white/20 rounded-lg hover:bg-white/10 transition-all"
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
                ? 'bg-indigo-500/20 text-white shadow-[0_0_14px_rgba(99,102,241,0.25)]'
                : 'text-white/60 hover:text-white hover:bg-white/5'
                }`}
            >
              $ US
            </button>
            <button
              onClick={() => setMarket('india')}
              className={`px-4 py-2 text-sm font-medium rounded-lg transition-all ${market === 'india'
                ? 'bg-indigo-500/20 text-white shadow-[0_0_14px_rgba(99,102,241,0.25)]'
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
              className="relative overflow-hidden px-8 py-2.5 bg-indigo-600/20 backdrop-blur-xl border border-indigo-400/40 text-indigo-200 hover:bg-indigo-600/30 hover:border-indigo-300/60 rounded-2xl text-[14px] font-dm-mono font-bold transition-all duration-300 shadow-[0_0_20px_rgba(99,102,241,0.2)] tracking-widest uppercase after:absolute after:inset-0 after:-translate-x-full hover:after:translate-x-full after:transition-transform after:duration-700 after:bg-gradient-to-r after:from-transparent after:via-indigo-300/25 after:to-transparent"
            >
              DISCOVER_PEERS
            </button>
          </form>
        </div>
      </motion.div>

      {error && <div className="p-4 bg-red-500/20 border border-red-500/50 rounded-lg text-red-400">{error}</div>}

      <motion.div
        initial={{ opacity: 0, y: 16 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5, delay: 0.05 }}
        className="bg-white/5 border border-white/20 rounded-2xl overflow-hidden backdrop-blur-xl"
      >
        <div className="px-6 py-4 border-b border-white/20 flex items-center justify-between">
          <div className="text-sm text-white/60">Showing peers for <span className="text-white font-semibold">{hasDiscovered ? symbol : '-'}</span></div>
          <div className="text-xs text-white/40">{peers.length} companies</div>
        </div>

        {!hasDiscovered ? (
          <div className="p-12 text-center text-white/60">Enter a ticker and click DISCOVER_PEERS to run discovery.</div>
        ) : loading ? (
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
                      <div className="text-white font-semibold group-hover/row:text-indigo-300 transition-colors">{row.name}</div>
                      <div className="text-xs text-white/40 tracking-wider font-mono">{row.symbol}</div>
                    </td>
                    <td className="px-4 py-3 text-right text-white">{sym}{formatNumber(row.price)}</td>
                    <td className="px-4 py-3 text-right text-white">{formatNumber(row.pe)}</td>
                    <td className="px-4 py-3 text-right text-white">{formatCompact(row.market_cap)}</td>
                    <td className="px-4 py-3 text-right text-white">{formatPercent(row.div_yield)}</td>
                    <td className="px-4 py-3 text-right text-white">{formatCompact(row.net_profit_q)}</td>
                    <td className={`px-4 py-3 text-right ${typeof row.profit_q_var === 'number' && row.profit_q_var >= 0 ? 'text-blue-400' : 'text-red-400'}`}>{formatPercent(row.profit_q_var)}</td>
                    <td className="px-4 py-3 text-right text-white">{formatCompact(row.sales_q)}</td>
                    <td className={`px-4 py-3 text-right ${typeof row.sales_q_var === 'number' && row.sales_q_var >= 0 ? 'text-blue-400' : 'text-red-400'}`}>{formatPercent(row.sales_q_var)}</td>
                    <td className="px-4 py-3 text-right text-white">{formatPercent(row.roce)}</td>
                    <td className="px-4 py-3 text-right">
                      <button
                        type="button"
                        onClick={(e) => {
                          e.stopPropagation();
                          handleOpenDetails(row);
                        }}
                        className="inline-flex items-center gap-1 text-blue-300 hover:text-blue-200"
                        aria-label={`View details for ${row.symbol}`}
                      >
                        View <ArrowUpRight size={14} />
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </motion.div>

      <AnimatePresence>
        {detailOpen && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 z-50 overflow-y-auto bg-black/70 backdrop-blur-sm p-4 md:p-8"
            onClick={() => setDetailOpen(false)}
          >
            <motion.div
              initial={{ opacity: 0, y: 20, scale: 0.98 }}
              animate={{ opacity: 1, y: 0, scale: 1 }}
              exit={{ opacity: 0, y: 10, scale: 0.98 }}
              transition={{ duration: 0.22 }}
              onClick={(e) => e.stopPropagation()}
              className="mx-auto my-2 flex max-h-[92vh] w-full max-w-4xl flex-col overflow-hidden rounded-2xl border border-white/20 bg-slate-950/95 shadow-[0_0_60px_rgba(56,189,248,0.2)]"
            >
              <div className="flex items-start justify-between gap-4 border-b border-white/10 p-5 md:p-6">
                <div>
                  <div className="text-xs uppercase tracking-[0.2em] text-blue-300/70 font-dm-mono">Stock Detail</div>
                  <h2 className="mt-1 text-2xl font-semibold text-white">
                    {stockDetail?.name || selectedPeer?.name || selectedPeer?.symbol}
                  </h2>
                  <div className="mt-1 text-sm text-white/50">{stockDetail?.symbol || selectedPeer?.symbol}</div>
                </div>
                <button
                  type="button"
                  onClick={() => setDetailOpen(false)}
                  className="rounded-lg border border-white/15 bg-white/5 p-2 text-white/70 hover:bg-white/10 hover:text-white"
                  aria-label="Close details"
                >
                  <X size={18} />
                </button>
              </div>

              <div className="min-h-0 flex-1 overflow-y-auto p-5 md:p-6">
                {detailLoading ? (
                  <div className="rounded-xl border border-blue-400/20 bg-blue-400/5 p-6 text-blue-100">Loading stock fundamentals...</div>
                ) : detailError ? (
                  <div className="rounded-xl border border-red-500/40 bg-red-500/10 p-6 text-red-300">{detailError}</div>
                ) : (
                  <div className="space-y-5">
                    <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
                      <div className="rounded-xl border border-white/10 bg-white/[0.03] p-4">
                        <div className="flex items-center gap-2 text-white/50 text-xs uppercase tracking-wider"><BarChart3 size={14} /> Price</div>
                        <div className="mt-2 text-2xl font-semibold text-white">{sym}{formatNumber(stockDetail?.price as number | null | undefined)}</div>
                      </div>
                      <div className="rounded-xl border border-white/10 bg-white/[0.03] p-4">
                        <div className="flex items-center gap-2 text-white/50 text-xs uppercase tracking-wider"><Building2 size={14} /> Market Cap</div>
                        <div className="mt-2 text-2xl font-semibold text-white">{formatCompact(stockDetail?.marketCap as number | null | undefined)}</div>
                      </div>
                      <div className="rounded-xl border border-white/10 bg-white/[0.03] p-4">
                        <div className="flex items-center gap-2 text-white/50 text-xs uppercase tracking-wider"><Globe size={14} /> Exchange</div>
                        <div className="mt-2 text-2xl font-semibold text-white">{stockDetail?.exchange || '-'}</div>
                      </div>
                    </div>

                    <div className="rounded-xl border border-white/10 bg-white/[0.03] p-4 md:p-5">
                      <h3 className="text-white font-medium">Company Snapshot</h3>
                      <div className="mt-3 grid grid-cols-1 gap-3 text-sm md:grid-cols-2">
                        <div><span className="text-white/50">Sector:</span> <span className="text-white">{stockDetail?.sector || '-'}</span></div>
                        <div><span className="text-white/50">Industry:</span> <span className="text-white">{stockDetail?.industry || '-'}</span></div>
                        <div><span className="text-white/50">Currency:</span> <span className="text-white">{stockDetail?.currency || '-'}</span></div>
                        <div>
                          <span className="text-white/50">Website:</span>{' '}
                          {stockDetail?.website ? (
                            <a
                              href={String(stockDetail.website)}
                              target="_blank"
                              rel="noreferrer"
                              className="text-blue-300 hover:text-blue-200 underline-offset-2 hover:underline"
                            >
                              Visit
                            </a>
                          ) : (
                            <span className="text-white">-</span>
                          )}
                        </div>
                      </div>
                      {stockDetail?.description && (
                        <p className="mt-4 text-sm leading-6 text-white/75">
                          {String(stockDetail.description)}
                        </p>
                      )}
                    </div>

                    <div className="rounded-xl border border-white/10 bg-white/[0.03] p-4 md:p-5">
                      <h3 className="text-white font-medium">Key Fundamental Metrics</h3>
                      <div className="mt-3 grid grid-cols-1 gap-3 md:grid-cols-2">
                        {Object.entries(stockDetail?.metrics || {})
                          .filter(([key, value]) => metricLabelMap[key] && value != null)
                          .map(([key, value]) => (
                            <div
                              key={key}
                              className="relative overflow-hidden rounded-lg border border-white/10 bg-black/20 px-3 py-2.5 flex items-center justify-between transition-all duration-300 hover:border-blue-400/50 hover:bg-blue-400/5 hover:shadow-[0_0_12px_rgba(59,130,246,0.2)] group/metric"
                            >
                              <span className="text-white/55 text-sm group-hover/metric:text-white/70 transition-colors">{metricLabelMap[key]}</span>
                              <span className="text-white/70 font-medium text-sm group-hover/metric:text-blue-300 group-hover/metric:font-semibold group-hover/metric:shadow-[0_0_8px_rgba(59,130,246,0.4)] transition-all duration-300">
                                {formatMetricValue(key, value)}
                              </span>
                            </div>
                          ))}
                      </div>
                    </div>
                  </div>
                )}
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
