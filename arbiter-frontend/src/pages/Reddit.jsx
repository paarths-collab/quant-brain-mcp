import { useState, useEffect } from 'react';
import { Search, TrendingUp, TrendingDown, MessageCircle, ArrowUpCircle, Clock, ExternalLink, Filter, RefreshCw } from 'lucide-react';
import { socialAPI } from '../api';
import './Reddit.css';

const subreddits = [
  { name: 'All', icon: '🌐' },
  { name: 'wallstreetbets', icon: '🦍' },
  { name: 'stocks', icon: '📈' },
  { name: 'IndianStreetBets', icon: '🇮🇳' },
  { name: 'investing', icon: '💼' },
];

const defaultTickers = [
  { symbol: 'NVDA', change: 0, sentiment: 'neutral' },
  { symbol: 'AAPL', change: 0, sentiment: 'neutral' },
  { symbol: 'TSLA', change: 0, sentiment: 'neutral' },
  { symbol: 'RELIANCE', change: 0, sentiment: 'neutral' },
  { symbol: 'TCS', change: 0, sentiment: 'neutral' },
];

function Reddit() {
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedSubreddit, setSelectedSubreddit] = useState('All');
  const [sentimentFilter, setSentimentFilter] = useState('all');
  const [isLoading, setIsLoading] = useState(false);
  const [posts, setPosts] = useState([]);
  const [trendingTickers, setTrendingTickers] = useState(defaultTickers);
  const [error, setError] = useState(null);

  // Fetch posts from backend API
  const fetchPosts = async (ticker = null) => {
    setIsLoading(true);
    setError(null);
    
    try {
      const subreddit = selectedSubreddit === 'All' ? 'wallstreetbets' : selectedSubreddit;
      const response = await socialAPI.getReddit(subreddit);
      
      if (response.data) {
        let fetchedPosts = response.data.posts || response.data || [];
        
        // Transform API response to our format
        fetchedPosts = fetchedPosts.map((post, idx) => ({
          id: post.id || idx,
          subreddit: post.subreddit || subreddit,
          title: post.title,
          author: post.author || 'anonymous',
          upvotes: post.score || post.upvotes || 0,
          comments: post.num_comments || post.comments || 0,
          time: post.created_utc ? formatTime(post.created_utc) : 'recently',
          sentiment: post.sentiment || 'neutral',
          tickers: post.tickers || extractTickers(post.title),
          flair: post.flair || post.link_flair_text || '',
          url: post.url || post.permalink || '#'
        }));
        
        // Filter by search query
        if (ticker || searchQuery) {
          const query = (ticker || searchQuery).toUpperCase();
          fetchedPosts = fetchedPosts.filter(post => 
            post.tickers.some(t => t.includes(query)) ||
            post.title.toUpperCase().includes(query)
          );
        }
        
        // Filter by sentiment
        if (sentimentFilter !== 'all') {
          fetchedPosts = fetchedPosts.filter(post => post.sentiment === sentimentFilter);
        }
        
        setPosts(fetchedPosts);
        
        // Update trending tickers based on posts
        updateTrendingTickers(fetchedPosts);
      }
    } catch (err) {
      console.error('Reddit fetch error:', err);
      setError('Failed to load Reddit posts. Make sure the backend is running.');
      setPosts([]);
    } finally {
      setIsLoading(false);
    }
  };

  // Extract ticker symbols from post title
  const extractTickers = (title) => {
    const matches = title.match(/\$([A-Z]{1,5})/g) || [];
    return matches.map(m => m.replace('$', ''));
  };

  // Format timestamp
  const formatTime = (timestamp) => {
    const seconds = Math.floor(Date.now() / 1000 - timestamp);
    if (seconds < 60) return 'just now';
    if (seconds < 3600) return `${Math.floor(seconds / 60)} min ago`;
    if (seconds < 86400) return `${Math.floor(seconds / 3600)} hours ago`;
    return `${Math.floor(seconds / 86400)} days ago`;
  };

  // Update trending tickers from posts
  const updateTrendingTickers = (posts) => {
    const tickerCounts = {};
    posts.forEach(post => {
      post.tickers.forEach(ticker => {
        tickerCounts[ticker] = (tickerCounts[ticker] || 0) + 1;
      });
    });
    
    const sorted = Object.entries(tickerCounts)
      .sort((a, b) => b[1] - a[1])
      .slice(0, 6)
      .map(([symbol, count]) => ({
        symbol,
        change: 0,
        sentiment: 'neutral',
        mentions: count
      }));
    
    if (sorted.length > 0) {
      setTrendingTickers(sorted);
    }
  };

  useEffect(() => {
    fetchPosts();
  }, [selectedSubreddit, sentimentFilter]);

  const handleSearch = (e) => {
    e.preventDefault();
    fetchPosts(searchQuery);
  };

  const handleTickerClick = (ticker) => {
    setSearchQuery(ticker);
    fetchPosts(ticker);
  };

  const handleRefresh = () => {
    setSearchQuery('');
    fetchPosts();
  };

  const formatUpvotes = (num) => {
    if (num >= 1000) return (num / 1000).toFixed(1) + 'K';
    return num;
  };

  return (
    <div className="reddit-page">
      {/* Header */}
      <div className="reddit-header">
        <div>
          <h1>📰 Reddit Feed</h1>
          <p>Latest stock market discussions from Reddit</p>
        </div>
        <div className="header-actions">
          <button className="refresh-btn" onClick={handleRefresh}>
            <RefreshCw size={16} className={isLoading ? 'spinning' : ''} />
            Refresh
          </button>
        </div>
      </div>

      {/* Search & Filters */}
      <div className="filters-section">
        <form className="search-form" onSubmit={handleSearch}>
          <Search size={18} />
          <input 
            type="text" 
            placeholder="Search ticker or keyword (e.g. AAPL, BTC, RELIANCE)..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
          />
          <button type="submit">Search</button>
        </form>
      </div>

      {/* Subreddit Tabs */}
      <div className="subreddit-tabs">
        {subreddits.map((sub) => (
          <button
            key={sub.name}
            className={selectedSubreddit === sub.name ? 'active' : ''}
            onClick={() => setSelectedSubreddit(sub.name)}
          >
            <span>{sub.icon}</span>
            {sub.name === 'All' ? 'All Feeds' : `r/${sub.name}`}
          </button>
        ))}
      </div>

      <div className="reddit-layout">
        {/* Posts Feed */}
        <div className="posts-feed">
          {isLoading ? (
            <div className="loading-state">
              <RefreshCw size={32} className="spinning" />
              <p>Loading posts...</p>
            </div>
          ) : posts.length === 0 ? (
            <div className="empty-state">
              <Search size={48} />
              <h3>No posts found</h3>
              <p>Try a different search term or filter</p>
            </div>
          ) : (
            posts.map((post) => (
              <div key={post.id} className="post-card">
                <div className="post-votes">
                  <ArrowUpCircle size={20} />
                  <span>{formatUpvotes(post.upvotes)}</span>
                </div>
                
                <div className="post-content">
                  <div className="post-meta">
                    <span className="subreddit">r/{post.subreddit}</span>
                    <span className="author">u/{post.author}</span>
                    <span className="time"><Clock size={12} /> {post.time}</span>
                    {post.flair && <span className="flair">{post.flair}</span>}
                  </div>
                  
                  <h3 className="post-title">{post.title}</h3>
                  
                  <div className="post-footer">
                    <div className="tickers">
                      {post.tickers.map((ticker, i) => (
                        <span 
                          key={i} 
                          className="ticker-tag"
                          onClick={() => handleTickerClick(ticker)}
                        >
                          ${ticker}
                        </span>
                      ))}
                    </div>
                    
                    <div className="post-stats">
                      <span className={`sentiment ${post.sentiment}`}>
                        {post.sentiment === 'bullish' ? '🟢 Bullish' : 
                         post.sentiment === 'bearish' ? '🔴 Bearish' : '⚪ Neutral'}
                      </span>
                      <span className="comments">
                        <MessageCircle size={14} />
                        {post.comments}
                      </span>
                      <a href={post.url} className="external-link">
                        <ExternalLink size={14} />
                      </a>
                    </div>
                  </div>
                </div>
              </div>
            ))
          )}
        </div>

        {/* Sidebar */}
        <div className="reddit-sidebar">
          {/* Trending Tickers */}
          <div className="sidebar-card">
            <h3>🔥 Trending Tickers</h3>
            <div className="trending-list">
              {trendingTickers.map((ticker, i) => (
                <div 
                  key={i} 
                  className="trending-item"
                  onClick={() => handleTickerClick(ticker.symbol)}
                >
                  <span className="ticker-symbol">${ticker.symbol}</span>
                  {ticker.mentions && (
                    <span className="ticker-mentions">{ticker.mentions} mentions</span>
                  )}
                </div>
              ))}
            </div>
          </div>

          {/* Quick Filters */}
          <div className="sidebar-card">
            <h3>⚡ Quick Search</h3>
            <div className="quick-filters">
              <button onClick={() => handleTickerClick('AAPL')}>$AAPL</button>
              <button onClick={() => handleTickerClick('TSLA')}>$TSLA</button>
              <button onClick={() => handleTickerClick('NVDA')}>$NVDA</button>
              <button onClick={() => handleTickerClick('BTC')}>$BTC</button>
              <button onClick={() => handleTickerClick('ETH')}>$ETH</button>
              <button onClick={() => handleTickerClick('RELIANCE')}>$RELIANCE</button>
              <button onClick={() => handleTickerClick('TCS')}>$TCS</button>
              <button onClick={() => handleTickerClick('GME')}>$GME</button>
            </div>
          </div>

          {/* Info */}
          <div className="sidebar-card info">
            <h3>ℹ️ About</h3>
            <p>Real-time aggregated posts from popular stock and crypto subreddits. Sentiment analysis powered by AI.</p>
          </div>
        </div>
      </div>
    </div>
  );
}

export default Reddit;
