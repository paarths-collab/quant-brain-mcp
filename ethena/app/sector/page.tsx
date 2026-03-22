// Sector page for Ethena, refactored to match the dashboard theme and logic from frontend-k2 Sectors page.
// This is a Next.js 14 app directory page component.

'use client';
import { useState, useEffect, useRef } from 'react';
import { IndianRupee, DollarSign } from 'lucide-react';
import * as d3 from 'd3';
// import { treemapAPI, getCurrencySymbol, formatLargeNumber } from '@/api';

const colorScale = d3.scaleLinear()
  .domain([-5, -2, 0, 2, 5])
  .range(['#dc2626', '#ef4444', '#3f3f46', '#22c55e', '#16a34a']);

export default function SectorPage() {
  const [market, setMarket] = useState('india');
  const [selectedIndex, setSelectedIndex] = useState(null);
  const [hoveredItem, setHoveredItem] = useState(null);
  const [isLoading, setIsLoading] = useState(false);
  const [indicesData, setIndicesData] = useState([]);
  const [stocksData, setStocksData] = useState(null);
  const [selectedStock, setSelectedStock] = useState(null);
  const [stockDetails, setStockDetails] = useState(null);
  const [loadingDetails, setLoadingDetails] = useState(false);
  const treemapRef = useRef(null);
  const currencySymbol = market === 'india' ? '\u20b9' : '$';

  // TODO: Replace with real API calls
  useEffect(() => {
    setIsLoading(true);
    setTimeout(() => {
      setIndicesData([
        { name: 'NIFTY 50', id: 'NIFTY50', change_percent: 1.2, price: 22000, constituents_count: 50 },
        { name: 'NIFTY BANK', id: 'NIFTYBANK', change_percent: -0.8, price: 48000, constituents_count: 12 },
      ]);
      setIsLoading(false);
    }, 800);
  }, [market]);

  useEffect(() => {
    if (!selectedIndex) return;
    setIsLoading(true);
    setTimeout(() => {
      setStocksData({
        index: { name: 'NIFTY 50' },
        stocks: [
          { name: 'RELIANCE', symbol: 'RELIANCE.NS', market_cap: 100, change_percent: 1.5, price: 3000 },
          { name: 'TCS', symbol: 'TCS.NS', market_cap: 80, change_percent: -0.5, price: 4000 },
        ]
      });
      setIsLoading(false);
    }, 800);
  }, [selectedIndex, market]);

  // D3 Treemap rendering logic (simplified)
  useEffect(() => {
    if (!treemapRef.current) return;
    const container = treemapRef.current;
    d3.select(container).selectAll('*').remove();
    const width = 800;
    const height = 400;
    let treeData;
    if (stocksData?.stocks) {
      treeData = {
        name: stocksData.index?.name || 'Index',
        children: stocksData.stocks.map(s => ({
          name: s.name,
          symbol: s.symbol,
          value: s.market_cap || 100,
          change: s.change_percent || 0,
          price: s.price
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
          price: idx.price
        }))
      };
    } else return;
    const root = d3.hierarchy(treeData)
      .sum(d => d.value || 1)
      .sort((a, b) => (b.value || 0) - (a.value || 0));
    d3.treemap()
      .size([width, height])
      .paddingInner(1)
      .paddingOuter(0)
      .round(true)
      .tile(d3.treemapSquarify)(root);
    const svg = d3.select(container).append('svg').attr('width', width).attr('height', height);
    const cells = svg.selectAll('g').data(root.leaves()).join('g')
      .attr('transform', d => `translate(${d.x0},${d.y0})`)
      .style('cursor', 'pointer');
    cells.append('rect')
      .attr('width', d => Math.max(0, d.x1 - d.x0))
      .attr('height', d => Math.max(0, d.y1 - d.y0))
      .attr('fill', d => colorScale(d.data.change || 0))
      .attr('rx', 0)
      .attr('stroke', 'rgba(0,0,0,0.4)')
      .attr('stroke-width', 1)
      .on('mouseenter', function(event, d) {
        d3.select(this).attr('stroke', '#FF9500').attr('stroke-width', 3);
        setHoveredItem(d.data);
      })
      .on('mouseleave', function() {
        d3.select(this).attr('stroke', 'rgba(0,0,0,0.4)').attr('stroke-width', 1);
        setHoveredItem(null);
      })
      .on('click', (event, d) => {
        event.stopPropagation();
        if (!selectedIndex && d.data.id) setSelectedIndex(d.data.id);
        else if (selectedIndex && d.data.symbol) setSelectedStock(d.data);
      });
    cells.append('text').attr('x', 10).attr('y', 24).attr('fill', '#fff')
      .attr('font-size', d => d.x1 - d.x0 > 160 ? '14px' : d.x1 - d.x0 > 120 ? '12px' : '10px')
      .attr('font-weight', '700')
      .text(d => d.x1 - d.x0 < 40 ? '' : d.data.name?.slice(0, Math.floor((d.x1 - d.x0) / 8)) || '');
    cells.append('text').attr('x', 10).attr('y', 60)
      .attr('fill', d => (d.data.change || 0) >= 0 ? '#22c55e' : '#ef4444')
      .attr('font-size', '12px').attr('font-weight', '700')
      .text(d => {
        if (d.x1 - d.x0 < 60 || d.y1 - d.y0 < 70) return '';
        const c = d.data.change || 0;
        return `${c >= 0 ? '+' : ''}${c.toFixed(2)}%`;
      });
  }, [indicesData, stocksData, market]);

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="font-display text-3xl font-bold text-white">
            {selectedIndex ? stocksData?.index?.name || 'Index' : 'Market Indices'}
          </h1>
          <p className="text-white/60">
            {selectedIndex ? `${stocksData?.stocks?.length || 0} stocks` : 'Click on an index'}
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
      <div ref={treemapRef} className="rounded-2xl bg-[#18181b] p-2 min-h-[500px] w-full shadow-lg" style={{ minHeight: 500 }} />
    </div>
  );
}
