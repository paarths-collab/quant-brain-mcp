import { useState, useEffect } from 'react';
import { Search, Activity, Settings, RefreshCw, AlertTriangle, BarChart2, TrendingUp, TrendingDown, Clock, Zap } from 'lucide-react';
import { technicalAPI, marketAPI } from '@/api';
import { LightweightChart } from '@/components/LightweightChart';
import { ErrorBoundary } from '@/components/ErrorBoundary';

// --- Types ---
interface StrategyConfig {
  id: string;
  name: string;
  description?: string;
  parameters: Record<string, any>;
}

interface StrategyResult {
  signals: any[];
  meta: {
    current_mood: string;
    signal_count: number;
    last_updated: string;
  };
  indicators: Record<string, any[]>;
}

export default function Technical() {
  const [symbol, setSymbol] = useState('AAPL');
  const [market, setMarket] = useState<'US' | 'IN'>('US');
  const [searchInput, setSearchInput] = useState('');
  const [activeStrategy, setActiveStrategy] = useState<string>('');
  const [strategies, setStrategies] = useState<StrategyConfig[]>([]);
  const [strategyParams, setStrategyParams] = useState<Record<string, any>>({});

  // Chart Configuration State
  const [timeRange, setTimeRange] = useState<'1M' | '3M' | '6M' | '1Y' | '2Y' | '5Y' | 'ALL'>('1Y');
  const [chartType, setChartType] = useState<'candle' | 'area' | 'line'>('candle');

  // Data for Chart
  const [candleData, setCandleData] = useState<any[]>([]);
  const [volumeData, setVolumeData] = useState<any[]>([]);
  const [chartMarkers, setChartMarkers] = useState<any[]>([]);
  const [indicatorLines, setIndicatorLines] = useState<any[]>([]);

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [meta, setMeta] = useState<StrategyResult['meta'] | null>(null);

  // 1. Fetch Available Strategies on Mount
  useEffect(() => {
    const fetchStrategies = async () => {
      try {
        const res = await technicalAPI.getStrategies();
        if (res.data.strategies) {
          setStrategies(res.data.strategies);
        }
      } catch (err) {
        console.error("Failed to fetch strategies", err);
        setError("Failed to load strategies. Is the backend running?");
      }
    };
    fetchStrategies();
  }, []);

  // Switch default symbol when market changes
  useEffect(() => {
    if (market === 'US') {
      setSymbol('AAPL');
    } else if (market === 'IN') {
      setSymbol('RELIANCE');
    }
  }, [market]);

  // 2. Fetch Strategy Analysis & Market Data
  useEffect(() => {
    if (!symbol) return;

    const fetchData = async () => {
      setLoading(true);
      setError(null);

      try {
        // --- A. Fetch Market Data (Candles) ---
        // Map timeRange to marketAPI params
        let interval = '1d';
        let range = '1y';

        switch (timeRange) {
          case '1M': range = '1mo'; interval = '1d'; break; // or 1h if available
          case '3M': range = '3mo'; interval = '1d'; break;
          case '6M': range = '6mo'; interval = '1d'; break;
          case '1Y': range = '1y'; interval = '1d'; break;
          case '2Y': range = '2y'; interval = '1d'; break;
          case '5Y': range = '5y'; interval = '1wk'; break; // weekly for long range? or 1d is fine
          case 'ALL': range = 'max'; interval = '1mo'; break; // monthly for max?
          default: range = '1y';
        }

        // Override interval to 1d for consistency with strategy unless very long range
        if (timeRange === 'ALL') interval = '1wk';
        if (timeRange === '5Y') interval = '1d';

        // Fetch standard OHLCV data
        // Pass market param to handle IN suffix logic in backend
        const candlesRes = await marketAPI.getCandles(symbol, interval, range, market);

        if (!candlesRes.data?.data || candlesRes.data.data.length === 0) {
          throw new Error(`No data found for ${symbol} in ${market} market`);
        }

        const cData = candlesRes.data.data.map((d: any) => ({
          time: (d.date || d.timestamp).split('T')[0],
          open: d.open,
          high: d.high,
          low: d.low,
          close: d.close,
        }));

        const vData = candlesRes.data.data.map((d: any) => ({
          time: (d.date || d.timestamp).split('T')[0],
          value: d.volume,
          color: d.close >= d.open ? 'rgba(38, 166, 154, 0.5)' : 'rgba(239, 83, 80, 0.5)'
        }));

        setCandleData(cData);
        setVolumeData(vData);

        // --- B. Run Strategy Analysis (Only if strategy selected) ---
        if (activeStrategy) {
          const paramsStr = JSON.stringify(strategyParams);
          const res = await technicalAPI.analyze({
            symbol: symbol,
            strategy: activeStrategy,
            params: paramsStr,
            period: timeRange,
            interval: interval,
            market: market
          });

          const result = res.data;

          // Process Signals & Indicators
          setMeta(result.meta);
          setChartMarkers(result.signals || []);

          // Transform Indicators for Chart
          const lines: any[] = [];
          if (result.indicators) {
            const colorList = ['#2979FF', '#FF6D00', '#00E676', '#AA00FF', '#FF1744'];
            let colorIdx = 0;

            Object.keys(result.indicators).forEach((key) => {
              if (!result.indicators[key] || result.indicators[key].length === 0) return;

              lines.push({
                name: key.replace(/_/g, ' ').toUpperCase(),
                data: result.indicators[key].map((d: any) => ({ ...d, time: d.time.split('T')[0] })), // Ensure time format matches candles
                color: colorList[colorIdx % colorList.length]
              });
              colorIdx++;
            });
          }
          setIndicatorLines(lines);
        } else {
          // Clear strategy data if no strategy selected
          setMeta(null);
          setChartMarkers([]);
          setIndicatorLines([]);
        }

      } catch (err: any) {
        console.error("Analysis Failed", err);
        setError(err.response?.data?.detail || err.message || "Failed to analyze symbol");
        setMeta(null);
        setChartMarkers([]);
        setIndicatorLines([]);

        if (err.message.includes("No data")) {
          setCandleData([]);
          setVolumeData([]);
        }
      } finally {
        setLoading(false);
      }
    };

    const timer = setTimeout(() => {
      fetchData();
    }, 500);

    return () => clearTimeout(timer);

  }, [symbol, activeStrategy, strategyParams, timeRange, market]);

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    if (searchInput.trim()) {
      setSymbol(searchInput.toUpperCase().trim());
      setSearchInput('');
    }
  };

  const handleStrategyChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    const newStrategyId = e.target.value;
    setActiveStrategy(newStrategyId);

    if (!newStrategyId) {
      setStrategyParams({});
      return;
    }

    const s = strategies.find(x => x.id === newStrategyId);
    if (s) setStrategyParams(s.parameters);
  };

  const handleParamChange = (key: string, value: any) => {
    setStrategyParams(prev => ({ ...prev, [key]: Number(value) }));
  };

  return (
    <div className="finverse-dashboard bg-black min-h-screen text-slate-200 p-8 font-manrope">
      <ErrorBoundary scope="Technical Analysis">
        <div className="max-w-7xl mx-auto space-y-6 h-full flex flex-col">

          {/* Header & Controls */}
          <div className="flex flex-col xl:flex-row xl:items-center justify-between gap-6 border-b border-white/10 pb-6">
            <div>
              <h1 className="text-3xl font-bold font-fraunces text-white flex items-center gap-3">
                <Activity className="text-orange-500" />
                Technical Intelligence
              </h1>
              <p className="text-white/60 mt-1">Real-time algorithmic strategy analysis</p>
            </div>

            <div className="flex flex-wrap items-center gap-4">

              {/* Market Toggle */}
              <div className="flex bg-white/5 rounded-lg p-1 border border-white/10">
                <button
                  onClick={() => setMarket('US')}
                  className={`px-4 py-2 rounded-md text-sm font-bold transition-all ${market === 'US'
                    ? 'bg-orange-500 text-white shadow-lg shadow-orange-500/20'
                    : 'text-white/40 hover:text-white hover:bg-white/5'
                    }`}
                >
                  US
                </button>
                <button
                  onClick={() => setMarket('IN')}
                  className={`px-4 py-2 rounded-md text-sm font-bold transition-all ${market === 'IN'
                    ? 'bg-orange-500 text-white shadow-lg shadow-orange-500/20'
                    : 'text-white/40 hover:text-white hover:bg-white/5'
                    }`}
                >
                  INDIA
                </button>
              </div>

              <div className="h-8 w-[1px] bg-white/10 hidden md:block"></div>

              {/* Reference Search */}
              <form onSubmit={handleSearch} className="flex items-center bg-white/5 border border-white/10 rounded-xl px-4 py-2 focus-within:border-orange-500/50 transition-colors">
                <input
                  value={searchInput}
                  onChange={e => setSearchInput(e.target.value)}
                  placeholder="Symbol (e.g. AAPL)"
                  className="bg-transparent border-none outline-none text-white w-28 placeholder:text-white/30 font-mono text-sm"
                />
                <button type="submit" className="hover:text-orange-400 transition-colors"><Search size={18} /></button>
              </form>

              <div className="h-8 w-[1px] bg-white/10 hidden md:block"></div>

              {/* Time Range Selector */}
              <div className="flex bg-white/5 rounded-lg p-1 border border-white/10">
                {['1M', '3M', '6M', '1Y', '2Y', '5Y', 'ALL'].map((r) => (
                  <button
                    key={r}
                    onClick={() => setTimeRange(r as any)}
                    className={`px-4 py-2 rounded-md text-sm font-bold transition-all ${timeRange === r
                      ? 'bg-orange-500 text-white shadow-lg shadow-orange-500/20'
                      : 'text-white/40 hover:text-white hover:bg-white/5'
                      }`}
                  >
                    {r}
                  </button>
                ))}
              </div>

              {/* Chart Type Selector */}
              <div className="flex bg-white/5 rounded-lg p-1 border border-white/10">
                {['candle', 'line', 'area'].map((t) => (
                  <button
                    key={t}
                    onClick={() => setChartType(t as any)}
                    className={`px-4 py-2 rounded-md text-sm font-bold capitalize transition-all ${chartType === t
                      ? 'bg-orange-600/80 text-white shadow-lg shadow-orange-500/20'
                      : 'text-white/40 hover:text-white hover:bg-white/5'
                      }`}
                  >
                    {t}
                  </button>
                ))}
              </div>

              <div className="h-8 w-[1px] bg-white/10 hidden md:block"></div>

              {/* Strategy Selector */}
              <div className="relative group">
                <select
                  value={activeStrategy}
                  onChange={handleStrategyChange}
                  className="bg-white/5 border border-white/10 rounded-xl px-4 py-2 pr-8 text-white text-sm outline-none appearance-none hover:bg-white/10 transition-colors cursor-pointer min-w-[180px]"
                >
                  <option value="" className="bg-black text-white/50">No Strategy</option>
                  {strategies.map(s => <option key={s.id} value={s.id} className="bg-black text-white">{s.name}</option>)}
                </select>
                <div className="absolute right-3 top-1/2 -translate-y-1/2 pointer-events-none text-white/50">
                  <BarChart2 size={16} />
                </div>
              </div>
            </div>
          </div>


          {/* Error Banner */}
          {error && (
            <div className="bg-red-500/10 border border-red-500/20 text-red-400 p-4 rounded-xl flex items-center gap-3">
              <AlertTriangle size={20} />
              <span>{error}</span>
            </div>
          )}

          {/* Main Content Grid */}
          <div className="grid grid-cols-1 lg:grid-cols-4 gap-6 flex-1 min-h-[600px]">

            {/* Left Panel: Strategy Controls & Meta */}
            <div className="lg:col-span-1 space-y-6">

              {/* Strategy Meta Card */}
              <div className="bg-white/5 border border-white/10 rounded-2xl p-6 relative overflow-hidden group">
                <div className="absolute top-0 right-0 p-4 opacity-5 group-hover:opacity-10 transition-opacity">
                  <Zap size={80} />
                </div>

                <div className="flex items-center justify-between mb-6">
                  <span className="text-white/40 text-xs font-bold uppercase tracking-wider">Signal Mood</span>
                  <span className={`px-2 py-1 rounded-lg text-xs font-bold flex items-center gap-1 ${meta?.current_mood === 'BULLISH' ? 'bg-green-500/20 text-green-400' :
                    meta?.current_mood === 'BEARISH' ? 'bg-red-500/20 text-red-400' :
                      'bg-white/10 text-white/50'
                    }`}>
                    {meta?.current_mood === 'BULLISH' && <TrendingUp size={12} />}
                    {meta?.current_mood === 'BEARISH' && <TrendingDown size={12} />}
                    {meta?.current_mood || 'NEUTRAL'}
                  </span>
                </div>

                <div className="mb-6">
                  <div className="text-4xl font-bold text-white font-fraunces mb-1">{symbol}</div>
                  <div className="text-xs text-white/40 flex items-center gap-1">
                    <Clock size={10} />
                    Updated: {meta?.last_updated ? new Date(meta.last_updated).toLocaleDateString() : '-'}
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-3">
                  <div className="bg-black/30 rounded-xl p-3 text-center border border-white/5">
                    <div className="text-[10px] text-white/40 uppercase mb-1">Signals</div>
                    <div className="text-xl font-mono text-white font-bold">{meta?.signal_count || 0}</div>
                  </div>
                  <div className="bg-black/30 rounded-xl p-3 text-center border border-white/5">
                    <div className="text-[10px] text-white/40 uppercase mb-1">Interval</div>
                    <div className="text-xl font-mono text-white font-bold">1D</div>
                  </div>
                </div>
              </div>

              {/* Dynamic Parameters */}
              <div className="bg-white/5 border border-white/10 rounded-2xl p-6">
                <div className="flex items-center gap-2 mb-6 text-white/90">
                  <Settings size={18} className="text-blue-400" />
                  <span className="font-bold">Strategy Parameters</span>
                </div>

                <div className="space-y-5">
                  {Object.keys(strategyParams).length > 0 ? Object.keys(strategyParams).map(key => (
                    <div key={key} className="group">
                      <div className="flex justify-between items-center mb-2">
                        <label className="text-xs text-white/60 capitalize group-hover:text-white transition-colors">{key.replace(/_/g, ' ')}</label>
                        <span className="text-xs font-mono text-blue-300 bg-blue-500/10 px-1.5 py-0.5 rounded">{strategyParams[key]}</span>
                      </div>
                      <input
                        type="range"
                        min="2" max="250" step="1"
                        value={strategyParams[key]}
                        onChange={(e) => handleParamChange(key, e.target.value)}
                        className="w-full h-1.5 bg-white/10 rounded-lg appearance-none cursor-pointer accent-blue-500 hover:accent-blue-400 transition-all"
                      />
                    </div>
                  )) : (
                    <div className="text-sm text-white/30 italic text-center py-4">No configurable parameters</div>
                  )}
                </div>
              </div>
            </div>

            {/* Right Panel: Chart */}
            <div className="lg:col-span-3 bg-white/5 border border-white/10 rounded-2xl overflow-hidden flex flex-col relative shadow-2xl">
              {loading && (
                <div className="absolute inset-0 bg-black/60 z-20 flex items-center justify-center backdrop-blur-sm">
                  <div className="flex flex-col items-center gap-3">
                    <RefreshCw className="animate-spin text-orange-500" size={32} />
                    <span className="text-white/60 text-sm animate-pulse">Running Analysis...</span>
                  </div>
                </div>
              )}

              <div className="flex-1 w-full h-full min-h-[500px]">
                {candleData.length > 0 ? (
                  <LightweightChart
                    data={{
                      candleData,
                      volumeData,
                      markers: chartMarkers,
                      lineData: indicatorLines
                    }}
                    height={600}
                    chartType={chartType}
                    colors={{
                      backgroundColor: 'transparent',
                      textColor: '#94a3b8',
                      gridColor: 'rgba(255, 255, 255, 0.04)',
                      upColor: '#22c55e',
                      downColor: '#ef4444'
                    }}
                  />
                ) : (
                  <div className="h-full flex flex-col items-center justify-center text-white/20 gap-4">
                    <Activity size={48} strokeWidth={1} />
                    <div>{loading ? 'Initializing Analysis...' : 'Enter a symbol to start analysis'}</div>
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>
      </ErrorBoundary>
    </div>
  );
}
