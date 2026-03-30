'use client';

import { useEffect, useState, useCallback } from 'react';
import { AreaChart, Area, ResponsiveContainer } from 'recharts';
import { marketAPI, fredAPI } from '@/lib/api';

// --- Constants & Styles ---
const BLUE_ACCENT = '#4f46e5';
const CARD_GLOW = "group relative rounded-2xl border border-white/[0.07] bg-white/[0.03] backdrop-blur-xl shadow-[0_0_24px_rgba(79,70,229,0.04)] hover:shadow-[0_0_32px_rgba(79,70,229,0.12)] hover:border-indigo-500/20 hover:bg-white/[0.05] transition-all duration-500 overflow-hidden hover:-translate-y-1";
const CACHE_KEY = 'bloomberg_market_data_v1';
const CACHE_TTL = 4 * 60 * 60 * 1000; // 4 hours

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
function MarketSpark({ data, color, id, height = 40 }: { data: { v: number }[]; color: string; id: string; height?: number }) {
  return (
    <div className="mt-4" style={{ height, filter: `drop-shadow(0 0 6px ${color}55)` }}>
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
            strokeWidth={2} 
            fill={`url(#spark-${id})`} 
            dot={false} 
            isAnimationActive={true}
          />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
}

function MarketCard({ item, symbol, size = 'md' }: { item: any; symbol: string; size?: 'md' | 'lg' }) {
  const isUp = (item.change_percent || 0) >= 0;
  const sparkData = makeSpark(24, isUp);
  const isLarge = size === 'lg';

  return (
    <div className={`${CARD_GLOW} ${isLarge ? 'p-7' : 'p-6'}`}>
      <div className="flex items-start justify-between gap-4">
        <div className="min-w-0 flex-1">
          <div className="heading-text text-[14px] text-white/80 truncate">
            {item.name}
          </div>
        </div>
        <div className={`shrink-0 data-text text-[10px] font-semibold px-2.5 py-1 rounded border ${isUp ? 'border-indigo-500/20 bg-indigo-500/5 text-indigo-300' : 'border-white/5 bg-white/2 text-white/25'}`}>
          {isUp ? '+' : ''}{item.change_percent?.toFixed(2)}%
        </div>
      </div>

      <div className={`metric-text glow-text text-white tabular-nums tracking-tight leading-none ${isLarge ? 'text-[30px] mt-4' : 'text-[26px] mt-3'}`}>
        {symbol}{item.price?.toLocaleString(undefined, { minimumFractionDigits: item.price < 10 ? 4 : 2, maximumFractionDigits: item.price < 10 ? 4 : 2 })}
      </div>

      <div className="flex items-center justify-between mt-2">
        <span className="data-text text-[10px] text-white/45 uppercase tracking-[0.28em]">{item.id}</span>
      </div>

      <MarketSpark data={sparkData} color={isUp ? BLUE_ACCENT : 'rgba(255,255,255,0.25)'} id={item.id} height={isLarge ? 56 : 40} />
    </div>
  );
}

function MarketSection({ title, items, symbol }: { title: string; items: any[]; symbol: string }) {
    if (!items || items.length === 0) return null;
    return (
        <section className="space-y-5">
            <div className="flex items-center gap-3">
                <div className="w-1.5 h-1.5 rounded-full bg-indigo-500 shadow-[0_0_8px_rgba(99,102,241,0.6)]" />
                <span className="data-text text-[10px] text-white/60 uppercase tracking-[0.35em] font-medium">{title}</span>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-5">
                {items.map(item => <MarketCard key={item.id} item={item} symbol={item.sym || symbol} />)}
            </div>
        </section>
    );
}

export default function MarketsPage() {
  const [refreshing, setRefreshing] = useState(false);
  const [data, setData] = useState<{
    globalIndices: any[];
    commodities: any[];
    fxPairs: any[];
    macroRates: any[];
  }>({
    globalIndices: [],
    commodities: [],
    fxPairs: [],
    macroRates: []
  });

  const loadFromCache = useCallback(() => {
    try {
      const cached = localStorage.getItem(CACHE_KEY);
      if (cached) {
        const { payload, timestamp } = JSON.parse(cached);
        if (Date.now() - timestamp < CACHE_TTL) {
          setData(payload);
          return true;
        }
      }
    } catch (e) {
      console.error('Failed to load cache:', e);
    }
    return false;
  }, []);

  const saveToCache = (payload: any) => {
    try {
      localStorage.setItem(CACHE_KEY, JSON.stringify({
        payload,
        timestamp: Date.now()
      }));
    } catch (e) {
      console.error('Failed to save cache:', e);
    }
  };

  const fetchAllData = async (force = false) => {
    try {
      const fredSeries = [
        'SP500', 'DJIA', 'NASDAQ100', 
        'DCOILWTICO', 'DCOILBRENTEU', 'NASDAQQSLVO',
        'DEXUSEU', 'DEXJPUS', 'DEXUSUK',
        'DGS10', 'VIXCLS', 'DTWEXBGS'
      ];

      // 1. Fetch FRED Data
      const fredResponse: any = force 
        ? await fredAPI.getLatestLive(fredSeries)
        : await fredAPI.getLatestCached(fredSeries);
      
      const fredData = fredResponse?.data || {};

      // 2. Fetch yfinance Data (Indices + Gold)
      const overviewRes: any = await marketAPI.getOverview();
      const overviewIndices = overviewRes?.indices || {};

      // 3. Mapping Logic
      const newGlobalIndices = [
        { name: 'S&P 500', id: 'SPX', change_percent: fredData.SP500?.change_pct || 0, price: fredData.SP500?.value || 0, sym: '$' },
        { name: 'NASDAQ 100', id: 'NDX', change_percent: fredData.NASDAQ100?.change_pct || 0, price: fredData.NASDAQ100?.value || 0, sym: '$' },
        { name: 'NIFTY 50', id: 'NIFTY', change_percent: overviewIndices['^NSEI']?.change_pct || 0.50, price: overviewIndices['^NSEI']?.price || 22402.40, sym: '₹' },
        { name: 'DOW JONES', id: 'DJI', change_percent: fredData.DJIA?.change_pct || 0, price: fredData.DJIA?.value || 0, sym: '$' },
        { name: 'SENSEX', id: 'BSESN', change_percent: overviewIndices['^BSESN']?.change_pct || -0.13, price: overviewIndices['^BSESN']?.price || 73877.30, sym: '₹' },
      ].filter(x => x.price > 0);

      const newCommodities = [
        { name: 'Gold Spot', id: 'GOLD', change_percent: overviewIndices['GC=F']?.change_pct || (fredData.GOLDAMGBD228NLBM?.change_pct || 0.54), price: overviewIndices['GC=F']?.price || (fredData.GOLDAMGBD228NLBM?.value || 2242.10), sym: '$' },
        { name: 'WTI Crude', id: 'WTI', change_percent: fredData.DCOILWTICO?.change_pct || 0, price: fredData.DCOILWTICO?.value || 0, sym: '$' },
        { name: 'Brent Crude', id: 'BRENT', change_percent: fredData.DCOILBRENTEU?.change_pct || 0, price: fredData.DCOILBRENTEU?.value || 0, sym: '$' },
        { name: 'Silver Spot', id: 'SILVER', change_percent: fredData.NASDAQQSLVO?.change_pct || 0, price: fredData.NASDAQQSLVO?.value || 0, sym: '$' },
      ].filter(x => x.price > 0);

      const newFxPairs = [
        { name: 'EUR / USD', id: 'EURUSD', change_percent: fredData.DEXUSEU?.change_pct || 0, price: fredData.DEXUSEU?.value || 0, sym: '' },
        { name: 'USD / JPY', id: 'USDJPY', change_percent: (fredData.DEXJPUS?.change_pct || 0) * -1, price: fredData.DEXJPUS?.value || 0, sym: '' },
        { name: 'GBP / USD', id: 'GBPUSD', change_percent: fredData.DEXUSUK?.change_pct || 0, price: fredData.DEXUSUK?.value || 0, sym: '' },
      ].filter(x => x.price > 0);

      const newMacroRates = [
        { name: 'US 10Y Yield', id: 'US10Y', change_percent: fredData.DGS10?.change_pct || 0, price: fredData.DGS10?.value || 0, sym: '%' },
        { name: 'VIX Index', id: 'VIX', change_percent: fredData.VIXCLS?.change_pct || 0, price: fredData.VIXCLS?.value || 16.31, sym: '' },
        { name: 'DXY Index', id: 'DXY', change_percent: fredData.DTWEXBGS?.change_pct || 0, price: fredData.DTWEXBGS?.value || 104.12, sym: '' },
      ].filter(x => x.price > 0);

      const payload = {
        globalIndices: newGlobalIndices.length > 0 ? newGlobalIndices : STATIC_GLOBAL_INDICES,
        commodities: newCommodities.length > 0 ? newCommodities : STATIC_COMMODITIES,
        fxPairs: newFxPairs.length > 0 ? newFxPairs : STATIC_FX_PAIRS,
        macroRates: newMacroRates.length > 0 ? newMacroRates : STATIC_MACRO_RATES
      };

      setData(payload);
      saveToCache(payload);
    } catch (err) {
      console.error('Fetch error:', err);
    }
  };

  const doRefresh = async () => {
    setRefreshing(true);
    await fetchAllData(true);
    await new Promise(r => setTimeout(r, 600));
    setRefreshing(false);
  };

  useEffect(() => {
    const hasCache = loadFromCache();
    if (!hasCache) {
      void fetchAllData();
    }
  }, [loadFromCache]);

  // --- Fallback Data (moved to internal constants for safety) ---
  const STATIC_GLOBAL_INDICES = [
    { name: 'S&P 500', id: 'SPX', change_percent: 0.82, price: 5842.47, sym: '$' },
    { name: 'NASDAQ 100', id: 'NDX', change_percent: 1.14, price: 20378.92, sym: '$' },
    { name: 'NIFTY 50', id: 'NIFTY', change_percent: 0.50, price: 22402.40, sym: '₹' },
    { name: 'DOW JONES', id: 'DJI', change_percent: -0.12, price: 43192.05, sym: '$' },
    { name: 'SENSEX', id: 'BSESN', change_percent: -0.13, price: 73877.30, sym: '₹' },
  ];

  const STATIC_COMMODITIES = [
    { name: 'Gold Spot', id: 'GOLD', change_percent: 0.54, price: 2242.10, sym: '$' },
    { name: 'WTI Crude', id: 'WTI', change_percent: 1.21, price: 81.42, sym: '$' },
    { name: 'Brent Crude', id: 'BRENT', change_percent: 1.15, price: 86.50, sym: '$' },
    { name: 'Silver Spot', id: 'SILVER', change_percent: -0.84, price: 25.14, sym: '$' },
  ];

  const STATIC_FX_PAIRS = [
    { name: 'EUR / USD', id: 'EURUSD', change_percent: 0.12, price: 1.0842, sym: '' },
    { name: 'USD / JPY', id: 'USDJPY', change_percent: -0.21, price: 149.85, sym: '' },
    { name: 'GBP / USD', id: 'GBPUSD', change_percent: 0.08, price: 1.2741, sym: '' },
  ];

  const STATIC_MACRO_RATES = [
    { name: 'US 10Y Yield', id: 'US10Y', change_percent: 1.05, price: 4.24, sym: '%' },
    { name: 'VIX Index', id: 'VIX', change_percent: -4.78, price: 16.31, sym: '' },
    { name: 'DXY Index', id: 'DXY', change_percent: 0.14, price: 104.12, sym: '' },
  ];

  const displayData = {
    globalIndices: data.globalIndices.length > 0 ? data.globalIndices : STATIC_GLOBAL_INDICES,
    commodities: data.commodities.length > 0 ? data.commodities : STATIC_COMMODITIES,
    fxPairs: data.fxPairs.length > 0 ? data.fxPairs : STATIC_FX_PAIRS,
    macroRates: data.macroRates.length > 0 ? data.macroRates : STATIC_MACRO_RATES,
  };

  return (
    <div className="space-y-12 pb-20 relative">
      <div
        className="pointer-events-none absolute inset-0"
        style={{ background: 'radial-gradient(circle at 70% 20%, rgba(79,107,255,0.08), transparent 55%)' }}
      />
      
      {/* Universal Header */}
      <header className="flex items-center justify-between sticky top-0 z-20 bg-black/70 backdrop-blur-xl py-5 border-b border-white/5">
        <div className="flex items-center gap-4">
          <div className="flex flex-col">
            <span className="data-text text-[10px] text-white/40 uppercase tracking-[0.32em]">Global Markets</span>
            <span className="heading-text text-[26px] text-white/90 tracking-[-0.01em]">Unified Terminal</span>
          </div>
        </div>

        <div className="flex items-center gap-4">
          {refreshing && (
            <div className="flex items-center gap-2">
              <div className="w-1.5 h-1.5 rounded-full bg-indigo-500 animate-pulse" />
              <span className="data-text text-[10px] text-indigo-400 uppercase tracking-widest">Live Syncing</span>
            </div>
          )}
          <button 
            onClick={doRefresh}
            disabled={refreshing}
            className="px-6 py-2 rounded-xl bg-indigo-500/10 backdrop-blur-xl border border-indigo-500/30 text-indigo-300 hover:bg-indigo-500/20 hover:border-indigo-500/50 hover:text-white disabled:opacity-50 disabled:cursor-not-allowed transition-all duration-300 data-text text-[10px] uppercase tracking-[0.28em] shadow-[0_0_15px_rgba(99,102,241,0.06)] hover:shadow-[0_0_22px_rgba(99,102,241,0.18)]"
          >
            {refreshing ? 'SYNCHRONIZING...' : 'REFRESH_TERMINAL'}
          </button>
        </div>
      </header>

      {/* Single Page Sections */}
      <div className="space-y-16 relative z-10">
        <section className="space-y-5">
          <div className="flex items-center gap-3">
            <div className="w-1.5 h-1.5 rounded-full bg-indigo-500 shadow-[0_0_8px_rgba(99,102,241,0.6)]" />
            <span className="data-text text-[10px] text-white/60 uppercase tracking-[0.35em] font-medium">World Indices</span>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
            {displayData.globalIndices.slice(0, 2).map(item => (
              <MarketCard key={item.id} item={item} symbol={item.sym} size="lg" />
            ))}
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-5">
            {displayData.globalIndices.slice(2).map(item => (
              <MarketCard key={item.id} item={item} symbol={item.sym} />
            ))}
          </div>
        </section>

        <MarketSection title="Resource Desk" items={displayData.commodities} symbol="$" />
        <MarketSection title="FX Oracle" items={displayData.fxPairs} symbol="" />
        <MarketSection title="Macro Stability" items={displayData.macroRates} symbol="" />
      </div>

      <style jsx global>{`
        .custom-scrollbar::-webkit-scrollbar { width: 3px; }
        .custom-scrollbar::-webkit-scrollbar-track { background: transparent; }
        .custom-scrollbar::-webkit-scrollbar-thumb { background: rgba(99, 102, 241, 0.1); border-radius: 10px; }
      `}</style>
    </div>
  );
}
