import { useState, useEffect } from 'react';
import { Search, Brain, TrendingUp, TrendingDown, DollarSign, IndianRupee, FileText, BarChart3, AlertTriangle, CheckCircle, Globe, MessageCircle, ExternalLink, RefreshCw } from 'lucide-react';
import { sentimentAPI, formatCurrency, getCurrencySymbol, formatLargeNumber } from '../api';
import './Research.css';

function Research() {
  const [searchInput, setSearchInput] = useState('');
  const [symbol, setSymbol] = useState('');
  const [market, setMarket] = useState('us'); // 'us' or 'india'
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);
  const [data, setData] = useState(null);
  
  const currencySymbol = data ? getCurrencySymbol(data.market) : '$';
  
  const fetchSentiment = async (sym, mkt) => {
    setIsLoading(true);
    setError(null);
    
    try {
      const response = await sentimentAPI.analyze(sym, mkt);
      setData(response.data);
      setSymbol(response.data.symbol);
    } catch (err) {
      console.error('Sentiment fetch error:', err);
      setError(err.response?.data?.detail || 'Failed to fetch analysis');
      setData(null);
    } finally {
      setIsLoading(false);
    }
  };
  
  const handleSearch = (e) => {
    e.preventDefault();
    const input = searchInput.toUpperCase().trim();
    if (input) {
      fetchSentiment(input, market);
      setSearchInput('');
    }
  };
  
  const handleMarketChange = (newMarket) => {
    setMarket(newMarket);
    if (symbol) {
      // Re-fetch with new market
      const cleanSymbol = symbol.replace('.NS', '').replace('.BO', '');
      fetchSentiment(cleanSymbol, newMarket);
    }
  };
  
  const getSentimentColor = (sentiment) => {
    if (sentiment >= 0.6) return '#22c55e';
    if (sentiment >= 0.4) return '#f59e0b';
    return '#ef4444';
  };
  
  const getRecommendationColor = (rec) => {
    if (!rec) return '#6b7280';
    const r = rec.toUpperCase();
    if (r === 'BUY' || r === 'STRONG BUY' || r === 'STRONG_BUY') return '#22c55e';
    if (r === 'HOLD') return '#f59e0b';
    return '#ef4444';
  };
  
  const getOutlookIcon = (outlook) => {
    if (outlook === 'Bullish') return <TrendingUp size={16} className="text-green" />;
    if (outlook === 'Bearish') return <TrendingDown size={16} className="text-red" />;
    return <span className="text-yellow">—</span>;
  };

  // Default suggestions
  const suggestions = market === 'india' 
    ? ['RELIANCE', 'TCS', 'INFY', 'HDFCBANK', 'ICICIBANK']
    : ['AAPL', 'MSFT', 'GOOGL', 'NVDA', 'TSLA'];

  return (
    <div className="research-page">
      {/* Header */}
      <div className="research-header">
        <div>
          <h1>AI Research</h1>
          <p>Sentiment analysis powered by AI + Reddit</p>
        </div>
        
        {/* Market Toggle */}
        <div className="market-toggle">
          <button 
            className={market === 'us' ? 'active' : ''}
            onClick={() => handleMarketChange('us')}
          >
            <DollarSign size={14} /> US
          </button>
          <button 
            className={market === 'india' ? 'active' : ''}
            onClick={() => handleMarketChange('india')}
          >
            <IndianRupee size={14} /> India
          </button>
        </div>
        
        <form className="search-form" onSubmit={handleSearch}>
          <Search size={18} />
          <input 
            type="text" 
            placeholder={`Search ${market === 'india' ? 'NSE' : 'US'} symbol...`}
            value={searchInput}
            onChange={(e) => setSearchInput(e.target.value)}
          />
          <button type="submit" disabled={isLoading}>
            {isLoading ? <RefreshCw size={14} className="spin" /> : 'Analyze'}
          </button>
        </form>
      </div>

      {/* Quick Suggestions */}
      {!data && !isLoading && (
        <div className="suggestions">
          <span>Try:</span>
          {suggestions.map((s) => (
            <button key={s} onClick={() => fetchSentiment(s, market)}>
              {s}
            </button>
          ))}
        </div>
      )}

      {/* Error State */}
      {error && (
        <div className="error-state">
          <AlertTriangle size={32} />
          <h3>Analysis Failed</h3>
          <p>{error}</p>
        </div>
      )}

      {/* Loading State */}
      {isLoading && (
        <div className="loading-state">
          <Brain size={48} className="pulse" />
          <h3>Analyzing {searchInput || symbol}...</h3>
          <p>Fetching market data, Reddit sentiment & AI analysis</p>
        </div>
      )}

      {/* Results */}
      {data && !isLoading && (
        <div className="research-content">
          {/* Stock Overview */}
          <div className="stock-overview">
            <div className="stock-main">
              <div className="stock-badge">
                {data.market === 'IN' ? <IndianRupee size={14} /> : <DollarSign size={14} />}
                <span>{data.market === 'IN' ? 'NSE' : 'NASDAQ'}</span>
              </div>
              <h2>{data.symbol.split('.')[0]}</h2>
              <span className="stock-name">{data.name}</span>
              <div className="price-section">
                <span className="current-price">{formatCurrency(data.price, data.market)}</span>
                {data.day_change_pct !== undefined && (
                  <span className={`price-change ${data.day_change_pct >= 0 ? 'positive' : 'negative'}`}>
                    {data.day_change_pct >= 0 ? '+' : ''}{data.day_change_pct.toFixed(2)}%
                  </span>
                )}
              </div>
            </div>
            
            <div className="recommendation-box" style={{ borderColor: getRecommendationColor(data.recommendation) }}>
              <span className="rec-label">AI Recommendation</span>
              <span className="rec-value" style={{ color: getRecommendationColor(data.recommendation) }}>
                {data.recommendation || 'HOLD'}
              </span>
              {data.targetPrice && (
                <span className="target-price">Target: {formatCurrency(data.targetPrice, data.market)}</span>
              )}
              {data.confidence && (
                <span className="confidence">Confidence: {(data.confidence * 100).toFixed(0)}%</span>
              )}
            </div>
          </div>

          {/* Sentiment & Metrics */}
          <div className="research-grid">
            <div className="sentiment-card">
              <h3><Brain size={18} /> Sentiment Score</h3>
              <div className="sentiment-display">
                <div className="sentiment-circle" style={{ borderColor: getSentimentColor(data.sentiment) }}>
                  <span style={{ color: getSentimentColor(data.sentiment) }}>
                    {((data.sentiment || 0.5) * 100).toFixed(0)}%
                  </span>
                </div>
                <span className="sentiment-label" style={{ color: getSentimentColor(data.sentiment) }}>
                  {getOutlookIcon(data.outlook)} {data.outlook || 'Neutral'}
                </span>
              </div>
              
              {/* Reddit Stats */}
              {data.reddit_posts_count !== undefined && (
                <div className="reddit-stats">
                  <MessageCircle size={14} />
                  <span>{data.reddit_posts_count} Reddit posts analyzed</span>
                </div>
              )}
            </div>
            
            <div className="metrics-card">
              <h3><BarChart3 size={18} /> Key Metrics</h3>
              <div className="metrics-list">
                <div className="metric-row">
                  <span>P/E Ratio</span>
                  <span>{data.metrics?.pe?.toFixed(2) || '-'}</span>
                </div>
                <div className="metric-row">
                  <span>EPS</span>
                  <span>{data.metrics?.eps ? `${currencySymbol}${data.metrics.eps.toFixed(2)}` : '-'}</span>
                </div>
                <div className="metric-row">
                  <span>Revenue</span>
                  <span>{data.metrics?.revenue || '-'}</span>
                </div>
                <div className="metric-row">
                  <span>Market Cap</span>
                  <span>{data.metrics?.marketCap || '-'}</span>
                </div>
              </div>
            </div>
          </div>

          {/* Summary */}
          <div className="summary-card">
            <h3><FileText size={18} /> AI Summary</h3>
            <p>{data.summary || 'No summary available.'}</p>
            {data.analysis_source && (
              <span className="analysis-source">Source: {data.analysis_source}</span>
            )}
          </div>

          {/* Risks & Catalysts */}
          <div className="analysis-grid">
            <div className="risks-card">
              <h3><AlertTriangle size={18} /> Key Risks</h3>
              <ul>
                {(data.risks || []).map((risk, i) => (
                  <li key={i}>
                    <TrendingDown size={14} />
                    {risk}
                  </li>
                ))}
                {(!data.risks || data.risks.length === 0) && (
                  <li className="empty">No significant risks identified</li>
                )}
              </ul>
            </div>
            
            <div className="catalysts-card">
              <h3><CheckCircle size={18} /> Catalysts</h3>
              <ul>
                {(data.catalysts || []).map((catalyst, i) => (
                  <li key={i}>
                    <TrendingUp size={14} />
                    {catalyst}
                  </li>
                ))}
                {(!data.catalysts || data.catalysts.length === 0) && (
                  <li className="empty">No catalysts identified</li>
                )}
              </ul>
            </div>
          </div>

          {/* Reddit Top Posts */}
          {data.reddit_top_posts && data.reddit_top_posts.length > 0 && (
            <div className="reddit-card">
              <h3><MessageCircle size={18} /> Top Reddit Discussions</h3>
              <div className="reddit-posts">
                {data.reddit_top_posts.slice(0, 5).map((post, i) => (
                  <a 
                    key={i} 
                    href={post.url} 
                    target="_blank" 
                    rel="noopener noreferrer"
                    className="reddit-post"
                  >
                    <span className="post-score">▲ {post.score}</span>
                    <span className="post-title">{post.title}</span>
                    <span className="post-sub">r/{post.subreddit}</span>
                    <ExternalLink size={12} />
                  </a>
                ))}
              </div>
            </div>
          )}

          {/* Timestamp */}
          <div className="timestamp">
            Last updated: {new Date(data.timestamp).toLocaleString()}
          </div>
        </div>
      )}
    </div>
  );
}

export default Research;
