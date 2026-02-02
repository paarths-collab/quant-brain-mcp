import { useState, useEffect } from 'react';
import { TrendingUp, TrendingDown, Activity, DollarSign, IndianRupee, RefreshCw } from 'lucide-react';
import { AreaChart, Area, XAxis, YAxis, Tooltip, ResponsiveContainer } from 'recharts';
import { formatCurrency, getCurrencySymbol, treemapAPI } from '../api';
import './Dashboard.css';

// Default watchlist symbols
const watchlistSymbols = {
  IN: ['RELIANCE.NS', 'TCS.NS', 'HDFCBANK.NS', 'INFY.NS'],
  US: ['AAPL', 'MSFT', 'GOOGL', 'NVDA']
};

// Index symbols for each market
const indexSymbols = {
  IN: ['^NSEI', '^BSESN', '^NSEBANK'],
  US: ['^GSPC', '^IXIC', '^DJI']
};

const indexNames = {
  '^NSEI': 'NIFTY 50',
  '^BSESN': 'SENSEX',
  '^NSEBANK': 'NIFTY BANK',
  '^GSPC': 'S&P 500',
  '^IXIC': 'NASDAQ',
  '^DJI': 'DOW JONES'
};

function Dashboard() {
  const [market, setMarket] = useState('IN');
  const [holdings, setHoldings] = useState([]);
  const [indices, setIndices] = useState([]);
  const [portfolioData, setPortfolioData] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  
  const symbol = getCurrencySymbol(market);

  // Fetch holdings data from yfinance via treemap API
  const fetchHoldings = async () => {
    try {
      const symbols = watchlistSymbols[market];
      const promises = symbols.map(sym => 
        treemapAPI.getStockDetails(sym, market === 'IN' ? 'india' : 'us')
          .catch(() => null)
      );
      
      const results = await Promise.all(promises);
      const validResults = results
        .filter(r => r?.data && !r.data.error)
        .map(r => ({
          symbol: r.data.symbol,
          name: r.data.name || r.data.symbol,
          price: r.data.price || 0,
          change: r.data.change_percent || 0,
          value: (r.data.price || 0) * 100,
        }));
      
      setHoldings(validResults);
    } catch (err) {
      console.error('Holdings fetch error:', err);
    }
  };

  // Fetch indices data
  const fetchIndices = async () => {
    try {
      const symbols = indexSymbols[market];
      const promises = symbols.map(idx => 
        treemapAPI.getStockDetails(idx, market === 'IN' ? 'india' : 'us')
          .then(r => ({
            name: indexNames[idx] || idx,
            value: r.data?.price || 0,
            change: r.data?.change_percent || 0,
          }))
          .catch(() => ({ name: indexNames[idx] || idx, value: 0, change: 0 }))
      );
      
      const results = await Promise.all(promises);
      setIndices(results);
    } catch (err) {
      console.error('Indices fetch error:', err);
    }
  };

  // Generate portfolio performance chart data
  const generatePortfolioData = () => {
    const months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
    let baseValue = market === 'IN' ? 1000000 : 100000;
    
    const data = months.map((month) => {
      const change = 1 + (Math.random() * 0.08 - 0.02);
      baseValue = baseValue * change;
      return { date: month, value: Math.round(baseValue) };
    });
    
    setPortfolioData(data);
  };

  // Fetch all data
  const fetchData = async () => {
    setLoading(true);
    setError(null);
    
    try {
      await Promise.all([fetchHoldings(), fetchIndices()]);
      generatePortfolioData();
    } catch (err) {
      setError('Failed to load dashboard data');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, [market]);

  const totalValue = holdings.reduce((sum, h) => sum + h.value, 0);
  const todayChange = holdings.reduce((sum, h) => sum + (h.value * h.change / 100), 0);
  const totalReturn = portfolioData.length > 1 
    ? ((portfolioData[portfolioData.length - 1]?.value - portfolioData[0]?.value) / portfolioData[0]?.value * 100)
    : 0;

  return (
    <div className="dashboard-page">
      {/* Header */}
      <div className="dash-header">
        <div>
          <h1>Dashboard</h1>
          <p>Portfolio Overview</p>
        </div>
        <div className="header-actions">
          <button className="refresh-btn" onClick={fetchData} disabled={loading}>
            <RefreshCw size={16} className={loading ? 'spin' : ''} />
          </button>
          <div className="market-toggle">
            <button 
              className={market === 'IN' ? 'active' : ''} 
              onClick={() => setMarket('IN')}
            >
              <IndianRupee size={16} /> India
            </button>
            <button 
              className={market === 'US' ? 'active' : ''} 
              onClick={() => setMarket('US')}
            >
              <DollarSign size={16} /> US
            </button>
          </div>
        </div>
      </div>

      {error && <div className="error-banner">{error}</div>}

      {/* Stats Cards */}
      <div className="stats-row">
        <div className="stat-card">
          <div className="stat-icon">
            {market === 'IN' ? <IndianRupee size={20} /> : <DollarSign size={20} />}
          </div>
          <div className="stat-info">
            <span className="stat-label">Total Value</span>
            <span className="stat-value">{formatCurrency(totalValue, market)}</span>
          </div>
        </div>
        <div className="stat-card">
          <div className={`stat-icon ${todayChange >= 0 ? 'positive' : 'negative'}`}>
            {todayChange >= 0 ? <TrendingUp size={20} /> : <TrendingDown size={20} />}
          </div>
          <div className="stat-info">
            <span className="stat-label">Today's {todayChange >= 0 ? 'Gain' : 'Loss'}</span>
            <span className={`stat-value ${todayChange >= 0 ? 'positive' : 'negative'}`}>
              {todayChange >= 0 ? '+' : ''}{formatCurrency(Math.abs(todayChange), market)}
            </span>
          </div>
        </div>
        <div className="stat-card">
          <div className={`stat-icon ${totalReturn >= 0 ? 'positive' : 'negative'}`}>
            <Activity size={20} />
          </div>
          <div className="stat-info">
            <span className="stat-label">Total Return</span>
            <span className={`stat-value ${totalReturn >= 0 ? 'positive' : 'negative'}`}>
              {totalReturn >= 0 ? '+' : ''}{totalReturn.toFixed(1)}%
            </span>
          </div>
        </div>
      </div>

      {/* Main Content */}
      <div className="dash-grid">
        {/* Portfolio Chart */}
        <div className="chart-card">
          <h3>Portfolio Performance</h3>
          <div className="chart-container">
            <ResponsiveContainer width="100%" height={300}>
              <AreaChart data={portfolioData}>
                <defs>
                  <linearGradient id="colorValue" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.3}/>
                    <stop offset="95%" stopColor="#3b82f6" stopOpacity={0}/>
                  </linearGradient>
                </defs>
                <XAxis dataKey="date" axisLine={false} tickLine={false} tick={{ fill: '#71717a', fontSize: 11 }} />
                <YAxis axisLine={false} tickLine={false} tick={{ fill: '#71717a', fontSize: 11 }} tickFormatter={(v) => `${symbol}${(v/1000).toFixed(0)}K`} />
                <Tooltip 
                  contentStyle={{ background: '#0d0d0d', border: '1px solid rgba(255,255,255,0.1)', borderRadius: 8 }}
                  formatter={(value) => [formatCurrency(value, market), 'Value']}
                />
                <Area type="monotone" dataKey="value" stroke="#3b82f6" strokeWidth={2} fill="url(#colorValue)" />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Indices */}
        <div className="indices-card">
          <h3>Market Indices</h3>
          <div className="indices-list">
            {loading ? (
              <div className="loading-placeholder">Loading indices...</div>
            ) : indices.map((index, i) => (
              <div key={i} className="index-item">
                <div className="index-info">
                  <span className="index-name">{index.name}</span>
                  <span className="index-value">{index.value.toLocaleString()}</span>
                </div>
                <span className={`index-change ${index.change >= 0 ? 'positive' : 'negative'}`}>
                  {index.change >= 0 ? '+' : ''}{(index.change || 0).toFixed(2)}%
                </span>
              </div>
            ))}
          </div>
        </div>

        {/* Holdings */}
        <div className="holdings-card">
          <h3>Watchlist</h3>
          {loading ? (
            <div className="loading-placeholder">Loading watchlist...</div>
          ) : (
            <table className="holdings-table">
              <thead>
                <tr>
                  <th>Symbol</th>
                  <th>Price</th>
                  <th>Change</th>
                  <th>Value</th>
                </tr>
              </thead>
              <tbody>
                {holdings.map((stock, i) => (
                  <tr key={i}>
                    <td>
                      <div className="stock-cell">
                        <span className="stock-symbol">{stock.symbol.split('.')[0]}</span>
                        <span className="stock-name">{stock.name}</span>
                      </div>
                    </td>
                    <td>{formatCurrency(stock.price, market)}</td>
                    <td className={stock.change >= 0 ? 'positive' : 'negative'}>
                      {stock.change >= 0 ? '+' : ''}{(stock.change || 0).toFixed(2)}%
                    </td>
                    <td>{formatCurrency(stock.value, market)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </div>
    </div>
  );
}

export default Dashboard;
