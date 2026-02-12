import { useEffect, useMemo, useState } from 'react';
import { ArrowUpRight, RefreshCw, SlidersHorizontal, Search } from 'lucide-react';
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

const defaultColumns = [
  { key: 'price', label: 'CMP' },
  { key: 'pe', label: 'P/E' },
  { key: 'market_cap', label: 'Market Cap' },
  { key: 'div_yield', label: 'Div Yield %' },
  { key: 'net_profit_q', label: 'NP Qtr' },
  { key: 'profit_q_var', label: 'Qtr Profit Var %' },
  { key: 'sales_q', label: 'Sales Qtr' },
  { key: 'sales_q_var', label: 'Qtr Sales Var %' },
  { key: 'roce', label: 'ROCE %' },
];

export default function Relationships() {
  const [symbol, setSymbol] = useState('AAPL');
  const [query, setQuery] = useState('AAPL');
  const [rows, setRows] = useState<PeerRow[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [visibleColumns, setVisibleColumns] = useState(defaultColumns.map((c) => c.key));

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

  const hasColumn = (key: string) => visibleColumns.includes(key);

  const sortedRows = useMemo(() => {
    const copy = [...rows];
    return copy;
  }, [rows]);

  const toggleColumn = (key: string) => {
    if (visibleColumns.includes(key)) {
      setVisibleColumns(visibleColumns.filter((c) => c !== key));
    } else {
      setVisibleColumns([...visibleColumns, key]);
    }
  };

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    if (!query.trim()) return;
    fetchPeers(query.trim().toUpperCase());
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

        <form onSubmit={handleSearch} className="mt-6 flex flex-wrap items-center gap-3">
          <div className="flex items-center gap-2 rounded-xl border border-white/10 bg-black/40 px-4 py-3 flex-1 min-w-[260px]">
            <Search size={18} className="text-white/40" />
            <input
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Enter ticker (e.g., AAPL, MSFT, TSLA)"
              className="flex-1 bg-transparent text-white outline-none"
            />
          </div>
          <button type="submit" className="rounded-lg bg-orange-500 px-4 py-2 text-sm font-medium text-white hover:bg-orange-400">
            Compare
          </button>
          <div className="inline-flex items-center gap-2 rounded-lg border border-white/10 bg-white/5 px-3 py-2 text-xs text-white/60">
            <SlidersHorizontal size={14} />
            Columns
          </div>
        </form>

        <div className="mt-3 flex flex-wrap gap-2">
          {defaultColumns.map((col) => (
            <button
              key={col.key}
              onClick={() => toggleColumn(col.key)}
              className={`rounded-full border px-3 py-1 text-xs ${
                visibleColumns.includes(col.key)
                  ? 'border-orange-500/60 bg-orange-500/20 text-orange-200'
                  : 'border-white/10 bg-white/5 text-white/60 hover:bg-white/10'
              }`}
            >
              {col.label}
            </button>
          ))}
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
                  {hasColumn('price') && <th className="px-4 py-3 text-right">CMP</th>}
                  {hasColumn('pe') && <th className="px-4 py-3 text-right">P/E</th>}
                  {hasColumn('market_cap') && <th className="px-4 py-3 text-right">Market Cap</th>}
                  {hasColumn('div_yield') && <th className="px-4 py-3 text-right">Div Yield %</th>}
                  {hasColumn('net_profit_q') && <th className="px-4 py-3 text-right">NP Qtr</th>}
                  {hasColumn('profit_q_var') && <th className="px-4 py-3 text-right">Qtr Profit Var %</th>}
                  {hasColumn('sales_q') && <th className="px-4 py-3 text-right">Sales Qtr</th>}
                  {hasColumn('sales_q_var') && <th className="px-4 py-3 text-right">Qtr Sales Var %</th>}
                  {hasColumn('roce') && <th className="px-4 py-3 text-right">ROCE %</th>}
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
                    {hasColumn('price') && <td className="px-4 py-3 text-right text-white">{formatNumber(row.price)}</td>}
                    {hasColumn('pe') && <td className="px-4 py-3 text-right text-white">{formatNumber(row.pe)}</td>}
                    {hasColumn('market_cap') && <td className="px-4 py-3 text-right text-white">{formatCompact(row.market_cap)}</td>}
                    {hasColumn('div_yield') && <td className="px-4 py-3 text-right text-white">{formatPercent(row.div_yield)}</td>}
                    {hasColumn('net_profit_q') && <td className="px-4 py-3 text-right text-white">{formatCompact(row.net_profit_q)}</td>}
                    {hasColumn('profit_q_var') && (
                      <td className={`px-4 py-3 text-right ${row.profit_q_var !== null && row.profit_q_var >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                        {formatPercent(row.profit_q_var)}
                      </td>
                    )}
                    {hasColumn('sales_q') && <td className="px-4 py-3 text-right text-white">{formatCompact(row.sales_q)}</td>}
                    {hasColumn('sales_q_var') && (
                      <td className={`px-4 py-3 text-right ${row.sales_q_var !== null && row.sales_q_var >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                        {formatPercent(row.sales_q_var)}
                      </td>
                    )}
                    {hasColumn('roce') && <td className="px-4 py-3 text-right text-white">{formatPercent(row.roce)}</td>}
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
