'use client';

import { useEffect, useState, useCallback } from 'react';
import { AreaChart, Area, ResponsiveContainer } from 'recharts';
import { marketAPI, fredAPI, extractErrorMessage } from '@/lib/api';

// --- Constants & Styles ---
const BLUE_ACCENT = '#4f46e5';
const CARD_GLOW = "group relative rounded-2xl border border-white/[0.07] bg-white/[0.03] backdrop-blur-xl shadow-[0_0_24px_rgba(79,70,229,0.04)] hover:shadow-[0_0_32px_rgba(79,70,229,0.12)] hover:border-indigo-500/20 hover:bg-white/[0.05] transition-all duration-500 overflow-hidden hover:-translate-y-1";
const CACHE_KEY = 'bloomberg_market_data_v1';
const CACHE_TTL = 4 * 60 * 60 * 1000; // 4 hours

type MarketItem = {
  name: string;
  id: string;
  change_percent: number;
  price: number;
  sym: string;
};

type MarketsPayload = {
  globalIndices: MarketItem[];
  commodities: MarketItem[];
  fxPairs: MarketItem[];
  macroRates: MarketItem[];
};

type QuotePoint = {
  value?: number;
  price?: number;
  change_pct?: number;
};

const asQuotePoint = (value: unknown): QuotePoint =>
  typeof value === 'object' && value !== null ? (value as QuotePoint) : {};

const STATIC_GLOBAL_INDICES: MarketItem[] = [
  { name: 'S&P 500', id: 'SPX', change_percent: 0.82, price: 5842.47, sym: '$' },
  { name: 'NASDAQ 100', id: 'NDX', change_percent: 1.14, price: 20378.92, sym: '$' },
  { name: 'NIFTY 50', id: 'NIFTY', change_percent: 0.5, price: 22402.4, sym: '₹' },
  { name: 'DOW JONES', id: 'DJI', change_percent: -0.12, price: 43192.05, sym: '$' },
  { name: 'SENSEX', id: 'BSESN', change_percent: -0.13, price: 73877.3, sym: '₹' },
];

const STATIC_COMMODITIES: MarketItem[] = [
  { name: 'Gold Spot', id: 'GOLD', change_percent: 0.54, price: 2242.1, sym: '$' },
  { name: 'WTI Crude', id: 'WTI', change_percent: 1.21, price: 81.42, sym: '$' },
  { name: 'Brent Crude', id: 'BRENT', change_percent: 1.15, price: 86.5, sym: '$' },
  { name: 'Silver Spot', id: 'SILVER', change_percent: -0.84, price: 25.14, sym: '$' },
];

const STATIC_FX_PAIRS: MarketItem[] = [
  { name: 'EUR / USD', id: 'EURUSD', change_percent: 0.12, price: 1.0842, sym: '' },
  { name: 'USD / JPY', id: 'USDJPY', change_percent: -0.21, price: 149.85, sym: '' },
  { name: 'GBP / USD', id: 'GBPUSD', change_percent: 0.08, price: 1.2741, sym: '' },
];

const STATIC_MACRO_RATES: MarketItem[] = [
  { name: 'US 10Y Yield', id: 'US10Y', change_percent: 1.05, price: 4.24, sym: '%' },
  { name: 'VIX Index', id: 'VIX', change_percent: -4.78, price: 16.31, sym: '' },
  { name: 'DXY Index', id: 'DXY', change_percent: 0.14, price: 104.12, sym: '' },
];

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

function MarketCard({ item, symbol, size = 'md' }: { item: MarketItem; symbol: string; size?: 'md' | 'lg' }) {
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

function MarketSection({ title, items, symbol }: { title: string; items: MarketItem[]; symbol: string }) {
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
  const [error, setError] = useState<string | null>(null);
  const [cacheInfo, setCacheInfo] = useState<{ used: boolean; timestamp: number | null }>({ used: false, timestamp: null });
  const [data, setData] = useState<MarketsPayload>({
    globalIndices: [],
    commodities: [],
    fxPairs: [],
    macroRates: []
  });

  const normalizePayload = (payload: unknown): MarketsPayload | null => {
    if (!payload || typeof payload !== 'object') return null;

    const asArray = (value: unknown): MarketItem[] => {
      if (!Array.isArray(value)) return [];
      return value
        .filter((item): item is Partial<MarketItem> => typeof item === 'object' && item !== null)
        .map((item) => ({
          name: typeof item.name === 'string' ? item.name : '',
          id: typeof item.id === 'string' ? item.id : '',
          change_percent: typeof item.change_percent === 'number' ? item.change_percent : 0,
          price: typeof item.price === 'number' ? item.price : 0,
          sym: typeof item.sym === 'string' ? item.sym : '',
        }))
        .filter((item) => item.id.length > 0 && item.name.length > 0);
    };

    const payloadObj = payload as Record<string, unknown>;
    return {
      globalIndices: asArray(payloadObj.globalIndices),
      commodities: asArray(payloadObj.commodities),
      fxPairs: asArray(payloadObj.fxPairs),
      macroRates: asArray(payloadObj.macroRates),
    };
  };

  const loadFromCache = useCallback((allowExpired = false) => {
    try {
      const cached = localStorage.getItem(CACHE_KEY);
      if (!cached) return false;

      const parsed = JSON.parse(cached);
      const payload = normalizePayload(parsed?.payload);
      const timestamp = Number(parsed?.timestamp);
      const validTimestamp = Number.isFinite(timestamp) && timestamp > 0;
      if (!payload || !validTimestamp) return false;

      const isFresh = Date.now() - timestamp < CACHE_TTL;
      if (isFresh || allowExpired) {
        setData(payload);
        setCacheInfo({ used: true, timestamp });
        return true;
      }
    } catch (e) {
      console.error('Failed to load cache:', e);
    }
    return false;
  }, []);

  const saveToCache = (payload: MarketsPayload) => {
    try {
      localStorage.setItem(CACHE_KEY, JSON.stringify({
        payload,
        timestamp: Date.now()
      }));
      setCacheInfo({ used: true, timestamp: Date.now() });
    } catch (e) {
      console.error('Failed to save cache:', e);
      setError('Unable to persist market snapshot in local cache.');
    }
  };

  const fetchAllData = async (force = false) => {
    try {
      setError(null);
      const fredSeries = [
        'SP500', 'DJIA', 'NASDAQ100', 
        'DCOILWTICO', 'DCOILBRENTEU', 'NASDAQQSLVO',
        'DEXUSEU', 'DEXJPUS', 'DEXUSUK',
        'DGS10', 'VIXCLS', 'DTWEXBGS'
      ];

      // 1. Fetch FRED Data
      const fredResponse = force 
        ? await fredAPI.getLatestLive(fredSeries)
        : await fredAPI.getLatestCached(fredSeries);
      
      const fredData = (fredResponse?.data as Record<string, QuotePoint> | undefined) || {};

      // 2. Fetch yfinance Data (Indices + Gold)
      const overviewRes = await marketAPI.getOverview();
      const overviewIndices = (overviewRes?.indices as Record<string, QuotePoint> | undefined) || {};

      // 3. Mapping Logic
      const newGlobalIndices = [
        { name: 'S&P 500', id: 'SPX', change_percent: asQuotePoint(fredData.SP500).change_pct || 0, price: asQuotePoint(fredData.SP500).value || 0, sym: '$' },
        { name: 'NASDAQ 100', id: 'NDX', change_percent: asQuotePoint(fredData.NASDAQ100).change_pct || 0, price: asQuotePoint(fredData.NASDAQ100).value || 0, sym: '$' },
        { name: 'NIFTY 50', id: 'NIFTY', change_percent: asQuotePoint(overviewIndices['^NSEI']).change_pct || 0.50, price: asQuotePoint(overviewIndices['^NSEI']).price || 22402.40, sym: '₹' },
        { name: 'DOW JONES', id: 'DJI', change_percent: asQuotePoint(fredData.DJIA).change_pct || 0, price: asQuotePoint(fredData.DJIA).value || 0, sym: '$' },
        { name: 'SENSEX', id: 'BSESN', change_percent: asQuotePoint(overviewIndices['^BSESN']).change_pct || -0.13, price: asQuotePoint(overviewIndices['^BSESN']).price || 73877.30, sym: '₹' },
      ].filter(x => x.price > 0);

      const newCommodities = [
        { name: 'Gold Spot', id: 'GOLD', change_percent: asQuotePoint(overviewIndices['GC=F']).change_pct || (asQuotePoint(fredData.GOLDAMGBD228NLBM).change_pct || 0.54), price: asQuotePoint(overviewIndices['GC=F']).price || (asQuotePoint(fredData.GOLDAMGBD228NLBM).value || 2242.10), sym: '$' },
        { name: 'WTI Crude', id: 'WTI', change_percent: asQuotePoint(fredData.DCOILWTICO).change_pct || 0, price: asQuotePoint(fredData.DCOILWTICO).value || 0, sym: '$' },
        { name: 'Brent Crude', id: 'BRENT', change_percent: asQuotePoint(fredData.DCOILBRENTEU).change_pct || 0, price: asQuotePoint(fredData.DCOILBRENTEU).value || 0, sym: '$' },
        { name: 'Silver Spot', id: 'SILVER', change_percent: asQuotePoint(fredData.NASDAQQSLVO).change_pct || 0, price: asQuotePoint(fredData.NASDAQQSLVO).value || 0, sym: '$' },
      ].filter(x => x.price > 0);

      const newFxPairs = [
        { name: 'EUR / USD', id: 'EURUSD', change_percent: asQuotePoint(fredData.DEXUSEU).change_pct || 0, price: asQuotePoint(fredData.DEXUSEU).value || 0, sym: '' },
        { name: 'USD / JPY', id: 'USDJPY', change_percent: (asQuotePoint(fredData.DEXJPUS).change_pct || 0) * -1, price: asQuotePoint(fredData.DEXJPUS).value || 0, sym: '' },
        { name: 'GBP / USD', id: 'GBPUSD', change_percent: asQuotePoint(fredData.DEXUSUK).change_pct || 0, price: asQuotePoint(fredData.DEXUSUK).value || 0, sym: '' },
      ].filter(x => x.price > 0);

      const newMacroRates = [
        { name: 'US 10Y Yield', id: 'US10Y', change_percent: asQuotePoint(fredData.DGS10).change_pct || 0, price: asQuotePoint(fredData.DGS10).value || 0, sym: '%' },
        { name: 'VIX Index', id: 'VIX', change_percent: asQuotePoint(fredData.VIXCLS).change_pct || 0, price: asQuotePoint(fredData.VIXCLS).value || 16.31, sym: '' },
        { name: 'DXY Index', id: 'DXY', change_percent: asQuotePoint(fredData.DTWEXBGS).change_pct || 0, price: asQuotePoint(fredData.DTWEXBGS).value || 104.12, sym: '' },
      ].filter(x => x.price > 0);

      const payload = {
        globalIndices: newGlobalIndices.length > 0 ? newGlobalIndices : STATIC_GLOBAL_INDICES,
        commodities: newCommodities.length > 0 ? newCommodities : STATIC_COMMODITIES,
        fxPairs: newFxPairs.length > 0 ? newFxPairs : STATIC_FX_PAIRS,
        macroRates: newMacroRates.length > 0 ? newMacroRates : STATIC_MACRO_RATES
      };

      setData(payload);
      saveToCache(payload);
      setError(null);
    } catch (err) {
      console.error('Fetch error:', err);
      // Keep UI useful by falling back to stale cache if live fetch fails.
      const usedStaleCache = loadFromCache(true);
      if (usedStaleCache) {
        setError('Live refresh failed. Showing cached market snapshot.');
        return;
      }
      setError(extractErrorMessage(err, 'Failed to fetch market data.'));
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
    // Always try background refresh so cache appears immediately but data stays current.
    void fetchAllData(!hasCache);
  }, [loadFromCache]);

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
        {error && (
          <div className="rounded-xl border border-red-400/30 bg-red-500/10 px-4 py-3 text-sm text-red-200">
            {error}
          </div>
        )}

        {cacheInfo.used && cacheInfo.timestamp && (
          <div className="rounded-xl border border-indigo-400/20 bg-indigo-500/10 px-4 py-3 text-xs text-indigo-200">
            Showing cached market snapshot from {new Date(cacheInfo.timestamp).toLocaleString()}.
          </div>
        )}

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
