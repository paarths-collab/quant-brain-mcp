import { useState, useEffect, useRef } from 'react';
import { IndianRupee, DollarSign, TrendingUp, TrendingDown, RefreshCw, Loader, X } from 'lucide-react';
import * as d3 from 'd3';
import { treemapAPI, getCurrencySymbol, formatLargeNumber } from '@/api';

const colorScale = d3.scaleLinear<string>()
  .domain([-5, -2, 0, 2, 5])
  .range(['#dc2626', '#ef4444', '#3f3f46', '#22c55e', '#16a34a']);

export default function Sectors() {
  const [market, setMarket] = useState('india');
  const [selectedIndex, setSelectedIndex] = useState<string | null>(null);
  const [hoveredItem, setHoveredItem] = useState<any>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [indicesData, setIndicesData] = useState<any[]>([]);
  const [stocksData, setStocksData] = useState<any>(null);
  const [selectedStock, setSelectedStock] = useState<any>(null);
  const [stockDetails, setStockDetails] = useState<any>(null);
  const [loadingDetails, setLoadingDetails] = useState(false);
  const treemapRef = useRef<HTMLDivElement>(null);
  const currencySymbol = market === 'india' ? '₹' : '$';
  const marketCode = market === 'india' ? 'IN' : 'US';

  useEffect(() => {
    if (!selectedStock) return;
    setLoadingDetails(true);
    treemapAPI.getStockDetails(selectedStock.symbol, market)
      .then(res => setStockDetails(res.data))
      .catch(err => console.error(err))
      .finally(() => setLoadingDetails(false));
  }, [selectedStock, market]);

  useEffect(() => {
    setIsLoading(true);
    setSelectedIndex(null);
    setStocksData(null);
    treemapAPI.getIndicesLive(market)
      .then(res => setIndicesData(res.data?.indices || []))
      .finally(() => setIsLoading(false));
  }, [market]);

  useEffect(() => {
    if (!selectedIndex) { setStocksData(null); return; }
    setIsLoading(true);
    treemapAPI.getIndexStocks(selectedIndex, market)
      .then(res => setStocksData(res.data))
      .finally(() => setIsLoading(false));
  }, [selectedIndex, market]);

  const renderTreemap = () => {
    if (!treemapRef.current) return;
    const container = treemapRef.current;
    d3.select(container).selectAll('*').remove();
    const rect = container.getBoundingClientRect();
    const width = rect.width || container.clientWidth || 800;
    const height = rect.height || 550;
    let treeData: any;
    
    if (stocksData?.stocks) {
      treeData = {
        name: stocksData.index?.name || 'Index',
        children: stocksData.stocks.map((s: any) => {
          // Use market cap directly - this is the weight
          const value = s.market_cap || 100;
          return {
            name: s.name, 
            symbol: s.symbol, 
            value: value,  // raw market cap for proper sizing
            change: s.change_percent || 0, 
            price: s.price
          };
        })
      };
    } else if (indicesData.length > 0) {
      treeData = {
        name: market === 'india' ? 'Indian Indices' : 'US Indices',
        children: indicesData.map((idx: any) => {
          // Use constituent count as weight
          const value = idx.constituents_count || 10;
          return {
            name: idx.name, 
            id: idx.id, 
            value: value,  // raw constituent count
            change: idx.change_percent || 0, 
            price: idx.price, 
            type: idx.type
          };
        })
      };
    } else return;
    
    const root = d3.hierarchy(treeData)
      .sum((d: any) => d.value || 1)
      .sort((a: any, b: any) => (b.value || 0) - (a.value || 0));
    
    // Bloomberg-level treemap configuration
    d3.treemap()
      .size([width, height])       // exact container match
      .paddingInner(1)              // minimal visual separation
      .paddingOuter(0)              // no outer padding - fill edges
      .round(true)                  // pixel-perfect alignment
      .tile(d3.treemapSquarify)(root);  // optimal packing algorithm
    
    const svg = d3.select(container).append('svg').attr('width', width).attr('height', height);
    const cells = svg.selectAll('g').data(root.leaves()).join('g')
      .attr('transform', (d: any) => `translate(${d.x0},${d.y0})`)
      .style('cursor', 'pointer');
    
    cells.append('rect')
      .attr('width', (d: any) => Math.max(0, d.x1 - d.x0))
      .attr('height', (d: any) => Math.max(0, d.y1 - d.y0))
      .attr('fill', (d: any) => colorScale(d.data.change || 0))
      .attr('rx', 0)
      .attr('stroke', 'rgba(0,0,0,0.4)')
      .attr('stroke-width', 1)
      .on('mouseenter', function(event, d: any) {
        d3.select(this).attr('stroke', '#FF9500').attr('stroke-width', 3);
        setHoveredItem(d.data);
      })
      .on('mouseleave', function() {
        d3.select(this).attr('stroke', 'rgba(0,0,0,0.4)').attr('stroke-width', 1);
        setHoveredItem(null);
      })
      .on('click', (event, d: any) => {
        event.stopPropagation();
        if (!selectedIndex && d.data.id) setSelectedIndex(d.data.id);
        else if (selectedIndex && d.data.symbol) setSelectedStock(d.data);
      });
    
    cells.append('text').attr('x', 10).attr('y', 24).attr('fill', '#fff')
      .attr('font-size', (d: any) => d.x1 - d.x0 > 160 ? '14px' : d.x1 - d.x0 > 120 ? '12px' : '10px')
      .attr('font-weight', '700')
      .text((d: any) => d.x1 - d.x0 < 40 ? '' : d.data.name?.slice(0, Math.floor((d.x1 - d.x0) / 8)) || '');
    
    cells.append('text').attr('x', 10).attr('y', 60)
      .attr('fill', (d: any) => (d.data.change || 0) >= 0 ? '#22c55e' : '#ef4444')
      .attr('font-size', '12px').attr('font-weight', '700')
      .text((d: any) => {
        if (d.x1 - d.x0 < 60 || d.y1 - d.y0 < 70) return '';
        const c = d.data.change || 0;
        return `${c >= 0 ? '+' : ''}${c.toFixed(2)}%`;
      });
  };

  useEffect(() => { renderTreemap(); }, [indicesData, stocksData, market]);

  useEffect(() => {
    if (!treemapRef.current) return;
    
    const resizeObserver = new ResizeObserver(() => {
      renderTreemap();
    });
    
    resizeObserver.observe(treemapRef.current);
    return () => resizeObserver.disconnect();
  }, [indicesData, stocksData, market]);

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="font-display text-3xl font-bold text-white">
            {selectedIndex ? stocksData?.index?.name || 'Index' : 'Market Indices'}
          </h1>
          <p className="text-white/60">
            {selectedIndex ? `${stocksData?.summary?.total || 0} stocks` : 'Click on an index'}
          </p>
        </div>
        <div className="flex gap-2">
          <button onClick={() => setMarket('india')} 
            className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium ${market === 'india' ? 'bg-orange-500 text-white' : 'bg-white/5 text-white/60'}`}>
            <IndianRupee size={16} />India
          </button>
          <button onClick={() => setMarket('us')}
            className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium ${market === 'us' ? 'bg-orange-500 text-white' : 'bg-white/5 text-white/60'}`}>
            <DollarSign size={16} />US
          </button>
        </div>
      </div>

      {selectedIndex && (
        <button onClick={() => setSelectedIndex(null)} className="text-orange-400 text-sm">← All Indices</button>
      )}

      {isLoading && (
        <div className="fixed inset-0 bg-black/50 backdrop-blur flex items-center justify-center z-50">
          <Loader size={32} className="text-orange-400 animate-spin" />
        </div>
      )}

      <div className="bg-white/5 border border-white/10 rounded-xl p-4">
        <div ref={treemapRef} className="w-full h-[550px]"></div>
      </div>

      {hoveredItem && (
        <div className="fixed bottom-6 left-1/2 -translate-x-1/2 bg-white/10 backdrop-blur border border-white/20 rounded-lg p-4 z-40">
          <h3 className="font-bold text-white">{hoveredItem.name}</h3>
          <div className="flex gap-4 mt-2">
            {hoveredItem.price && <div><span className="text-xs text-white/40">Price</span><div className="text-sm font-semibold text-white">{currencySymbol}{hoveredItem.price?.toLocaleString()}</div></div>}
            <div><span className="text-xs text-white/40">Change</span><div className={`text-sm font-semibold ${(hoveredItem.change || 0) >= 0 ? 'text-green-500' : 'text-red-500'}`}>{(hoveredItem.change || 0) >= 0 ? '+' : ''}{(hoveredItem.change || 0).toFixed(2)}%</div></div>
          </div>
        </div>
      )}

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {selectedIndex && stocksData?.stocks ? (
          stocksData.stocks.slice(0, 20).map((stock: any, i: number) => (
            <div key={i} className="p-4 bg-white/5 border border-white/10 rounded-lg hover:bg-white/10 cursor-pointer" onClick={() => setSelectedStock(stock)}>
              <div className="flex justify-between mb-2">
                <h3 className="font-bold text-white">{stock.symbol?.replace('.NS', '')}</h3>
                <span className={`text-xs ${(stock.change_percent || 0) >= 0 ? 'text-green-500' : 'text-red-500'}`}>
                  {(stock.change_percent || 0) >= 0 ? '+' : ''}{(stock.change_percent || 0).toFixed(2)}%
                </span>
              </div>
              <div className="text-sm text-white/60">{stock.name}</div>
              <div className="text-lg font-bold text-white mt-1">{currencySymbol}{stock.price?.toLocaleString()}</div>
            </div>
          ))
        ) : (
          indicesData.map((idx: any, i: number) => (
            <div key={i} onClick={() => setSelectedIndex(idx.id)}
              className={`p-4 border rounded-lg cursor-pointer ${selectedIndex === idx.id ? 'border-orange-500 bg-orange-500/20' : 'border-white/10 bg-white/5'}`}>
              <div className="flex justify-between mb-2">
                <h3 className="font-bold text-white">{idx.name}</h3>
                <span className={`text-xs ${(idx.change_percent || 0) >= 0 ? 'text-green-500' : 'text-red-500'}`}>
                  {(idx.change_percent || 0) >= 0 ? '+' : ''}{(idx.change_percent || 0).toFixed(2)}%
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-xs px-2 py-1 bg-white/10 rounded text-white/80">{idx.type}</span>
                <span className="text-xs text-white/60">{idx.constituents_count} stocks</span>
              </div>
              {idx.price && <div className="text-lg font-bold text-white mt-2">{currencySymbol}{idx.price.toLocaleString()}</div>}
            </div>
          ))
        )}
      </div>

      {selectedStock && (
        <div className="fixed inset-0 bg-black/80 backdrop-blur flex items-center justify-center z-50 p-6" onClick={() => setSelectedStock(null)}>
          {loadingDetails ? (
            <div className="flex items-center gap-3 text-white">
              <Loader size={24} className="animate-spin text-orange-400" />
              <span>Loading stock details...</span>
            </div>
          ) : stockDetails ? (
            <div className="bg-zinc-900 border border-white/10 rounded-xl max-w-5xl w-full max-h-[90vh] overflow-y-auto" onClick={e => e.stopPropagation()}>
            <div className="sticky top-0 bg-zinc-900 p-6 border-b border-white/10 flex justify-between items-start z-10">
              <div>
                <h2 className="text-2xl font-bold text-white">{stockDetails.name}</h2>
                <div className="flex items-center gap-3 mt-1">
                  <span className="text-sm text-white/60">{stockDetails.symbol}</span>
                  {stockDetails.sector && <span className="text-xs px-2 py-1 bg-orange-500/20 text-orange-400 rounded">{stockDetails.sector}</span>}
                  {stockDetails.industry && <span className="text-xs text-white/40">• {stockDetails.industry}</span>}
                </div>
              </div>
              <button onClick={() => setSelectedStock(null)} className="p-2 hover:bg-white/10 rounded transition-colors">
                <X size={20} className="text-white" />
              </button>
            </div>

            <div className="p-6 space-y-6">
              {/* Current Price */}
              <div className="flex items-end gap-4">
                <div className="text-4xl font-bold text-white">{formatLargeNumber(stockDetails.price?.current || stockDetails.price, marketCode)}</div>
                {stockDetails.change && (
                  <div className={`flex items-center gap-1 text-lg font-semibold ${stockDetails.change >= 0 ? 'text-green-500' : 'text-red-500'}`}>
                    {stockDetails.change >= 0 ? <TrendingUp size={20} /> : <TrendingDown size={20} />}
                    {stockDetails.change >= 0 ? '+' : ''}{stockDetails.change?.toFixed(2)}
                    {stockDetails.change_percent && ` (${stockDetails.change_percent >= 0 ? '+' : ''}${stockDetails.change_percent.toFixed(2)}%)`}
                  </div>
                )}
              </div>

              {/* Trading Information */}
              {(stockDetails.price?.open || stockDetails.price?.high || stockDetails.price?.low || stockDetails.trading?.volume) && (
                <div>
                  <h3 className="text-sm font-semibold text-white/60 mb-3">Trading Data</h3>
                  <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                    {stockDetails.price?.open && (
                      <div className="p-3 bg-white/5 border border-white/10 rounded-lg">
                        <div className="text-xs text-white/40 mb-1">Open</div>
                        <div className="text-white font-semibold">{formatLargeNumber(stockDetails.price.open, marketCode)}</div>
                      </div>
                    )}
                    {stockDetails.price?.high && (
                      <div className="p-3 bg-white/5 border border-white/10 rounded-lg">
                        <div className="text-xs text-white/40 mb-1">High</div>
                        <div className="text-green-500 font-semibold">{formatLargeNumber(stockDetails.price.high, marketCode)}</div>
                      </div>
                    )}
                    {stockDetails.price?.low && (
                      <div className="p-3 bg-white/5 border border-white/10 rounded-lg">
                        <div className="text-xs text-white/40 mb-1">Low</div>
                        <div className="text-red-500 font-semibold">{formatLargeNumber(stockDetails.price.low, marketCode)}</div>
                      </div>
                    )}
                    {stockDetails.trading?.volume && (
                      <div className="p-3 bg-white/5 border border-white/10 rounded-lg">
                        <div className="text-xs text-white/40 mb-1">Volume</div>
                        <div className="text-white font-semibold">{formatLargeNumber(stockDetails.trading.volume, marketCode).replace(currencySymbol, '')}</div>
                      </div>
                    )}
                    {stockDetails.trading?.avg_volume && (
                      <div className="p-3 bg-white/5 border border-white/10 rounded-lg">
                        <div className="text-xs text-white/40 mb-1">Avg Volume</div>
                        <div className="text-white font-semibold">{formatLargeNumber(stockDetails.trading.avg_volume, marketCode).replace(currencySymbol, '')}</div>
                      </div>
                    )}
                    {stockDetails.trading?.week_52_high && (
                      <div className="p-3 bg-white/5 border border-white/10 rounded-lg">
                        <div className="text-xs text-white/40 mb-1">52W High</div>
                        <div className="text-white font-semibold">{formatLargeNumber(stockDetails.trading.week_52_high, marketCode)}</div>
                      </div>
                    )}
                    {stockDetails.trading?.week_52_low && (
                      <div className="p-3 bg-white/5 border border-white/10 rounded-lg">
                        <div className="text-xs text-white/40 mb-1">52W Low</div>
                        <div className="text-white font-semibold">{formatLargeNumber(stockDetails.trading.week_52_low, marketCode)}</div>
                      </div>
                    )}
                    {stockDetails.trading?.beta && (
                      <div className="p-3 bg-white/5 border border-white/10 rounded-lg">
                        <div className="text-xs text-white/40 mb-1">Beta</div>
                        <div className="text-white font-semibold">{stockDetails.trading.beta.toFixed(2)}</div>
                      </div>
                    )}
                  </div>
                </div>
              )}

              {/* Valuation Metrics */}
              <div>
                <h3 className="text-sm font-semibold text-white/60 mb-3">Valuation</h3>
                <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                  {stockDetails.valuation?.market_cap && (
                    <div className="p-3 bg-white/5 border border-white/10 rounded-lg">
                      <div className="text-xs text-white/40 mb-1">Market Cap</div>
                      <div className="text-white font-semibold">{formatLargeNumber(stockDetails.valuation.market_cap, marketCode)}</div>
                    </div>
                  )}
                  {stockDetails.valuation?.pe_ratio && (
                    <div className="p-3 bg-white/5 border border-white/10 rounded-lg">
                      <div className="text-xs text-white/40 mb-1">P/E Ratio</div>
                      <div className="text-white font-semibold">{stockDetails.valuation.pe_ratio.toFixed(2)}</div>
                    </div>
                  )}
                  {stockDetails.valuation?.pb_ratio && (
                    <div className="p-3 bg-white/5 border border-white/10 rounded-lg">
                      <div className="text-xs text-white/40 mb-1">P/B Ratio</div>
                      <div className="text-white font-semibold">{stockDetails.valuation.pb_ratio.toFixed(2)}</div>
                    </div>
                  )}
                  {stockDetails.valuation?.ps_ratio && (
                    <div className="p-3 bg-white/5 border border-white/10 rounded-lg">
                      <div className="text-xs text-white/40 mb-1">P/S Ratio</div>
                      <div className="text-white font-semibold">{stockDetails.valuation.ps_ratio.toFixed(2)}</div>
                    </div>
                  )}
                  {stockDetails.valuation?.peg_ratio && (
                    <div className="p-3 bg-white/5 border border-white/10 rounded-lg">
                      <div className="text-xs text-white/40 mb-1">PEG Ratio</div>
                      <div className="text-white font-semibold">{stockDetails.valuation.peg_ratio.toFixed(2)}</div>
                    </div>
                  )}
                  {stockDetails.valuation?.ev_ebitda && (
                    <div className="p-3 bg-white/5 border border-white/10 rounded-lg">
                      <div className="text-xs text-white/40 mb-1">EV/EBITDA</div>
                      <div className="text-white font-semibold">{stockDetails.valuation.ev_ebitda.toFixed(2)}</div>
                    </div>
                  )}
                  {stockDetails.valuation?.enterprise_value && (
                    <div className="p-3 bg-white/5 border border-white/10 rounded-lg">
                      <div className="text-xs text-white/40 mb-1">Enterprise Value</div>
                      <div className="text-white font-semibold">{formatLargeNumber(stockDetails.valuation.enterprise_value, marketCode)}</div>
                    </div>
                  )}
                </div>
              </div>

              {/* Financial Performance */}
              <div>
                <h3 className="text-sm font-semibold text-white/60 mb-3">Financials</h3>
                <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                  {stockDetails.financials?.revenue && (
                    <div className="p-3 bg-white/5 border border-white/10 rounded-lg">
                      <div className="text-xs text-white/40 mb-1">Revenue</div>
                      <div className="text-white font-semibold">{formatLargeNumber(stockDetails.financials.revenue, marketCode)}</div>
                    </div>
                  )}
                  {stockDetails.financials?.profit && (
                    <div className="p-3 bg-white/5 border border-white/10 rounded-lg">
                      <div className="text-xs text-white/40 mb-1">Net Income</div>
                      <div className="text-white font-semibold">{formatLargeNumber(stockDetails.financials.profit, marketCode)}</div>
                    </div>
                  )}
                  {stockDetails.financials?.eps && (
                    <div className="p-3 bg-white/5 border border-white/10 rounded-lg">
                      <div className="text-xs text-white/40 mb-1">EPS</div>
                      <div className="text-white font-semibold">{currencySymbol}{stockDetails.financials.eps.toFixed(2)}</div>
                    </div>
                  )}
                  {stockDetails.financials?.profit_margin && (
                    <div className="p-3 bg-white/5 border border-white/10 rounded-lg">
                      <div className="text-xs text-white/40 mb-1">Profit Margin</div>
                      <div className="text-white font-semibold">{(stockDetails.financials.profit_margin * 100).toFixed(2)}%</div>
                    </div>
                  )}
                  {stockDetails.financials?.roe && (
                    <div className="p-3 bg-white/5 border border-white/10 rounded-lg">
                      <div className="text-xs text-white/40 mb-1">ROE</div>
                      <div className="text-white font-semibold">{(stockDetails.financials.roe * 100).toFixed(2)}%</div>
                    </div>
                  )}
                  {stockDetails.financials?.roa && (
                    <div className="p-3 bg-white/5 border border-white/10 rounded-lg">
                      <div className="text-xs text-white/40 mb-1">ROA</div>
                      <div className="text-white font-semibold">{(stockDetails.financials.roa * 100).toFixed(2)}%</div>
                    </div>
                  )}
                  {stockDetails.dividends?.dividend_yield && (
                    <div className="p-3 bg-white/5 border border-white/10 rounded-lg">
                      <div className="text-xs text-white/40 mb-1">Dividend Yield</div>
                      <div className="text-white font-semibold">{(stockDetails.dividends.dividend_yield * 100).toFixed(2)}%</div>
                    </div>
                  )}
                  {stockDetails.dividends?.payout_ratio && (
                    <div className="p-3 bg-white/5 border border-white/10 rounded-lg">
                      <div className="text-xs text-white/40 mb-1">Payout Ratio</div>
                      <div className="text-white font-semibold">{(stockDetails.dividends.payout_ratio * 100).toFixed(2)}%</div>
                    </div>
                  )}
                </div>
              </div>

              {/* Description */}
              {stockDetails.company?.description && (
                <div>
                  <h3 className="text-sm font-semibold text-white/60 mb-3">About</h3>
                  <p className="text-sm text-white/80 leading-relaxed">{stockDetails.company.description}</p>
                </div>
              )}

              {/* Additional Info */}
              {(stockDetails.company?.website || stockDetails.company?.employees || stockDetails.company?.country) && (
                <div>
                  <h3 className="text-sm font-semibold text-white/60 mb-3">Company Info</h3>
                  <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
                    {stockDetails.company?.website && (
                      <div className="p-3 bg-white/5 border border-white/10 rounded-lg">
                        <div className="text-xs text-white/40 mb-1">Website</div>
                        <a href={stockDetails.company.website} target="_blank" rel="noopener noreferrer" className="text-orange-400 text-sm hover:underline break-all">{stockDetails.company.website}</a>
                      </div>
                    )}
                    {stockDetails.company?.employees && (
                      <div className="p-3 bg-white/5 border border-white/10 rounded-lg">
                        <div className="text-xs text-white/40 mb-1">Employees</div>
                        <div className="text-white font-semibold">{stockDetails.company.employees.toLocaleString()}</div>
                      </div>
                    )}
                    {stockDetails.company?.country && (
                      <div className="p-3 bg-white/5 border border-white/10 rounded-lg">
                        <div className="text-xs text-white/40 mb-1">Country</div>
                        <div className="text-white font-semibold">{stockDetails.company.country}</div>
                      </div>
                    )}
                    {stockDetails.company?.city && (
                      <div className="p-3 bg-white/5 border border-white/10 rounded-lg">
                        <div className="text-xs text-white/40 mb-1">City</div>
                        <div className="text-white font-semibold">{stockDetails.company.city}</div>
                      </div>
                    )}
                    {stockDetails.company?.phone && (
                      <div className="p-3 bg-white/5 border border-white/10 rounded-lg">
                        <div className="text-xs text-white/40 mb-1">Phone</div>
                        <div className="text-white font-semibold text-sm">{stockDetails.company.phone}</div>
                      </div>
                    )}
                  </div>
                </div>
              )}
            </div>
          </div>
          ) : (
            <div className="text-white">Failed to load stock details</div>
          )}
        </div>
      )}
    </div>
  );
}
