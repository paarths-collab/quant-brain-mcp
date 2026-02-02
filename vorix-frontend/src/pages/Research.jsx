import { useState } from 'react';
import { 
  Search, Loader2, CheckCircle, Circle, 
  TrendingUp, AlertTriangle, FileText, BarChart3
} from 'lucide-react';
import { researchAPI } from '../api';
import './Research.css';

const analysisSteps = [
  { id: 1, name: 'Fetching Market Data', status: 'completed' },
  { id: 2, name: 'Analyzing Fundamentals', status: 'completed' },
  { id: 3, name: 'Technical Analysis', status: 'completed' },
  { id: 4, name: 'Sentiment Analysis', status: 'completed' },
  { id: 5, name: 'Risk Assessment', status: 'completed' },
  { id: 6, name: 'Generating Report', status: 'completed' },
];

const mockAnalysis = {
  symbol: 'AAPL',
  recommendation: 'BUY',
  targetPrice: '$215.00',
  currentPrice: '$192.80',
  upside: '+11.5%',
  riskLevel: 'Moderate',
  summary: `Apple Inc. shows strong fundamentals with consistent revenue growth and robust cash flow. The company's services segment continues to expand, providing recurring revenue streams. Technical indicators suggest bullish momentum with price above key moving averages.`,
  strengths: [
    'Strong brand loyalty and ecosystem',
    'Growing services revenue',
    'Solid balance sheet with $162B cash',
    'AI integration in upcoming products'
  ],
  risks: [
    'iPhone sales dependency',
    'China market exposure',
    'Regulatory pressures',
    'Valuation concerns'
  ],
  metrics: {
    peRatio: '31.2',
    forwardPE: '28.5',
    revenue: '$383.3B',
    profitMargin: '25.3%',
    debtToEquity: '1.87',
    roe: '147.2%'
  }
};

function Research() {
  const [symbol, setSymbol] = useState('');
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [results, setResults] = useState(mockAnalysis);
  const [activeTab, setActiveTab] = useState('summary');

  const handleAnalyze = (e) => {
    e.preventDefault();
    if (!symbol.trim()) return;
    setIsAnalyzing(true);
    // Simulate analysis
    setTimeout(() => {
      setIsAnalyzing(false);
      setResults({ ...mockAnalysis, symbol: symbol.toUpperCase() });
    }, 2000);
  };

  return (
    <div className="research-page">
      <h1 className="page-title">AI Research Agent</h1>

      {/* Search */}
      <form className="research-search" onSubmit={handleAnalyze}>
        <Search size={20} />
        <input 
          type="text"
          placeholder="Enter stock symbol to analyze (e.g., AAPL, MSFT, GOOGL)"
          value={symbol}
          onChange={(e) => setSymbol(e.target.value)}
        />
        <button type="submit" disabled={isAnalyzing}>
          {isAnalyzing ? <Loader2 size={18} className="spin" /> : 'Analyze'}
        </button>
      </form>

      {/* Analysis Progress */}
      {isAnalyzing && (
        <div className="analysis-progress glass-card">
          <h3>Analyzing {symbol.toUpperCase()}...</h3>
          <div className="steps-list">
            {analysisSteps.map((step, i) => (
              <div key={step.id} className={`step-item ${i < 3 ? 'completed' : 'pending'}`}>
                {i < 3 ? <CheckCircle size={18} /> : <Circle size={18} />}
                <span>{step.name}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Results */}
      {results && !isAnalyzing && (
        <div className="research-results">
          {/* Header Card */}
          <div className="result-header glass-card">
            <div className="result-symbol">
              <span className="symbol-name">{results.symbol}</span>
              <span className={`recommendation ${results.recommendation.toLowerCase()}`}>
                {results.recommendation}
              </span>
            </div>
            <div className="result-prices">
              <div className="price-item">
                <span className="price-label">Current Price</span>
                <span className="price-value">{results.currentPrice}</span>
              </div>
              <div className="price-item">
                <span className="price-label">Target Price</span>
                <span className="price-value highlight">{results.targetPrice}</span>
              </div>
              <div className="price-item">
                <span className="price-label">Upside</span>
                <span className="price-value positive">{results.upside}</span>
              </div>
              <div className="price-item">
                <span className="price-label">Risk Level</span>
                <span className="price-value warning">{results.riskLevel}</span>
              </div>
            </div>
          </div>

          {/* Tabs */}
          <div className="result-tabs">
            {['summary', 'metrics', 'strengths', 'risks'].map((tab) => (
              <button 
                key={tab}
                className={`tab-btn ${activeTab === tab ? 'active' : ''}`}
                onClick={() => setActiveTab(tab)}
              >
                {tab.charAt(0).toUpperCase() + tab.slice(1)}
              </button>
            ))}
          </div>

          {/* Tab Content */}
          <div className="tab-content glass-card">
            {activeTab === 'summary' && (
              <div className="summary-content">
                <FileText size={20} />
                <p>{results.summary}</p>
              </div>
            )}

            {activeTab === 'metrics' && (
              <div className="metrics-content">
                {Object.entries(results.metrics).map(([key, value]) => (
                  <div key={key} className="metric-item">
                    <span className="metric-key">{key.replace(/([A-Z])/g, ' $1').trim()}</span>
                    <span className="metric-val">{value}</span>
                  </div>
                ))}
              </div>
            )}

            {activeTab === 'strengths' && (
              <div className="list-content">
                {results.strengths.map((item, i) => (
                  <div key={i} className="list-item positive">
                    <TrendingUp size={16} />
                    <span>{item}</span>
                  </div>
                ))}
              </div>
            )}

            {activeTab === 'risks' && (
              <div className="list-content">
                {results.risks.map((item, i) => (
                  <div key={i} className="list-item negative">
                    <AlertTriangle size={16} />
                    <span>{item}</span>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

export default Research;
