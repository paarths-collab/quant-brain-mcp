import { useState, useEffect } from 'react';
import { useQuery } from '@tanstack/react-query';
import { 
  Wallet, TrendingUp, TrendingDown, RefreshCw, Info, 
  ArrowUpRight, ArrowDownRight, Calendar, ChevronDown
} from 'lucide-react';
import { 
  AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
  PieChart, Pie, Cell
} from 'recharts';
import { marketAPI } from '../api';
import './Dashboard.css';

const mockChartData = [
  { name: 'Jan', value: 3200 }, { name: 'Feb', value: 4100 }, { name: 'Mar', value: 3800 },
  { name: 'Apr', value: 5200 }, { name: 'May', value: 4800 }, { name: 'Jun', value: 6200 },
  { name: 'Jul', value: 5800 }, { name: 'Aug', value: 8000 }, { name: 'Sep', value: 7200 },
  { name: 'Oct', value: 7800 }, { name: 'Nov', value: 8500 }, { name: 'Dec', value: 9200 },
];

const mockCurrencies = [
  { name: 'BTC/USD', value: '$525,525.00' },
  { name: 'EUR/USD', value: '$414,587.00' },
  { name: 'ETH/USD', value: '$785,58.00' },
  { name: 'GBP/USD', value: '$875,525.00' },
];

const mockTransactions = [
  { id: 1, name: 'William Hirsch', country: 'USA', invoice: 'INV-5784', type: 'Service Fee', date: '20 July 2025', amount: '$585,658.00', status: 'Paid' },
  { id: 2, name: 'Sarah Chen', country: 'CHN', invoice: 'INV-5783', type: 'Subscription', date: '19 July 2025', amount: '$120,000.00', status: 'Paid' },
  { id: 3, name: 'Marcus Johnson', country: 'UK', invoice: 'INV-5782', type: 'Transfer', date: '18 July 2025', amount: '$45,200.00', status: 'Pending' },
];

const pieData = [
  { name: 'USD', value: 55, color: '#a855f7' },
  { name: 'Euro', value: 25, color: '#22d3ee' },
  { name: 'Pound', value: 20, color: '#f59e0b' },
];

function Dashboard() {
  return (
    <div className="dashboard">
      <h1 className="page-title">Payment</h1>
      
      {/* Top Row */}
      <div className="top-row">
        {/* Balance Card */}
        <div className="balance-card glass-card">
          <div className="balance-header">
            <div className="balance-icon"><Wallet size={18} /></div>
            <span>My Balance</span>
            <Info size={14} className="info-icon" />
            <div className="card-selector">
              <span className="card-dot red"></span>
              <span>xx25</span>
              <ChevronDown size={14} />
            </div>
          </div>
          <div className="balance-amount">
            <span className="amount">$875,985.00</span>
            <span className="change positive">+55.58%</span>
          </div>
          <div className="balance-actions">
            <button className="action-btn primary">
              <ArrowUpRight size={16} /> Transfer
            </button>
            <button className="action-btn secondary">
              Request <ArrowDownRight size={16} />
            </button>
          </div>
          <div className="currency-row">
            {mockCurrencies.map((c, i) => (
              <div key={i} className="currency-item">
                <span className="currency-value">{c.value}</span>
                <span className="currency-name">{c.name}</span>
              </div>
            ))}
          </div>
        </div>

        {/* Stats Cards */}
        <div className="stats-column">
          <div className="stat-card glass-card">
            <span className="stat-label">GROSS VOLUME</span>
            <span className="stat-value">$865,741.00</span>
          </div>
          <div className="stat-card glass-card">
            <div className="stat-icon"><RefreshCw size={16} /></div>
            <span className="stat-label">NET VOLUME</span>
            <span className="stat-value">$475,744.00</span>
          </div>
          <div className="stat-card glass-card">
            <span className="stat-label">PER CUSTOMER</span>
            <span className="stat-value">$747,985.00</span>
          </div>
        </div>
      </div>

      {/* Middle Row */}
      <div className="middle-row">
        {/* Chart */}
        <div className="chart-card glass-card">
          <div className="chart-header">
            <div className="chart-title">
              <span>Payment Activity</span>
              <Info size={14} className="info-icon" />
            </div>
            <div className="chart-filter">
              <Calendar size={14} />
              <span>This Year</span>
              <ChevronDown size={14} />
            </div>
          </div>
          <div className="chart-container">
            <ResponsiveContainer width="100%" height={260}>
              <AreaChart data={mockChartData}>
                <defs>
                  <linearGradient id="colorActivity" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#a855f7" stopOpacity={0.3}/>
                    <stop offset="95%" stopColor="#a855f7" stopOpacity={0}/>
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" vertical={false} />
                <XAxis dataKey="name" axisLine={false} tickLine={false} tick={{ fill: '#6b6b80', fontSize: 11 }} />
                <YAxis axisLine={false} tickLine={false} tick={{ fill: '#6b6b80', fontSize: 11 }} tickFormatter={(v) => `$${v}`} />
                <Tooltip 
                  contentStyle={{ background: '#1e1e32', border: '1px solid rgba(255,255,255,0.1)', borderRadius: 8 }}
                  labelStyle={{ color: '#fff' }}
                />
                <Area type="monotone" dataKey="value" stroke="#a855f7" strokeWidth={2} fill="url(#colorActivity)" />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Pie Chart */}
        <div className="pie-card glass-card">
          <div className="chart-header">
            <span>Balance Details</span>
            <Info size={14} className="info-icon" />
          </div>
          <div className="pie-container">
            <ResponsiveContainer width="100%" height={180}>
              <PieChart>
                <Pie
                  data={pieData}
                  cx="50%"
                  cy="50%"
                  innerRadius={50}
                  outerRadius={75}
                  dataKey="value"
                  strokeWidth={0}
                >
                  {pieData.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={entry.color} />
                  ))}
                </Pie>
              </PieChart>
            </ResponsiveContainer>
            <div className="pie-center">100%</div>
          </div>
          <div className="pie-legend">
            {pieData.map((item, i) => (
              <div key={i} className="legend-item">
                <span className="legend-dot" style={{ background: item.color }}></span>
                <span>{item.name}</span>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Table */}
      <div className="table-card glass-card">
        <div className="table-header">
          <span>Payment History</span>
          <Info size={14} className="info-icon" />
        </div>
        <table className="data-table">
          <thead>
            <tr>
              <th>Members</th>
              <th>Invoice</th>
              <th>Payments Details</th>
              <th>Date</th>
              <th>AApprox</th>
              <th>Status</th>
            </tr>
          </thead>
          <tbody>
            {mockTransactions.map((tx) => (
              <tr key={tx.id}>
                <td>
                  <div className="member-cell">
                    <div className="member-avatar">{tx.name[0]}</div>
                    <div className="member-info">
                      <span className="member-name">{tx.name}</span>
                      <span className="member-country">{tx.country}</span>
                    </div>
                  </div>
                </td>
                <td className="text-muted">{tx.invoice}</td>
                <td className="text-muted">{tx.type}</td>
                <td className="text-muted">{tx.date}</td>
                <td>{tx.amount}</td>
                <td>
                  <span className={`status-badge ${tx.status.toLowerCase()}`}>{tx.status}</span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

export default Dashboard;
