import { useState, useEffect, useRef } from 'react';
import { IndianRupee, DollarSign, TrendingUp, TrendingDown, Globe, RefreshCw, Loader, X, Building2, BarChart3, Wallet, Users } from 'lucide-react';
import * as d3 from 'd3';
import { treemapAPI, getCurrencySymbol, formatLargeNumber } from '../api';
import './Sectors.css';

const colorScale = d3.scaleLinear()
  .domain([-3, 0, 3])
  .range(['#ef4444', '#27272a', '#22c55e']);

function Sectors() {
  const [market, setMarket] = useState('india');
  const [selectedIndex, setSelectedIndex] = useState(null);
  const [hoveredItem, setHoveredItem] = useState(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);
  
  const [indicesData, setIndicesData] = useState([]);
  const [stocksData, setStocksData] = useState(null);
  const [benchmarks, setBenchmarks] = useState([]);
  
  // Stock detail modal state
  const [selectedStock, setSelectedStock] = useState(null);
  const [stockDetails, setStockDetails] = useState(null);
  const [loadingDetails, setLoadingDetails] = useState(false);
  
  const treemapRef = useRef(null);
  const containerRef = useRef(null);
  
  const currencySymbol = market === 'india' ? '₹' : '$';
  const marketCode = market === 'india' ? 'IN' : 'US';

  // Fetch stock details when a stock is selected
  useEffect(() => {
    if (!selectedStock) {
      setStockDetails(null);
      return;
    }
    
    const fetchDetails = async () => {
      setLoadingDetails(true);
      try {
        const res = await treemapAPI.getStockDetails(selectedStock.symbol, market);
        setStockDetails(res.data);
      } catch (err) {
        console.error('Failed to fetch stock details:', err);
      } finally {
        setLoadingDetails(false);
      }
    };
    
    fetchDetails();
  }, [selectedStock, market]);

  const handleStockClick = (stock) => {
    setSelectedStock(stock);
  };

  const closeStockModal = () => {
    setSelectedStock(null);
    setStockDetails(null);
  };

  useEffect(() => {
    const fetchBenchmarks = async () => {
      try {
        const [indiaRes, usRes] = await Promise.all([
          treemapAPI.getBenchmarks('india'),
          treemapAPI.getBenchmarks('us')
        ]);
        const allBenchmarks = [
          ...(indiaRes.data?.benchmarks || []),
          ...(usRes.data?.benchmarks || [])
        ];
        setBenchmarks(allBenchmarks);
      } catch (err) {
        console.error('Failed to fetch benchmarks:', err);
      }
    };
    fetchBenchmarks();
  }, []);

  useEffect(() => {
    const fetchIndices = async () => {
      setIsLoading(true);
      setError(null);
      setSelectedIndex(null);
      setStocksData(null);
      
      try {
        const res = await treemapAPI.getIndicesLive(market);
        setIndicesData(res.data?.indices || []);
      } catch (err) {
        console.error('Failed to fetch indices:', err);
        setError('Failed to load indices. Is the backend running?');
      } finally {
        setIsLoading(false);
      }
    };
    
    fetchIndices();
  }, [market]);

  useEffect(() => {
    if (!selectedIndex) {
      setStocksData(null);
      return;
    }
    
    const fetchStocks = async () => {
      setIsLoading(true);
      try {
        const res = await treemapAPI.getIndexStocks(selectedIndex, market);
        setStocksData(res.data);
      } catch (err) {
        console.error('Failed to fetch stocks:', err);
        setError('Failed to load stocks');
      } finally {
        setIsLoading(false);
      }
    };
    
    fetchStocks();
  }, [selectedIndex, market]);

  const handleIndexClick = (indexId) => {
    if (selectedIndex === indexId) {
      setSelectedIndex(null);
    } else {
      setSelectedIndex(indexId);
    }
  };

  const renderTreemap = () => {
    if (!treemapRef.current) return;
    
    const container = treemapRef.current;
    d3.select(container).selectAll('*').remove();
    
    const width = container.clientWidth || 800;
    const height = 550;
    
    let treeData;
    
    if (stocksData && stocksData.stocks) {
      treeData = {
        name: stocksData.index?.name || 'Index',
        children: stocksData.stocks.map(stock => ({
          name: stock.name,
          symbol: stock.symbol,
          value: Math.abs(stock.change_percent || 1) + 1,
          change: stock.change_percent || 0,
          price: stock.price,
          volume: stock.volume
        }))
      };
    } else if (indicesData.length > 0) {
      treeData = {
        name: market === 'india' ? 'Indian Indices' : 'US Indices',
        children: indicesData.map(idx => ({
          name: idx.name,
          id: idx.id,
          value: idx.constituents_count || 10,
          change: idx.change_percent || 0,
          price: idx.price,
          type: idx.type
        }))
      };
    } else {
      return;
    }
    
    const root = d3.hierarchy(treeData)
      .sum(d => d.value || 1)
      .sort((a, b) => (b.value || 0) - (a.value || 0));
    
    d3.treemap()
      .size([width, height])
      .padding(3)
      .round(true)(root);
    
    const svg = d3.select(container)
      .append('svg')
      .attr('width', width)
      .attr('height', height)
      .style('display', 'block');
    
    const cells = svg.selectAll('g')
      .data(root.leaves())
      .join('g')
      .attr('transform', d => `translate(${d.x0},${d.y0})`)
      .style('cursor', 'pointer');
    
    cells.append('rect')
      .attr('width', d => Math.max(0, d.x1 - d.x0))
      .attr('height', d => Math.max(0, d.y1 - d.y0))
      .attr('fill', d => colorScale(d.data.change || 0))
      .attr('rx', 6)
      .attr('stroke', '#000')
      .attr('stroke-width', 1.5)
      .on('mouseenter', function(event, d) {
        d3.select(this).attr('stroke', '#3b82f6').attr('stroke-width', 2.5);
        setHoveredItem(d.data);
      })
      .on('mouseleave', function() {
        d3.select(this).attr('stroke', '#000').attr('stroke-width', 1.5);
        setHoveredItem(null);
      })
      .on('click', (event, d) => {
        event.stopPropagation();
        if (!selectedIndex && d.data.id) {
          handleIndexClick(d.data.id);
        } else if (selectedIndex && d.data.symbol) {
          // Click on stock - open detail modal
          handleStockClick(d.data);
        }
      });
    
    cells.append('text')
      .attr('x', 10)
      .attr('y', 24)
      .attr('fill', '#fff')
      .attr('font-size', d => {
        const cellWidth = d.x1 - d.x0;
        if (cellWidth > 160) return '14px';
        if (cellWidth > 120) return '12px';
        if (cellWidth > 80) return '10px';
        return '9px';
      })
      .attr('font-weight', '700')
      .text(d => {
        const cellWidth = d.x1 - d.x0;
        if (cellWidth < 40) return '';
        const maxChars = Math.floor(cellWidth / 8);
        return d.data.name?.slice(0, maxChars) || '';
      });
    
    cells.append('text')
      .attr('x', 10)
      .attr('y', 42)
      .attr('fill', 'rgba(255,255,255,0.7)')
      .attr('font-size', '11px')
      .attr('font-weight', '500')
      .text(d => {
        const cellWidth = d.x1 - d.x0;
        const cellHeight = d.y1 - d.y0;
        if (cellWidth < 70 || cellHeight < 55) return '';
        if (d.data.symbol) {
          return d.data.symbol.replace('.NS', '').replace('.BO', '');
        }
        return d.data.type || '';
      });
    
    cells.append('text')
      .attr('x', 10)
      .attr('y', 60)
      .attr('fill', d => (d.data.change || 0) >= 0 ? '#22c55e' : '#ef4444')
      .attr('font-size', '12px')
      .attr('font-weight', '700')
      .text(d => {
        const cellWidth = d.x1 - d.x0;
        const cellHeight = d.y1 - d.y0;
        if (cellWidth < 60 || cellHeight < 70) return '';
        const change = d.data.change || 0;
        return `${change >= 0 ? '+' : ''}${change.toFixed(2)}%`;
      });

    cells.append('text')
      .attr('x', 10)
      .attr('y', 78)
      .attr('fill', 'rgba(255,255,255,0.6)')
      .attr('font-size', '11px')
      .text(d => {
        const cellWidth = d.x1 - d.x0;
        const cellHeight = d.y1 - d.y0;
        if (cellWidth < 80 || cellHeight < 90 || !d.data.price) return '';
        return `${currencySymbol}${d.data.price.toLocaleString()}`;
      });
  };

  useEffect(() => {
    renderTreemap();
  }, [indicesData, stocksData, selectedIndex, market]);

  useEffect(() => {
    const handleResize = () => renderTreemap();
    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, [indicesData, stocksData]);

  const handleRefresh = () => {
    if (selectedIndex) {
      const currentIndex = selectedIndex;
      setSelectedIndex(null);
      setTimeout(() => setSelectedIndex(currentIndex), 100);
    } else {
      setIndicesData([]);
      treemapAPI.getIndicesLive(market).then(res => {
        setIndicesData(res.data?.indices || []);
      });
    }
  };

  const displayedBenchmarks = market === 'india' 
    ? benchmarks.filter(b => b.exchange === 'NSE' || b.exchange === 'BSE')
    : benchmarks;

  return (
    <div className="sectors-page" ref={containerRef}>
      <div className="global-indices">
        <div className="indices-header">
          <Globe size={18} />
          <span>Global Indices</span>
        </div>
        <div className="indices-ticker">
          {displayedBenchmarks.length > 0 ? (
            displayedBenchmarks.map((idx, i) => (
              <div key={i} className="index-item">
                <span className="index-name">{idx.name}</span>
                <span className="index-value">
                  {idx.currency}{idx.price?.toLocaleString() || '-'}
                </span>
                <span className={`index-change ${(idx.change_percent || 0) >= 0 ? 'positive' : 'negative'}`}>
                  {(idx.change_percent || 0) >= 0 ? '+' : ''}{(idx.change_percent || 0).toFixed(2)}%
                </span>
              </div>
            ))
          ) : (
            <span className="loading-text">Loading indices...</span>
          )}
        </div>
      </div>

      <div className="sectors-header">
        <div>
          <h1>{selectedIndex ? stocksData?.index?.name || 'Index' : 'Market Indices'}</h1>
          <p>
            {selectedIndex 
              ? `${stocksData?.summary?.total || 0} stocks • ${stocksData?.summary?.gainers || 0} gainers, ${stocksData?.summary?.losers || 0} losers`
              : 'Click on an index to see constituent stocks'
            }
          </p>
        </div>
        <div className="header-actions">
          <button className="refresh-btn" onClick={handleRefresh} disabled={isLoading}>
            <RefreshCw size={16} className={isLoading ? 'spinning' : ''} />
          </button>
          <div className="market-toggle">
            <button 
              className={market === 'india' ? 'active' : ''}
              onClick={() => setMarket('india')}
            >
              <IndianRupee size={16} />
              <span>India</span>
            </button>
            <button 
              className={market === 'us' ? 'active' : ''}
              onClick={() => setMarket('us')}
            >
              <DollarSign size={16} />
              <span>US</span>
            </button>
          </div>
        </div>
      </div>

      {selectedIndex && (
        <div className="breadcrumb">
          <button onClick={() => setSelectedIndex(null)}>
            ← All Indices
          </button>
          <span className="breadcrumb-divider">/</span>
          <span className="breadcrumb-current">{stocksData?.index?.name || selectedIndex}</span>
        </div>
      )}

      <div className="legend">
        <div className="legend-item">
          <div className="legend-color bearish"></div>
          <span>Bearish (-3%)</span>
        </div>
        <div className="legend-item">
          <div className="legend-color neutral"></div>
          <span>Neutral</span>
        </div>
        <div className="legend-item">
          <div className="legend-color bullish"></div>
          <span>Bullish (+3%)</span>
        </div>
      </div>

      {error && (
        <div className="error-message">
          <p>{error}</p>
          <button onClick={handleRefresh}>Retry</button>
        </div>
      )}

      {isLoading && (
        <div className="loading-overlay">
          <Loader size={32} className="spinning" />
          <span>Loading {selectedIndex ? 'stocks' : 'indices'}...</span>
        </div>
      )}

      <div className="treemap-container">
        <div ref={treemapRef} className="treemap"></div>
      </div>

      {hoveredItem && (
        <div className="hover-info">
          <h3>{hoveredItem.name}</h3>
          {hoveredItem.symbol && (
            <span className="hover-symbol">{hoveredItem.symbol}</span>
          )}
          <div className="hover-stats">
            {hoveredItem.price && (
              <div>
                <span className="label">Price</span>
                <span className="value">{currencySymbol}{hoveredItem.price?.toLocaleString()}</span>
              </div>
            )}
            <div>
              <span className="label">Change</span>
              <span className={`value ${(hoveredItem.change || 0) >= 0 ? 'positive' : 'negative'}`}>
                {(hoveredItem.change || 0) >= 0 ? '+' : ''}{(hoveredItem.change || 0).toFixed(2)}%
              </span>
            </div>
          </div>
        </div>
      )}

      <h2 className="cards-title">
        {selectedIndex ? 'Stocks' : `${market === 'india' ? 'Indian' : 'US'} Indices`}
      </h2>
      <div className="sector-cards">
        {selectedIndex && stocksData?.stocks ? (
          stocksData.stocks.slice(0, 20).map((stock, i) => (
            <div 
              key={i} 
              className="sector-card stock-card clickable"
              onClick={() => handleStockClick(stock)}
            >
              <div className="sector-card-header">
                <h3>{stock.symbol?.replace('.NS', '').replace('.BO', '')}</h3>
                <span className={`change ${(stock.change_percent || 0) >= 0 ? 'positive' : 'negative'}`}>
                  {(stock.change_percent || 0) >= 0 ? <TrendingUp size={14} /> : <TrendingDown size={14} />}
                  {(stock.change_percent || 0) >= 0 ? '+' : ''}{(stock.change_percent || 0).toFixed(2)}%
                </span>
              </div>
              <div className="sector-card-body">
                <span className="stock-name">{stock.name}</span>
                <span className="price">{currencySymbol}{stock.price?.toLocaleString() || '-'}</span>
              </div>
            </div>
          ))
        ) : (
          indicesData.map((idx, i) => (
            <div 
              key={i} 
              className={`sector-card ${selectedIndex === idx.id ? 'selected' : ''}`}
              onClick={() => handleIndexClick(idx.id)}
            >
              <div className="sector-card-header">
                <h3>{idx.name}</h3>
                <span className={`change ${(idx.change_percent || 0) >= 0 ? 'positive' : 'negative'}`}>
                  {(idx.change_percent || 0) >= 0 ? <TrendingUp size={14} /> : <TrendingDown size={14} />}
                  {(idx.change_percent || 0) >= 0 ? '+' : ''}{(idx.change_percent || 0).toFixed(2)}%
                </span>
              </div>
              <div className="sector-card-body">
                <span className="type-badge">{idx.type}</span>
                <span className="stocks">{idx.constituents_count} stocks</span>
              </div>
              {idx.price && (
                <div className="sector-card-price">
                  {currencySymbol}{idx.price.toLocaleString()}
                </div>
              )}
            </div>
          ))
        )}
      </div>

      {/* Stock Detail Modal */}
      {selectedStock && (
        <div className="stock-modal-overlay" onClick={closeStockModal}>
          <div className="stock-modal" onClick={e => e.stopPropagation()}>
            <button className="modal-close" onClick={closeStockModal}>
              <X size={20} />
            </button>
            
            {loadingDetails ? (
              <div className="modal-loading">
                <Loader size={32} className="spinning" />
                <span>Loading stock details...</span>
              </div>
            ) : stockDetails ? (
              <>
                <div className="modal-header">
                  <div className="modal-title">
                    <h2>{stockDetails.name}</h2>
                    <span className="modal-symbol">{stockDetails.symbol}</span>
                  </div>
                  <div className="modal-price-section">
                    <span className="modal-price">
                      {currencySymbol}{stockDetails.price?.current?.toLocaleString() || '-'}
                    </span>
                    <span className={`modal-change ${(stockDetails.price?.change_percent || 0) >= 0 ? 'positive' : 'negative'}`}>
                      {(stockDetails.price?.change_percent || 0) >= 0 ? '+' : ''}
                      {stockDetails.price?.change?.toFixed(2)} ({stockDetails.price?.change_percent?.toFixed(2)}%)
                    </span>
                  </div>
                </div>

                <div className="modal-info-row">
                  {stockDetails.sector && (
                    <span className="info-tag"><Building2 size={14} />{stockDetails.sector}</span>
                  )}
                  {stockDetails.industry && (
                    <span className="info-tag">{stockDetails.industry}</span>
                  )}
                </div>

                <div className="modal-grid">
                  {/* Price Section */}
                  <div className="modal-section">
                    <h3><BarChart3 size={16} /> Price & Range</h3>
                    <div className="stats-grid">
                      <div className="stat">
                        <span className="stat-label">Open</span>
                        <span className="stat-value">{currencySymbol}{stockDetails.price?.open?.toLocaleString() || '-'}</span>
                      </div>
                      <div className="stat">
                        <span className="stat-label">Day High</span>
                        <span className="stat-value">{currencySymbol}{stockDetails.price?.day_high?.toLocaleString() || '-'}</span>
                      </div>
                      <div className="stat">
                        <span className="stat-label">Day Low</span>
                        <span className="stat-value">{currencySymbol}{stockDetails.price?.day_low?.toLocaleString() || '-'}</span>
                      </div>
                      <div className="stat">
                        <span className="stat-label">Prev Close</span>
                        <span className="stat-value">{currencySymbol}{stockDetails.price?.previous_close?.toLocaleString() || '-'}</span>
                      </div>
                      <div className="stat">
                        <span className="stat-label">52W High</span>
                        <span className="stat-value positive">{currencySymbol}{stockDetails.price?.week_52_high?.toLocaleString() || '-'}</span>
                      </div>
                      <div className="stat">
                        <span className="stat-label">52W Low</span>
                        <span className="stat-value negative">{currencySymbol}{stockDetails.price?.week_52_low?.toLocaleString() || '-'}</span>
                      </div>
                    </div>
                  </div>

                  {/* Valuation Section */}
                  <div className="modal-section">
                    <h3><Wallet size={16} /> Valuation</h3>
                    <div className="stats-grid">
                      <div className="stat">
                        <span className="stat-label">Market Cap</span>
                        <span className="stat-value">{formatLargeNumber(stockDetails.valuation?.market_cap, marketCode)}</span>
                      </div>
                      <div className="stat">
                        <span className="stat-label">P/E Ratio</span>
                        <span className="stat-value">{stockDetails.valuation?.pe_ratio?.toFixed(2) || '-'}</span>
                      </div>
                      <div className="stat">
                        <span className="stat-label">Forward P/E</span>
                        <span className="stat-value">{stockDetails.valuation?.forward_pe?.toFixed(2) || '-'}</span>
                      </div>
                      <div className="stat">
                        <span className="stat-label">PEG Ratio</span>
                        <span className="stat-value">{stockDetails.valuation?.peg_ratio?.toFixed(2) || '-'}</span>
                      </div>
                      <div className="stat">
                        <span className="stat-label">P/B Ratio</span>
                        <span className="stat-value">{stockDetails.valuation?.price_to_book?.toFixed(2) || '-'}</span>
                      </div>
                      <div className="stat">
                        <span className="stat-label">EV/EBITDA</span>
                        <span className="stat-value">{stockDetails.valuation?.ev_to_ebitda?.toFixed(2) || '-'}</span>
                      </div>
                    </div>
                  </div>

                  {/* Financials Section */}
                  <div className="modal-section">
                    <h3><TrendingUp size={16} /> Financials</h3>
                    <div className="stats-grid">
                      <div className="stat">
                        <span className="stat-label">Revenue</span>
                        <span className="stat-value">{formatLargeNumber(stockDetails.financials?.revenue, marketCode)}</span>
                      </div>
                      <div className="stat">
                        <span className="stat-label">EPS (TTM)</span>
                        <span className="stat-value">{currencySymbol}{stockDetails.financials?.eps_trailing?.toFixed(2) || '-'}</span>
                      </div>
                      <div className="stat">
                        <span className="stat-label">Profit Margin</span>
                        <span className="stat-value">{stockDetails.financials?.profit_margin ? (stockDetails.financials.profit_margin * 100).toFixed(2) + '%' : '-'}</span>
                      </div>
                      <div className="stat">
                        <span className="stat-label">ROE</span>
                        <span className="stat-value">{stockDetails.financials?.return_on_equity ? (stockDetails.financials.return_on_equity * 100).toFixed(2) + '%' : '-'}</span>
                      </div>
                      <div className="stat">
                        <span className="stat-label">EBITDA</span>
                        <span className="stat-value">{formatLargeNumber(stockDetails.financials?.ebitda, marketCode)}</span>
                      </div>
                      <div className="stat">
                        <span className="stat-label">Gross Margin</span>
                        <span className="stat-value">{stockDetails.financials?.gross_margin ? (stockDetails.financials.gross_margin * 100).toFixed(2) + '%' : '-'}</span>
                      </div>
                    </div>
                  </div>

                  {/* Dividends Section */}
                  <div className="modal-section">
                    <h3><Users size={16} /> Dividends & Analyst</h3>
                    <div className="stats-grid">
                      <div className="stat">
                        <span className="stat-label">Dividend Yield</span>
                        <span className="stat-value">{stockDetails.dividends?.dividend_yield ? (stockDetails.dividends.dividend_yield * 100).toFixed(2) + '%' : '-'}</span>
                      </div>
                      <div className="stat">
                        <span className="stat-label">Payout Ratio</span>
                        <span className="stat-value">{stockDetails.dividends?.payout_ratio ? (stockDetails.dividends.payout_ratio * 100).toFixed(2) + '%' : '-'}</span>
                      </div>
                      <div className="stat">
                        <span className="stat-label">Target Price</span>
                        <span className="stat-value">{currencySymbol}{stockDetails.analyst?.target_mean?.toLocaleString() || '-'}</span>
                      </div>
                      <div className="stat">
                        <span className="stat-label">Recommendation</span>
                        <span className={`stat-value ${stockDetails.analyst?.recommendation === 'buy' || stockDetails.analyst?.recommendation === 'strong_buy' ? 'positive' : ''}`}>
                          {stockDetails.analyst?.recommendation?.toUpperCase() || '-'}
                        </span>
                      </div>
                      <div className="stat">
                        <span className="stat-label">Volume</span>
                        <span className="stat-value">{stockDetails.volume?.current?.toLocaleString() || '-'}</span>
                      </div>
                      <div className="stat">
                        <span className="stat-label">Beta</span>
                        <span className="stat-value">{stockDetails.trading?.beta?.toFixed(2) || '-'}</span>
                      </div>
                    </div>
                  </div>
                </div>

                {stockDetails.company?.description && (
                  <div className="modal-description">
                    <h3>About</h3>
                    <p>{stockDetails.company.description.slice(0, 500)}...</p>
                  </div>
                )}
              </>
            ) : (
              <div className="modal-error">
                <p>Failed to load stock details</p>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

export default Sectors;
