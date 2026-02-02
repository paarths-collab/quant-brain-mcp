import { useState } from 'react';
import { Play, Settings, TrendingUp, TrendingDown, DollarSign, IndianRupee, Calendar, Target, Percent, BarChart3, Activity, Zap, Check, X, Trophy, Medal, Download, FileText, FileSpreadsheet } from 'lucide-react';
import { AreaChart, Area, XAxis, YAxis, Tooltip, ResponsiveContainer, LineChart, Line, Legend } from 'recharts';
import { formatCurrency, getCurrencySymbol, backtestAPI } from '../api';
import './Backtest.css';

const strategies = [
  { 
    id: 'momentum', 
    name: 'Momentum', 
    description: 'Buy stocks with strong price momentum over the past N days',
    icon: TrendingUp,
    color: '#3b82f6',
    params: { lookback_period: 20, threshold: 0.05 }
  },
  { 
    id: 'mean_reversion', 
    name: 'Mean Reversion', 
    description: 'Trade based on price deviation from moving average',
    icon: Activity,
    color: '#10b981',
    params: { ma_period: 20, std_multiplier: 2 }
  },
  { 
    id: 'ema_crossover', 
    name: 'EMA Cross', 
    description: 'Golden/Death cross using exponential moving averages',
    icon: Zap,
    color: '#f59e0b',
    params: { fast: 12, slow: 26 }
  },
  { 
    id: 'rsi_strategy', 
    name: 'RSI', 
    description: 'Buy oversold, sell overbought based on RSI levels',
    icon: BarChart3,
    color: '#ef4444',
    params: { rsi_period: 14, oversold: 30, overbought: 70 }
  },
  { 
    id: 'bollinger', 
    name: 'Bollinger', 
    description: 'Trade based on price touching Bollinger bands',
    icon: Target,
    color: '#8b5cf6',
    params: { bb_period: 20, std_dev: 2 }
  },
  { 
    id: 'macd', 
    name: 'MACD', 
    description: 'Trade on MACD line crossing signal line',
    icon: Activity,
    color: '#ec4899',
    params: { fast: 12, slow: 26, signal: 9 }
  },
];

function Backtest() {
  const [market, setMarket] = useState('US');
  const [selectedStrategies, setSelectedStrategies] = useState(['ema_crossover']);
  const [symbol, setSymbol] = useState('AAPL');
  const [startDate, setStartDate] = useState('2023-01-01');
  const [endDate, setEndDate] = useState('2024-01-01');
  const [initialCapital, setInitialCapital] = useState(100000);
  const [isRunning, setIsRunning] = useState(false);
  const [results, setResults] = useState(null);
  const [error, setError] = useState(null);
  const [isDownloading, setIsDownloading] = useState(false);
  
  const currencySymbol = getCurrencySymbol(market);
  const isMultiStrategy = selectedStrategies.length > 1;

  const handleDownloadReport = async (format = 'html') => {
    if (!results) return;
    
    setIsDownloading(true);
    try {
      const payload = {
        symbol: symbol,
        strategies: selectedStrategies,
        results: results.isMulti ? {
          mode: 'multi_strategy',
          strategies: results.strategies,
          ranking: results.ranking,
          initialCapital: results.initialCapital || initialCapital
        } : {
          metrics: results.metrics,
          initialCapital: initialCapital
        },
        format: format
      };
      
      const response = await backtestAPI.generateReport(payload);
      
      if (response.data?.success && response.data?.downloadUrl) {
        // Trigger download
        const link = document.createElement('a');
        link.href = `http://localhost:8000${response.data.downloadUrl}`;
        link.download = response.data.filename;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
      } else {
        throw new Error(response.data?.error || 'Failed to generate report');
      }
    } catch (err) {
      console.error('Download error:', err);
      setError('Failed to download report');
    } finally {
      setIsDownloading(false);
    }
  };

  const toggleStrategy = (strategyId) => {
    setSelectedStrategies(prev => {
      if (prev.includes(strategyId)) {
        // Don't allow deselecting if it's the only one
        if (prev.length === 1) return prev;
        return prev.filter(s => s !== strategyId);
      }
      // Max 4 strategies for comparison
      if (prev.length >= 4) return prev;
      return [...prev, strategyId];
    });
  };
  
  const handleRunBacktest = async () => {
    setIsRunning(true);
    setError(null);
    
    try {
      // Build params dict for selected strategies
      const paramsDict = {};
      selectedStrategies.forEach(stratId => {
        const strat = strategies.find(s => s.id === stratId);
        if (strat) paramsDict[stratId] = strat.params;
      });
      
      const payload = {
        symbol: symbol,
        strategies: selectedStrategies,
        range: '1y',
        params: paramsDict
      };
      
      const response = await backtestAPI.run(payload);
      
      if (response.data) {
        const data = response.data;
        
        if (data.mode === 'multi_strategy') {
          // Multi-strategy response
          setResults({
            isMulti: true,
            strategies: data.strategies,
            combinedChartData: data.combinedChartData,
            ranking: data.ranking,
            initialCapital: data.initialCapital
          });
        } else {
          // Single strategy response (backward compatible)
          const equityCurve = data.equity_curve?.map((point, idx) => ({
            date: point.date || `Day ${idx + 1}`,
            portfolio: point.value || point.portfolio || initialCapital * (1 + idx * 0.001),
            benchmark: point.benchmark || initialCapital * (1 + idx * 0.0008),
          })) || generateFallbackCurve();
          
          setResults({
            isMulti: false,
            equityCurve,
            metrics: {
              totalReturn: data.metrics?.totalReturn?.toFixed?.(2) || data.total_return?.toFixed(2) || '0',
              sharpeRatio: data.metrics?.sharpeRatio?.toFixed?.(2) || data.sharpe_ratio?.toFixed(2) || '0',
              maxDrawdown: data.metrics?.maxDrawdown?.toFixed?.(2) || data.max_drawdown?.toFixed(2) || '0',
              winRate: data.metrics?.winRate?.toFixed?.(1) || data.win_rate?.toFixed(1) || '50',
              profitFactor: data.metrics?.profitFactor?.toFixed?.(2) || data.profit_factor?.toFixed(2) || '1',
              avgTrade: data.metrics?.avgTrade?.toFixed?.(2) || data.avg_trade?.toFixed(2) || '0',
              totalTrades: data.metrics?.totalTrades || data.total_trades || 0,
              finalValue: data.metrics?.finalEquity || data.final_value || equityCurve[equityCurve.length - 1]?.portfolio || initialCapital,
            }
          });
        }
      }
    } catch (err) {
      console.error('Backtest error:', err);
      setError('Failed to run backtest. Using simulated results.');
      
      // Fallback to simulated results
      const equityCurve = generateFallbackCurve();
      const finalValue = equityCurve[equityCurve.length - 1].portfolio;
      
      setResults({
        isMulti: false,
        equityCurve,
        metrics: {
          totalReturn: ((finalValue - initialCapital) / initialCapital * 100).toFixed(2),
          sharpeRatio: (Math.random() * 1.5 + 0.5).toFixed(2),
          maxDrawdown: (-Math.random() * 15 - 5).toFixed(2),
          winRate: (Math.random() * 20 + 50).toFixed(1),
          profitFactor: (Math.random() * 1.5 + 1).toFixed(2),
          avgTrade: (Math.random() * 2 + 0.5).toFixed(2),
          totalTrades: Math.floor(Math.random() * 100 + 50),
          finalValue,
        }
      });
    } finally {
      setIsRunning(false);
    }
  };

  const generateFallbackCurve = () => {
    const data = [];
    let portfolio = initialCapital;
    let benchmark = initialCapital;
    
    for (let i = 0; i < 252; i++) {
      portfolio *= (1 + (Math.random() - 0.45) * 0.02);
      benchmark *= (1 + (Math.random() - 0.48) * 0.015);
      
      data.push({
        date: `Day ${i + 1}`,
        portfolio: Math.round(portfolio),
        benchmark: Math.round(benchmark),
      });
    }
    return data;
  };

  const getSelectedStrategyObjects = () => 
    strategies.filter(s => selectedStrategies.includes(s.id));

  return (
    <div className="backtest-page">
      {/* Header */}
      <div className="backtest-header">
        <div>
          <h1>Backtesting</h1>
          <p>Test and compare trading strategies with historical data</p>
        </div>
        <div className="market-toggle">
          <button 
            className={market === 'IN' ? 'active' : ''}
            onClick={() => { setMarket('IN'); setSymbol('RELIANCE.NS'); }}
          >
            <IndianRupee size={16} />
            <span>India</span>
          </button>
          <button 
            className={market === 'US' ? 'active' : ''}
            onClick={() => { setMarket('US'); setSymbol('AAPL'); }}
          >
            <DollarSign size={16} />
            <span>US</span>
          </button>
        </div>
      </div>

      <div className="backtest-layout">
        {/* Config Panel */}
        <div className="config-panel">
          <div className="config-section">
            <h3><Settings size={16} /> Configuration</h3>
            
            <div className="form-group">
              <label>Symbol</label>
              <input 
                type="text" 
                value={symbol}
                onChange={(e) => setSymbol(e.target.value)}
                placeholder="Enter symbol..."
              />
            </div>
            
            <div className="form-row">
              <div className="form-group">
                <label><Calendar size={14} /> Start Date</label>
                <input 
                  type="date" 
                  value={startDate}
                  onChange={(e) => setStartDate(e.target.value)}
                />
              </div>
              <div className="form-group">
                <label><Calendar size={14} /> End Date</label>
                <input 
                  type="date" 
                  value={endDate}
                  onChange={(e) => setEndDate(e.target.value)}
                />
              </div>
            </div>
            
            <div className="form-group">
              <label>
                {market === 'IN' ? <IndianRupee size={14} /> : <DollarSign size={14} />}
                Initial Capital
              </label>
              <input 
                type="number" 
                value={initialCapital}
                onChange={(e) => setInitialCapital(Number(e.target.value))}
              />
            </div>
          </div>

          <div className="config-section">
            <h3><Zap size={16} /> Strategies <span className="hint">(Select up to 4)</span></h3>
            
            <div className="strategy-select multi">
              {strategies.map((s) => {
                const Icon = s.icon;
                const isSelected = selectedStrategies.includes(s.id);
                return (
                  <div 
                    key={s.id}
                    className={`strategy-option ${isSelected ? 'selected' : ''}`}
                    onClick={() => toggleStrategy(s.id)}
                    style={isSelected ? { borderColor: s.color, background: `${s.color}15` } : {}}
                  >
                    <div className="strategy-check">
                      {isSelected ? <Check size={14} /> : null}
                    </div>
                    <Icon size={18} style={isSelected ? { color: s.color } : {}} />
                    <span>{s.name}</span>
                  </div>
                );
              })}
            </div>
            
            <div className="selected-strategies">
              {getSelectedStrategyObjects().map(s => (
                <span key={s.id} className="strategy-tag" style={{ background: s.color }}>
                  {s.name}
                  {selectedStrategies.length > 1 && (
                    <X size={12} onClick={(e) => { e.stopPropagation(); toggleStrategy(s.id); }} />
                  )}
                </span>
              ))}
            </div>
          </div>

          <button 
            className="run-button"
            onClick={handleRunBacktest}
            disabled={isRunning}
          >
            {isRunning ? (
              <>
                <span className="spinner"></span>
                Running...
              </>
            ) : (
              <>
                <Play size={18} />
                {isMultiStrategy ? 'Compare Strategies' : 'Run Backtest'}
              </>
            )}
          </button>

          {error && <div className="error-message">{error}</div>}
        </div>

        {/* Results Panel */}
        <div className="results-panel">
          {!results ? (
            <div className="empty-results">
              <BarChart3 size={48} />
              <h3>No Results Yet</h3>
              <p>Select strategies and run a backtest to compare performance</p>
            </div>
          ) : results.isMulti ? (
            /* Multi-Strategy Comparison View */
            <>
              {/* Download Buttons */}
              <div className="report-actions">
                <button 
                  className="download-btn html"
                  onClick={() => handleDownloadReport('html')}
                  disabled={isDownloading}
                >
                  <FileText size={16} />
                  {isDownloading ? 'Generating...' : 'Download HTML'}
                </button>
                <button 
                  className="download-btn csv"
                  onClick={() => handleDownloadReport('csv')}
                  disabled={isDownloading}
                >
                  <FileSpreadsheet size={16} />
                  {isDownloading ? 'Generating...' : 'Download CSV'}
                </button>
              </div>

              {/* Strategy Ranking */}
              {results.ranking && results.ranking.length > 0 && (
                <div className="ranking-section">
                  <h3><Trophy size={16} /> Strategy Ranking</h3>
                  <div className="ranking-list">
                    {results.ranking.map((item, idx) => {
                      const strat = strategies.find(s => s.id === item.strategy);
                      return (
                        <div key={item.strategy} className={`ranking-item rank-${idx + 1}`}>
                          <span className="rank-badge">
                            {idx === 0 ? <Trophy size={14} /> : idx === 1 ? <Medal size={14} /> : `#${idx + 1}`}
                          </span>
                          <span className="rank-name" style={{ color: strat?.color }}>{strat?.name || item.strategy}</span>
                          <span className={`rank-return ${item.return >= 0 ? 'positive' : 'negative'}`}>
                            {item.return >= 0 ? '+' : ''}{item.return}%
                          </span>
                        </div>
                      );
                    })}
                  </div>
                </div>
              )}

              {/* Per-Strategy Full Metrics */}
              <div className="multi-strategy-sections">
                {Object.entries(results.strategies).map(([stratId, stratData]) => {
                  const strat = strategies.find(s => s.id === stratId);
                  if (!stratData.metrics) return null;
                  return (
                    <div key={stratId} className="strategy-full-section" style={{ borderColor: strat?.color }}>
                      <h4 style={{ color: strat?.color }}>
                        {strat?.name || stratId}
                      </h4>
                      
                      <div className="metrics-grid">
                        <div className="metric-card">
                          <span className="metric-label">Total Return</span>
                          <span className={`metric-value ${stratData.metrics.totalReturn >= 0 ? 'positive' : 'negative'}`}>
                            {stratData.metrics.totalReturn >= 0 ? '+' : ''}{stratData.metrics.totalReturn}%
                          </span>
                        </div>
                        <div className="metric-card">
                          <span className="metric-label">Sharpe Ratio</span>
                          <span className="metric-value">{stratData.metrics.sharpeRatio}</span>
                        </div>
                        <div className="metric-card">
                          <span className="metric-label">Max Drawdown</span>
                          <span className="metric-value negative">{stratData.metrics.maxDrawdown}%</span>
                        </div>
                        <div className="metric-card">
                          <span className="metric-label">Win Rate</span>
                          <span className="metric-value">{stratData.metrics.winRate || '50.0'}%</span>
                        </div>
                        <div className="metric-card">
                          <span className="metric-label">Profit Factor</span>
                          <span className="metric-value">{stratData.metrics.profitFactor || '1.00'}</span>
                        </div>
                        <div className="metric-card">
                          <span className="metric-label">Total Trades</span>
                          <span className="metric-value">{stratData.metrics.totalTrades}</span>
                        </div>
                        <div className="metric-card highlight">
                          <span className="metric-label">Final Portfolio</span>
                          <span className="metric-value">{formatCurrency(stratData.metrics.finalEquity, market)}</span>
                        </div>
                        <div className="metric-card">
                          <span className="metric-label">Avg Trade</span>
                          <span className="metric-value positive">+{stratData.metrics.avgTrade || '0.00'}%</span>
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>

              {/* Combined Equity Chart */}
              <div className="equity-chart-container">
                <h3>Equity Curve Comparison</h3>
                <div className="chart-legend multi">
                  {getSelectedStrategyObjects().map(s => (
                    <span key={s.id}><span className="dot" style={{ background: s.color }}></span> {s.name}</span>
                  ))}
                </div>
                <div className="equity-chart">
                  <ResponsiveContainer width="100%" height={350}>
                    <LineChart data={results.combinedChartData}>
                      <XAxis 
                        dataKey="date" 
                        axisLine={false} 
                        tickLine={false}
                        tick={{ fill: '#71717a', fontSize: 11 }}
                        interval="preserveStartEnd"
                      />
                      <YAxis 
                        axisLine={false} 
                        tickLine={false}
                        tick={{ fill: '#71717a', fontSize: 11 }}
                        tickFormatter={(v) => `${currencySymbol}${(v/1000).toFixed(0)}K`}
                      />
                      <Tooltip 
                        contentStyle={{ 
                          background: '#18181b', 
                          border: '1px solid #27272a',
                          borderRadius: '8px',
                        }}
                        labelStyle={{ color: '#fff' }}
                        formatter={(value, name) => [formatCurrency(value, market), strategies.find(s => s.id === name)?.name || name]}
                      />
                      <Legend />
                      {getSelectedStrategyObjects().map(s => (
                        <Line 
                          key={s.id}
                          type="monotone" 
                          dataKey={s.id}
                          name={s.name}
                          stroke={s.color}
                          strokeWidth={2}
                          dot={false}
                        />
                      ))}
                    </LineChart>
                  </ResponsiveContainer>
                </div>
              </div>
            </>
          ) : (
            /* Single Strategy View */
            <>
              {/* Metrics Grid */}
              <div className="metrics-grid">
                <div className="metric-card">
                  <span className="metric-label">Total Return</span>
                  <span className={`metric-value ${Number(results.metrics.totalReturn) >= 0 ? 'positive' : 'negative'}`}>
                    {Number(results.metrics.totalReturn) >= 0 ? '+' : ''}{results.metrics.totalReturn}%
                  </span>
                </div>
                <div className="metric-card">
                  <span className="metric-label">Sharpe Ratio</span>
                  <span className="metric-value">{results.metrics.sharpeRatio}</span>
                </div>
                <div className="metric-card">
                  <span className="metric-label">Max Drawdown</span>
                  <span className="metric-value negative">{results.metrics.maxDrawdown}%</span>
                </div>
                <div className="metric-card">
                  <span className="metric-label">Win Rate</span>
                  <span className="metric-value">{results.metrics.winRate}%</span>
                </div>
                <div className="metric-card">
                  <span className="metric-label">Profit Factor</span>
                  <span className="metric-value">{results.metrics.profitFactor}</span>
                </div>
                <div className="metric-card">
                  <span className="metric-label">Total Trades</span>
                  <span className="metric-value">{results.metrics.totalTrades}</span>
                </div>
                <div className="metric-card highlight">
                  <span className="metric-label">Final Portfolio</span>
                  <span className="metric-value">{formatCurrency(results.metrics.finalValue, market)}</span>
                </div>
                <div className="metric-card">
                  <span className="metric-label">Avg Trade</span>
                  <span className="metric-value positive">+{results.metrics.avgTrade}%</span>
                </div>
              </div>

              {/* Equity Curve */}
              <div className="equity-chart-container">
                <h3>Equity Curve</h3>
                <div className="chart-legend">
                  <span><span className="dot portfolio"></span> Portfolio</span>
                  <span><span className="dot benchmark"></span> Benchmark</span>
                </div>
                <div className="equity-chart">
                  <ResponsiveContainer width="100%" height={300}>
                    <AreaChart data={results.equityCurve}>
                      <defs>
                        <linearGradient id="portfolioGradient" x1="0" y1="0" x2="0" y2="1">
                          <stop offset="0%" stopColor="#3b82f6" stopOpacity={0.3} />
                          <stop offset="100%" stopColor="#3b82f6" stopOpacity={0} />
                        </linearGradient>
                        <linearGradient id="benchmarkGradient" x1="0" y1="0" x2="0" y2="1">
                          <stop offset="0%" stopColor="#71717a" stopOpacity={0.2} />
                          <stop offset="100%" stopColor="#71717a" stopOpacity={0} />
                        </linearGradient>
                      </defs>
                      <XAxis 
                        dataKey="date" 
                        axisLine={false} 
                        tickLine={false}
                        tick={{ fill: '#71717a', fontSize: 11 }}
                        interval="preserveStartEnd"
                      />
                      <YAxis 
                        axisLine={false} 
                        tickLine={false}
                        tick={{ fill: '#71717a', fontSize: 11 }}
                        tickFormatter={(v) => `${currencySymbol}${(v/1000).toFixed(0)}K`}
                      />
                      <Tooltip 
                        contentStyle={{ 
                          background: '#18181b', 
                          border: '1px solid #27272a',
                          borderRadius: '8px',
                        }}
                        labelStyle={{ color: '#fff' }}
                        formatter={(value) => formatCurrency(value, market)}
                      />
                      <Area 
                        type="monotone" 
                        dataKey="benchmark" 
                        stroke="#71717a" 
                        fill="url(#benchmarkGradient)"
                        strokeWidth={1.5}
                      />
                      <Area 
                        type="monotone" 
                        dataKey="portfolio" 
                        stroke="#3b82f6" 
                        fill="url(#portfolioGradient)"
                        strokeWidth={2}
                      />
                    </AreaChart>
                  </ResponsiveContainer>
                </div>
              </div>

              {/* Download Buttons for Single Strategy */}
              <div className="report-actions">
                <h4>Download Report</h4>
                <div className="download-buttons">
                  <button 
                    className="download-btn html"
                    onClick={() => handleDownloadReport('html')}
                    disabled={isDownloading}
                  >
                    <FileText size={16} />
                    {isDownloading ? 'Generating...' : 'HTML Report'}
                  </button>
                  <button 
                    className="download-btn csv"
                    onClick={() => handleDownloadReport('csv')}
                    disabled={isDownloading}
                  >
                    <FileSpreadsheet size={16} />
                    {isDownloading ? 'Generating...' : 'CSV Data'}
                  </button>
                </div>
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
}

export default Backtest;
