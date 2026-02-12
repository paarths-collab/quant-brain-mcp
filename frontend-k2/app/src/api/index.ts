import axios from 'axios';

const API_ROOT = (import.meta.env.VITE_API_BASE_URL || 'http://localhost:8001').replace(/\/$/, '');
const API_BASE = `${API_ROOT}/api`;

const api = axios.create({
  baseURL: API_BASE,
  timeout: 360000, // 360 seconds for complex AI operations
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request interceptor for debugging
api.interceptors.request.use((config) => {
  console.log(`[API] ${config.method?.toUpperCase()} ${config.url}`);
  return config;
});

// Response interceptor for error handling
api.interceptors.response.use(
  (response) => response,
  (error) => {
    console.error('[API Error]', error.response?.status, error.message);
    return Promise.reject(error);
  }
);

// Market Data API
export const marketAPI = {
  getOverview: () => api.get('/market/overview'),
  getCandles: (symbol: string, interval = '1d', range = '1y') =>
    api.get(`/market/candles/${symbol}`, { params: { interval, range } }),
  getIndicators: (symbol: string, interval = '1d', range = '1y') =>
    api.get(`/market/indicators/${symbol}`, { params: { interval, range } }),
};

// Sectors API  
export const sectorsAPI = {
  getPerformance: () => api.get('/sectors/performance'),
};

// Fundamentals API
export const fundamentalsAPI = {
  getOverview: (symbol: string) => api.get(`/fundamentals/overview/${symbol}`),
  getFinancials: (symbol: string) => api.get(`/fundamentals/financials/${symbol}`),
};

// Backtest API
export const backtestAPI = {
  run: (payload: any) => api.post('/backtest/run', payload),
  getStrategies: () => api.get('/backtest/strategies'),
  heatmap: (payload: any) => api.post('/backtest/heatmap', payload),
  generateReport: (payload: any) => api.post('/backtest/report', payload),
  downloadReport: (filename: string) => `${API_BASE}/backtest/report/download/${filename}`,
  quantstatsReport: (payload: any) => api.post('/backtest/quantstats-report', payload),
};

// Research API
export const researchAPI = {
  analyze: (symbol: string) => api.post('/research/analyze', { symbol }),
  getSentiment: (symbol: string) => api.get(`/research/sentiment/${symbol}`),
  generateReport: (payload: any) => api.post('/research/report', payload),
  downloadReport: (filename: string) => `${API_BASE}/research/report/download/${filename}`,
};

// Sentiment API - AI-powered stock analysis
export const sentimentAPI = {
  // Full sentiment analysis with Reddit + AI
  analyze: (symbol: string, market = 'us') =>
    api.get(`/sentiment/analyze/${symbol}`, { params: { market } }),

  // Quick sentiment check (faster, minimal data)
  quick: (symbol: string, market = 'us') =>
    api.get(`/sentiment/quick/${symbol}`, { params: { market } }),

  // Batch analysis (max 10 symbols)
  batch: (symbols: string[]) => api.post('/sentiment/batch', { symbols }),
};

// Advanced AI Wealth Management API
export const wealthAPI = {
  // Full investment recommendation with multi-agent analysis
  analyze: (userInput: string, market = 'US') =>
    api.post('/wealth/analyze', { user_input: userInput, market }),

  // Execute trade
  executeTrade: (ticker: string, amount: number, side = 'buy', market = 'US') =>
    api.post('/wealth/trade/execute', { ticker, amount, side, market }),
};

// Network API
export const networkAPI = {
  getGraph: (symbol: string) => api.get(`/network/graph/${symbol}`),
};

// Peers API
export const peersAPI = {
  get: (symbol: string) => api.get(`/peers/${symbol}`),
  compare: (symbol: string, limit = 12) => api.get(`/peers/compare/${symbol}`, { params: { limit } }),
};

// Macro API
export const macroAPI = {
  getIndicators: () => api.get('/macro/indicators'),
};

// Social API (Reddit, News)
export const socialAPI = {
  getNews: (query?: string, limit = 12) =>
    api.get('/social/news', { params: query ? { query, limit } : { limit } }),
  getReddit: (subreddit = 'wallstreetbets') => api.get(`/social/reddit/${subreddit}`),
};

// Treemap API - Indian & US indices with live prices
export const treemapAPI = {
  // Get all indices for a market (fast, no prices)
  getIndices: (market = 'india') => api.get('/treemap/indices', { params: { market } }),

  // Get all indices with live prices
  getIndicesLive: (market = 'india') => api.get('/treemap/indices/live', { params: { market } }),

  // Get stocks for a specific index with prices
  getIndexStocks: (indexId: string, market = 'india') =>
    api.get(`/treemap/index/${indexId}`, { params: { market } }),

  // Main treemap data endpoint
  getData: (market = 'india', indexId: string | null = null) =>
    api.get('/treemap/data', { params: { market, index_id: indexId } }),

  // Get top gainers and losers for an index
  getGainersLosers: (indexId: string, market = 'india', topN = 5) =>
    api.get(`/treemap/gainers-losers/${indexId}`, { params: { market, top_n: topN } }),

  // Search stocks
  search: (query: string, market = 'india') =>
    api.get('/treemap/search', { params: { q: query, market } }),

  // Get only sectoral indices
  getSectors: (market = 'india') => api.get('/treemap/sectors', { params: { market } }),

  // Get benchmark indices with live prices
  getBenchmarks: (market = 'india') => api.get('/treemap/benchmarks', { params: { market } }),

  // Get comprehensive stock details
  getStockDetails: (symbol: string, market = 'india') =>
    api.get(`/treemap/stock/${symbol}`, { params: { market } }),
};

// FRED API - Economic data (indices, rates, commodities)
export const fredAPI = {
  // Get available series
  getAvailableSeries: () => api.get('/fred/available-series'),

  // Get dashboard with all indices and rates
  getDashboard: () => api.get('/fred/dashboard'),

  // Get latest values for multiple series
  getLatest: (seriesIds?: string[]) => api.get('/fred/latest', {
    params: seriesIds ? { series_ids: seriesIds.join(',') } : {}
  }),

  // Get specific series data with smart refresh
  getSeries: (seriesId: string, maxAgeHours = 24) =>
    api.get(`/fred/smart/${seriesId}`, { params: { max_age_hours: maxAgeHours } }),

  // Get latest value for a series
  getSeriesLatest: (seriesId: string) => api.get(`/fred/series/${seriesId}/latest`),

  // Get latest values directly from FRED (no cache)
  getLatestLive: (seriesIds?: string[]) => api.get('/fred/latest-live', {
    params: seriesIds ? { series_ids: seriesIds.join(',') } : {}
  }),

  // Get latest values from cache (refresh only if stale)
  getLatestCached: (seriesIds?: string[], maxAgeHours = 24) => api.get('/fred/latest-cached', {
    params: seriesIds ? { series_ids: seriesIds.join(','), max_age_hours: maxAgeHours } : { max_age_hours: maxAgeHours }
  }),

  // Get trending index news via DuckDuckGo
  getTrendingNews: (seriesIds?: string[], maxAgeHours = 12, limit = 6) => api.get('/fred/trending-news', {
    params: seriesIds ? { series_ids: seriesIds.join(','), max_age_hours: maxAgeHours, limit } : { max_age_hours: maxAgeHours, limit }
  }),

  // Get news per index
  getIndexNews: (seriesIds?: string[], maxAgeHours = 12, limit = 5) => api.get('/fred/index-news', {
    params: seriesIds ? { series_ids: seriesIds.join(','), max_age_hours: maxAgeHours, limit } : { max_age_hours: maxAgeHours, limit }
  }),

  // Get news per series (any FRED series ids)
  getSeriesNews: (seriesIds?: string[], maxAgeHours = 12, limit = 5) => api.get('/fred/index-news', {
    params: seriesIds ? { series_ids: seriesIds.join(','), max_age_hours: maxAgeHours, limit } : { max_age_hours: maxAgeHours, limit }
  }),
};

// Currency Formatter - properly handles INR (₹) and USD ($)
export const formatCurrency = (value: number | string | null | undefined, market = 'US') => {
  if (value === null || value === undefined) return '-';
  const num = typeof value === 'string' ? parseFloat(value) : value;
  if (isNaN(num)) return '-';

  if (market === 'IN' || market === 'NSE' || market === 'BSE') {
    return new Intl.NumberFormat('en-IN', {
      style: 'currency',
      currency: 'INR',
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    }).format(num);
  }

  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(num);
};

export const getCurrencySymbol = (market = 'US') => {
  return (market === 'IN' || market === 'NSE' || market === 'BSE') ? '₹' : '$';
};

// Format large numbers (for market cap, volume etc)
export const formatLargeNumber = (value: number | string | null | undefined, market = 'US') => {
  if (value === null || value === undefined) return '-';
  const num = typeof value === 'string' ? parseFloat(value) : value;
  if (isNaN(num)) return '-';

  const currSymbol = getCurrencySymbol(market);
  const absNum = Math.abs(num);

  if (absNum >= 1e12) return `${currSymbol}${(num / 1e12).toFixed(2)}T`;
  if (absNum >= 1e9) return `${currSymbol}${(num / 1e9).toFixed(2)}B`;
  if (absNum >= 1e6) return `${currSymbol}${(num / 1e6).toFixed(2)}M`;
  if (absNum >= 1e3) return `${currSymbol}${(num / 1e3).toFixed(2)}K`;
  
  return `${currSymbol}${num.toFixed(2)}`;
};

export default api;
