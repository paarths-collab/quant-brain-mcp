import axios from 'axios';

const API_BASE_URL = 'http://localhost:8000';

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Market APIs
export const marketAPI = {
  getOverview: () => api.get('/api/market/overview'),
  getIndices: () => api.get('/api/market/indices'),
  getQuote: (symbol) => api.get(`/api/market/quote/${symbol}`),
  getHistory: (symbol, period = '1y') => api.get(`/api/market/history/${symbol}?period=${period}`),
};

// Fundamentals APIs
export const fundamentalsAPI = {
  getProfile: (symbol) => api.get(`/api/fundamentals/${symbol}/profile`),
  getMetrics: (symbol) => api.get(`/api/fundamentals/${symbol}/metrics`),
  getFinancials: (symbol) => api.get(`/api/fundamentals/${symbol}/financials`),
};

// EIA Energy APIs
export const eiaAPI = {
  getOilReserves: () => api.get('/api/eia/reserves/oil'),
  getPetroleumSummary: () => api.get('/api/eia/petroleum/summary'),
};

// Network Graph API
export const networkAPI = {
  getGraph: (symbol) => api.get(`/api/network/${symbol}`),
};

// Backtest API
export const backtestAPI = {
  run: (config) => api.post('/api/backtest/run', config),
};

// Research API
export const researchAPI = {
  analyze: (symbol) => api.post('/api/research/analyze', { symbol }),
};

// Macro API
export const macroAPI = {
  getIndicators: () => api.get('/api/macro/indicators'),
  getCalendar: () => api.get('/api/macro/calendar'),
};

export default api;
