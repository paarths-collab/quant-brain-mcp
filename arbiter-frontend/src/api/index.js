import axios from 'axios';

const API_BASE = 'http://localhost:8000/api';

const api = axios.create({
  baseURL: API_BASE,
  timeout: 30000,
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
  getCandles: (symbol, interval = '1d', range = '1y') =>
    api.get(`/market/candles/${symbol}`, { params: { interval, range } }),
  getIndicators: (symbol, interval = '1d', range = '1y') =>
    api.get(`/market/indicators/${symbol}`, { params: { interval, range } }),
};

// Sectors API  
export const sectorsAPI = {
  getPerformance: () => api.get('/sectors/performance'),
};

// Fundamentals API
export const fundamentalsAPI = {
  getOverview: (symbol) => api.get(`/fundamentals/overview/${symbol}`),
  getFinancials: (symbol) => api.get(`/fundamentals/financials/${symbol}`),
};

// Backtest API
export const backtestAPI = {
  run: (payload) => api.post('/backtest/run', payload),
  getStrategies: () => api.get('/backtest/strategies'),
  generateReport: (payload) => api.post('/backtest/report', payload),
  downloadReport: (filename) => `${API_BASE}/backtest/report/download/${filename}`,
};

// Research API
export const researchAPI = {
  analyze: (symbol) => api.post('/research/analyze', { symbol }),
  getSentiment: (symbol) => api.get(`/research/sentiment/${symbol}`),
};

// Sentiment API - AI-powered stock analysis
export const sentimentAPI = {
  // Full sentiment analysis with Reddit + AI
  analyze: (symbol, market = 'us') =>
    api.get(`/sentiment/analyze/${symbol}`, { params: { market } }),

  // Quick sentiment check (faster, minimal data)
  quick: (symbol, market = 'us') =>
    api.get(`/sentiment/quick/${symbol}`, { params: { market } }),

  // Batch analysis (max 10 symbols)
  batch: (symbols) => api.post('/sentiment/batch', { symbols }),
};

// Advanced AI Wealth Management API
export const wealthAPI = {
  // Full investment recommendation with multi-agent analysis
  analyze: (userInput, market = 'US') =>
    api.post('/wealth/analyze', { user_input: userInput, market }),

  // Streaming analysis with real-time progress
  analyzeStream: (userInput, market = 'US') => {
    const url = `${API_BASE}/wealth/analyze/stream?user_input=${encodeURIComponent(userInput)}&market=${market}`;
    return new EventSource(url);
  },

  // Execute trade
  executeTrade: (ticker, amount, side = 'buy', market = 'US') =>
    api.post('/wealth/trade/execute', { ticker, amount, side, market }),
};

// Network API
export const networkAPI = {
  getGraph: (symbol) => api.get(`/network/graph/${symbol}`),
};

// Peers API
export const peersAPI = {
  get: (symbol) => api.get(`/peers/${symbol}`),
};

// Macro API
export const macroAPI = {
  getIndicators: () => api.get('/macro/indicators'),
};

// Social API (Reddit, News)
export const socialAPI = {
  getNews: () => api.get('/social/news'),
  getReddit: (subreddit = 'wallstreetbets') => api.get(`/social/reddit/${subreddit}`),
};

// Treemap API - Indian & US indices with live prices
export const treemapAPI = {
  // Get all indices for a market (fast, no prices)
  getIndices: (market = 'india') => api.get('/treemap/indices', { params: { market } }),

  // Get all indices with live prices
  getIndicesLive: (market = 'india') => api.get('/treemap/indices/live', { params: { market } }),

  // Get stocks for a specific index with prices
  getIndexStocks: (indexId, market = 'india') =>
    api.get(`/treemap/index/${indexId}`, { params: { market } }),

  // Main treemap data endpoint
  getData: (market = 'india', indexId = null) =>
    api.get('/treemap/data', { params: { market, index_id: indexId } }),

  // Get top gainers and losers for an index
  getGainersLosers: (indexId, market = 'india', topN = 5) =>
    api.get(`/treemap/gainers-losers/${indexId}`, { params: { market, top_n: topN } }),

  // Search stocks
  search: (query, market = 'india') =>
    api.get('/treemap/search', { params: { q: query, market } }),

  // Get only sectoral indices
  getSectors: (market = 'india') => api.get('/treemap/sectors', { params: { market } }),

  // Get benchmark indices with live prices
  getBenchmarks: (market = 'india') => api.get('/treemap/benchmarks', { params: { market } }),

  // Get comprehensive stock details
  getStockDetails: (symbol, market = 'india') =>
    api.get(`/treemap/stock/${symbol}`, { params: { market } }),
};

// FRED API - Economic data (indices, rates, commodities)
export const fredAPI = {
  // Get available series
  getAvailableSeries: () => api.get('/fred/available-series'),

  // Get dashboard with all indices and rates
  getDashboard: () => api.get('/fred/dashboard'),

  // Get latest values for multiple series
  getLatest: (seriesIds) => api.get('/fred/latest', {
    params: seriesIds ? { series_ids: seriesIds.join(',') } : {}
  }),

  // Get specific series data with smart refresh
  getSeries: (seriesId, maxAgeHours = 24) =>
    api.get(`/fred/smart/${seriesId}`, { params: { max_age_hours: maxAgeHours } }),

  // Get latest value for a series
  getSeriesLatest: (seriesId) => api.get(`/fred/series/${seriesId}/latest`),
};

// Currency Formatter - properly handles INR (₹) and USD ($)
export const formatCurrency = (value, market = 'US') => {
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
export const formatLargeNumber = (value, market = 'US') => {
  if (value === null || value === undefined) return '-';
  const num = typeof value === 'string' ? parseFloat(value) : value;
  if (isNaN(num)) return '-';

  const symbol = getCurrencySymbol(market);

  if (market === 'IN' || market === 'NSE' || market === 'BSE') {
    // Indian numbering system (Lakhs, Crores)
    if (num >= 1e7) return `${symbol}${(num / 1e7).toFixed(2)} Cr`;
    if (num >= 1e5) return `${symbol}${(num / 1e5).toFixed(2)} L`;
    if (num >= 1e3) return `${symbol}${(num / 1e3).toFixed(2)} K`;
    return `${symbol}${num.toFixed(2)}`;
  }

  // Western numbering (Millions, Billions)
  if (num >= 1e12) return `${symbol}${(num / 1e12).toFixed(2)}T`;
  if (num >= 1e9) return `${symbol}${(num / 1e9).toFixed(2)}B`;
  if (num >= 1e6) return `${symbol}${(num / 1e6).toFixed(2)}M`;
  if (num >= 1e3) return `${symbol}${(num / 1e3).toFixed(2)}K`;
  return `${symbol}${num.toFixed(2)}`;
};

export default api;
