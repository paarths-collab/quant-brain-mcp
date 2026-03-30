'use client';

import { useState, useEffect, useRef, useCallback } from 'react';
import * as d3 from 'd3';
import { treemapAPI, formatLargeNumber } from '@/lib/api';

// ─── Color scale: purple for positive, grey for negative ─────────────────────
const MAX_ABS_CHANGE_FOR_COLOR = 8;

const colorScale = (val: number) => {
  const safe = Number.isFinite(val) ? val : 0;

  const intensity = d3.scaleLinear()
    .domain([0, MAX_ABS_CHANGE_FOR_COLOR])
    .range([0.58, 0.95])
    .clamp(true)(Math.abs(safe));

  return safe >= 0
    ? `rgba(168,85,247,${intensity})`
    : `rgba(156,163,175,${Math.max(0.45, intensity - 0.14)})`;
};

const CARD = 'relative rounded-2xl border border-white/[0.07] bg-white/[0.03] backdrop-blur-xl';
const CONTROL_BTN = 'px-4 py-2 rounded-lg text-[12px] font-mono uppercase tracking-widest transition-all duration-300 border border-white/[0.08]';

// ─── Stock Detail Modal ───────────────────────────────────────────────────────
function StockDetailModal({
  stock, details, loading, currency, marketCode, onClose
}: {
  stock: any; details: any; loading: boolean;
  currency: string; marketCode: string; onClose: () => void;
}) {
  return (
    <div
      className="fixed inset-0 bg-black/80 backdrop-blur-md flex items-center justify-center z-[200] p-4"
      onClick={onClose}
    >
      <div
        className="bg-[#09090b] border border-white/10 rounded-3xl w-full max-w-5xl max-h-[92vh] overflow-hidden flex flex-col shadow-[0_0_80px_rgba(99,102,241,0.15)]"
        onClick={e => e.stopPropagation()}
      >
        {loading ? (
          <div className="flex flex-col items-center justify-center gap-5 p-24">
            <div className="w-10 h-10 border-2 border-indigo-500/20 border-t-indigo-400 rounded-full animate-spin" />
            <p className="font-mono text-[11px] text-indigo-400/60 tracking-[0.3em] uppercase animate-pulse">
              Fetching Intelligence…
            </p>
          </div>
        ) : details ? (
          <>
            {/* Header */}
            <div className="flex items-start justify-between p-8 border-b border-white/[0.06] bg-white/[0.015] shrink-0">
              <div className="space-y-1.5">
                <div className="flex items-center gap-3 flex-wrap">
                  <h2 className="text-2xl font-bold text-white">{details.name}</h2>
                  <span className="px-2.5 py-1 bg-indigo-500/10 border border-indigo-500/25 rounded text-indigo-400 font-mono text-[10px] tracking-widest uppercase">
                    {details.symbol}
                  </span>
                  {details.sector && (
                    <span className="px-2.5 py-1 bg-white/5 border border-white/10 rounded text-white/40 font-mono text-[10px] uppercase">
                      {details.sector}
                    </span>
                  )}
                </div>
                {details.industry && (
                  <p className="text-[11px] text-white/30 font-mono uppercase tracking-[0.15em]">{details.industry}</p>
                )}
              </div>
              <button
                onClick={onClose}
                className="ml-4 p-2.5 bg-white/5 hover:bg-white/10 border border-white/5 rounded-full text-white/30 hover:text-white transition-all shrink-0"
              >
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
                  <line x1="18" y1="6" x2="6" y2="18" /><line x1="6" y1="6" x2="18" y2="18" />
                </svg>
              </button>
            </div>

            <div className="flex-1 overflow-y-auto p-8 space-y-8">
              {/* Price Banner */}
              <div className="flex flex-wrap items-baseline gap-4 p-6 bg-white/[0.02] border border-white/[0.05] rounded-2xl">
                <span className="text-5xl font-mono font-bold text-white">
                  {currency}{details.price?.current?.toLocaleString() ?? '—'}
                </span>
                <span className={`text-xl font-mono font-bold ${(details.price?.change ?? 0) >= 0 ? 'text-indigo-300' : 'text-indigo-400/80'}`}>
                  {(details.price?.change ?? 0) >= 0 ? '▲' : '▼'}{' '}
                  {Math.abs(details.price?.change ?? 0).toFixed(2)}
                  {' '}({details.price?.change_percent?.toFixed(2) ?? '0'}%)
                </span>
              </div>

              {/* Key Metrics */}
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                {[
                  { l: 'Market Cap', v: formatLargeNumber(details.valuation?.market_cap, marketCode) },
                  { l: 'P/E Ratio', v: details.valuation?.pe_ratio?.toFixed(2) ?? '—' },
                  { l: 'Revenue', v: formatLargeNumber(details.financials?.revenue, marketCode) },
                  { l: 'Div Yield', v: details.dividends?.dividend_yield ? `${(details.dividends.dividend_yield * 100).toFixed(2)}%` : '—' },
                ].map(x => (
                  <div key={x.l} className="bg-white/[0.02] border border-white/[0.05] rounded-xl p-5">
                    <p className="text-[10px] text-white/25 uppercase tracking-[0.2em] mb-2">{x.l}</p>
                    <p className="text-xl font-mono font-bold text-white/90">{x.v}</p>
                  </div>
                ))}
              </div>

              {/* Two Columns: Trading + Financials */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
                <div>
                  <p className="text-[10px] text-indigo-400/50 font-mono uppercase tracking-[0.25em] mb-4">Market Operations</p>
                  <div className="space-y-0 border border-white/[0.05] rounded-xl overflow-hidden">
                    {[
                      { l: 'Open', v: details.price?.open != null ? `${currency}${details.price.open.toLocaleString()}` : '—' },
                      { l: 'Day High', v: details.price?.day_high != null ? `${currency}${details.price.day_high.toLocaleString()}` : '—' },
                      { l: 'Day Low', v: details.price?.day_low != null ? `${currency}${details.price.day_low.toLocaleString()}` : '—' },
                      { l: '52W High', v: details.price?.week_52_high != null ? `${currency}${details.price.week_52_high.toLocaleString()}` : '—' },
                      { l: '52W Low', v: details.price?.week_52_low != null ? `${currency}${details.price.week_52_low.toLocaleString()}` : '—' },
                      { l: 'Volume (Today)', v: formatLargeNumber(details.volume?.current, marketCode)?.replace(currency, '') ?? '—' },
                      { l: 'Avg Volume (3M)', v: formatLargeNumber(details.volume?.avg_3m, marketCode)?.replace(currency, '') ?? '—' },
                      { l: 'Beta', v: details.trading?.beta?.toFixed(2) ?? '—' },
                    ].map((x, i) => (
                      <div key={x.l} className={`flex justify-between px-4 py-3 font-mono text-[12px] ${i % 2 === 0 ? 'bg-black/20' : ''}`}>
                        <span className="text-white/30 uppercase tracking-widest">{x.l}</span>
                        <span className="text-white/80 font-semibold">{x.v}</span>
                      </div>
                    ))}
                  </div>
                </div>

                <div>
                  <p className="text-[10px] text-indigo-400/50 font-mono uppercase tracking-[0.25em] mb-4">Financial Integrity</p>
                  <div className="space-y-0 border border-white/[0.05] rounded-xl overflow-hidden">
                    {[
                      { l: 'EV', v: formatLargeNumber(details.valuation?.enterprise_value, marketCode) ?? '—' },
                      { l: 'P/B Ratio', v: details.valuation?.price_to_book?.toFixed(2) ?? '—' },
                      { l: 'P/S Ratio', v: details.valuation?.price_to_sales?.toFixed(2) ?? '—' },
                      { l: 'EPS (Trail)', v: details.financials?.eps_trailing != null ? `${currency}${details.financials.eps_trailing.toFixed(2)}` : '—' },
                      { l: 'Net Income', v: formatLargeNumber(details.financials?.net_income, marketCode) ?? '—' },
                      { l: 'Profit Margin', v: details.financials?.profit_margin != null ? `${(details.financials.profit_margin * 100).toFixed(1)}%` : '—' },
                      { l: 'ROE', v: details.financials?.return_on_equity != null ? `${(details.financials.return_on_equity * 100).toFixed(1)}%` : '—' },
                      { l: 'Total Debt', v: formatLargeNumber(details.balance_sheet?.total_debt, marketCode) ?? '—' },
                    ].map((x, i) => (
                      <div key={x.l} className={`flex justify-between px-4 py-3 font-mono text-[12px] ${i % 2 === 0 ? 'bg-black/20' : ''}`}>
                        <span className="text-white/30 uppercase tracking-widest">{x.l}</span>
                        <span className="text-white/80 font-semibold">{x.v}</span>
                      </div>
                    ))}
                  </div>
                </div>
              </div>

              {/* Analyst Consensus */}
              {details.analyst?.recommendation && (
                <div className="p-5 bg-white/[0.02] border border-white/[0.05] rounded-xl flex flex-wrap gap-6 items-center">
                  <div>
                    <p className="text-[10px] text-white/25 tracking-widest uppercase mb-1">Consensus</p>
                    <p className="font-mono text-lg font-bold text-indigo-400 uppercase">{details.analyst.recommendation}</p>
                  </div>
                  {details.analyst.target_mean && (
                    <div>
                      <p className="text-[10px] text-white/25 tracking-widest uppercase mb-1">Target Price</p>
                      <p className="font-mono text-lg font-bold text-white">{currency}{details.analyst.target_mean.toFixed(2)}</p>
                    </div>
                  )}
                  {details.analyst.num_analysts && (
                    <div>
                      <p className="text-[10px] text-white/25 tracking-widest uppercase mb-1">Analysts</p>
                      <p className="font-mono text-lg font-bold text-white">{details.analyst.num_analysts}</p>
                    </div>
                  )}
                </div>
              )}

              {/* About */}
              {details.company?.description && (
                <div>
                  <p className="text-[10px] text-indigo-400/50 font-mono uppercase tracking-[0.25em] mb-3">About</p>
                  <p className="text-sm text-white/50 leading-relaxed">{details.company.description}</p>
                </div>
              )}

              {/* Company Info */}
              {(details.company?.website || details.company?.employees || details.company?.country) && (
                <div className="grid grid-cols-2 md:grid-cols-3 gap-4 pt-2 border-t border-white/[0.05]">
                  {details.company.website && (
                    <div>
                      <p className="text-[10px] text-white/25 mb-1 uppercase tracking-widest">Website</p>
                      <a href={details.company.website} target="_blank" rel="noopener noreferrer" className="font-mono text-[11px] text-indigo-400 hover:underline break-all">{details.company.website}</a>
                    </div>
                  )}
                  {details.company.employees && (
                    <div>
                      <p className="text-[10px] text-white/25 mb-1 uppercase tracking-widest">Employees</p>
                      <p className="font-mono text-sm text-white/80">{details.company.employees.toLocaleString()}</p>
                    </div>
                  )}
                  {details.company.country && (
                    <div>
                      <p className="text-[10px] text-white/25 mb-1 uppercase tracking-widest">Country</p>
                      <p className="font-mono text-sm text-white/80">{details.company.country}</p>
                    </div>
                  )}
                </div>
              )}
            </div>
          </>
        ) : (
          <div className="p-20 text-center text-white/20 font-mono uppercase tracking-widest text-sm">
            Failed to load stock data
          </div>
        )}
      </div>
    </div>
  );
}

// ─── Main Page ────────────────────────────────────────────────────────────────
export default function SectorsPage() {
  const [market, setMarket] = useState('india');
  const [indicesData, setIndicesData] = useState<any[]>([]);
  const [stocksData, setStocksData] = useState<any>(null);
  const [hoveredItem, setHoveredItem] = useState<any>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [selectedStock, setSelectedStock] = useState<any>(null);
  const [stockDetails, setStockDetails] = useState<any>(null);
  const [loadingDetails, setLoadingDetails] = useState(false);

  // ← KEY FIX: use a ref so D3 closures always see the latest value
  const selectedIndexRef = useRef<string | null>(null);
  const [selectedIndex, _setSelectedIndex] = useState<string | null>(null);
  const setSelectedIndex = useCallback((val: string | null) => {
    selectedIndexRef.current = val;
    _setSelectedIndex(val);
  }, []);

  const treemapRef = useRef<HTMLDivElement>(null);
  const currencySymbol = market === 'india' ? '₹' : '$';
  const marketCode = market === 'india' ? 'IN' : 'US';

  // Load indices on market change
  useEffect(() => {
    setIsLoading(true);
    setSelectedIndex(null);
    setStocksData(null);

    let cancelled = false;
    const load = async () => {
      setIsLoading(true);
      try {
        console.log(`[Sectors] Loading data for market=${market}...`);
        
        // 1. Start both requests in parallel
        const livePromise = treemapAPI.getIndicesLive(market);
        const basePromise = treemapAPI.getIndices(market);

        // 2. Handle base (fast) indices as soon as they arrive
        basePromise.then((base: any) => {
          if (cancelled) return;
          console.log(`[Sectors] Base indices arrived:`, base);
          const baseIndices = Array.isArray(base?.indices) ? base.indices : [];
          if (baseIndices.length > 0) {
            setIndicesData(baseIndices);
            console.log(`[Sectors] ✓ Rendered base metadata (${baseIndices.length} items)`);
          }
        }).catch(err => {
          console.error(`[Sectors] Base indices failed:`, err);
        });

        // 3. Handle live (with prices) indices when they arrive
        try {
          // Wrap in a timeout race to ensure we don't hang if yfinance is slow
          const live: any = await Promise.race([
            livePromise,
            new Promise((_, reject) => setTimeout(() => reject(new Error('Live indices timeout')), 10000)),
          ]);
          
          if (!cancelled && live?.indices?.length > 0) {
            setIndicesData(live.indices);
            console.log(`[Sectors] ✓ Sync'd live prices (${live.indices.length} items)`);
          }
        } catch (liveErr) {
          console.warn(`[Sectors] Live indices sync failed or timed out:`, liveErr);
        }

      } catch (err) {
        console.error(`[Sectors] Primary loading error:`, err);
      } finally {
        if (!cancelled) setIsLoading(false);
      }
    };

    load();
    return () => {
      cancelled = true;
    };
  }, [market]);

  // Load stocks when an index is selected
  useEffect(() => {
    if (!selectedIndex) {
      setStocksData(null);
      return;
    }
    
    setIsLoading(true);
    let cancelled = false;

    // 1. Fetch metadata immediately (fast symbols/names list)
    treemapAPI.getIndexStocks(selectedIndex, market, false)
      .then((res: any) => {
        if (cancelled) return;
        // Only set if we don't have better data from a live sync already
        setStocksData((prev: any) => (prev?.stocks?.length && prev.index?.id === selectedIndex) ? prev : res);
        console.log(`[Sectors] ✓ Rendered stock skeleton for ${selectedIndex}`);
      })
      .catch(console.error);

    // 2. Fetch live prices in the background
    treemapAPI.getIndexStocks(selectedIndex, market, true)
      .then((res: any) => {
        if (cancelled) return;
        setStocksData(res);
        console.log(`[Sectors] ✓ Sync'd live stock prices for ${selectedIndex}`);
      })
      .catch(console.error)
      .finally(() => {
        if (!cancelled) setIsLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [selectedIndex, market]);

  // Load full details when a stock is clicked
  useEffect(() => {
    if (!selectedStock) { setStockDetails(null); return; }
    setLoadingDetails(true);
    treemapAPI.getStockDetails(selectedStock.symbol, market)
      .then((res: any) => setStockDetails(res))
      .catch(console.error)
      .finally(() => setLoadingDetails(false));
  }, [selectedStock, market]);

  // ─── Treemap Renderer ────────────────────────────────────────────────────────
  const renderTreemap = useCallback(() => {
    const container = treemapRef.current;
    console.log(`[Treemap] renderTreemap() called, container exists: ${!!container}`);
    if (!container) {
      console.log('[Treemap] Container ref not available');
      return;
    }

    d3.select(container).selectAll('*').remove();

    const isShowingStocks = !!selectedIndexRef.current && !!stocksData?.stocks;
    const items = isShowingStocks ? stocksData.stocks : indicesData;
    console.log(`[Treemap] Mode: ${isShowingStocks ? 'STOCKS' : 'INDICES'}, items=${items?.length}`);
    if (!items?.length) {
      console.log('[Treemap] No items to render');
      return;
    }

    // Use container's direct dimensions, not parent
    const rect = container.getBoundingClientRect();
    const parentRect = container.parentElement?.getBoundingClientRect();
    const parentParentRect = container.parentElement?.parentElement?.getBoundingClientRect();
    
    console.log(`[Treemap] Container rect: ${rect.width}x${rect.height}`);
    console.log(`[Treemap] Parent rect: ${parentRect?.width}x${parentRect?.height}`);
    console.log(`[Treemap] GrandParent rect: ${parentParentRect?.width}x${parentParentRect?.height}`);

    let width = 1200;
    let height = 700;

    // Prioritize available space
    if (parentRect && parentRect.width > 100) {
      width = Math.max(800, Math.floor(parentRect.width - 16));
    }
    
    if (parentRect && parentRect.height > 100) {
      height = Math.max(500, Math.floor(parentRect.height - 80));
    }

    console.log(`[Treemap] Using dimensions: ${width}x${height}, items=${items.length}`);

    const treeData = {
      name: 'root',
      children: isShowingStocks
        ? items.map((s: any) => ({
          name: s.name,
          symbol: s.symbol,
          value: Math.max(s.market_cap || 1, 1),
          change: s.change_percent || 0,
          price: s.price,
        }))
        : items.map((idx: any) => ({
          name: idx.name,
          id: idx.id,
          // Keep index-level tiles evenly sized for clear visual scanning.
          value: 1,
          change: idx.change_percent || 0,
          price: idx.price,
        })),
    };

    const root = d3.hierarchy(treeData)
      .sum((d: any) => d.value || 1)
      .sort((a: any, b: any) => (b.value || 0) - (a.value || 0));

    d3.treemap()
      .size([width, height])
      .paddingInner(1)
      .paddingOuter(0)
      .round(true)
      .tile(d3.treemapSquarify)(root as any);

    const svg = d3.select(container).append('svg')
      .attr('width', width)
      .attr('height', height)
      .style('display', 'block')
      .style('width', '100%')
      .style('height', '100%')
      .style('background', '#111111');

    // Debug: ensure SVG is rendered
    const svgElement = container.querySelector('svg') as SVGSVGElement;
    console.log(`[Treemap] SVG created:`, { width, height, actualWidth: svgElement?.clientWidth, actualHeight: svgElement?.clientHeight });
    
    if (!svgElement) {
      console.error('[Treemap] SVG element not found!');
      return;
    }

    const leaves = (root as any).leaves();
    console.log(`[Treemap] Rendering ${leaves.length} leaf nodes`);

    const cells = svg.selectAll<SVGGElement, any>('g')
      .data(leaves)
      .join('g')
      .attr('transform', (d: any) => `translate(${d.x0},${d.y0})`)
      .style('cursor', 'pointer');

    // Background rect
    cells.append('rect')
      .attr('width', (d: any) => Math.max(0, d.x1 - d.x0))
      .attr('height', (d: any) => Math.max(0, d.y1 - d.y0))
      .attr('fill', (d: any) => colorScale(d.data.change ?? 0))
      .attr('stroke', 'rgba(255,255,255,0.04)')
      .attr('stroke-width', 1)
      .on('mouseenter', function (_, d: any) {
        d3.select(this)
          .transition().duration(150)
          .attr('stroke', 'rgba(255,255,255,0.3)')
          .attr('stroke-width', 2);
        setHoveredItem(d.data);
      })
      .on('mouseleave', function (_, d: any) {
        d3.select(this)
          .transition().duration(150)
          .attr('stroke', 'rgba(255,255,255,0.04)')
          .attr('stroke-width', 1);
        setHoveredItem(null);
      })
      .on('click', function (_, d: any) {
        // Always read from ref — never from stale closure
        if (!selectedIndexRef.current && d.data.id) {
          setSelectedIndex(d.data.id);
        } else if (selectedIndexRef.current && d.data.symbol) {
          setSelectedStock(d.data);
        }
      });

    // Name label with adaptive wrapping and clipping for readability.
    cells.append('text')
      .attr('x', 10)
      .attr('y', 18)
      .attr('fill', 'rgba(255,255,255,0.98)')
      .attr('stroke', 'rgba(0,0,0,0.65)')
      .attr('stroke-width', 1.1)
      .attr('paint-order', 'stroke')
      .attr('font-size', (d: any) => {
        const w = d.x1 - d.x0;
        const h = d.y1 - d.y0;
        const base = Math.max(9, Math.min(14, Math.floor(Math.min(w / 13, h / 5.5))));
        return `${base}px`;
      })
      .attr('font-weight', '700')
      .attr('font-family', 'monospace')
      .attr('letter-spacing', '0.03em')
      .attr('pointer-events', 'none')
      .each(function (d: any) {
        const text = d3.select(this);
        const w = d.x1 - d.x0;
        const h = d.y1 - d.y0;
        const raw: string = ((isShowingStocks ? d.data.symbol : d.data.name) || '').trim();

        if (!raw || w < 46 || h < 26) {
          text.text('');
          return;
        }

        // Max chars per line based on cell width.
        const charsPerLine = Math.max(5, Math.floor((w - 14) / 7));
        const maxLines = h > 120 ? 3 : h > 70 ? 2 : 1;

        const words = raw.split(/\s+/).filter(Boolean);
        const lines: string[] = [];
        let current = '';

        for (const word of words) {
          const next = current ? `${current} ${word}` : word;
          if (next.length <= charsPerLine) {
            current = next;
            continue;
          }

          if (current) lines.push(current);
          current = word;
          if (lines.length >= maxLines - 1) break;
        }

        if (current && lines.length < maxLines) lines.push(current);

        // Fallback for tokens without spaces (e.g., long symbols/names).
        if (!lines.length) {
          lines.push(raw.length > charsPerLine ? `${raw.slice(0, charsPerLine - 1)}…` : raw);
        }

        text.text('');
        lines.slice(0, maxLines).forEach((line, i) => {
          const output = i === maxLines - 1 && line.length > charsPerLine
            ? `${line.slice(0, charsPerLine - 1)}…`
            : line;
          text.append('tspan')
            .attr('x', 10)
            .attr('dy', i === 0 ? 0 : 14)
            .text(output);
        });
      });

    // Change % badge for high contrast visibility (stocks view only).
    // Indices view doesn't have real-time change data from the base endpoint.
    const changeBadge = cells.append('g')
      .attr('pointer-events', 'none')
      .style('display', (d: any) => {
        const w = d.x1 - d.x0;
        const h = d.y1 - d.y0;
        // Hide badge in indices view or for small tiles
        if (!isShowingStocks) return 'none';
        return (w < 44 || h < 24) ? 'none' : null;
      });

    changeBadge.append('rect')
      .attr('x', 8)
      .attr('y', (d: any) => Math.max(3, d.y1 - d.y0 - 20))
      .attr('width', (d: any) => {
        const w = d.x1 - d.x0;
        return Math.min(72, Math.max(36, w - 12));
      })
      .attr('height', 14)
      .attr('rx', 4)
      .attr('ry', 4)
      .attr('fill', 'rgba(0,0,0,0.72)')
      .attr('stroke', 'none');

    changeBadge.append('text')
      .attr('x', 12)
      .attr('y', (d: any) => Math.max(3, d.y1 - d.y0 - 20) + 10)
      .attr('fill', 'rgba(255,255,255,1)')
      .attr('font-size', '9px')
      .attr('font-weight', '800')
      .attr('font-family', 'monospace')
      .text((d: any) => {
        const c = Number.isFinite(d.data.change) ? d.data.change : 0;
        console.log(`[Badge] ${d.data.name}: change=${c}`);
        return `${c >= 0 ? '+' : ''}${c.toFixed(2)}%`;
      });
  }, [indicesData, stocksData]);

  // Re-render treemap whenever data or market changes
  useEffect(() => {
    renderTreemap();
  }, [renderTreemap]);

  // ResizeObserver for container width changes
  useEffect(() => {
    const container = treemapRef.current;
    if (!container) return;
    const obs = new ResizeObserver(() => renderTreemap());
    obs.observe(container);
    return () => obs.disconnect();
  }, [renderTreemap]);

  const totalItems = stocksData?.stocks?.length ?? indicesData.length;

  return (
    <div className="flex flex-col gap-6" style={{ minHeight: 'calc(100vh - 100px)' }}>
      {/* Header Controls */}
      <div className="flex items-center justify-between shrink-0 flex-wrap gap-3">
        <div className="flex items-center gap-3 flex-wrap">
          {/* Market toggle */}
          <div className="flex items-center gap-1">
            {(['india', 'us'] as const).map(m => (
              <button key={m} onClick={() => setMarket(m)}
                className={`${CONTROL_BTN} ${market === m ? 'bg-indigo-500/10 text-indigo-400 border-indigo-500/30' : 'bg-white/[0.03] text-white/30 hover:bg-white/[0.06]'}`}
              >
                {m === 'india' ? '🇮🇳 India' : '🇺🇸 US'}
              </button>
            ))}
          </div>
          {/* Breadcrumb back button */}
          {selectedIndex && (
            <button
              onClick={() => setSelectedIndex(null)}
              className="font-mono text-[11px] text-indigo-400/60 hover:text-indigo-400 transition-colors uppercase tracking-widest"
            >
              ← All Indices
            </button>
          )}
        </div>

        {/* Status badge */}
        <div className="flex items-center gap-3 px-4 py-2 rounded-lg bg-white/[0.03] border border-indigo-500/20">
          <span className="font-mono text-[10px] text-white/30 uppercase tracking-widest">
            {selectedIndex
              ? `${totalItems} stocks`
              : `${totalItems} indices`}
          </span>
          <div className={`w-1.5 h-1.5 rounded-full ${isLoading ? 'bg-amber-400 animate-pulse' : 'bg-indigo-500 animate-ping'}`} />
        </div>
      </div>

      {/* Loading overlay */}
      {isLoading && (
        <div className="absolute inset-0 z-40 flex items-center justify-center bg-black/40 backdrop-blur-sm rounded-2xl">
          <div className="flex flex-col items-center gap-3">
            <div className="w-8 h-8 border-2 border-indigo-500/20 border-t-indigo-400 rounded-full animate-spin" />
            <p className="font-mono text-[10px] text-indigo-400/50 tracking-[0.3em] uppercase">Loading…</p>
          </div>
        </div>
      )}

      {/* Treemap area */}
      <div className={`${CARD} relative w-full flex flex-col`} style={{ minHeight: '600px', height: '70vh', maxHeight: 'calc(100vh - 200px)' }}>
        {/* Sticky label */}
        <div className="sticky top-0 left-0 p-4 z-10 pointer-events-none shrink-0">
          <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-black/70 backdrop-blur-sm border border-white/5">
            <span className="font-mono text-[10px] text-white/40 uppercase tracking-widest">
              {selectedIndex ? (stocksData?.index?.name ?? selectedIndex) : 'Market Heatmap'}
            </span>
            <span className="text-white/20">·</span>
            <span className="font-mono text-[10px] text-indigo-400/50 uppercase tracking-widest">
              {totalItems} elements
            </span>
          </div>
        </div>

        <div ref={treemapRef} className="w-full flex-1 relative" style={{ minHeight: '400px', overflow: 'auto', background: 'rgba(0,0,0,0.2)' }} />

        {/* Hover tooltip */}
        {hoveredItem && (
          <div className="fixed bottom-8 right-8 p-5 rounded-2xl bg-black/95 border border-indigo-500/25 z-50 min-w-[200px] shadow-2xl pointer-events-none">
            <p className="font-mono text-[9px] text-indigo-400/40 uppercase tracking-widest mb-2">Live Oracle</p>
            <p className="font-bold text-white text-base mb-0.5">{hoveredItem.name}</p>
            <p className="font-mono text-[10px] text-white/30 mb-3 uppercase">{hoveredItem.symbol || hoveredItem.id}</p>
            <div className="space-y-1.5 pt-3 border-t border-white/[0.06]">
              {hoveredItem.price != null && (
                <div className="flex justify-between">
                  <span className="font-mono text-[10px] text-white/20 uppercase">Price</span>
                  <span className="font-mono text-sm text-white">{currencySymbol}{hoveredItem.price.toLocaleString()}</span>
                </div>
              )}
              <div className="flex justify-between">
                <span className="font-mono text-[10px] text-white/20 uppercase">Change</span>
                <span className={`font-mono text-sm font-bold ${(hoveredItem.change ?? 0) >= 0 ? 'text-indigo-300' : 'text-indigo-400/80'}`}>
                  {(hoveredItem.change ?? 0) >= 0 ? '+' : ''}{(hoveredItem.change ?? 0).toFixed(2)}%
                </span>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Stock grid — shown when drilling into an index */}
      {selectedIndex && stocksData?.stocks && (
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5 gap-3 pb-8">
          {stocksData.stocks.map((stock: any, i: number) => (
            <button
              key={i}
              onClick={() => setSelectedStock(stock)}
              className="text-left p-4 bg-white/[0.025] border border-white/[0.06] rounded-xl hover:border-indigo-500/40 hover:bg-white/[0.05] transition-all group"
            >
              <div className="flex items-start justify-between mb-2">
                <div className="min-w-0">
                  <p className="font-mono text-[11px] font-bold text-white/80 group-hover:text-indigo-300 transition-colors truncate">
                    {stock.symbol?.replace('.NS', '').replace('.BO', '')}
                  </p>
                  <p className="font-mono text-[9px] text-white/25 uppercase truncate">{stock.name}</p>
                </div>
                <span className={`ml-1 shrink-0 font-mono text-[10px] font-bold ${(stock.change_percent ?? 0) >= 0 ? 'text-indigo-300' : 'text-indigo-400/80'}`}>
                  {(stock.change_percent ?? 0) >= 0 ? '+' : ''}{(stock.change_percent ?? 0).toFixed(2)}%
                </span>
              </div>
              <p className="font-mono text-sm font-bold text-white/90">
                {currencySymbol}{stock.price?.toLocaleString() ?? '—'}
              </p>
            </button>
          ))}
        </div>
      )}

      {/* Stock Detail Modal */}
      {selectedStock && (
        <StockDetailModal
          stock={selectedStock}
          details={stockDetails}
          loading={loadingDetails}
          currency={currencySymbol}
          marketCode={marketCode}
          onClose={() => setSelectedStock(null)}
        />
      )}

      <style jsx global>{`
        ::-webkit-scrollbar { width: 2px; }
        ::-webkit-scrollbar-track { background: transparent; }
        ::-webkit-scrollbar-thumb { background: rgba(99,102,241,0.2); border-radius: 99px; }
      `}</style>
    </div>
  );
}
