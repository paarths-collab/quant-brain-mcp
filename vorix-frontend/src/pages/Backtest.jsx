import { useState } from 'react';
import { 
  Play, Settings, TrendingUp, TrendingDown, 
  Calendar, DollarSign, Percent, BarChart3
} from 'lucide-react';
import { 
  AreaChart, Area, XAxis, YAxis, CartesianGrid, 
  Tooltip, ResponsiveContainer, BarChart, Bar
} from 'recharts';
import { backtestAPI } from '../api';
import './Backtest.css';

const mockEquityCurve = [
  { date: 'Jan', value: 100000 }, { date: 'Feb', value: 105000 },
  { date: 'Mar', value: 102000 }, { date: 'Apr', value: 115000 },
  { date: 'May', value: 125000 }, { date: 'Jun', value: 120000 },
  { date: 'Jul', value: 135000 }, { date: 'Aug', value: 142000 },
  { date: 'Sep', value: 138000 }, { date: 'Oct', value: 155000 },
  { date: 'Nov', value: 162000 }, { date: 'Dec', value: 175000 },
];

const mockMonthlyReturns = [
  { month: 'Jan', return: 5.0 }, { month: 'Feb', return: -2.8 },
  { month: 'Mar', return: 12.7 }, { month: 'Apr', return: 8.7 },
  { month: 'May', return: -4.0 }, { month: 'Jun', return: 12.5 },
  { month: 'Jul', return: 5.2 }, { month: 'Aug', return: -2.9 },
  { month: 'Sep', return: 12.3 }, { month: 'Oct', return: 4.5 },
  { month: 'Nov', return: 8.0 }, { month: 'Dec', return: -1.2 },
];

const strategies = [
  { id: 'momentum', name: 'Momentum Strategy', description: 'Buy high-momentum stocks' },
  { id: 'mean_reversion', name: 'Mean Reversion', description: 'Trade price reversals' },
  { id: 'value', name: 'Value Investing', description: 'Low P/E, high dividend stocks' },
  { id: 'growth', name: 'Growth Strategy', description: 'High revenue growth stocks' },
];

function Backtest() {
  const [selectedStrategy, setSelectedStrategy] = useState('momentum');
  const [capital, setCapital] = useState('100000');
  const [startDate, setStartDate] = useState('2024-01-01');
  const [endDate, setEndDate] = useState('2024-12-31');
  const [results, setResults] = useState(true);

  const metrics = [
    { label: 'Total Return', value: '+75.0%', icon: TrendingUp, positive: true },
    { label: 'Sharpe Ratio', value: '1.85', icon: BarChart3 },
    { label: 'Max Drawdown', value: '-12.3%', icon: TrendingDown, negative: true },
    { label: 'Win Rate', value: '68.5%', icon: Percent },
    { label: 'Profit Factor', value: '2.42', icon: DollarSign },
    { label: 'Total Trades', value: '156', icon: BarChart3 },
  ];

  return (
    <div className="backtest-page">
      <h1 className="page-title">Strategy Backtesting</h1>

      <div className="backtest-grid">
        {/* Configuration Panel */}
        <div className="config-panel glass-card">
          <h3>Configuration</h3>
          
          <div className="config-section">
            <label>Strategy</label>
            <div className="strategy-list">
              {strategies.map((s) => (
                <button 
                  key={s.id}
                  className={`strategy-btn ${selectedStrategy === s.id ? 'active' : ''}`}
                  onClick={() => setSelectedStrategy(s.id)}
                >
                  <span className="strategy-name">{s.name}</span>
                  <span className="strategy-desc">{s.description}</span>
                </button>
              ))}
            </div>
          </div>

          <div className="config-row">
            <div className="config-field">
              <label>Initial Capital</label>
              <div className="input-wrapper">
                <DollarSign size={16} />
                <input 
                  type="text" 
                  value={capital} 
                  onChange={(e) => setCapital(e.target.value)} 
                />
              </div>
            </div>
          </div>

          <div className="config-row">
            <div className="config-field">
              <label>Start Date</label>
              <div className="input-wrapper">
                <Calendar size={16} />
                <input 
                  type="date" 
                  value={startDate} 
                  onChange={(e) => setStartDate(e.target.value)} 
                />
              </div>
            </div>
            <div className="config-field">
              <label>End Date</label>
              <div className="input-wrapper">
                <Calendar size={16} />
                <input 
                  type="date" 
                  value={endDate} 
                  onChange={(e) => setEndDate(e.target.value)} 
                />
              </div>
            </div>
          </div>

          <button className="run-btn">
            <Play size={18} /> Run Backtest
          </button>
        </div>

        {/* Results */}
        {results && (
          <>
            {/* Metrics */}
            <div className="metrics-grid">
              {metrics.map((m, i) => (
                <div key={i} className="metric-card glass-card">
                  <div className="metric-icon">
                    <m.icon size={20} />
                  </div>
                  <div className="metric-content">
                    <span className="metric-label">{m.label}</span>
                    <span className={`metric-value ${m.positive ? 'positive' : ''} ${m.negative ? 'negative' : ''}`}>
                      {m.value}
                    </span>
                  </div>
                </div>
              ))}
            </div>

            {/* Equity Curve */}
            <div className="equity-chart glass-card">
              <h3>Equity Curve</h3>
              <div className="chart-container">
                <ResponsiveContainer width="100%" height={280}>
                  <AreaChart data={mockEquityCurve}>
                    <defs>
                      <linearGradient id="colorEquity" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%" stopColor="#a855f7" stopOpacity={0.3}/>
                        <stop offset="95%" stopColor="#a855f7" stopOpacity={0}/>
                      </linearGradient>
                    </defs>
                    <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
                    <XAxis dataKey="date" axisLine={false} tickLine={false} tick={{ fill: '#6b6b80', fontSize: 11 }} />
                    <YAxis axisLine={false} tickLine={false} tick={{ fill: '#6b6b80', fontSize: 11 }} tickFormatter={(v) => `$${v/1000}k`} />
                    <Tooltip contentStyle={{ background: '#1e1e32', border: '1px solid rgba(255,255,255,0.1)', borderRadius: 8 }} />
                    <Area type="monotone" dataKey="value" stroke="#a855f7" strokeWidth={2} fill="url(#colorEquity)" />
                  </AreaChart>
                </ResponsiveContainer>
              </div>
            </div>

            {/* Monthly Returns */}
            <div className="returns-chart glass-card">
              <h3>Monthly Returns</h3>
              <div className="chart-container">
                <ResponsiveContainer width="100%" height={200}>
                  <BarChart data={mockMonthlyReturns}>
                    <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
                    <XAxis dataKey="month" axisLine={false} tickLine={false} tick={{ fill: '#6b6b80', fontSize: 11 }} />
                    <YAxis axisLine={false} tickLine={false} tick={{ fill: '#6b6b80', fontSize: 11 }} tickFormatter={(v) => `${v}%`} />
                    <Tooltip contentStyle={{ background: '#1e1e32', border: '1px solid rgba(255,255,255,0.1)', borderRadius: 8 }} />
                    <Bar dataKey="return" fill="#a855f7" radius={[4, 4, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </div>
          </>
        )}
      </div>
    </div>
  );
}

export default Backtest;
