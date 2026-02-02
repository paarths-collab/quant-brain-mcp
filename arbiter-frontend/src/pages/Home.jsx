import { useNavigate } from 'react-router-dom';
import { ArrowRight, TrendingUp, BarChart3, Globe, Zap, Shield, Users, Clock, CheckCircle, Sun, Moon, Plus } from 'lucide-react';
import Hyperspeed from '../components/Hyperspeed';
import { useTheme } from '../context/ThemeContext';
import './Home.css';

const features = [
  { icon: TrendingUp, title: 'Real-time Market Data', desc: 'Live streaming quotes from NSE, BSE and US exchanges' },
  { icon: BarChart3, title: 'Candlestick Charts', desc: 'Professional OHLC charts with 50+ technical indicators' },
  { icon: Globe, title: 'Global Markets', desc: 'Track international markets with interactive visualizations' },
  { icon: Zap, title: 'AI-Powered Research', desc: 'Machine learning driven stock analysis and recommendations' },
  { icon: Shield, title: 'Strategy Backtesting', desc: 'Test 10+ trading strategies against historical data' },
  { icon: Users, title: 'Sector Analysis', desc: 'Interactive treemaps for NIFTY and S&P 500 sectors' },
];

const pricingPlans = [
  {
    name: 'Starter',
    description: 'Everything you need to get started.',
    price: 19,
    features: [
      { name: 'Custom domains', included: true },
      { name: 'Edge content delivery', included: true },
      { name: 'Advanced analytics', included: true },
      { name: 'Quarterly workshops', included: false },
      { name: 'Single sign-on (SSO)', included: false },
      { name: 'Priority phone support', included: false },
    ],
  },
  {
    name: 'Growth',
    description: 'All the extras for your growing team.',
    price: 49,
    popular: true,
    features: [
      { name: 'Custom domains', included: true },
      { name: 'Edge content delivery', included: true },
      { name: 'Advanced analytics', included: true },
      { name: 'Quarterly workshops', included: true },
      { name: 'Single sign-on (SSO)', included: false },
      { name: 'Priority phone support', included: false },
    ],
  },
  {
    name: 'Scale',
    description: 'Added flexibility at scale.',
    price: 99,
    features: [
      { name: 'Custom domains', included: true },
      { name: 'Edge content delivery', included: true },
      { name: 'Advanced analytics', included: true },
      { name: 'Quarterly workshops', included: true },
      { name: 'Single sign-on (SSO)', included: true },
      { name: 'Priority phone support', included: false },
    ],
  },
];

const hyperspeedOptions = {
  onSpeedUp: () => { },
  onSlowDown: () => { },
  distortion: 'turbulentDistortion',
  length: 400,
  roadWidth: 10,
  islandWidth: 2,
  lanesPerRoad: 3,
  fov: 90,
  fovSpeedUp: 150,
  speedUp: 2,
  carLightsFade: 0.4,
  totalSideLightSticks: 50,
  lightPairsPerRoadWay: 70,
  shoulderLinesWidthPercentage: 0.05,
  brokenLinesWidthPercentage: 0.1,
  brokenLinesLengthPercentage: 0.5,
  lightStickWidth: [0.12, 0.5],
  lightStickHeight: [1.3, 1.7],
  movingAwaySpeed: [60, 80],
  movingCloserSpeed: [-120, -160],
  carLightsLength: [400 * 0.05, 400 * 0.3],
  carLightsRadius: [0.05, 0.14],
  carWidthPercentage: [0.3, 0.5],
  carShiftX: [-0.8, 0.8],
  carFloorColor: 0x080808,
  colors: {
    roadColor: 0x0a0a0a,
    islandColor: 0x0f0f0f,
    background: 0x000000,
    shoulderLines: 0x333333,
    brokenLines: 0x444444,
    // White/light gray tones (left side)
    leftCars: [0xffffff, 0xe0e0e0, 0xcccccc, 0xf5f5f5, 0xd0d0d0, 0xfafafa, 0xebebeb],
    // White with slight cool tints (right side)
    rightCars: [0xffffff, 0xf0f8ff, 0xe8f4fc, 0xf5f5f5, 0xfafafa, 0xe0e8f0, 0xf8f8f8],
    sticks: 0x888888,
  },
};

const stats = [
  { value: '₹50L+', label: 'Assets Tracked' },
  { value: '100+', label: 'Markets Covered' },
  { value: '99.9%', label: 'Uptime' },
  { value: '<50ms', label: 'Data Latency' },
];

function Home() {
  const navigate = useNavigate();
  const { theme, toggleTheme } = useTheme();
  const isDark = theme === 'dark';

  return (
    <div className="home-page">
      {/* Navigation */}
      <nav className="home-nav">
        <div className="nav-logo">
          <TrendingUp size={28} />
          <span className="shiny-text">Bloomberg</span>
        </div>
        <div className="nav-links">
          <a href="#features">Features</a>
          <a href="#pricing">Pricing</a>
          <a href="#about">About</a>
        </div>
        <div className="nav-actions">
          <button className="theme-toggle" onClick={toggleTheme} aria-label="Toggle theme">
            {isDark ? <Sun size={18} /> : <Moon size={18} />}
          </button>
          <button className="nav-cta" onClick={() => navigate('/dashboard')}>
            Launch App
            <ArrowRight size={16} />
          </button>
        </div>
      </nav>

      {/* Hero with Hyperspeed Background */}
      <section className="hero-section">
        <div className="hyperspeed-container">
          <Hyperspeed effectOptions={hyperspeedOptions} />
        </div>
        <div className="hero-content">
          <div className="hero-badge">
            <Zap size={14} />
            <span>Financial Intelligence Platform</span>
          </div>
          <h1 className="hero-title">
            <span className="shiny-text bloomberg-title">Bloomberg</span>
            <br />
            <span className="gradient-text">Market Analytics</span>
          </h1>
          <p className="hero-subtitle">
            Advanced portfolio analytics for Indian and US markets. Real-time data,
            AI-powered insights, and professional-grade charting tools.
          </p>
          <div className="hero-actions">
            <button className="btn-primary" onClick={() => navigate('/dashboard')}>
              Get Started
              <ArrowRight size={18} />
            </button>
            <button className="btn-secondary" onClick={() => navigate('/technical')}>
              View Demo
            </button>
          </div>
        </div>
      </section>

      {/* Stats */}
      <section className="stats-section">
        {stats.map((stat, i) => (
          <div key={i} className="stat-card">
            <span className="stat-value">{stat.value}</span>
            <span className="stat-label">{stat.label}</span>
          </div>
        ))}
      </section>

      {/* Pricing */}
      <section className="pricing-section" id="pricing">
        <div className="section-header">
          <span className="section-tag">Pricing</span>
          <h2>Simple, Transparent Pricing</h2>
          <p>Choose the plan that's right for you</p>
        </div>
        <div className="pricing-grid">
          {pricingPlans.map((plan, i) => (
            <div key={i} className={`pricing-card ${plan.popular ? 'popular' : ''}`}>
              {plan.popular && <span className="popular-badge">Most Popular</span>}
              <h3 className="plan-name">{plan.name}</h3>
              <p className="plan-description">{plan.description}</p>
              <div className="plan-price">
                <span className="price-amount">${plan.price}</span>
                <div className="price-period">
                  <span>USD</span>
                  <span>per month</span>
                </div>
              </div>
              <button className="plan-cta">Start a free trial</button>
              <div className="plan-features">
                <span className="features-label">Start selling with:</span>
                <ul>
                  {plan.features.map((feature, j) => (
                    <li key={j} className={feature.included ? 'included' : 'excluded'}>
                      <Plus size={14} />
                      <span>{feature.name}</span>
                    </li>
                  ))}
                </ul>
              </div>
            </div>
          ))}
        </div>
      </section>

      {/* Features */}
      <section className="features-section" id="features">
        <div className="section-header">
          <span className="section-tag">Features</span>
          <h2>Everything You Need</h2>
          <p>Comprehensive tools for Indian and US market analysis</p>
        </div>
        <div className="features-grid">
          {features.map((feature, i) => (
            <div key={i} className="feature-card">
              <div className="feature-icon">
                <feature.icon size={22} />
              </div>
              <h3>{feature.title}</h3>
              <p>{feature.desc}</p>
            </div>
          ))}
        </div>
      </section>

      {/* About */}
      <section className="about-section" id="about">
        <div className="about-content">
          <span className="section-tag">Why Bloomberg</span>
          <h2>Built for Traders</h2>
          <p>
            Whether you're trading on NSE, BSE, or US markets, Bloomberg provides
            the tools and data you need for informed decisions.
          </p>
          <ul className="benefits-list">
            <li><CheckCircle size={18} /> INR (₹) and USD ($) currency support</li>
            <li><CheckCircle size={18} /> NIFTY 500 and S&P 500 coverage</li>
            <li><CheckCircle size={18} /> Professional candlestick charting</li>
            <li><CheckCircle size={18} /> 10+ backtesting strategies</li>
            <li><CheckCircle size={18} /> Real-time sector treemaps</li>
            <li><CheckCircle size={18} /> AI-driven stock research</li>
          </ul>
          <button className="btn-primary" onClick={() => navigate('/dashboard')}>
            Start Trading
            <ArrowRight size={18} />
          </button>
        </div>
        <div className="about-visual">
          <div className="visual-card">
            <div className="card-header">
              <span>Portfolio Performance</span>
              <span className="badge positive">+24.8%</span>
            </div>
            <div className="card-chart">
              <svg viewBox="0 0 200 60">
                <path
                  d="M0,50 Q30,45 60,30 T120,25 T180,15 T200,10"
                  fill="none"
                  stroke="url(#lineGrad)"
                  strokeWidth="2"
                />
                <defs>
                  <linearGradient id="lineGrad" x1="0%" y1="0%" x2="100%" y2="0%">
                    <stop offset="0%" stopColor="#3b82f6" />
                    <stop offset="100%" stopColor="#22c55e" />
                  </linearGradient>
                </defs>
              </svg>
            </div>
            <div className="card-stats">
              <div><span>Total Value</span><strong>₹12,84,590</strong></div>
              <div><span>Today</span><strong className="positive">+₹1,24,500</strong></div>
            </div>
          </div>
        </div>
      </section>

      {/* Trust */}
      <section className="trust-section">
        <div className="trust-item">
          <Shield size={20} />
          <span>Bank-Level Security</span>
        </div>
        <div className="trust-item">
          <Clock size={20} />
          <span>24/7 Market Monitoring</span>
        </div>
        <div className="trust-item">
          <Users size={20} />
          <span>Trusted by 10K+ Traders</span>
        </div>
      </section>

      {/* Footer */}
      <footer className="home-footer">
        <div className="footer-logo">
          <TrendingUp size={24} />
          <span className="shiny-text">Bloomberg</span>
        </div>
        <p>© 2024 Bloomberg. Professional Financial Analytics.</p>
      </footer>
    </div>
  );
}

export default Home;
