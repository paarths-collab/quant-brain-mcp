import { useNavigate } from 'react-router-dom';
import { ArrowRight, TrendingUp, Shield, Zap, BarChart3 } from 'lucide-react';
import './Starter.css';

function Starter() {
  const navigate = useNavigate();

  return (
    <div className="starter-page">
      {/* Background Elements */}
      <div className="bg-gradient"></div>
      <div className="bg-grid"></div>
      
      {/* Content */}
      <div className="starter-content">
        {/* Logo */}
        <div className="starter-logo">
          <div className="logo-mark">V</div>
          <span className="logo-name">Vorix</span>
        </div>

        {/* Hero */}
        <div className="hero-section">
          <h1 className="hero-title">
            Smart Financial
            <span className="gradient-text"> Analytics</span>
          </h1>
          <p className="hero-subtitle">
            Advanced portfolio management, real-time market data, and AI-powered insights
            for modern investors.
          </p>
          <button className="cta-button" onClick={() => navigate('/dashboard')}>
            Get Started
            <ArrowRight size={18} />
          </button>
        </div>

        {/* Features */}
        <div className="features-grid">
          <div className="feature-card">
            <div className="feature-icon">
              <TrendingUp size={24} />
            </div>
            <h3>Real-time Data</h3>
            <p>Live market updates and stock tracking</p>
          </div>
          <div className="feature-card">
            <div className="feature-icon">
              <BarChart3 size={24} />
            </div>
            <h3>Technical Analysis</h3>
            <p>Advanced charting and indicators</p>
          </div>
          <div className="feature-card">
            <div className="feature-icon">
              <Zap size={24} />
            </div>
            <h3>AI Research</h3>
            <p>Intelligent stock recommendations</p>
          </div>
          <div className="feature-card">
            <div className="feature-icon">
              <Shield size={24} />
            </div>
            <h3>Backtesting</h3>
            <p>Test strategies with historical data</p>
          </div>
        </div>
      </div>
    </div>
  );
}

export default Starter;
