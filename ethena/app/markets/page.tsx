'use client';

import { useState } from 'react';
import { AreaChart, Area, ResponsiveContainer } from 'recharts';

// --- Constants & Styles ---
const BLUE_ACCENT = '#4f46e5';
const CARD_GLOW = "group relative p-6 rounded-2xl border border-white/[0.07] bg-white/[0.03] backdrop-blur-xl shadow-[0_0_24px_rgba(79,70,229,0.04)] hover:shadow-[0_0_32px_rgba(79,70,229,0.1)] hover:border-indigo-500/20 hover:bg-white/[0.05] transition-all duration-500 overflow-hidden";

// --- Mock Data Generator ---
function makeSpark(n = 20, up = true) {
  const arr = [];
  let v = 100;
  for (let i = 0; i < n; i++) {
    v += (Math.random() - (up ? 0.4 : 0.6)) * 4;
    arr.push({ v: Math.max(70, v) });
  }
  return arr;
}

// --- Components ---
function MarketSpark({ data, color, id }: { data: { v: number }[]; color: string; id: string }) {
  return (
    <div className="h-10 mt-4" style={{ filter: `drop-shadow(0 0 4px ${color}40)` }}>
      <ResponsiveContainer width="100%" height="100%">
        <AreaChart data={data} margin={{ top: 0, right: 0, bottom: 0, left: 0 }}>
          <defs>
            <linearGradient id={`spark-${id}`} x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor={color} stopOpacity={0.15} />
              <stop offset="100%" stopColor={color} stopOpacity={0} />
            </linearGradient>
          </defs>
          <Area 
            type="monotone" 
            dataKey="v" 
            stroke={color} 
            strokeWidth={1.5} 
            fill={`url(#spark-${id})`} 
            dot={false} 
            isAnimationActive={true}
          />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
}

function MarketCard({ item, symbol }: { item: any; symbol: string }) {
  const isUp = (item.change_percent || 0) >= 0;
  const sparkData = makeSpark(24, isUp);

  return (
    <div className={CARD_GLOW}>
      <div className="flex items-start justify-between mb-4">
        <div className="min-w-0 flex-1">
          <div className="font-dm-mono text-[10px] tracking-[0.3em] text-white/50 uppercase mb-0.5 truncate">{item.id}</div>
          <div className="font-inter text-[13px] text-white/70 font-light truncate">{item.name}</div>
        </div>
        <div className={`shrink-0 font-dm-mono text-[10px] font-bold px-2 py-1 rounded border ${isUp ? 'border-indigo-500/20 bg-indigo-500/5 text-indigo-400' : 'border-white/5 bg-white/2 text-white/25'}`}>
          {isUp ? '+' : ''}{item.change_percent.toFixed(2)}%
        </div>
      </div>

      <div className="font-dm-mono text-[26px] font-medium text-white tabular-nums tracking-tight leading-none mb-4">
        {symbol}{item.price?.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
      </div>

      <MarketSpark data={sparkData} color={isUp ? BLUE_ACCENT : 'rgba(255,255,255,0.2)'} id={item.id} />
    </div>
  );
}

function MarketSection({ title, items, symbol }: { title: string; items: any[]; symbol: string }) {
    return (
        <section className="space-y-5">
            <div className="flex items-center gap-3">
                <div className="w-1.5 h-1.5 rounded-full bg-indigo-500 shadow-[0_0_8px_rgba(99,102,241,0.6)]" />
                <span className="font-dm-mono text-[11px] text-white/60 uppercase tracking-[0.4em] font-medium">{title}</span>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-5">
                {items.map(item => <MarketCard key={item.id} item={item} symbol={symbol} />)}
            </div>
        </section>
    );
}

export default function MarketsPage() {
  const [refreshing, setRefreshing] = useState(false);

  const doRefresh = async () => {
    setRefreshing(true);
    await new Promise(r => setTimeout(r, 600));
    setRefreshing(false);
  };

  // --- Unified Market Data ---
  const GLOBAL_INDICES = [
    { name: 'S&P 500', id: 'SPX', change_percent: 0.82, price: 5842.47, sym: '$' },
    { name: 'NASDAQ 100', id: 'NDX', change_percent: 1.14, price: 20378.92, sym: '$' },
    { name: 'NIFTY 50', id: 'NIFTY', change_percent: 0.50, price: 22402.40, sym: '₹' },
    { name: 'DOW JONES', id: 'DJI', change_percent: -0.12, price: 43192.05, sym: '$' },
    { name: 'SENSEX', id: 'BSESN', change_percent: -0.13, price: 73877.30, sym: '₹' },
    { name: 'FTSE 100', id: 'UK100', change_percent: 0.24, price: 8245.10, sym: '£' },
    { name: 'DAX 40', id: 'GER40', change_percent: -0.62, price: 18142.40, sym: '€' },
    { name: 'NIKKEI 225', id: 'JPN225', change_percent: 1.72, price: 40142.60, sym: '¥' },
    { name: 'HANG SENG', id: 'HKG33', change_percent: -0.84, price: 16842.15, sym: '$' },
    { name: 'EURO STOXX 50', id: 'ESTX50', change_percent: 0.35, price: 4942.30, sym: '€' },
    { name: 'CAC 40', id: 'FRA40', change_percent: 0.28, price: 8142.60, sym: '€' },
    { name: 'ASX 200', id: 'AUS200', change_percent: 0.65, price: 7842.10, sym: '$' },
  ];

  const COMMODITIES = [
    { name: 'Gold Spot', id: 'GOLD', change_percent: 0.54, price: 2242.10, sym: '$' },
    { name: 'WTI Crude', id: 'WTI', change_percent: 1.21, price: 81.42, sym: '$' },
    { name: 'Brent Crude', id: 'BRENT', change_percent: 1.15, price: 86.50, sym: '$' },
    { name: 'Silver Spot', id: 'SILVER', change_percent: -0.84, price: 25.14, sym: '$' },
    { name: 'Copper Spot', id: 'HG', change_percent: 0.32, price: 9842.05, sym: '$' },
    { name: 'Natural Gas', id: 'NG', change_percent: -2.45, price: 1.842, sym: '$' },
    { name: 'Platinum', id: 'XPT', change_percent: 0.12, price: 942.30, sym: '$' },
    { name: 'Palladium', id: 'XPD', change_percent: -0.92, price: 1042.15, sym: '$' },
  ];

  const FX_PAIRS = [
    { name: 'EUR / USD', id: 'EURUSD', change_percent: 0.12, price: 1.0842, sym: '' },
    { name: 'USD / JPY', id: 'USDJPY', change_percent: -0.21, price: 149.85, sym: '' },
    { name: 'GBP / USD', id: 'GBPUSD', change_percent: 0.08, price: 1.2741, sym: '' },
    { name: 'USD / INR', id: 'USDINR', change_percent: 0.05, price: 83.472, sym: '' },
    { name: 'AUD / USD', id: 'AUDUSD', change_percent: 0.18, price: 0.6542, sym: '' },
    { name: 'USD / CAD', id: 'USDCAD', change_percent: -0.11, price: 1.3541, sym: '' },
    { name: 'USD / CHF', id: 'USDCHF', change_percent: -0.05, price: 0.8842, sym: '' },
    { name: 'NZD / USD', id: 'NZDUSD', change_percent: 0.14, price: 0.6042, sym: '' },
  ];

  const MACRO_RATES = [
    { name: 'US 10Y Yield', id: 'US10Y', change_percent: 1.05, price: 4.24, sym: '%' },
    { name: 'VIX Index', id: 'VIX', change_percent: -4.78, price: 16.31, sym: '' },
    { name: 'MOVE Index', id: 'MOVE', change_percent: -0.74, price: 110.25, sym: '' },
    { name: 'DXY Index', id: 'DXY', change_percent: 0.14, price: 104.12, sym: '' },
  ];

  return (
    <div className="space-y-10 pb-20">
      {/* Universal Header */}
      <header className="flex items-center justify-between sticky top-0 z-20 bg-black/60 backdrop-blur-xl py-4 border-b border-white/5">
        <div className="flex items-center gap-4">
          <span className="inline-flex items-center gap-2 px-2.5 py-1 text-[9px] border border-indigo-500/20 rounded-full text-indigo-400/80 bg-indigo-500/5">
            <span className="w-1 h-1 rounded-full bg-indigo-400 animate-pulse" />
            GLOBAL_MARKETS_SYNC
          </span>
        </div>

        <button 
          onClick={doRefresh}
          className="px-6 py-2 rounded-xl bg-indigo-500/10 backdrop-blur-xl border border-indigo-500/30 text-indigo-400/90 hover:bg-indigo-500/20 hover:border-indigo-500/50 hover:text-indigo-400 transition-all duration-300 font-dm-mono text-[10px] uppercase tracking-widest shadow-[0_0_15px_rgba(99,102,241,0.05)] hover:shadow-[0_0_20px_rgba(99,102,241,0.15)]"
        >
          {refreshing ? 'SYNCHRONIZING...' : 'FETCH_LATEST'}
        </button>
      </header>

      {/* Single Page Sections */}
      <div className="space-y-16">
        <MarketSection title="Global Indices" items={GLOBAL_INDICES} symbol="" />
        <MarketSection title="Commodity Desk" items={COMMODITIES} symbol="$" />
        <MarketSection title="FX Oracle" items={FX_PAIRS} symbol="" />
        <MarketSection title="Macro & Volatility" items={MACRO_RATES} symbol="" />
      </div>

      <style jsx global>{`
        .custom-scrollbar::-webkit-scrollbar { width: 3px; }
        .custom-scrollbar::-webkit-scrollbar-track { background: transparent; }
        .custom-scrollbar::-webkit-scrollbar-thumb { background: rgba(99, 102, 241, 0.1); border-radius: 10px; }
      `}</style>
    </div>
  );
}
