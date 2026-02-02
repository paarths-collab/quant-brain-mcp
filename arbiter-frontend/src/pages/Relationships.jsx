import { useState } from 'react';
import { Search, Building2, TrendingUp, Users, Package } from 'lucide-react';
import { peersAPI } from '../api';
import './Relationships.css';

function Relationships() {
  const [symbol, setSymbol] = useState('');
  const [searchSymbol, setSearchSymbol] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [data, setData] = useState({
    competitors: [],
    suppliers: [],
    customers: [],
  });

  const handleSearch = async (e) => {
    e.preventDefault();
    if (!symbol.trim()) return;

    setLoading(true);
    setError(null);
    setSearchSymbol(symbol.toUpperCase());

    try {
      const response = await peersAPI.get(symbol);
      
      // For now, we only have competitors from the API
      // Suppliers and customers would come from additional data sources
      const competitors = response.data || [];
      
      setData({
        competitors,
        suppliers: [], // Future: Add supplier data
        customers: [], // Future: Add customer data
      });
    } catch (err) {
      console.error('Fetch error:', err);
      setError('Failed to fetch stock relationships. Please try again.');
      setData({ competitors: [], suppliers: [], customers: [] });
    } finally {
      setLoading(false);
    }
  };

  const formatMarketCap = (marketCap) => {
    if (!marketCap) return 'N/A';
    const num = parseFloat(marketCap);
    if (isNaN(num)) return 'N/A';
    
    if (num >= 1e12) return `$${(num / 1e12).toFixed(2)}T`;
    if (num >= 1e9) return `$${(num / 1e9).toFixed(2)}B`;
    if (num >= 1e6) return `$${(num / 1e6).toFixed(2)}M`;
    if (num >= 1e3) return `$${(num / 1e3).toFixed(2)}K`;
    return `$${num.toFixed(2)}`;
  };

  const formatPrice = (price) => {
    if (!price) return 'N/A';
    const num = parseFloat(price);
    return isNaN(num) ? 'N/A' : `$${num.toFixed(2)}`;
  };

  const renderTable = (items, title, icon) => {
  const Icon = icon;

  return (
    <div className="relationship-section">
      <div className="section-header">
        <Icon size={20} />
        <h3>{title}</h3>
        <span className="count">{items.length} companies</span>
      </div>

      {items.length === 0 ? (
        <div className="empty-state">
          <p>No {title.toLowerCase()} data available</p>
        </div>
      ) : (
        <div className="table-container">
          <table className="relationships-table">
            <thead>
              <tr>
                <th>Symbol</th>
                <th>Company Name</th>
                <th>Price</th>
                <th>Market Cap</th>
              </tr>
            </thead>
            <tbody>
              {items.map((item, idx) => (
                <tr key={idx}>
                  <td className="symbol-cell">
                    <span className="symbol-badge">{item.symbol}</span>
                  </td>
                  <td className="company-name">{item.companyName || 'N/A'}</td>
                  <td className="price-cell">{formatPrice(item.price)}</td>
                  <td className="marketcap-cell">
                    {formatMarketCap(item.marketCap)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
};

  return (
    <div className="relationships-container">
      <div className="search-section">
        <h1>Stock Relationships</h1>
        <form onSubmit={handleSearch} className="search-form">
          <div className="search-input-container">
            <Search size={20} className="search-icon" />
            <input
              type="text"
              value={symbol}
              onChange={(e) => setSymbol(e.target.value)}
              placeholder="Enter stock symbol (e.g., AAPL)"
              className="search-input"
            />
            <button type="submit" disabled={loading} className="search-button">
              {loading ? 'Searching...' : 'Search'}
            </button>
          </div>
        </form>
        {error && <div className="error-message">{error}</div>}
      </div>

      <div className="results-section">
        {searchSymbol && (
          <div className="searched-symbol">
            Showing relationships for: <strong>{searchSymbol}</strong>
          </div>
        )}
        
        {renderTable(data.competitors, 'Competitors', TrendingUp)}
        {renderTable(data.suppliers, 'Suppliers', Package)}
        {renderTable(data.customers, 'Customers', Users)}
      </div>
    </div>
  );
}

export default Relationships;
