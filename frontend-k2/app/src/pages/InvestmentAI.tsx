import { useMemo, useRef, useState } from 'react';
import { Activity, Brain, RefreshCw, Send, Shield, Sparkles, Target } from 'lucide-react';
import { wealthAPI } from '@/api';

type InsightState = {
  allocation?: Record<string, number>;
  profile?: any;
  selected?: any;
  stocks?: any[];
  topSectors?: string[];
  report?: string;
  selectionRationale?: Array<{ symbol?: string; why_selected?: string }>;
  tradePlans?: Array<{
    symbol?: string;
    buy_at?: number;
    sell_at?: number;
    stop_loss?: number;
    risk_reward?: number;
    backtest_report_url?: string;
    best_strategy?: string;
  }>;
  newsContext?: {
    market_news?: Array<any>;
    sector_news?: Record<string, any[]>;
    stock_news?: Record<string, any[]>;
  };
  executionLog?: string[];
};

const samplePrompts = [
  'I earn $8,000/month, save $2,000, and want to retire in 20 years with moderate risk.',
  'I have ₹15L savings and want to invest for a house in 5 years. Conservative profile.',
  'Build a long-term portfolio for growth. I can invest $1,500/month.',
  'I have $50k to invest now and want a balanced allocation across 3 stocks.',
  'Assess my risk and suggest allocations for a 10+ year horizon.',
];

const capabilityCards = [
  { icon: Target, title: 'Goal-First Planning', desc: 'Allocations aligned to time horizon' },
  { icon: Shield, title: 'Risk Calibration', desc: 'Guardrails for concentration & volatility' },
  { icon: Brain, title: 'Stock Selection', desc: 'Data-driven picks with rationale' },
  { icon: Activity, title: 'Market Context', desc: 'News + market signals at every step' },
];

const toLabel = (value: unknown, fallback: string) => {
  if (value === null || value === undefined) return fallback;
  const text = String(value).trim();
  if (!text) return fallback;
  return text.charAt(0).toUpperCase() + text.slice(1);
};

const extractRiskLabel = (profile: any) => {
  if (!profile?.preferences) return 'Moderate';
  return toLabel(profile.preferences.risk_tolerance, 'Moderate');
};

const extractHorizonLabel = (profile: any) => {
  if (!profile?.preferences) return 'Medium';
  return toLabel(profile.preferences.horizon, 'Medium');
};

const toAllocationRows = (allocation: Record<string, number> = {}) => {
  const reserved = new Set(['stocks', 'cash', 'CASH', 'mutual_funds', 'bonds', 'gold']);
  const rows = Object.entries(allocation)
    .filter(([key]) => !reserved.has(key))
    .map(([key, value]) => ({ key, value }));
  rows.sort((a, b) => (b.value || 0) - (a.value || 0));
  return rows;
};

const normalizeNewsItem = (item: any) => {
  if (!item) return null;
  if (typeof item === 'string') {
    return { title: item, url: '' };
  }
  return {
    title: item.title || item.heading || 'Untitled',
    url: item.url || item.href || '',
    snippet: item.snippet || item.body || item.description || '',
  };
};

export default function InvestmentAI() {
  const [input, setInput] = useState('');
  const [isTyping, setIsTyping] = useState(false);
  const [market, setMarket] = useState<'US' | 'IN'>('US');
  const [insight, setInsight] = useState<InsightState | null>(null);
  const inputRef = useRef<HTMLTextAreaElement | null>(null);

  const allocationRows = useMemo(
    () => toAllocationRows(insight?.allocation || {}),
    [insight]
  );

  const tradeMap = useMemo(() => {
    const map: Record<string, any> = {};
    (insight?.tradePlans || []).forEach((plan) => {
      if (plan?.symbol) map[plan.symbol] = plan;
    });
    return map;
  }, [insight]);

  const marketNews = (insight?.newsContext?.market_news || [])
    .map(normalizeNewsItem)
    .filter(Boolean)
    .slice(0, 5) as Array<{ title: string; url?: string; snippet?: string }>;
  const sectorNewsEntries = Object.entries(insight?.newsContext?.sector_news || {});
  const stockNewsEntries = Object.entries(insight?.newsContext?.stock_news || {});

  const dominantStrategy = useMemo(() => {
    const counts: Record<string, number> = {};
    (insight?.tradePlans || []).forEach((plan) => {
      const key = plan?.best_strategy || '';
      if (!key) return;
      counts[key] = (counts[key] || 0) + 1;
    });
    const sorted = Object.entries(counts).sort((a, b) => b[1] - a[1]);
    return sorted[0]?.[0] || '—';
  }, [insight]);

  const handleSample = (text: string) => {
    setInput(text);
    inputRef.current?.focus();
  };

  const resetView = () => {
    setInput('');
    setInsight(null);
  };

  const handleSend = async () => {
    if (!input.trim()) return;
    const userContent = input.trim();
    setIsTyping(true);

    try {
      const response = await wealthAPI.analyze(userContent, market);
      const data = response?.data || {};

      if (data?.errors?.length) {
        throw new Error(data.errors.join(' | '));
      }

      setInsight({
        allocation: data.allocation || {},
        profile: data.profile,
        selected: data.selected_stock,
        stocks: data.stocks || [],
        topSectors: data.top_sectors || data.sectors || [],
        report: data.report || '',
        selectionRationale: data.selection_rationale || [],
        tradePlans: data.trade_plans || [],
        newsContext: data.news_context || {},
        executionLog: data.execution_log || [],
      });
    } catch (error: any) {
      const errorMsg = error?.response?.data?.detail || error?.message || 'Request failed';
      setInsight({
        report: `Analysis failed: ${errorMsg}`,
      });
    } finally {
      setIsTyping(false);
    }
  };

  return (
    <div className="finverse-dashboard">
      <style>{`
        @import url('https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,400;9..144,600;9..144,700&family=Manrope:wght@300;400;500;600;700&family=IBM+Plex+Mono:wght@400;500;600&display=swap');

        :root {
          --ink: #0a0d12;
          --slate: #111827;
          --mist: #eef2f8;
          --glow: rgba(255, 122, 26, 0.3);
          --accent: #ff7a1a;
          --accent-soft: rgba(255, 122, 26, 0.12);
          --border: rgba(255, 255, 255, 0.08);
        }

        .finverse-dashboard {
          min-height: 100vh;
          background: #000000;
          color: #f8fafc;
          font-family: 'Manrope', sans-serif;
          padding: 32px;
        }

        .finverse-dashboard div {
          background-color: #000000 !important;
        }

        .finverse-shell {
          max-width: 1280px;
          margin: 0 auto;
          display: flex;
          flex-direction: column;
          gap: 24px;
        }

        .finverse-header {
          display: flex;
          align-items: center;
          justify-content: space-between;
          gap: 24px;
          padding-bottom: 16px;
          border-bottom: 1px solid var(--border);
        }

        .finverse-kicker {
          text-transform: uppercase;
          letter-spacing: 0.3em;
          font-size: 11px;
          color: rgba(255,255,255,0.5);
        }

        .finverse-title {
          font-family: 'Fraunces', serif;
          font-size: clamp(28px, 4vw, 44px);
          font-weight: 700;
          margin-top: 6px;
        }

        .finverse-subtitle {
          max-width: 520px;
          color: rgba(248,250,252,0.6);
          font-size: 14px;
          line-height: 1.6;
        }

        .finverse-btn {
          border: 1px solid rgba(255,255,255,0.12);
          padding: 10px 16px;
          border-radius: 999px;
          font-size: 12px;
          text-transform: uppercase;
          letter-spacing: 0.18em;
          color: rgba(255,255,255,0.7);
          transition: all 0.2s ease;
        }

        .finverse-btn:hover {
          border-color: rgba(255,122,26,0.4);
          color: #fff;
          background: rgba(255,122,26,0.08);
        }

        .finverse-grid {
          display: grid;
          grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
          gap: 20px;
        }

        .finverse-grid--wide {
          display: grid;
          grid-template-columns: minmax(0, 1.25fr) minmax(0, 0.75fr);
          gap: 20px;
        }

        .finverse-panel {
          background: rgba(15, 23, 42, 0.6);
          border: 1px solid var(--border);
          border-radius: 20px;
          padding: 20px;
          box-shadow: 0 20px 60px rgba(15, 23, 42, 0.4);
          backdrop-filter: blur(8px);
        }

        .finverse-panel h3 {
          font-size: 12px;
          text-transform: uppercase;
          letter-spacing: 0.22em;
          color: rgba(255,255,255,0.6);
          margin-bottom: 12px;
        }

        .finverse-input {
          width: 100%;
          min-height: 120px;
          resize: vertical;
          border-radius: 14px;
          border: 1px solid rgba(255,255,255,0.12);
          background: rgba(10,13,18,0.8);
          color: #f8fafc;
          padding: 14px;
          font-size: 14px;
          outline: none;
        }

        .finverse-input:focus {
          border-color: rgba(255,122,26,0.6);
          box-shadow: 0 0 0 2px rgba(255,122,26,0.1);
        }

        .finverse-toolbar {
          display: flex;
          flex-wrap: wrap;
          gap: 12px;
          margin-top: 14px;
          align-items: center;
          justify-content: space-between;
        }

        .finverse-toggle {
          display: flex;
          gap: 8px;
          background: rgba(255,255,255,0.04);
          border-radius: 999px;
          padding: 4px;
          border: 1px solid rgba(255,255,255,0.08);
        }

        .finverse-toggle button {
          padding: 6px 14px;
          border-radius: 999px;
          font-size: 12px;
          color: rgba(255,255,255,0.6);
          transition: all 0.2s ease;
        }

        .finverse-toggle button.active {
          background: rgba(255,122,26,0.16);
          color: #fff;
          border: 1px solid rgba(255,122,26,0.4);
        }

        .finverse-primary {
          background: var(--accent);
          color: #0b0f14;
          padding: 10px 18px;
          border-radius: 12px;
          font-weight: 600;
          display: inline-flex;
          gap: 8px;
          align-items: center;
          box-shadow: 0 15px 30px rgba(255,122,26,0.25);
        }

        .finverse-chip {
          padding: 6px 12px;
          border-radius: 999px;
          border: 1px solid rgba(255,255,255,0.12);
          font-size: 12px;
          color: rgba(255,255,255,0.6);
          transition: all 0.2s ease;
        }

        .finverse-chip:hover {
          border-color: rgba(255,122,26,0.4);
          color: #fff;
        }

        .finverse-mono {
          font-family: 'IBM Plex Mono', monospace;
        }

        .finverse-metrics {
          display: grid;
          grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
          gap: 12px;
        }

        .finverse-metric {
          border: 1px solid rgba(255,255,255,0.08);
          border-radius: 16px;
          padding: 14px;
          background: rgba(10, 13, 18, 0.6);
        }

        .finverse-metric span {
          display: block;
          font-size: 11px;
          text-transform: uppercase;
          letter-spacing: 0.2em;
          color: rgba(255,255,255,0.5);
        }

        .finverse-metric strong {
          display: block;
          margin-top: 8px;
          font-size: 16px;
          font-weight: 600;
        }

        .finverse-table {
          width: 100%;
          border-collapse: collapse;
          font-size: 13px;
        }

        .finverse-table th,
        .finverse-table td {
          padding: 10px 8px;
          border-bottom: 1px solid rgba(255,255,255,0.08);
          text-align: left;
        }

        .finverse-table th {
          text-transform: uppercase;
          letter-spacing: 0.2em;
          font-size: 10px;
          color: rgba(255,255,255,0.5);
        }

        .finverse-report {
          white-space: pre-wrap;
          font-size: 12px;
          line-height: 1.6;
          color: rgba(248,250,252,0.7);
          background: rgba(10, 13, 18, 0.6);
          border-radius: 16px;
          padding: 16px;
          border: 1px solid rgba(255,255,255,0.08);
        }

        .finverse-card {
          border: 1px solid rgba(255,255,255,0.08);
          border-radius: 16px;
          padding: 14px;
          background: rgba(10, 13, 18, 0.6);
        }

        .finverse-card h4 {
          font-size: 13px;
          margin-bottom: 8px;
        }

        .finverse-link {
          color: #ffb37a;
          transition: color 0.2s ease;
        }

        .finverse-link:hover {
          color: #ffd3b3;
        }
      `}</style>

      <div className="finverse-shell">
        <header className="finverse-header">
          <div>
            <div className="finverse-kicker">Finverse Research Desk</div>
            <div className="finverse-title">Stock Recommendation Dashboard</div>
            <div className="finverse-subtitle">
              Build a portfolio-grade equity plan with live sector intelligence, multi-pass selection,
              and backtest-aware trade levels.
            </div>
          </div>
          <button type="button" className="finverse-btn" onClick={resetView}>
            <RefreshCw size={14} /> Reset
          </button>
        </header>

        <div className="finverse-grid">
          <section className="finverse-panel">
            <h3>Investor Brief</h3>
            <textarea
              ref={inputRef}
              value={input}
              onChange={(event) => setInput(event.target.value)}
              placeholder="Describe your income, goals, risk tolerance, and horizon..."
              className="finverse-input"
            />
            <div className="finverse-toolbar">
              <div className="finverse-toggle">
                <button
                  type="button"
                  className={market === 'US' ? 'active' : ''}
                  onClick={() => setMarket('US')}
                >
                  United States
                </button>
                <button
                  type="button"
                  className={market === 'IN' ? 'active' : ''}
                  onClick={() => setMarket('IN')}
                >
                  India
                </button>
              </div>
              <button
                type="button"
                onClick={handleSend}
                disabled={isTyping || !input.trim()}
                className="finverse-primary"
              >
                <Send size={16} />
                {isTyping ? 'Analyzing…' : 'Run Analysis'}
              </button>
            </div>
            <div className="mt-4 flex flex-wrap gap-2">
              {samplePrompts.map((prompt) => (
                <button
                  type="button"
                  key={prompt}
                  className="finverse-chip"
                  onClick={() => handleSample(prompt)}
                >
                  {prompt}
                </button>
              ))}
            </div>
          </section>

          <section className="finverse-panel">
            <h3>Portfolio Snapshot</h3>
            <div className="finverse-metrics">
              <div className="finverse-metric">
                <span>Risk Profile</span>
                <strong>{insight ? extractRiskLabel(insight.profile) : '—'}</strong>
              </div>
              <div className="finverse-metric">
                <span>Time Horizon</span>
                <strong>{insight ? extractHorizonLabel(insight.profile) : '—'}</strong>
              </div>
              <div className="finverse-metric">
                <span>Top Sector</span>
                <strong>{insight?.topSectors?.[0] || '—'}</strong>
              </div>
              <div className="finverse-metric">
                <span>Top Pick</span>
                <strong>{insight?.selected?.Ticker || insight?.selected?.symbol || '—'}</strong>
              </div>
              <div className="finverse-metric">
                <span>Equity Weight</span>
                <strong>
                  {insight?.allocation?.stocks !== undefined
                    ? `${Math.round(insight.allocation.stocks * 100)}%`
                    : '—'}
                </strong>
              </div>
              <div className="finverse-metric">
                <span>Dominant Strategy</span>
                <strong>{dominantStrategy}</strong>
              </div>
            </div>
          </section>
        </div>

        <div className="finverse-grid">
          {capabilityCards.map((card) => (
            <div key={card.title} className="finverse-panel">
              <h3>{card.title}</h3>
              <div className="finverse-card">
                <div className="flex items-center gap-3 text-white">
                  <card.icon size={18} />
                  <div>
                    <div className="text-sm font-semibold">{card.title}</div>
                    <div className="text-xs text-white/60">{card.desc}</div>
                  </div>
                </div>
              </div>
            </div>
          ))}
        </div>

        <div className="finverse-grid--wide">
          <section className="finverse-panel">
            <h3>Portfolio Allocation</h3>
            {allocationRows.length === 0 ? (
              <div className="finverse-card">Awaiting allocations.</div>
            ) : (
              <table className="finverse-table">
                <thead>
                  <tr>
                    <th>Stock</th>
                    <th>Company</th>
                    <th>Weight</th>
                    <th>Buy</th>
                    <th>Sell</th>
                    <th>Stop</th>
                    <th>Strategy</th>
                  </tr>
                </thead>
                <tbody>
                  {allocationRows.map((row) => {
                    const pick = (insight?.stocks || []).find((s) => s?.symbol === row.key || s?.Ticker === row.key);
                    const trade = tradeMap[row.key] || {};
                    return (
                      <tr key={row.key}>
                        <td className="finverse-mono">{row.key}</td>
                        <td>{pick?.name || pick?.Name || '—'}</td>
                        <td>{Math.round((row.value || 0) * 100)}%</td>
                        <td>{trade.buy_at ?? '—'}</td>
                        <td>{trade.sell_at ?? '—'}</td>
                        <td>{trade.stop_loss ?? '—'}</td>
                        <td>{trade.best_strategy || '—'}</td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            )}
          </section>

          <section className="finverse-panel">
            <h3>Selection Rationale</h3>
            {(insight?.selectionRationale || []).length === 0 ? (
              <div className="finverse-card">Awaiting selection rationale.</div>
            ) : (
              (insight?.selectionRationale || []).map((item, idx) => (
                <div key={`sel-${idx}`} className="finverse-card">
                  <div className="text-sm font-semibold text-white">{item.symbol}</div>
                  <div className="text-xs text-white/60">{item.why_selected || '—'}</div>
                </div>
              ))
            )}
          </section>
        </div>

        <div className="finverse-grid--wide">
          <section className="finverse-panel">
            <h3>Blueprint Report</h3>
            <div className="finverse-report">
              {insight?.report || 'Run an analysis to generate the report.'}
            </div>
          </section>
          <section className="finverse-panel">
            <h3>Trade Levels</h3>
            {(insight?.tradePlans || []).length === 0 ? (
              <div className="finverse-card">Awaiting trade levels.</div>
            ) : (
              (insight?.tradePlans || []).map((plan, idx) => (
                <div key={`${plan.symbol}-${idx}`} className="finverse-card">
                  <h4 className="text-white font-semibold">{plan.symbol}</h4>
                  <div className="finverse-mono text-xs text-white/60">
                    Buy {plan.buy_at ?? '—'} • Sell {plan.sell_at ?? '—'} • Stop {plan.stop_loss ?? '—'} •
                    R/R {plan.risk_reward ?? '—'}
                  </div>
                  <div className="mt-2 text-xs text-white/50">
                    Strategy: {plan.best_strategy || '—'}
                  </div>
                  {plan.backtest_report_url && (
                    <a
                      className="finverse-link text-xs mt-2 inline-block"
                      href={plan.backtest_report_url}
                      target="_blank"
                      rel="noreferrer"
                    >
                      View Backtest Report
                    </a>
                  )}
                </div>
              ))
            )}
          </section>
        </div>

        <div className="finverse-grid">
          <section className="finverse-panel">
            <h3>News & Signals</h3>
            <div className="finverse-card">
              <div className="text-xs uppercase tracking-wider text-white/50 mb-2">Market Headlines</div>
              {marketNews.length === 0 ? (
                <div className="text-xs text-white/60">Awaiting market headlines.</div>
              ) : (
                marketNews.map((item, idx) => (
                  <div key={`market-${idx}`} className="mb-2">
                    {item.url ? (
                      <a href={item.url} target="_blank" rel="noreferrer" className="finverse-link">
                        {item.title}
                      </a>
                    ) : (
                      <span>{item.title}</span>
                    )}
                    {item.snippet && <div className="text-[11px] text-white/50">{item.snippet}</div>}
                  </div>
                ))
              )}
            </div>
          </section>

          <section className="finverse-panel">
            <h3>Sector Highlights</h3>
            {sectorNewsEntries.length === 0 ? (
              <div className="finverse-card">Awaiting sector updates.</div>
            ) : (
              sectorNewsEntries.slice(0, 3).map(([sector, items]) => (
                <div key={sector} className="finverse-card">
                  <div className="text-sm font-semibold text-white">{sector}</div>
                  <div className="mt-2 space-y-1">
                    {(items || [])
                      .map(normalizeNewsItem)
                      .filter(Boolean)
                      .slice(0, 2)
                      .map((item: any, idx: number) => (
                        <div key={`${sector}-${idx}`}>
                          {item.url ? (
                            <a href={item.url} target="_blank" rel="noreferrer" className="finverse-link">
                              {item.title}
                            </a>
                          ) : (
                            <span>{item.title}</span>
                          )}
                        </div>
                      ))}
                  </div>
                </div>
              ))
            )}
          </section>

          <section className="finverse-panel">
            <h3>Stock Headlines</h3>
            {stockNewsEntries.length === 0 ? (
              <div className="finverse-card">Awaiting stock headlines.</div>
            ) : (
              stockNewsEntries.slice(0, 3).map(([symbol, items]) => (
                <div key={symbol} className="finverse-card">
                  <div className="text-sm font-semibold text-white">{symbol}</div>
                  <div className="mt-2 space-y-1">
                    {(items || [])
                      .map(normalizeNewsItem)
                      .filter(Boolean)
                      .slice(0, 2)
                      .map((item: any, idx: number) => (
                        <div key={`${symbol}-${idx}`}>
                          {item.url ? (
                            <a href={item.url} target="_blank" rel="noreferrer" className="finverse-link">
                              {item.title}
                            </a>
                          ) : (
                            <span>{item.title}</span>
                          )}
                        </div>
                      ))}
                  </div>
                </div>
              ))
            )}
          </section>
        </div>
      </div>
    </div>
  );
}
