import { useState, useEffect, useRef } from 'react';
import { Search, TrendingUp, TrendingDown, DollarSign, IndianRupee } from 'lucide-react';
import * as d3 from 'd3';
import { formatCurrency, getCurrencySymbol, marketAPI, treemapAPI } from '@/api';

interface CandleData {
  date: Date;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
}

interface Indicator {
  name: string;
  value: string;
  status: string;
}

interface StockInfo {
  name: string;
  market: string;
  price?: number;
  change?: number;
}

export default function Technical() {
  const [symbol, setSymbol] = useState('AAPL');
  const [searchInput, setSearchInput] = useState('');
  const [chartType, setChartType] = useState('candle');
  const [timeframe, setTimeframe] = useState('1M');
  const [candleData, setCandleData] = useState<CandleData[]>([]);
  const [indicators, setIndicators] = useState<Indicator[]>([]);
  const [stockInfo, setStockInfo] = useState<StockInfo>({ name: 'Apple', market: 'US' });
  const [loading, setLoading] = useState(false);
  const chartRef = useRef<HTMLDivElement>(null);
  
  const market = stockInfo.market;
  const currencySymbol = getCurrencySymbol(market);
  
  const timeframeToRange: Record<string, string> = {
    '1M': '1mo',
    '3M': '3mo',
    '6M': '6mo',
    '1Y': '1y'
  };
  
  const getLast = (arr: any) => (Array.isArray(arr) && arr.length ? arr[arr.length - 1] : null);

  const fetchStockData = async (sym: string) => {
    setLoading(true);
    
    try {
      const isIndian = sym.endsWith('.NS') || sym.endsWith('.BO');
      const marketType = isIndian ? 'india' : 'us';
      const range = timeframeToRange[timeframe] || '3mo';
      const interval = '1d';
      
      const [candleResponse, stockResponse] = await Promise.all([
        marketAPI.getCandles(sym, interval, range).catch(() => null),
        treemapAPI.getStockDetails(sym, marketType).catch(() => null)
      ]);
      
      let latestClose: number | null = null;
      let avgVolume: number | null = null;
      let chartData: CandleData[] = [];
  
      if (candleResponse?.data?.data) {
        chartData = candleResponse.data.data.map((d: any) => ({
          date: new Date(d.date || d.timestamp),
          open: d.open,
          high: d.high,
          low: d.low,
          close: d.close,
          volume: d.volume
        }));
        setCandleData(chartData);
        
        if (chartData.length > 0) {
          latestClose = chartData[chartData.length - 1]?.close ?? null;
          const volumes = chartData.map(d => d.volume).filter((v: any) => typeof v === 'number');
          if (volumes.length) {
            avgVolume = volumes.reduce((sum: number, v: number) => sum + v, 0) / volumes.length;
          }
        }
      }
      
      if (stockResponse?.data) {
        setStockInfo({
          name: stockResponse.data.name || sym,
          market: isIndian ? 'IN' : 'US',
          price: stockResponse.data.price,
          change: stockResponse.data.change_percent
        });
      }
      
      const indicatorResponse = await marketAPI.getIndicators(sym, interval, range).catch(() => null);
      if (indicatorResponse?.data?.indicators) {
        const ind = indicatorResponse.data.indicators;
        console.log('Indicators received:', ind); // Debug log
        const rsi = getLast(ind.rsi);
        const macdLine = getLast(ind.macd?.line);
        const macdSignal = getLast(ind.macd?.signal);
        const ema20 = getLast(ind.ema?.['20']);
        const ema50 = getLast(ind.ema?.['50']);
        const atr = getLast(ind.atr);
        
        console.log('Parsed values:', { rsi, macdLine, macdSignal, ema20, ema50, atr }); // Debug log
        
        setIndicators([
          { 
            name: 'RSI (14)', 
            value: rsi !== null && typeof rsi === 'number' ? rsi.toFixed(2) : '-', 
            status: rsi !== null && typeof rsi === 'number' ? (rsi > 70 ? 'overbought' : rsi < 30 ? 'oversold' : 'neutral') : 'neutral'
          },
          { 
            name: 'MACD', 
            value: macdLine !== null && typeof macdLine === 'number' ? macdLine.toFixed(2) : '-', 
            status: macdLine !== null && macdSignal !== null && typeof macdLine === 'number' && typeof macdSignal === 'number' && macdLine >= macdSignal ? 'bullish' : 'bearish'
          },
          { 
            name: 'EMA 20', 
            value: ema20 !== null && latestClose !== null && typeof ema20 === 'number' ? (latestClose >= ema20 ? 'Above' : 'Below') : '-', 
            status: ema20 !== null && latestClose !== null && typeof ema20 === 'number' && latestClose >= ema20 ? 'bullish' : 'bearish'
          },
          { 
            name: 'EMA 50', 
            value: ema50 !== null && latestClose !== null && typeof ema50 === 'number' ? (latestClose >= ema50 ? 'Above' : 'Below') : '-', 
            status: ema50 !== null && latestClose !== null && typeof ema50 === 'number' && latestClose >= ema50 ? 'bullish' : 'bearish'
          },
          { 
            name: 'Volume', 
            value: avgVolume !== null ? formatVolume(avgVolume) : '-', 
            status: 'normal' 
          },
          { 
            name: 'ATR', 
            value: atr !== null && typeof atr === 'number' ? atr.toFixed(2) : '-', 
            status: 'normal' 
          },
        ]);
      } else {
        console.log('No indicators data received'); // Debug log
        // Set default empty indicators
        setIndicators([
          { name: 'RSI (14)', value: '-', status: 'neutral' },
          { name: 'MACD', value: '-', status: 'neutral' },
          { name: 'EMA 20', value: '-', status: 'neutral' },
          { name: 'EMA 50', value: '-', status: 'neutral' },
          { name: 'Volume', value: avgVolume !== null ? formatVolume(avgVolume) : '-', status: 'normal' },
          { name: 'ATR', value: '-', status: 'normal' },
        ]);
      }
    } catch (err) {
      console.error('Technical data fetch error:', err);
    } finally {
      setLoading(false);
    }
  };

  const formatVolume = (vol: number) => {
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
    if (!chartRef.current || candleData.length === 0) return;
    
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
    
    // Tooltip
    const tooltip = d3.select(container)
      .append('div')
      .attr('class', 'chart-tooltip')
      .style('position', 'absolute')
      .style('background', 'rgba(0, 0, 0, 0.9)')
      .style('color', 'white')
      .style('padding', '8px 12px')
      .style('border-radius', '6px')
      .style('font-size', '12px')
      .style('pointer-events', 'none')
      .style('opacity', '0')
      .style('z-index', '1000')
      .style('border', '1px solid rgba(255, 255, 255, 0.1)');
    
    if (chartType === 'line') {
      // Line chart
      const xScale = d3.scaleTime()
        .domain(d3.extent(candleData, d => d.date) as [Date, Date])
        .range([0, width]);
      
      const yScale = d3.scaleLinear()
        .domain([
          d3.min(candleData, d => d.close)! * 0.995,
          d3.max(candleData, d => d.close)! * 1.005
        ])
        .range([height, 0]);
      
      // Grid lines
      svg.append('g')
        .selectAll('line')
        .data(yScale.ticks(8))
        .join('line')
        .attr('x1', 0)
        .attr('x2', width)
        .attr('y1', d => yScale(d))
        .attr('y2', d => yScale(d))
        .attr('stroke', 'rgba(255,255,255,0.05)');
      
      // Y-axis
      svg.append('g')
        .attr('transform', `translate(${width}, 0)`)
        .call(d3.axisRight(yScale).ticks(8).tickFormat(d => `${currencySymbol}${d.toFixed(0)}`))
        .call(g => g.select('.domain').remove())
        .call(g => g.selectAll('.tick line').remove())
        .call(g => g.selectAll('.tick text').attr('fill', '#71717a').attr('font-size', '11px'));
      
      // Area gradient
      const gradient = svg.append('defs')
        .append('linearGradient')
        .attr('id', 'areaGradient')
        .attr('x1', '0%')
        .attr('x2', '0%')
        .attr('y1', '0%')
        .attr('y2', '100%');
      
      gradient.append('stop')
        .attr('offset', '0%')
        .attr('stop-color', '#FF9500')
        .attr('stop-opacity', 0.3);
      
      gradient.append('stop')
        .attr('offset', '100%')
        .attr('stop-color', '#FF9500')
        .attr('stop-opacity', 0);
      
      // Area
      const area = d3.area<CandleData>()
        .x(d => xScale(d.date))
        .y0(height)
        .y1(d => yScale(d.close))
        .curve(d3.curveMonotoneX);
      
      svg.append('path')
        .datum(candleData)
        .attr('fill', 'url(#areaGradient)')
        .attr('d', area);
      
      // Line
      const line = d3.line<CandleData>()
        .x(d => xScale(d.date))
        .y(d => yScale(d.close))
        .curve(d3.curveMonotoneX);
      
      svg.append('path')
        .datum(candleData)
        .attr('fill', 'none')
        .attr('stroke', '#FF9500')
        .attr('stroke-width', 2)
        .attr('d', line);
      
      // Hover points for line chart
      svg.selectAll('.hover-point')
        .data(candleData)
        .join('circle')
        .attr('class', 'hover-point')
        .attr('cx', d => xScale(d.date))
        .attr('cy', d => yScale(d.close))
        .attr('r', 4)
        .attr('fill', '#FF9500')
        .attr('opacity', 0)
        .on('mouseover', function(event, d) {
          d3.select(this).attr('opacity', 1);
          tooltip
            .style('opacity', '1')
            .html(`
              <div style="font-weight: 600; margin-bottom: 4px;">
                ${d.date.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })}
              </div>
              <div style="color: #FF9500;">
                Close: ${formatCurrency(d.close, market)}
              </div>
            `)
            .style('left', (event.pageX - container.getBoundingClientRect().left + 10) + 'px')
            .style('top', (event.pageY - container.getBoundingClientRect().top - 10) + 'px');
        })
        .on('mouseout', function() {
          d3.select(this).attr('opacity', 0);
          tooltip.style('opacity', '0');
        });
      
      // X-axis labels
      const tickDates = candleData
        .filter((d, i) => i % Math.ceil(candleData.length / 8) === 0);
      
      svg.append('g')
        .attr('transform', `translate(0, ${height})`)
        .selectAll('text')
        .data(tickDates)
        .join('text')
        .attr('x', d => xScale(d.date))
        .attr('y', 20)
        .attr('text-anchor', 'middle')
        .attr('fill', '#71717a')
        .attr('font-size', '10px')
        .text(d => d.date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' }));
      
    } else {
      // Candlestick chart
      const xScale = d3.scaleBand()
        .domain(candleData.map((d, i) => i.toString()))
        .range([0, width])
        .padding(0.3);
      
      const yScale = d3.scaleLinear()
        .domain([
          d3.min(candleData, d => d.low)! * 0.995,
          d3.max(candleData, d => d.high)! * 1.005
        ])
        .range([height, 0]);
      
      // Grid lines
      svg.append('g')
        .selectAll('line')
        .data(yScale.ticks(8))
        .join('line')
        .attr('x1', 0)
        .attr('x2', width)
        .attr('y1', d => yScale(d))
        .attr('y2', d => yScale(d))
        .attr('stroke', 'rgba(255,255,255,0.05)');
      
      // Y-axis
      svg.append('g')
        .attr('transform', `translate(${width}, 0)`)
        .call(d3.axisRight(yScale).ticks(8).tickFormat(d => `${currencySymbol}${d.toFixed(0)}`))
        .call(g => g.select('.domain').remove())
        .call(g => g.selectAll('.tick line').remove())
        .call(g => g.selectAll('.tick text').attr('fill', '#71717a').attr('font-size', '11px'));
      
      // Candles
      const candles = svg.selectAll('.candle')
        .data(candleData)
        .join('g')
        .attr('class', 'candle')
        .style('cursor', 'pointer');
      
      candles.append('line')
        .attr('x1', (d, i) => (xScale(i.toString()) || 0) + xScale.bandwidth() / 2)
        .attr('x2', (d, i) => (xScale(i.toString()) || 0) + xScale.bandwidth() / 2)
        .attr('y1', d => yScale(d.high))
        .attr('y2', d => yScale(d.low))
        .attr('stroke', d => d.close >= d.open ? '#22c55e' : '#ef4444')
        .attr('stroke-width', 1);
      
      candles.append('rect')
        .attr('x', (d, i) => xScale(i.toString()) || 0)
        .attr('y', d => yScale(Math.max(d.open, d.close)))
        .attr('width', xScale.bandwidth())
        .attr('height', d => Math.max(1, Math.abs(yScale(d.open) - yScale(d.close))))
        .attr('fill', d => d.close >= d.open ? '#22c55e' : '#ef4444')
        .attr('rx', 1);
      
      // Tooltip for candlesticks
      candles.on('mouseover', function(event, d) {
        d3.select(this).selectAll('rect').attr('opacity', 0.8);
        const isGreen = d.close >= d.open;
        tooltip
          .style('opacity', '1')
          .html(`
            <div style="font-weight: 600; margin-bottom: 6px;">
              ${d.date.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })}
            </div>
            <div style="display: grid; grid-template-columns: auto auto; gap: 4px 12px;">
              <span style="color: #94a3b8;">Open:</span><span>${formatCurrency(d.open, market)}</span>
              <span style="color: #94a3b8;">High:</span><span style="color: #22c55e;">${formatCurrency(d.high, market)}</span>
              <span style="color: #94a3b8;">Low:</span><span style="color: #ef4444;">${formatCurrency(d.low, market)}</span>
              <span style="color: #94a3b8;">Close:</span><span style="color: ${isGreen ? '#22c55e' : '#ef4444'}; font-weight: 600;">${formatCurrency(d.close, market)}</span>
            </div>
          `)
          .style('left', (event.pageX - container.getBoundingClientRect().left + 10) + 'px')
          .style('top', (event.pageY - container.getBoundingClientRect().top - 10) + 'px');
      })
      .on('mouseout', function() {
        d3.select(this).selectAll('rect').attr('opacity', 1);
        tooltip.style('opacity', '0');
      });
      
      // X-axis labels
      const tickIndices = candleData
        .map((d, i) => ({ date: d.date, i }))
        .filter((d, i) => i % 10 === 0);
      
      svg.append('g')
        .attr('transform', `translate(0, ${height})`)
        .selectAll('text')
        .data(tickIndices)
        .join('text')
        .attr('x', d => (xScale(d.i.toString()) || 0) + xScale.bandwidth() / 2)
        .attr('y', 20)
        .attr('text-anchor', 'middle')
        .attr('fill', '#71717a')
        .attr('font-size', '10px')
        .text(d => d.date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' }));
    }
    
  }, [candleData, chartType, currencySymbol]);

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    const input = searchInput.toUpperCase().trim();
    if (input) setSymbol(input);
    setSearchInput('');
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="font-display text-3xl font-bold text-white">Technical Analysis</h1>
          <p className="text-white/60">Professional candlestick charts</p>
        </div>
        <form onSubmit={handleSearch} className="flex items-center gap-2 px-4 py-3 bg-white/5 border border-white/10 rounded-lg">
          <Search size={18} className="text-white/40" />
          <input 
            type="text" 
            placeholder="Search symbol..."
            value={searchInput}
            onChange={(e) => setSearchInput(e.target.value)}
            className="bg-transparent border-none outline-none text-sm w-40 text-white placeholder:text-white/40"
          />
        </form>
      </div>

      <div className="flex items-center justify-between p-6 bg-white/5 border border-white/10 rounded-xl">
        <div className="space-y-2">
          <div className="inline-flex items-center gap-1.5 px-2.5 py-1 bg-orange-500/20 rounded-md text-xs font-semibold text-orange-400">
            {market === 'IN' ? <IndianRupee size={14} /> : <DollarSign size={14} />}
            <span>{market === 'IN' ? 'NSE' : 'NASDAQ'}</span>
          </div>
          <h2 className="text-3xl font-bold text-white">{symbol.split('.')[0]}</h2>
          <span className="text-sm text-white/60">{stockInfo.name}</span>
        </div>
        <div className="text-right">
          <span className="block text-4xl font-bold text-white">{formatCurrency(currentPrice, market)}</span>
          <span className={`inline-flex items-center gap-1 text-sm font-medium ${priceChange >= 0 ? 'text-green-500' : 'text-red-500'}`}>
            {priceChange >= 0 ? <TrendingUp size={16} /> : <TrendingDown size={16} />}
            {priceChange >= 0 ? '+' : ''}{formatCurrency(Math.abs(priceChange), market)} ({priceChangePercent.toFixed(2)}%)
          </span>
        </div>
      </div>

      <div className="flex items-center justify-between">
        <div className="flex gap-2">
          <button 
            className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${chartType === 'candle' ? 'bg-orange-500 text-white' : 'bg-white/5 text-white/60 hover:text-white'}`}
            onClick={() => setChartType('candle')}
          >
            Candlestick
          </button>
          <button 
            className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${chartType === 'line' ? 'bg-orange-500 text-white' : 'bg-white/5 text-white/60 hover:text-white'}`}
            onClick={() => setChartType('line')}
          >
            Line
          </button>
        </div>
        <div className="flex gap-2">
          {['1M', '3M', '6M', '1Y'].map((tf) => (
            <button 
              key={tf} 
              className={`px-3 py-1.5 rounded-lg text-sm font-medium transition-colors ${timeframe === tf ? 'bg-orange-500 text-white' : 'bg-white/5 text-white/60 hover:text-white'}`}
              onClick={() => setTimeframe(tf)}
            >
              {tf}
            </button>
          ))}
        </div>
      </div>

      <div className="bg-white/5 border border-white/10 rounded-xl p-4">
        <div ref={chartRef} className="w-full h-[400px]"></div>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4">
        {indicators.map((ind, i) => (
          <div key={i} className="p-4 bg-white/5 border border-white/10 rounded-lg space-y-1">
            <span className="text-xs text-white/40">{ind.name}</span>
            <div className="text-lg font-bold text-white">{ind.value}</div>
            <span className={`text-xs font-medium capitalize ${
              ind.status === 'bullish' ? 'text-green-500' : 
              ind.status === 'bearish' ? 'text-red-500' : 
              ind.status === 'overbought' ? 'text-orange-500' : 
              ind.status === 'oversold' ? 'text-blue-500' : 
              'text-white/60'
            }`}>{ind.status}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
