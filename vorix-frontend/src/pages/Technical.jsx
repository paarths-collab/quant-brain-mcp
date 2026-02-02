import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { 
  Search, TrendingUp, TrendingDown, BarChart3, 
  Activity, ChevronDown, RefreshCw
} from 'lucide-react';
import { 
  AreaChart, Area, XAxis, YAxis, CartesianGrid, 
  Tooltip, ResponsiveContainer 
} from 'recharts';
import { marketAPI, fundamentalsAPI } from '../api';
import './Technical.css';

const mockPriceData = [
  { date: '9:30', price: 185.2 }, { date: '10:00', price: 186.5 },
  { date: '10:30', price: 185.8 }, { date: '11:00', price: 187.2 },
  { date: '11:30', price: 188.1 }, { date: '12:00', price: 187.5 },
  { date: '12:30', price: 189.0 }, { date: '13:00', price: 188.3 },
  { date: '13:30', price: 190.2 }, { date: '14:00', price: 191.5 },
  { date: '14:30', price: 190.8 }, { date: '15:00', price: 192.1 },
  { date: '15:30', price: 193.4 }, { date: '16:00', price: 192.8 },
];

const mockIndicators = [
  { name: 'RSI (14)', value: '58.32', status: 'neutral' },
  { name: 'MACD', value: '2.45', status: 'bullish' },
  { name: 'SMA 20', value: '$188.50', status: 'above' },
  { name: 'SMA 50', value: '$182.30', status: 'above' },
  { name: 'Volume', value: '45.2M', status: 'high' },
  { name: 'ATR', value: '3.21', status: 'normal' },
];

function Technical() {
  const [symbol, setSymbol] = useState('AAPL');
  const [searchInput, setSearchInput] = useState('');
  const [timeframe, setTimeframe] = useState('1D');

  const handleSearch = (e) => {
    e.preventDefault();
    if (searchInput.trim()) {
      setSymbol(searchInput.toUpperCase());
      setSearchInput('');
    }
  };

  return (
    <div className="technical-page">
      <div className="page-header">
        <h1 className="page-title">Technical Analysis</h1>
        <form className="search-form" onSubmit={handleSearch}>
          <Search size={18} />
          <input 
            type="text" 
            placeholder="Search symbol..."
            value={searchInput}
            onChange={(e) => setSearchInput(e.target.value)}
          />
        </form>
      </div>

      <div className="technical-grid">
        {/* Chart Section */}
        <div className="chart-section glass-card">
          <div className="chart-header">
            <div className="stock-info">
              <h2>{symbol}</h2>
              <span className="stock-price">$192.80</span>
              <span className="stock-change positive">+4.12 (+2.18%)</span>
            </div>
            <div className="timeframe-selector">
              {['1D', '1W', '1M', '3M', '1Y'].map((tf) => (
                <button 
                  key={tf} 
                  className={`tf-btn ${timeframe === tf ? 'active' : ''}`}
                  onClick={() => setTimeframe(tf)}
                >
                  {tf}
                </button>
              ))}
            </div>
          </div>
          <div className="chart-container">
            <ResponsiveContainer width="100%" height={350}>
              <AreaChart data={mockPriceData}>
                <defs>
                  <linearGradient id="colorPrice" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#22c55e" stopOpacity={0.3}/>
                    <stop offset="95%" stopColor="#22c55e" stopOpacity={0}/>
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
                <XAxis dataKey="date" axisLine={false} tickLine={false} tick={{ fill: '#6b6b80', fontSize: 11 }} />
                <YAxis domain={['auto', 'auto']} axisLine={false} tickLine={false} tick={{ fill: '#6b6b80', fontSize: 11 }} tickFormatter={(v) => `$${v}`} />
                <Tooltip 
                  contentStyle={{ background: '#1e1e32', border: '1px solid rgba(255,255,255,0.1)', borderRadius: 8 }}
                  labelStyle={{ color: '#fff' }}
                />
                <Area type="monotone" dataKey="price" stroke="#22c55e" strokeWidth={2} fill="url(#colorPrice)" />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Indicators */}
        <div className="indicators-section glass-card">
          <h3>Technical Indicators</h3>
          <div className="indicators-list">
            {mockIndicators.map((ind, i) => (
              <div key={i} className="indicator-item">
                <span className="ind-name">{ind.name}</span>
                <span className="ind-value">{ind.value}</span>
                <span className={`ind-status ${ind.status}`}>{ind.status}</span>
              </div>
            ))}
          </div>
        </div>

        {/* Key Stats */}
        <div className="stats-section glass-card">
          <h3>Key Statistics</h3>
          <div className="stats-grid">
            <div className="stat-item">
              <span className="stat-label">Market Cap</span>
              <span className="stat-value">$2.98T</span>
            </div>
            <div className="stat-item">
              <span className="stat-label">P/E Ratio</span>
              <span className="stat-value">31.24</span>
            </div>
            <div className="stat-item">
              <span className="stat-label">52W High</span>
              <span className="stat-value">$199.62</span>
            </div>
            <div className="stat-item">
              <span className="stat-label">52W Low</span>
              <span className="stat-value">$164.08</span>
            </div>
            <div className="stat-item">
              <span className="stat-label">Avg Volume</span>
              <span className="stat-value">58.2M</span>
            </div>
            <div className="stat-item">
              <span className="stat-label">Dividend</span>
              <span className="stat-value">0.51%</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

export default Technical;
