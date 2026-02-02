import { useState, useEffect, useRef } from 'react';
import { Search, TrendingUp, TrendingDown, DollarSign, IndianRupee, RefreshCw } from 'lucide-react';
import * as d3 from 'd3';
import { formatCurrency, getCurrencySymbol, marketAPI, treemapAPI } from '../api';
import './Technical.css';

const defaultStocks = {
  US: ['AAPL', 'MSFT', 'GOOGL', 'NVDA'],
  IN: ['RELIANCE.NS', 'TCS.NS', 'HDFCBANK.NS', 'INFY.NS']
};

function Technical() {
  const [symbol, setSymbol] = useState('AAPL');
  const [searchInput, setSearchInput] = useState('');
  const [chartType, setChartType] = useState('candle');
  const [timeframe, setTimeframe] = useState('1M');
  const [candleData, setCandleData] = useState([]);
  const [indicators, setIndicators] = useState([]);
  const [stockInfo, setStockInfo] = useState({ name: 'Apple', market: 'US' });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const chartRef = useRef(null);
  
  const market = stockInfo.market;
  const currencySymbol = getCurrencySymbol(market);
  
  // Map timeframe to API range parameter
  const timeframeToRange = {
    '1M': '1mo',
    '3M': '3mo',
    '6M': '6mo',
    '1Y': '1y'
  };

  // Fetch stock data from backend
  const fetchStockData = async (sym) => {
    setLoading(true);
    setError(null);
    
    try {
      // Determine market
      const isIndian = sym.endsWith('.NS') || sym.endsWith('.BO');
      const marketType = isIndian ? 'india' : 'us';
      
      // Fetch candle data
      const range = timeframeToRange[timeframe] || '3mo';
      const interval = '1d';
      
      const [candleResponse, stockResponse] = await Promise.all([
        marketAPI.getCandles(sym, interval, range).catch(() => null),
        treemapAPI.getStockDetails(sym, marketType).catch(() => null)
      ]);
      
      if (candleResponse?.data?.data) {
        // Convert API data to chart format
        const chartData = candleResponse.data.data.map(d => ({
          date: new Date(d.date || d.timestamp),
          open: d.open,
          high: d.high,
          low: d.low,
          close: d.close,
          volume: d.volume
        }));
        setCandleData(chartData);
      }
      
      if (stockResponse?.data) {
        setStockInfo({
          name: stockResponse.data.name || sym,
          market: isIndian ? 'IN' : 'US',
          price: stockResponse.data.price,
          change: stockResponse.data.change_percent
        });
      }
      
      // Fetch indicators
      const indicatorResponse = await marketAPI.getIndicators(sym, interval, range).catch(() => null);
      if (indicatorResponse?.data?.indicators) {
        const ind = indicatorResponse.data.indicators;
        setIndicators([
          { name: 'RSI (14)', value: ind.rsi?.toFixed(2) || '-', status: ind.rsi > 70 ? 'overbought' : ind.rsi < 30 ? 'oversold' : 'neutral' },
          { name: 'MACD', value: ind.macd?.toFixed(2) || '-', status: ind.macd_signal === 'bullish' ? 'bullish' : 'bearish' },
          { name: 'SMA 20', value: ind.sma_20 ? 'Above' : 'Below', status: ind.sma_20 ? 'bullish' : 'bearish' },
          { name: 'SMA 50', value: ind.sma_50 ? 'Above' : 'Below', status: ind.sma_50 ? 'bullish' : 'bearish' },
          { name: 'Volume', value: formatVolume(ind.avg_volume), status: 'normal' },
          { name: 'ATR', value: ind.atr?.toFixed(2) || '-', status: 'normal' },
        ]);
      } else {
        // Default indicators if API fails
        setIndicators([
          { name: 'RSI (14)', value: '-', status: 'neutral' },
          { name: 'MACD', value: '-', status: 'neutral' },
          { name: 'SMA 20', value: '-', status: 'neutral' },
          { name: 'SMA 50', value: '-', status: 'neutral' },
          { name: 'Volume', value: '-', status: 'normal' },
          { name: 'ATR', value: '-', status: 'normal' },
        ]);
      }
    } catch (err) {
      console.error('Technical data fetch error:', err);
      setError('Failed to load chart data');
    } finally {
      setLoading(false);
    }
  };

  const formatVolume = (vol) => {
    if (!vol) return '-';
    if (vol >= 1e9) return (vol / 1e9).toFixed(1) + 'B';
    if (vol >= 1e6) return (vol / 1e6).toFixed(1) + 'M';
    if (vol >= 1e3) return (vol / 1e3).toFixed(1) + 'K';
    return vol.toString();
  };

  useEffect(() => {
    fetchStockData(symbol);
  }, [symbol, timeframe]);
  
  const currentPrice = candleData.length > 0 ? candleData[candleData.length - 1]?.close : stockInfo.price || 0;
  const prevPrice = candleData.length > 1 ? candleData[candleData.length - 2]?.close : currentPrice;
  const priceChange = currentPrice - prevPrice;
  const priceChangePercent = prevPrice ? (priceChange / prevPrice) * 100 : stockInfo.change || 0;

  useEffect(() => {
    if (!chartRef.current || chartType !== 'candle') return;
    
    const container = chartRef.current;
    d3.select(container).selectAll('*').remove();
    
    const margin = { top: 20, right: 60, bottom: 30, left: 10 };
    const width = container.clientWidth - margin.left - margin.right;
    const height = 400 - margin.top - margin.bottom;
    
    const svg = d3.select(container)
      .append('svg')
      .attr('width', width + margin.left + margin.right)
      .attr('height', height + margin.top + margin.bottom)
      .append('g')
      .attr('transform', `translate(${margin.left},${margin.top})`);
    
    // Scales
    const xScale = d3.scaleBand()
      .domain(candleData.map((d, i) => i))
      .range([0, width])
      .padding(0.3);
    
    const yScale = d3.scaleLinear()
      .domain([
        d3.min(candleData, d => d.low) * 0.995,
        d3.max(candleData, d => d.high) * 1.005
      ])
      .range([height, 0]);
    
    // Grid
    svg.append('g')
      .attr('class', 'grid')
      .selectAll('line')
      .data(yScale.ticks(8))
      .join('line')
      .attr('x1', 0)
      .attr('x2', width)
      .attr('y1', d => yScale(d))
      .attr('y2', d => yScale(d))
      .attr('stroke', 'rgba(255,255,255,0.05)');
    
    // Y Axis
    svg.append('g')
      .attr('transform', `translate(${width}, 0)`)
      .call(d3.axisRight(yScale).ticks(8).tickFormat(d => `${currencySymbol}${d.toFixed(0)}`))
      .call(g => g.select('.domain').remove())
      .call(g => g.selectAll('.tick line').remove())
      .call(g => g.selectAll('.tick text').attr('fill', '#71717a').attr('font-size', '11px'));
    
    // Candlesticks
    const candles = svg.selectAll('.candle')
      .data(candleData)
      .join('g')
      .attr('class', 'candle');
    
    // Wicks
    candles.append('line')
      .attr('x1', (d, i) => xScale(i) + xScale.bandwidth() / 2)
      .attr('x2', (d, i) => xScale(i) + xScale.bandwidth() / 2)
      .attr('y1', d => yScale(d.high))
      .attr('y2', d => yScale(d.low))
      .attr('stroke', d => d.close >= d.open ? '#22c55e' : '#ef4444')
      .attr('stroke-width', 1);
    
    // Bodies
    candles.append('rect')
      .attr('x', (d, i) => xScale(i))
      .attr('y', d => yScale(Math.max(d.open, d.close)))
      .attr('width', xScale.bandwidth())
      .attr('height', d => Math.max(1, Math.abs(yScale(d.open) - yScale(d.close))))
      .attr('fill', d => d.close >= d.open ? '#22c55e' : '#ef4444')
      .attr('rx', 1);
    
    // X Axis (dates)
    const tickIndices = candleData
      .map((d, i) => ({ date: d.date, i }))
      .filter((d, i) => i % 10 === 0);
    
    svg.append('g')
      .attr('transform', `translate(0, ${height})`)
      .selectAll('text')
      .data(tickIndices)
      .join('text')
      .attr('x', d => xScale(d.i) + xScale.bandwidth() / 2)
      .attr('y', 20)
      .attr('text-anchor', 'middle')
      .attr('fill', '#71717a')
      .attr('font-size', '10px')
      .text(d => d.date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' }));
    
  }, [candleData, chartType, currencySymbol]);

  const handleSearch = (e) => {
    e.preventDefault();
    const input = searchInput.toUpperCase().trim();
    if (input) {
      // Automatically add .NS for Indian stocks if searching without suffix
      if (input.includes('.NS') || input.includes('.BO')) {
        setSymbol(input);
      } else {
        setSymbol(input);
      }
    }
    setSearchInput('');
  };

  return (
    <div className="technical-page">
      {/* Header */}
      <div className="tech-header">
        <div>
          <h1>Technical Analysis</h1>
          <p>Professional candlestick charts</p>
        </div>
        <form className="search-form" onSubmit={handleSearch}>
          <Search size={18} />
          <input 
            type="text" 
            placeholder="Search symbol..."
            value={searchInput}
            onChange={(e) => setSearchInput(e.target.value)}
          />
        </form>
      </div>

      {/* Stock Info */}
      <div className="stock-header">
        <div className="stock-info">
          <div className="stock-badge">
            {market === 'IN' ? <IndianRupee size={16} /> : <DollarSign size={16} />}
            <span>{market === 'IN' ? 'NSE' : 'NASDAQ'}</span>
          </div>
          <h2>{symbol.split('.')[0]}</h2>
          <span className="stock-name">{stockInfo.name}</span>
        </div>
        <div className="stock-price-info">
          <span className="current-price">{formatCurrency(currentPrice, market)}</span>
          <span className={`price-change ${priceChange >= 0 ? 'positive' : 'negative'}`}>
            {priceChange >= 0 ? <TrendingUp size={16} /> : <TrendingDown size={16} />}
            {priceChange >= 0 ? '+' : ''}{formatCurrency(Math.abs(priceChange), market)} ({priceChangePercent.toFixed(2)}%)
          </span>
        </div>
      </div>

      {/* Chart Controls */}
      <div className="chart-controls">
        <div className="chart-type-toggle">
          <button 
            className={chartType === 'candle' ? 'active' : ''}
            onClick={() => setChartType('candle')}
          >
            Candlestick
          </button>
          <button 
            className={chartType === 'line' ? 'active' : ''}
            onClick={() => setChartType('line')}
          >
            Line
          </button>
        </div>
        <div className="timeframe-toggle">
          {['1M', '3M', '6M', '1Y'].map((tf) => (
            <button 
              key={tf} 
              className={timeframe === tf ? 'active' : ''}
              onClick={() => setTimeframe(tf)}
            >
              {tf}
            </button>
          ))}
        </div>
      </div>

      {/* Chart */}
      <div className="chart-card">
        <div ref={chartRef} className="candlestick-chart"></div>
      </div>

      {/* Indicators */}
      <div className="indicators-grid">
        {indicators.map((ind, i) => (
          <div key={i} className="indicator-card">
            <span className="ind-name">{ind.name}</span>
            <span className="ind-value">{ind.value}</span>
            <span className={`ind-status ${ind.status}`}>{ind.status}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

export default Technical;
