
import { useState, useEffect } from 'react';
import {
  Activity,
  Brain,
  RefreshCw,
  Shield,
  TrendingUp,
  TrendingDown,
  Minus,
  User,
  Zap,
  AlertTriangle
} from 'lucide-react';
import {
  stockAdvisorAPI,
  marketPulseAPI,
  investorProfileAPI,
  longTermAPI
} from '@/api';

import { Link } from 'react-router-dom';
import { SectorIntelWidget } from '../components/SectorIntelWidget';
import { MarketStatsBar } from '../components/MarketStatsBar';
import { ErrorBoundary } from '../components/ErrorBoundary';
import { SuperAgentChat } from '../components/SuperAgentChat';
import { QuantDashboard } from '../components/quant/QuantDashboard';

// Types
type PovState = {
  symbol: string;
  bull: any;
  bear: any;
  neutral: any;
};

type SectorNewsState = {
  market: string;
  total_items: number;
  sectors: Record<string, any[]>;
};

const PovCard = ({ title, data, type }: { title: string; data: any; type: 'bull' | 'bear' | 'neutral' }) => {
  if (!data || !data.verdict) return <div className="finverse-card opacity-50">Awaiting {title}...</div>;

  const color = type === 'bull' ? 'text-green-400' : type === 'bear' ? 'text-red-400' : 'text-yellow-400';
  const icon = type === 'bull' ? <TrendingUp size={16} /> : type === 'bear' ? <TrendingDown size={16} /> : <Minus size={16} />;

  return (
    <div className="finverse-card border-l-4" style={{ borderLeftColor: type === 'bull' ? '#4ade80' : type === 'bear' ? '#f87171' : '#facc15' }}>
      <div className={`flex items-center gap-2 font-bold mb-2 ${color}`}>
        {icon} {title}
      </div>
      <div className="text-sm font-semibold mb-1">{data.verdict} <span className="text-xs text-white/50">({Math.round((data.confidence ?? 0) * 100)}% conf)</span></div>
      <div className="text-xs text-white/80 mb-3 leading-relaxed">{data.reasoning}</div>
      <div className="space-y-1">
        {(Array.isArray(data.key_factors) ? data.key_factors : []).slice(0, 3).map((f: string, i: number) => {
          if (!f) return null;
          return (
            <div key={i} className="text-[11px] text-white/50 flex items-start gap-1">
              <span className="mt-1">•</span> {String(f)}
            </div>
          );
        })}
      </div>
    </div>
  );
};



export default function InvestmentAI() {
  // Dashboard State (kept for future expansion or removed if strictly unused)
  const [pov, setPov] = useState<PovState | null>(null);
  const [sectorNews, setSectorNews] = useState<SectorNewsState | null>(null);

  const [portfolio, setPortfolio] = useState<any>(null);
  const [longTermData, setLongTermData] = useState<any>(null);
  const [showLongTermModal, setShowLongTermModal] = useState(false);
  const [analyzingLongTerm, setAnalyzingLongTerm] = useState(false);

  // Strategy Selection State
  const [showStrategyModal, setShowStrategyModal] = useState(false);
  const [selectedSymbol, setSelectedSymbol] = useState<string | null>(null);

  // Kept for short-term analysis loading state
  const [isTyping, setIsTyping] = useState(false);
  // Market state used for context
  const [market] = useState<'US' | 'IN'>('US');
  const [userProfile, setUserProfile] = useState<any>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const init = async () => {
      await Promise.all([
        loadUserProfile(),
        loadSectorNews(),
        loadPortfolio()
      ]);
    };
    init();
  }, []);

  const loadPortfolio = async () => {
    try {
      const { data } = await investorProfileAPI.getPortfolio();
      setPortfolio(data);
    } catch (e) {
      console.error('Portfolio load error', e);
    }
  };

  const handleTrade = async (symbol: string, side: 'buy' | 'sell', qty: number) => {
    try {
      if (!symbol) return;
      await investorProfileAPI.trade({ symbol, side, quantity: qty });
      loadPortfolio();
    } catch (e) {
      console.error('Trade error', e);
      alert('Trade failed: ' + (e as any).response?.data?.detail);
    }
  };

  const openStrategySelector = (symbol: string) => {
    setSelectedSymbol(symbol);
    setShowStrategyModal(true);
  };

  const executeShortTermAnalysis = async () => {
    if (!selectedSymbol) return;
    setShowStrategyModal(false);

    // Simulate typing for UX
    setIsTyping(true);

    try {
      const { data } = await stockAdvisorAPI.multiPov({
        symbol: selectedSymbol,
        market,
        context: 'Short term technical analysis, support/resistance, and momentum.'
      });
      setPov(data);
    } catch (e: any) {
      console.error('Short term analysis error', e);
      setError(e.message || 'Analysis failed');
    } finally {
      setIsTyping(false);
    }
  };

  const executeLongTermAnalysis = async () => {
    if (!selectedSymbol) return;
    setShowStrategyModal(false);
    setAnalyzingLongTerm(true);
    setShowLongTermModal(true);

    try {
      const { data } = await longTermAPI.analyze({
        ticker: selectedSymbol,
        risk_profile: userProfile?.risk_tolerance || 'moderate',
        capital: 10000,
        monthly_investment: 500
      });
      setLongTermData(data.data);
    } catch (e) {
      console.error('Long term analysis error', e);
    } finally {
      setAnalyzingLongTerm(false);
    }
  };

  const loadUserProfile = async () => {
    try {
      const { data } = await investorProfileAPI.load();
      if (data.status === 'ok') setUserProfile(data.profile);
    } catch (e) { console.error('Profile load error', e); }
  };

  const loadSectorNews = async () => {
    try {
      const { data } = await marketPulseAPI.getSectorNews(market, undefined, 30);
      setSectorNews(data);
    } catch (e) { console.error('Sector news error', e); }
  };

  return (
    <div className="finverse-dashboard bg-black min-h-screen text-slate-200 p-8 font-manrope">
      <ErrorBoundary scope="InvestmentAI Dashboard">
        <div className="max-w-7xl mx-auto space-y-8">

          {/* Header */}
          <header className="flex justify-between items-end border-b border-white/10 pb-6">
            <div>
              <div className="text-xs font-bold tracking-[0.3em] text-orange-500 uppercase mb-2">Finverse AI Core</div>
              <h1 className="text-4xl font-bold font-fraunces text-white">Market Command Center</h1>
              <p className="text-white/60 mt-2 max-w-xl">
                Real-time multi-agent analysis powered by Gemini (Bull), Groq (Bear), and DeepSeek (Neutral).
              </p>
            </div>
            <div className="flex gap-4">
              <Link to="/profile" className="finverse-btn flex items-center gap-2 px-4 py-2 rounded-full border border-white/10 hover:bg-white/5 transition-colors">
                <User size={14} /> My Profile
              </Link>
              <button onClick={() => window.location.reload()} className="finverse-btn px-4 py-2 rounded-full border border-white/10 hover:bg-white/5">
                <RefreshCw size={14} />
              </button>
            </div>
          </header>




          {/* Super Agent Chat - Compact Mode */}
          <SuperAgentChat />

          {/* Market Stats Bar */}
          <ErrorBoundary scope="Market Stats">
            <MarketStatsBar />
          </ErrorBoundary>

          {/* Quant Engine Dashboard (New Section) */}
          <ErrorBoundary scope="Quant Engine">
            <div className="mb-8">
              <div className="flex items-center gap-2 mb-4">
                <Zap className="text-purple-500" />
                <h2 className="text-xl font-bold text-white">Live Quant Engine</h2>
                <span className="px-2 py-0.5 bg-purple-500/20 text-purple-300 text-[10px] rounded uppercase font-bold border border-purple-500/30">Beta</span>
              </div>
              <QuantDashboard />
            </div>
          </ErrorBoundary>

          {/* Input & Profile Summary */}

          {/* Strategy Selection Modal */}
          {showStrategyModal && selectedSymbol && (
            <div className="fixed inset-0 z-[60] flex items-center justify-center p-4 bg-black/90 backdrop-blur-md">
              <div className="bg-[#0a0a0a] border border-white/10 rounded-2xl w-full max-w-md p-6 relative animate-in fade-in zoom-in duration-200">
                <button
                  onClick={() => setShowStrategyModal(false)}
                  className="absolute top-4 right-4 p-2 hover:bg-white/10 rounded-full transition-colors"
                >
                  <Minus className="rotate-45" />
                </button>

                <div className="text-center mb-8">
                  <div className="text-sm font-bold text-orange-500 tracking-widest uppercase mb-2">Decision Matrix</div>
                  <h2 className="text-2xl font-bold font-fraunces text-white">Select Investment Horizon</h2>
                  <p className="text-white/60 mt-2 text-sm">How do you plan to trade <span className="text-white font-bold">{selectedSymbol}</span>?</p>
                </div>

                <div className="grid grid-cols-1 gap-4">
                  <button
                    onClick={executeShortTermAnalysis}
                    className="group p-4 rounded-xl border border-white/10 hover:border-blue-500/50 hover:bg-blue-500/10 transition-all text-left flex items-start gap-4"
                  >
                    <div className="p-3 rounded-lg bg-blue-500/20 text-blue-400 group-hover:scale-110 transition-transform">
                      <Activity size={24} />
                    </div>
                    <div>
                      <div className="font-bold text-white group-hover:text-blue-300">Short Term (Swing)</div>
                      <div className="text-xs text-white/50 mt-1">Technical analysis, momentum, support/resistance levels. Ideal for days to weeks.</div>
                    </div>
                  </button>

                  <button
                    onClick={executeLongTermAnalysis}
                    className="group p-4 rounded-xl border border-white/10 hover:border-green-500/50 hover:bg-green-500/10 transition-all text-left flex items-start gap-4"
                  >
                    <div className="p-3 rounded-lg bg-green-500/20 text-green-400 group-hover:scale-110 transition-transform">
                      <TrendingUp size={24} />
                    </div>
                    <div>
                      <div className="font-bold text-white group-hover:text-green-300">Long Term (Wealth)</div>
                      <div className="text-xs text-white/50 mt-1">Fundamental analysis, DCA projections, dividend growth. Ideal for years.</div>
                    </div>
                  </button>
                </div>
              </div>
            </div>
          )}

          {/* Long Term Strategy Modal */}
          {showLongTermModal && (
            <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm">
              <div className="bg-[#0a0a0a] border border-white/10 rounded-2xl w-full max-w-4xl max-h-[90vh] overflow-y-auto p-6 relative">
                <button
                  onClick={() => setShowLongTermModal(false)}
                  className="absolute top-4 right-4 p-2 hover:bg-white/10 rounded-full transition-colors"
                >
                  <Minus className="rotate-45" />
                </button>

                <div className="flex items-center gap-3 mb-6">
                  <TrendingUp className="text-blue-500" size={24} />
                  <h2 className="text-2xl font-bold font-fraunces">Long-Term Strategy Analysis</h2>
                </div>

                {analyzingLongTerm ? (
                  <div className="flex flex-col items-center justify-center py-20 gap-4">
                    <RefreshCw className="animate-spin text-blue-500" size={32} />
                    <div className="text-white/60 animate-pulse">Running Monte Carlo simulations...</div>
                  </div>
                ) : longTermData ? (
                  <div className="space-y-8">
                    {/* Strategy Summary */}
                    <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                      <div className="p-4 bg-white/5 rounded-xl border border-white/10">
                        <div className="text-xs uppercase text-white/40 mb-1">Risk Profile</div>
                        <div className="text-lg font-bold capitalize">{longTermData.metadata.risk_profile}</div>
                      </div>
                      <div className="p-4 bg-white/5 rounded-xl border border-white/10">
                        <div className="text-xs uppercase text-white/40 mb-1">Capital</div>
                        <div className="text-lg font-bold font-mono">${(longTermData?.metadata?.capital ?? 0).toLocaleString()}</div>
                      </div>
                      <div className="p-4 bg-white/5 rounded-xl border border-white/10">
                        <div className="text-xs uppercase text-white/40 mb-1">Active Strategies</div>
                        <div className="flex gap-2 mt-1">
                          {Object.keys(longTermData?.results || {}).map(s => (
                            <span key={s} className="px-2 py-0.5 bg-blue-500/20 text-blue-300 text-xs rounded uppercase">{s}</span>
                          ))}
                        </div>
                      </div>
                    </div>

                    {/* Results Grid */}
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                      {/* DCA Result */}
                      {longTermData.results.dca && (
                        <div className="p-6 bg-white/5 rounded-xl border-l-4 border-green-500">
                          <h3 className="font-bold text-lg mb-4 flex items-center gap-2">
                            <Activity size={18} className="text-green-500" /> DCA Projection
                          </h3>
                          <div className="space-y-2">
                            <div className="flex justify-between">
                              <span className="text-white/60">Total Invested</span>
                              <span className="font-mono">${longTermData.results.dca.total_invested?.toLocaleString()}</span>
                            </div>
                            <div className="flex justify-between">
                              <span className="text-white/60">Final Value</span>
                              <span className="font-mono font-bold text-green-400">${longTermData.results.dca.current_value?.toLocaleString()}</span>
                            </div>
                            <div className="flex justify-between border-t border-white/10 pt-2 mt-2">
                              <span className="text-white/60">Total Return</span>
                              <span className="text-green-400 font-bold">
                                {longTermData.results.dca.absolute_return_pct?.toFixed(2)}%
                              </span>
                            </div>
                          </div>
                        </div>
                      )}

                      {/* Dividend Result */}
                      {longTermData.results.dividend && (
                        <div className="p-6 bg-white/5 rounded-xl border-l-4 border-yellow-500">
                          <h3 className="font-bold text-lg mb-4 flex items-center gap-2">
                            <Zap size={18} className="text-yellow-500" /> Dividend Income
                          </h3>
                          <div className="space-y-4">
                            <div className="grid grid-cols-2 gap-2">
                              <div className="p-2 bg-black/20 rounded">
                                <div className="text-[10px] uppercase text-white/40">Yield</div>
                                <div className="font-mono text-yellow-400">{longTermData.results.dividend.dividend_yield_pct?.toFixed(2)}%</div>
                              </div>
                              <div className="p-2 bg-black/20 rounded">
                                <div className="text-[10px] uppercase text-white/40">Growth (5Y)</div>
                                <div className="font-mono text-green-400">+{longTermData.results.dividend.dividend_growth_5y_pct?.toFixed(2)}%</div>
                              </div>
                            </div>
                            <div className="text-xs text-white/60 p-2 bg-white/5 rounded">
                              {longTermData.results.dividend.rating || 'No rating available'}
                            </div>
                          </div>
                        </div>
                      )}

                      {/* Value Result */}
                      {longTermData.results.value && (
                        <div className="p-6 bg-white/5 rounded-xl border-l-4 border-purple-500">
                          <h3 className="font-bold text-lg mb-4 flex items-center gap-2">
                            <Shield size={18} className="text-purple-500" /> Value Analysis
                          </h3>
                          <div className="space-y-2">
                            <div className="flex justify-between items-center">
                              <span className="text-white/60">Graham Number</span>
                              <span className="font-mono">${longTermData.results.value.graham_number?.toFixed(2)}</span>
                            </div>
                            <div className="flex justify-between items-center">
                              <span className="text-white/60">Current Price</span>
                              <span className="font-mono">${longTermData.results.value.current_price?.toFixed(2)}</span>
                            </div>
                            <div className={`text-center p-2 rounded mt-2 font-bold ${longTermData.results.value.is_undervalued ? 'bg-green-500/20 text-green-300' : 'bg-red-500/20 text-red-300'}`}>
                              {longTermData.results.value.is_undervalued ? 'UNDERVALUED' : 'OVERVALUED'}
                            </div>
                          </div>
                        </div>
                      )}
                    </div>
                  </div>
                ) : (
                  <div className="text-center py-10 text-white/40">No data available</div>
                )}
              </div>
            </div>
          )}

          {/* Input & Profile Summary */}
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            <div className="lg:col-span-2 space-y-4">
              {/* Left Column Content - Empty for now since Chat moved up */}
              {/* We can move Recent Alerts or other widgets here later */}
            </div>

            <div className="space-y-6">
              {/* Portfolio Panel */}
              <div className="bg-white/5 border border-white/10 rounded-2xl p-6 relative overflow-hidden">
                <div className="absolute top-0 right-0 p-4 opacity-10"><TrendingUp size={64} /></div>
                <div className="flex justify-between items-center mb-4">
                  <div className="flex items-center gap-2 text-green-400 font-bold uppercase text-xs tracking-wider">
                    <Activity size={14} /> Live Portfolio
                  </div>
                  <button onClick={loadPortfolio} className="p-1.5 hover:bg-white/10 rounded-full transition-colors"><RefreshCw size={12} /></button>
                </div>

                {portfolio ? (
                  <div>
                    <div className="flex justify-between items-end mb-6">
                      <div>
                        <div className="text-[10px] uppercase text-white/40 mb-1">Net Worth</div>
                        <div className="text-2xl font-bold font-mono text-white">${portfolio.total_value?.toFixed(2) ?? '0.00'}</div>
                      </div>
                      <div className={`text-right ${(portfolio.total_pl ?? 0) >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                        <div className="text-[10px] uppercase text-white/40 mb-1">Total P/L</div>
                        <div className="font-mono font-bold">{(portfolio.total_pl ?? 0) >= 0 ? '+' : ''}${portfolio.total_pl?.toFixed(2) ?? '0.00'}</div>
                        <div className="text-xs">({portfolio.total_pl_pct?.toFixed(2) ?? '0.00'}%)</div>
                      </div>
                    </div>

                    <div className="space-y-3 max-h-[300px] overflow-y-auto pr-1">
                      {(Array.isArray(portfolio.holdings) ? portfolio.holdings : []).length === 0 ? (
                        <div className="text-center text-white/30 text-xs py-4">No active holdings</div>
                      ) : (Array.isArray(portfolio.holdings) ? portfolio.holdings : []).map((h: any) => (
                        <div key={h.symbol} className="bg-black/40 p-3 rounded-xl border border-white/5 flex justify-between items-center group">
                          <div>
                            <div className="font-bold text-sm text-white">{h.symbol}</div>
                            <div className="text-xs text-white/50">{h.quantity?.toFixed(2) ?? '0.00'} shares</div>
                          </div>
                          <div className="text-right">
                            <div className="text-sm font-mono text-white">${(h.current_value ?? 0).toFixed(2)}</div>
                            <div className={`text-[10px] ${(h.pl ?? 0) >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                              {(h.pl ?? 0) >= 0 ? '+' : ''}{(h.pl ?? 0).toFixed(2)}
                            </div>
                          </div>
                          {/* Quick Actions overlay */}
                          <div className="absolute inset-0 bg-black/80 hidden group-hover:flex items-center justify-center gap-2 backdrop-blur-sm rounded-xl transition-all">
                            <button onClick={() => handleTrade(h.symbol, 'buy', 1)} className="px-3 py-1 bg-green-500/20 text-green-400 rounded-lg text-xs font-bold hover:bg-green-500/30">Buy 1</button>
                            <button onClick={() => handleTrade(h.symbol, 'sell', 1)} className="px-3 py-1 bg-red-500/20 text-red-400 rounded-lg text-xs font-bold hover:bg-red-500/30">Sell 1</button>
                            <button onClick={() => openStrategySelector(h.symbol)} className="px-3 py-1 bg-blue-500/20 text-blue-400 rounded-lg text-xs font-bold hover:bg-blue-500/30">Analyze</button>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                ) : (
                  <div className="text-center py-6 text-white/30 text-xs animate-pulse">Loading assets...</div>
                )}
              </div>

              {/* Active Profile Panel */}
              <div className="bg-white/5 border border-white/10 rounded-2xl p-6">
                <div className="flex items-center gap-2 mb-4 text-orange-400 font-bold uppercase text-xs tracking-wider">
                  <Shield size={14} /> Active Profile
                </div>
                {userProfile ? (
                  <div className="space-y-4">
                    <div>
                      <div className="text-2xl font-bold font-fraunces text-white">{userProfile.name || 'Investor'}</div>
                      <div className="text-sm text-white/60">{userProfile.primary_goal || 'Wealth Growth'}</div>
                    </div>
                    <div className="grid grid-cols-2 gap-4">
                      <div className="p-3 bg-black/40 rounded-xl">
                        <div className="text-[10px] uppercase text-white/40 mb-1">Risk Profile</div>
                        <div className="font-mono text-sm">{userProfile.risk_tolerance}</div>
                      </div>
                      <div className="p-3 bg-black/40 rounded-xl">
                        <div className="text-[10px] uppercase text-white/40 mb-1">Horizon</div>
                        <div className="font-mono text-sm">{userProfile.horizon_years} Years</div>
                      </div>
                    </div>
                  </div>
                ) : (
                  <div className="text-center py-6 text-white/40 text-sm">
                    <User size={32} className="mx-auto mb-2 opacity-50" />
                    No profile loaded
                  </div>
                )}
              </div>
            </div>
          </div>

          {/* Execution Feedback / Errors */}
          {error && (
            <div className="p-4 bg-red-500/20 border border-red-500/50 rounded-2xl text-red-400 flex items-center gap-3">
              <AlertTriangle className="shrink-0" size={20} />
              <div className="text-sm font-medium">{error}</div>
            </div>
          )}

          {/* 3-Agent POV */}
          {(pov || isTyping) && (
            <div className="space-y-4">
              <div className="flex items-center gap-2 text-white font-bold text-lg">
                <Brain className="text-purple-400" /> Multi-Perspective Analysis
                {pov?.symbol && <span className="bg-white/10 px-2 py-0.5 rounded text-sm font-mono text-white/80">{pov.symbol}</span>}
              </div>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                {isTyping && !pov ? (
                  [1, 2, 3].map(i => <div key={i} className="h-48 bg-white/5 animate-pulse rounded-2xl" />)
                ) : (
                  <>
                    <PovCard title="The Bull (Gemini)" data={pov?.bull} type="bull" />
                    <PovCard title="The Bear (Groq)" data={pov?.bear} type="bear" />
                    <PovCard title="The Neutral (DeepSeek)" data={pov?.neutral} type="neutral" />
                  </>
                )}
              </div>
            </div>
          )}



          {/* Sector Intelligence Widget */}
          <ErrorBoundary scope="Sector Intel">
            <SectorIntelWidget market={market} />
          </ErrorBoundary>

          {/* Sector News */}
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2 text-white font-bold text-lg">
                <Zap className="text-yellow-400" /> Sector Intel
              </div>
              {sectorNews && <div className="text-xs text-white/40">{sectorNews.total_items} updates</div>}
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {(sectorNews?.sectors ? Object.entries(sectorNews.sectors) : []).slice(0, 6).map(([sector, items]: [string, any[]]) => (
                <div key={sector} className="bg-white/5 border border-white/10 rounded-xl p-4">
                  <div className="font-bold text-sm text-white/90 mb-3 border-b border-white/5 pb-2">{sector}</div>
                  <div className="space-y-3">
                    {(Array.isArray(items) ? items : []).slice(0, 2).map((item, i) => {
                      if (!item) return null;
                      return (
                        <a key={i} href={item.url} target="_blank" rel="noreferrer" className="block group">
                          <div className="text-xs font-medium text-white/80 group-hover:text-blue-300 transition-colors line-clamp-2 mb-1">
                            {item.title}
                          </div>
                          <div className="text-[10px] text-white/40">{item.source} • {item.published_at ? new Date(item.published_at).toLocaleDateString() : 'Recent'}</div>
                        </a>
                      );
                    })}
                  </div>
                </div>
              ))}
            </div>
          </div>



        </div>
      </ErrorBoundary>
    </div>
  );
}
