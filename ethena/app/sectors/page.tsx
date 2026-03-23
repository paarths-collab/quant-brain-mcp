'use client';

import { useState, useEffect, useRef } from 'react';
import * as d3 from 'd3';
import { treemapAPI, formatLargeNumber } from '@/lib/api';

const colorScale = d3.scaleLinear<string>()
  .domain([-5, -2, 0, 2, 5])
  .range(['rgba(255, 255, 255, 0.1)', 'rgba(255, 255, 255, 0.05)', '#111111', 'rgba(99, 102, 241, 0.4)', 'rgba(99, 102, 241, 0.9)']);

const CARD = "relative rounded-2xl border border-white/[0.07] bg-white/[0.03] backdrop-blur-xl overflow-hidden";
const CONTROL_BTN = "px-4 py-2 rounded-lg text-[12px] font-dm-mono uppercase tracking-widest transition-all duration-300 border border-white/[0.08]";

export default function SectorsPage() {
  const [market, setMarket] = useState('india');
  const [selectedIndex, setSelectedIndex] = useState<string | null>(null);
  const [hoveredItem, setHoveredItem] = useState<any>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [indicesData, setIndicesData] = useState<any[]>([]);
  const [stocksData, setStocksData] = useState<any>(null);
  const treemapRef = useRef<HTMLDivElement>(null);

  const currencySymbol = market === 'india' ? '₹' : '$';
  const marketCode = market === 'india' ? 'IN' : 'US';

  useEffect(() => {
    setIsLoading(true);
    setSelectedIndex(null);
    setStocksData(null);
    treemapAPI.getIndicesLive(market)
      .then(res => setIndicesData(res.indices || []))
      .catch(err => console.error(err))
      .finally(() => setIsLoading(false));
  }, [market]);

  useEffect(() => {
    if (!selectedIndex) { setStocksData(null); return; }
    setIsLoading(true);
    treemapAPI.getIndexStocks(selectedIndex, market)
      .then(res => setStocksData(res))
      .catch(err => console.error(err))
      .finally(() => setIsLoading(false));
  }, [selectedIndex, market]);

  useEffect(() => {
    if (!treemapRef.current) return;
    const container = treemapRef.current;

    const observer = new ResizeObserver(() => {
      renderTreemap();
    });
    observer.observe(container);

    return () => {
      observer.disconnect();
    };
  }, [indicesData, stocksData, market]);

  const renderTreemap = () => {
    if (!treemapRef.current) return;
    const container = treemapRef.current;
    
    // Ensure the container is large enough to show names
    const itemCount = stocksData?.stocks?.length || indicesData.length;
    // Hybrid logic: calculate a required height to make each box "big"
    // For 50 stocks, we want roughly 1200-1500px height.
    const minCalculatedHeight = Math.max(800, Math.ceil(itemCount / 3) * 120);
    const width = container.clientWidth;
    const height = minCalculatedHeight; // Allow vertical growth

    d3.select(container).selectAll('*').remove();

    let treeData: any;
    
    if (stocksData?.stocks) {
      treeData = {
        name: stocksData.index?.name || 'Index',
        children: stocksData.stocks.map((s: any) => ({
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
        children: indicesData.map((idx: any) => ({
          name: idx.name, 
          id: idx.id, 
          value: idx.constituents_count || 30, // Indices are usually bigger
          change: idx.change_percent || 0, 
          price: idx.price
        }))
      };
    } else return;
    
    const root = d3.hierarchy(treeData)
      .sum((d: any) => d.value || 1)
      .sort((a: any, b: any) => (b.value || 0) - (a.value || 0));
    
    d3.treemap()
      .size([width, height])
      .paddingInner(0)
      .paddingOuter(0)
      .round(false)
      .tile(d3.treemapSquarify)(root);
    
    const svg = d3.select(container).append('svg')
      .attr('width', width)
      .attr('height', height)
      .attr('viewBox', `0 0 ${width} ${height}`)
      .style('display', 'block')
      .style('width', '100%')
      .style('height', `${height}px`) // Fixed height for scrolling
      .style('overflow', 'visible');

    const cells = svg.selectAll('g')
      .data(root.leaves())
      .join('g')
      .attr('transform', (d: any) => `translate(${d.x0},${d.y0})`)
      .style('cursor', 'pointer');
    
    // Background Rect with Ethena Glow
    cells.append('rect')
      .attr('width', (d: any) => Math.max(0, d.x1 - d.x0))
      .attr('height', (d: any) => Math.max(0, d.y1 - d.y0))
      .attr('fill', (d: any) => colorScale(d.data.change || 0))
      .attr('stroke', 'rgba(255,255,255,0.03)')
      .attr('stroke-width', 1)
      .on('mouseenter', function(event, d: any) {
        d3.select(this)
          .transition()
          .duration(300)
          .attr('fill', (d: any) => (d.data.change || 0) >= 0 ? 'rgba(99, 102, 241, 0.95)' : 'rgba(255, 255, 255, 0.25)')
          .attr('stroke', 'rgba(255,255,255,0.4)');
        setHoveredItem(d.data);
      })
      .on('mouseleave', function() {
        d3.select(this)
          .transition()
          .duration(300)
          .attr('fill', (d: any) => colorScale(d.data.change || 0))
          .attr('stroke', 'rgba(255,255,255,0.03)');
        setHoveredItem(null);
      })
      .on('click', (event, d: any) => {
        event.stopPropagation();
        if (!selectedIndex && d.data.id) setSelectedIndex(d.data.id);
      });
    
    // Stock/Index Name
    cells.append('text')
      .attr('x', 14)
      .attr('y', 28)
      .attr('fill', 'white')
      .attr('font-size', '13px')
      .attr('font-family', 'var(--font-inter), sans-serif')
      .attr('font-weight', '700')
      .attr('letter-spacing', '0.02em')
      .text((d: any) => (d.x1 - d.x0 < 60 ? '' : d.data.name?.toUpperCase() || ''));
    
    // Symbol or Type
    cells.append('text')
      .attr('x', 14)
      .attr('y', 46)
      .attr('fill', 'rgba(255,255,255,0.4)')
      .attr('font-size', '10px')
      .attr('font-family', 'var(--font-dm-mono), monospace')
      .attr('font-weight', '500')
      .attr('letter-spacing', '0.1em')
      .text((d: any) => (d.x1 - d.x0 < 60 ? '' : d.data.symbol || (d.data.id?.toUpperCase().replace('_', ' ')) || ''));

    // Change Percent (Large)
    cells.append('text')
      .attr('x', 14)
      .attr('y', (d: any) => (d.y1 - d.y0) - 20)
      .attr('fill', (d: any) => (d.data.change || 0) >= 0 ? '#818cf8' : 'white')
      .attr('font-size', '18px')
      .attr('font-family', 'var(--font-dm-mono), monospace')
      .attr('font-weight', '700')
      .text((d: any) => {
        if (d.x1 - d.x0 < 50 || d.y1 - d.y0 < 60) return '';
        const c = d.data.change || 0;
        return `${c >= 0 ? '↑' : '↓'}${(Math.abs(c)).toFixed(2)}%`;
      });
  };

  return (
    <div className="flex flex-col h-[calc(100vh-100px)] space-y-6">
      {/* Header Controls */}
      <div className="flex items-center justify-between shrink-0">
        <div className="flex items-center gap-6">
          <div className="flex items-center gap-2">
             <button 
              onClick={() => setMarket('india')} 
              className={`${CONTROL_BTN} ${market === 'india' ? 'bg-indigo-500/10 text-indigo-400 border-indigo-500/30' : 'bg-white/[0.03] text-white/30 hover:bg-white/[0.06]'}`}
            >
              India
            </button>
            <button 
              onClick={() => setMarket('us')}
              className={`${CONTROL_BTN} ${market === 'us' ? 'bg-indigo-500/10 text-indigo-400 border-indigo-500/30' : 'bg-white/[0.03] text-white/30 hover:bg-white/[0.06]'}`}
            >
              US Market
            </button>
          </div>
          
          {selectedIndex && (
            <button 
              onClick={() => setSelectedIndex(null)} 
              className="font-dm-mono text-[10px] text-indigo-400/60 uppercase tracking-[0.2em] hover:text-indigo-400 transition-colors"
            >
              [ BACK_TO_INDICES ]
            </button>
          )}
        </div>

        <div className="flex items-center gap-4 px-5 py-2.5 rounded-lg bg-white/[0.03] border border-indigo-500/20">
          <span className="font-dm-mono text-[10px] text-indigo-400/40 uppercase tracking-widest">High Resolution Stream</span>
          <div className="w-1.5 h-1.5 rounded-full bg-indigo-500 animate-ping shadow-[0_0_12px_rgba(99,102,241,0.8)]" />
        </div>
      </div>

      {/* Main Treemap Area - With Scroll */}
      <div className={`${CARD} flex-1 relative min-h-0 overflow-y-auto custom-scrollbar`}>
        <div className="sticky top-0 left-0 p-6 z-10 pointer-events-none">
          <div className="inline-flex items-center gap-3 px-4 py-2 rounded-full bg-black/60 backdrop-blur-md border border-white/5">
            <span className="font-dm-mono text-[11px] text-white/50 uppercase tracking-[0.2em] font-medium">
              {selectedIndex ? stocksData?.index?.name : 'Institutional Heatmap'}
            </span>
            <div className="w-1 h-3 bg-indigo-500/30 rounded-full" />
            <span className="font-dm-mono text-[10px] text-indigo-400/60 uppercase tracking-widest">
              {stocksData?.stocks?.length || indicesData.length} Elements
            </span>
          </div>
        </div>
        
        <div ref={treemapRef} className="w-full" />

        {/* Floating Tooltip */}
        {hoveredItem && (
          <div className="fixed bottom-32 right-12 p-5 rounded-2xl bg-black/90 backdrop-blur-3xl border border-indigo-500/30 z-50 min-w-[220px] shadow-[0_20px_50px_rgba(0,0,0,0.5)] animate-in fade-in slide-in-from-bottom-2 duration-300">
            <div className="font-dm-mono text-[10px] text-indigo-400/40 uppercase tracking-widest mb-3">Live_Entity_Oracle</div>
            <h3 className="font-inter text-lg font-bold text-white mb-1">{hoveredItem.name}</h3>
            <div className="font-dm-mono text-[11px] text-white/30 uppercase tracking-[0.2em] mb-4">{hoveredItem.symbol || hoveredItem.id}</div>
            <div className="space-y-2 pt-4 border-t border-white/5">
              {hoveredItem.price && (
                <div className="flex justify-between items-center">
                  <span className="text-white/20 font-dm-mono text-[10px] uppercase">Market_Price</span>
                  <span className="text-white font-dm-mono text-[14px]">{currencySymbol}{hoveredItem.price?.toLocaleString()}</span>
                </div>
              )}
              <div className="flex justify-between items-center">
                <span className="text-white/20 font-dm-mono text-[10px] uppercase">Performance</span>
                <span className={`font-dm-mono text-[14px] ${(hoveredItem.change || 0) >= 0 ? 'text-indigo-400 font-bold' : 'text-white/60'}`}>
                  {(hoveredItem.change || 0) >= 0 ? '+' : ''}{(hoveredItem.change || 0).toFixed(2)}%
                </span>
              </div>
            </div>
          </div>
        )}
      </div>

      <style jsx global>{`
        .custom-scrollbar::-webkit-scrollbar {
          width: 2px;
        }
        .custom-scrollbar::-webkit-scrollbar-track {
          background: rgba(255, 255, 255, 0.01);
        }
        .custom-scrollbar::-webkit-scrollbar-thumb {
          background: rgba(99, 102, 241, 0.2);
          border-radius: 10px;
        }
        .custom-scrollbar::-webkit-scrollbar-thumb:hover {
          background: rgba(99, 102, 241, 0.5);
        }
      `}</style>
    </div>
  );
}
