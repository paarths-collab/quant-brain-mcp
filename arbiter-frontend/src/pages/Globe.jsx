import { useState, useEffect } from 'react';
import { TrendingUp, TrendingDown, Globe as GlobeIcon, RefreshCw, Droplet, DollarSign, Percent, Briefcase, ShoppingCart, BarChart3, Building2, Users } from 'lucide-react';
import { treemapAPI, fredAPI } from '../api';
import './Globe.css';

// Global market indices with their yfinance symbols
const globalIndices = [
  { name: 'NYSE (S&P 500)', symbol: '^GSPC', city: 'New York', country: 'USA', currency: '$' },
  { name: 'NASDAQ', symbol: '^IXIC', city: 'New York', country: 'USA', currency: '$' },
  { name: 'DOW JONES', symbol: '^DJI', city: 'New York', country: 'USA', currency: '$' },
  { name: 'NSE (NIFTY)', symbol: '^NSEI', city: 'Mumbai', country: 'India', currency: '₹' },
  { name: 'BSE (SENSEX)', symbol: '^BSESN', city: 'Mumbai', country: 'India', currency: '₹' },
  { name: 'FTSE 100', symbol: '^FTSE', city: 'London', country: 'UK', currency: '£' },
  { name: 'DAX', symbol: '^GDAXI', city: 'Frankfurt', country: 'Germany', currency: '€' },
  { name: 'NIKKEI 225', symbol: '^N225', city: 'Tokyo', country: 'Japan', currency: '¥' },
  { name: 'HANG SENG', symbol: '^HSI', city: 'Hong Kong', country: 'Hong Kong', currency: 'HK$' },
  { name: 'SSE Composite', symbol: '000001.SS', city: 'Shanghai', country: 'China', currency: '¥' },
  { name: 'CAC 40', symbol: '^FCHI', city: 'Paris', country: 'France', currency: '€' },
  { name: 'ASX 200', symbol: '^AXJO', city: 'Sydney', country: 'Australia', currency: 'A$' },
];

// Comprehensive FRED economic series
const fredSeries = {
  gdp: [
    { id: 'GDP', name: 'GDP (Nominal)', icon: BarChart3, unit: 'B' },
    { id: 'GDPC1', name: 'GDP (Real)', icon: BarChart3, unit: 'B' },
    { id: 'PCEC', name: 'Personal Consumption', icon: ShoppingCart, unit: 'B' },
    { id: 'GPDI', name: 'Gross Investment', icon: Building2, unit: 'B' },
  ],
  labor: [
    { id: 'UNRATE', name: 'Unemployment Rate', icon: Users, unit: '%' },
    { id: 'CIVPART', name: 'Labor Force Participation', icon: Users, unit: '%' },
    { id: 'PAYEMS', name: 'Nonfarm Payrolls', icon: Briefcase, unit: 'K' },
    { id: 'ICSA', name: 'Initial Jobless Claims', icon: Users, unit: 'K' },
  ],
  inflation: [
    { id: 'CPIAUCSL', name: 'CPI (All Items)', icon: ShoppingCart, unit: '' },
    { id: 'PCEPI', name: 'PCE Price Index', icon: ShoppingCart, unit: '' },
    { id: 'CPILFESL', name: 'Core CPI', icon: ShoppingCart, unit: '' },
    { id: 'PPIFIS', name: 'Producer Price Index', icon: Building2, unit: '' },
  ],
  finance: [
    { id: 'DGS10', name: '10Y Treasury', icon: Percent, unit: '%' },
    { id: 'DGS2', name: '2Y Treasury', icon: Percent, unit: '%' },
    { id: 'FEDFUNDS', name: 'Fed Funds Rate', icon: Percent, unit: '%' },
    { id: 'VIXCLS', name: 'VIX Volatility', icon: TrendingUp, unit: '' },
    { id: 'SP500', name: 'S&P 500 Index', icon: TrendingUp, unit: '' },
  ],
  commodities: [
    { id: 'DCOILWTICO', name: 'WTI Crude Oil', icon: Droplet, unit: '$/bbl' },
    { id: 'DCOILBRENTEU', name: 'Brent Oil', icon: Droplet, unit: '$/bbl' },
    { id: 'GOLDPMGBD228NLBM', name: 'Gold Price', icon: DollarSign, unit: '$/oz' },
    { id: 'GASREGW', name: 'US Gas Price', icon: Droplet, unit: '$/gal' },
  ],
  forex: [
    { id: 'DEXUSEU', name: 'USD/EUR', icon: DollarSign, unit: '' },
    { id: 'DEXJPUS', name: 'JPY/USD', icon: DollarSign, unit: '' },
    { id: 'DEXUSUK', name: 'USD/GBP', icon: DollarSign, unit: '' },
    { id: 'DEXCHUS', name: 'CNY/USD', icon: DollarSign, unit: '' },
  ],
};

function Globe() {
  const [markets, setMarkets] = useState([]);
  const [fredData, setFredData] = useState({ gdp: [], labor: [], inflation: [], finance: [], commodities: [], forex: [] });
  const [selectedMarket, setSelectedMarket] = useState(null);
  const [loading, setLoading] = useState(true);
  const [fredLoading, setFredLoading] = useState(true);
  const [error, setError] = useState(null);

  const fetchFredData = async () => {
    setFredLoading(true);
    try {
      const allSeries = [
        ...fredSeries.gdp.map(s => s.id),
        ...fredSeries.labor.map(s => s.id),
        ...fredSeries.inflation.map(s => s.id),
        ...fredSeries.finance.map(s => s.id),
        ...fredSeries.commodities.map(s => s.id),
        ...fredSeries.forex.map(s => s.id),
      ];
      
      const response = await fredAPI.getLatest(allSeries);
      const dataMap = {};
      
      if (response.data?.data) {
        response.data.data.forEach(item => {
          dataMap[item.series_id] = item.value;
        });
      }
      
      setFredData({
        gdp: fredSeries.gdp.map(s => ({ ...s, value: dataMap[s.id] })),
        labor: fredSeries.labor.map(s => ({ ...s, value: dataMap[s.id] })),
        inflation: fredSeries.inflation.map(s => ({ ...s, value: dataMap[s.id] })),
        finance: fredSeries.finance.map(s => ({ ...s, value: dataMap[s.id] })),
        commodities: fredSeries.commodities.map(s => ({ ...s, value: dataMap[s.id] })),
        forex: fredSeries.forex.map(s => ({ ...s, value: dataMap[s.id] })),
      });
    } catch (err) {
      console.error('FRED fetch error:', err);
    } finally {
      setFredLoading(false);
    }
  };

  const fetchMarketData = async () => {
    setLoading(true);
    setError(null);
    
    try {
      const promises = globalIndices.map(async (idx) => {
        try {
          const response = await treemapAPI.getStockDetails(idx.symbol, 'us');
          const data = response.data || {};
          // API returns nested structure: data.price.current, data.price.change_percent, data.valuation.market_cap
          const priceData = data.price || {};
          const valuationData = data.valuation || {};
          return {
            ...idx,
            value: typeof priceData.current === 'number' ? priceData.current : 0,
            change: typeof priceData.change_percent === 'number' ? priceData.change_percent : 0,
            marketCap: typeof valuationData.market_cap === 'number' ? valuationData.market_cap : null,
          };
        } catch {
          return { ...idx, value: 0, change: 0 };
        }
      });
      
      const results = await Promise.all(promises);
      setMarkets(results);
    } catch (err) {
      console.error('Market fetch error:', err);
      setError('Failed to fetch market data');
      // Fallback to static data
      setMarkets(globalIndices.map(idx => ({ ...idx, value: 0, change: 0 })));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchMarketData();
    fetchFredData();
    // Refresh every 5 minutes
    const interval = setInterval(() => {
      fetchMarketData();
      fetchFredData();
    }, 5 * 60 * 1000);
    return () => clearInterval(interval);
  }, []);

  const formatValue = (value) => {
    if (!value || value === 0) return 'N/A';
    // Handle if value is an object
    if (typeof value === 'object') {
      return 'N/A';
    }
    if (typeof value === 'number') {
      return value.toLocaleString(undefined, { maximumFractionDigits: 2 });
    }
    return String(value);
  };

  return (
    <div className="globe-page">
      <div className="globe-header">
        <div>
          <h1>Global Markets</h1>
          <p>World stock exchanges overview</p>
        </div>
        <button className="refresh-btn" onClick={fetchMarketData} disabled={loading}>
          <RefreshCw size={16} className={loading ? 'spin' : ''} />
        </button>
      </div>

      {error && <div className="error-banner">{error}</div>}

      {selectedMarket && (
        <div className="market-popup">
          <button className="close-btn" onClick={() => setSelectedMarket(null)}>×</button>
          <h3>{selectedMarket.name}</h3>
          <span className="city">{selectedMarket.city}, {selectedMarket.country}</span>
          <div className="market-stats">
            <div>
              <span className="label">Value</span>
              <span className="value">{formatValue(selectedMarket.value)}</span>
            </div>
            <div>
              <span className="label">Today</span>
              <span className={`value ${selectedMarket.change >= 0 ? 'positive' : 'negative'}`}>
                {selectedMarket.change >= 0 ? '+' : ''}{(selectedMarket.change || 0).toFixed(2)}%
              </span>
            </div>
          </div>
        </div>
      )}

      <div className="markets-list">
        <h3>Major Exchanges</h3>
        {loading ? (
          <div className="loading-placeholder">Loading global markets...</div>
        ) : (
          <div className="markets-grid">
            {markets.map((market, i) => (
              <div 
                key={i} 
                className={`market-item ${selectedMarket?.name === market.name ? 'selected' : ''}`}
                onClick={() => setSelectedMarket(market)}
              >
                <div className="market-item-header">
                  <span className="market-name">{market.name}</span>
                  <span className={`market-change ${market.change >= 0 ? 'positive' : 'negative'}`}>
                    {market.change >= 0 ? <TrendingUp size={12} /> : <TrendingDown size={12} />}
                    {market.change >= 0 ? '+' : ''}{(market.change || 0).toFixed(2)}%
                  </span>
                </div>
                <span className="market-city">{market.city}</span>
                <span className="market-cap">{formatValue(market.value)}</span>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* FRED Economic Data */}
      <div className="fred-sections">
        <div className="fred-section">
          <h3><BarChart3 size={16} /> GDP & National Accounts</h3>
          <div className="fred-grid">
            {fredLoading ? (
              <div className="loading-placeholder">Loading...</div>
            ) : (
              fredData.gdp.map((item, i) => {
                const Icon = item.icon;
                return (
                  <div key={i} className="fred-item">
                    <Icon size={14} />
                    <div className="fred-info">
                      <span className="fred-name">{item.name}</span>
                      <span className="fred-value">
                        {item.value ? `${(item.value / 1000).toFixed(2)}T ${item.unit}` : 'N/A'}
                      </span>
                    </div>
                  </div>
                );
              })
            )}
          </div>
        </div>

        <div className="fred-section">
          <h3><Users size={16} /> Labor Markets</h3>
          <div className="fred-grid">
            {fredLoading ? (
              <div className="loading-placeholder">Loading...</div>
            ) : (
              fredData.labor.map((item, i) => {
                const Icon = item.icon;
                return (
                  <div key={i} className="fred-item">
                    <Icon size={14} />
                    <div className="fred-info">
                      <span className="fred-name">{item.name}</span>
                      <span className="fred-value">
                        {item.value ? `${item.value.toFixed(1)}${item.unit}` : 'N/A'}
                      </span>
                    </div>
                  </div>
                );
              })
            )}
          </div>
        </div>

        <div className="fred-section">
          <h3><ShoppingCart size={16} /> Prices & Inflation</h3>
          <div className="fred-grid">
            {fredLoading ? (
              <div className="loading-placeholder">Loading...</div>
            ) : (
              fredData.inflation.map((item, i) => {
                const Icon = item.icon;
                return (
                  <div key={i} className="fred-item">
                    <Icon size={14} />
                    <div className="fred-info">
                      <span className="fred-name">{item.name}</span>
                      <span className="fred-value">
                        {item.value ? item.value.toFixed(2) : 'N/A'}
                      </span>
                    </div>
                  </div>
                );
              })
            )}
          </div>
        </div>

        <div className="fred-section">
          <h3><Percent size={16} /> Finance & Markets</h3>
          <div className="fred-grid">
            {fredLoading ? (
              <div className="loading-placeholder">Loading...</div>
            ) : (
              fredData.finance.map((item, i) => {
                const Icon = item.icon;
                return (
                  <div key={i} className="fred-item">
                    <Icon size={14} />
                    <div className="fred-info">
                      <span className="fred-name">{item.name}</span>
                      <span className="fred-value">
                        {item.value ? `${item.value.toFixed(2)}${item.unit}` : 'N/A'}
                      </span>
                    </div>
                  </div>
                );
              })
            )}
          </div>
        </div>

        <div className="fred-section">
          <h3><Droplet size={16} /> Commodities</h3>
          <div className="fred-grid">
            {fredLoading ? (
              <div className="loading-placeholder">Loading...</div>
            ) : (
              fredData.commodities.map((item, i) => {
                const Icon = item.icon;
                return (
                  <div key={i} className="fred-item">
                    <Icon size={14} />
                    <div className="fred-info">
                      <span className="fred-name">{item.name}</span>
                      <span className="fred-value">
                        {item.value ? `${item.value.toFixed(2)} ${item.unit}` : 'N/A'}
                      </span>
                    </div>
                  </div>
                );
              })
            )}
          </div>
        </div>

        <div className="fred-section">
          <h3><DollarSign size={16} /> International Forex</h3>
          <div className="fred-grid">
            {fredLoading ? (
              <div className="loading-placeholder">Loading...</div>
            ) : (
              fredData.forex.map((item, i) => {
                const Icon = item.icon;
                return (
                  <div key={i} className="fred-item">
                    <Icon size={14} />
                    <div className="fred-info">
                      <span className="fred-name">{item.name}</span>
                      <span className="fred-value">
                        {item.value ? item.value.toFixed(4) : 'N/A'}
                      </span>
                    </div>
                  </div>
                );
              })
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

export default Globe;
