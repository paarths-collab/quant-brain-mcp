import { useEffect, useState } from 'react';
import { Search, Brain, TrendingUp, TrendingDown, DollarSign, IndianRupee, RefreshCw, AlertTriangle, ExternalLink, Download } from 'lucide-react';
import { sentimentAPI, formatCurrency, getCurrencySymbol, researchAPI, formatLargeNumber } from '@/api';
import { useSearchParams } from 'react-router-dom';

export default function Research() {
  const [searchParams] = useSearchParams();
  const [searchInput, setSearchInput] = useState('');
  const [symbol, setSymbol] = useState('');
  const [market, setMarket] = useState('us');
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [data, setData] = useState<any>(null);
  const [reportLink, setReportLink] = useState<string | null>(null);
  const [reportLoading, setReportLoading] = useState(false);
  const [reportError, setReportError] = useState<string | null>(null);
  const marketData = data?.market_data || {};
  const currencySymbol = data ? getCurrencySymbol(data.market || marketData.market) : '$';
  const currentPrice = marketData.current_price ?? data?.price ?? 0;
  const dayChange = marketData.day_change ?? data?.day_change ?? 0;
  const dayChangePct = marketData.day_change_pct ?? data?.day_change_pct ?? 0;
  const companyName = data?.name || marketData.company_name || data?.symbol || '';

  const formatPercent = (value: any) => {
    if (value === null || value === undefined || value === '') return '-';
    const num = Number(value);
    if (Number.isNaN(num)) return '-';
    return `${num.toFixed(2)}%`;
  };

  const formatRatio = (value: any) => {
    if (value === null || value === undefined || value === '') return '-';
    const num = Number(value);
    if (Number.isNaN(num)) return '-';
    return num.toFixed(2);
  };

  const formatValue = (value: any) => {
    if (value === null || value === undefined || value === '') return '-';
    return value;
  };

  const formatLarge = (value: any) => {
    if (value === null || value === undefined || value === '') return '-';
    return formatLargeNumber(Number(value), data?.market || market);
  };

  const fetchSentiment = async (sym: string, mkt: string) => {
    setIsLoading(true);
    setError(null);
    setReportLink(null);
    setReportError(null);
    try {
      const response = await sentimentAPI.analyze(sym, mkt);
      setData(response.data);
      setSymbol(response.data.symbol);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to fetch analysis');
      setData(null);
    } finally {
      setIsLoading(false);
    }
  };

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    const input = searchInput.toUpperCase().trim();
    if (input) {
      fetchSentiment(input, market);
      setSearchInput('');
    }
  };

  const handleDownloadReport = async () => {
    setReportLoading(true);
    setReportError(null);
    try {
      const fullUrl = researchAPI.downloadReport('portfolio_report.html');
      setReportLink(fullUrl);
    } catch (err: any) {
      setReportError(err?.response?.data?.detail || 'HTML report not found.');
    } finally {
      setReportLoading(false);
    }
  };

  const getSentimentColor = (sentiment: number) => {
    if (sentiment >= 0.6) return 'text-green-500';
    if (sentiment >= 0.4) return 'text-yellow-500';
    return 'text-red-500';
  };

  const suggestions = market === 'india' ? ['RELIANCE', 'TCS', 'INFY', 'HDFCBANK'] : ['AAPL', 'MSFT', 'GOOGL', 'NVDA', 'TSLA'];

  useEffect(() => {
    const sym = searchParams.get('symbol');
    const mkt = searchParams.get('market');
    if (sym) {
      const nextMarket = mkt || market;
      setMarket(nextMarket);
      fetchSentiment(sym.toUpperCase(), nextMarket);
    }
  }, [searchParams]);

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="font-display text-3xl font-bold text-white">AI Research</h1>
          <p className="text-white/60">Sentiment analysis powered by AI + Reddit</p>
        </div>
        <div className="flex gap-2">
          <button onClick={() => setMarket('us')} className={`flex items-center gap-2 px-4 py-2 rounded-lg ${market === 'us' ? 'bg-orange-500 text-white' : 'bg-white/5 text-white/60'}`}><DollarSign size={14} />US</button>
          <button onClick={() => setMarket('india')} className={`flex items-center gap-2 px-4 py-2 rounded-lg ${market === 'india' ? 'bg-orange-500 text-white' : 'bg-white/5 text-white/60'}`}><IndianRupee size={14} />India</button>
        </div>
      </div>

      <form onSubmit={handleSearch} className="flex items-center gap-2 px-4 py-3 bg-white/5 border border-white/10 rounded-lg">
        <Search size={18} className="text-white/40" />
        <input type="text" placeholder={`Search ${market === 'india' ? 'NSE' : 'US'} symbol...`} value={searchInput} onChange={e => setSearchInput(e.target.value)} className="flex-1 bg-transparent text-white outline-none" />
        <button type="submit" disabled={isLoading} className="px-4 py-1 bg-orange-500 text-white rounded text-sm hover:bg-orange-600 disabled:opacity-50">
          {isLoading ? <RefreshCw size={14} className="animate-spin" /> : 'Analyze'}
        </button>
      </form>

      {!data && !isLoading && !error && (
        <div className="flex gap-2">
          <span className="text-white/60 text-sm">Try:</span>
          {suggestions.map(s => <button key={s} onClick={() => fetchSentiment(s, market)} className="px-3 py-1 bg-white/5 hover:bg-white/10 rounded text-sm text-white">{s}</button>)}
        </div>
      )}

      {error && (
        <div className="p-6 bg-red-500/20 border border-red-500/50 rounded-xl flex items-center gap-4">
          <AlertTriangle className="text-red-500" size={32} />
          <div><h3 className="font-bold text-white">Analysis Failed</h3><p className="text-white/80 text-sm">{error}</p></div>
        </div>
      )}

      {isLoading && (
        <div className="p-12 flex flex-col items-center justify-center">
          <Brain size={48} className="text-orange-400 mb-4 animate-pulse" />
          <h3 className="text-xl font-bold text-white">Analyzing {searchInput || symbol}...</h3>
          <p className="text-white/60 text-sm mt-2">Fetching market data, Reddit sentiment & AI analysis</p>
        </div>
      )}

      {data && !isLoading && (
        <div className="space-y-4">
          <div className="p-6 bg-white/5 border border-white/10 rounded-xl">
            <div className="flex items-start justify-between">
              <div>
                <h2 className="text-3xl font-bold text-white">{data.symbol}</h2>
                <p className="text-white/60">{companyName}</p>
              </div>
              <div className="text-right">
                <div className="text-3xl font-bold text-white">{formatCurrency(currentPrice, data.market)}</div>
                <span className={`text-sm ${dayChangePct >= 0 ? 'text-green-500' : 'text-red-500'}`}>
                  {dayChangePct >= 0 ? <TrendingUp className="inline" size={14} /> : <TrendingDown className="inline" size={14} />}
                  {dayChangePct >= 0 ? '+' : ''}{dayChangePct.toFixed(2)}% ({dayChange >= 0 ? '+' : ''}{formatCurrency(dayChange, data.market)})
                </span>
              </div>
            </div>
            <div className="mt-4 flex flex-wrap items-center gap-3">
              <button
                onClick={handleDownloadReport}
                disabled={reportLoading}
                className="flex items-center gap-2 px-4 py-2 rounded-lg bg-orange-500 text-white text-sm hover:bg-orange-600 disabled:opacity-50"
              >
                <Download size={14} />
                {reportLoading ? 'Opening…' : 'Open Portfolio Report (HTML)'}
              </button>
              {reportLink && (
                <a className="text-xs text-orange-300 hover:text-orange-200" href={reportLink} target="_blank" rel="noreferrer">
                  Open report
                </a>
              )}
              {reportError && <div className="text-xs text-red-400">{reportError}</div>}
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="p-4 bg-white/5 border border-white/10 rounded-lg">
              <div className="text-xs text-white/40 mb-1">AI Sentiment Score</div>
              <div className={`text-3xl font-bold ${getSentimentColor(data.sentiment?.overall || 0.5)}`}>
                {((data.sentiment?.overall || 0.5) * 100).toFixed(0)}%
              </div>
              <div className="text-xs text-white/60 mt-1">{data.sentiment?.summary || 'Neutral'}</div>
            </div>
            <div className="p-4 bg-white/5 border border-white/10 rounded-lg">
              <div className="text-xs text-white/40 mb-1">Reddit Sentiment</div>
              <div className={`text-3xl font-bold ${getSentimentColor(data.reddit_sentiment?.score || 0.5)}`}>
                {((data.reddit_sentiment?.score || 0.5) * 100).toFixed(0)}%
              </div>
              <div className="text-xs text-white/60 mt-1">{data.reddit_sentiment?.mentions || 0} mentions</div>
            </div>
            <div className="p-4 bg-white/5 border border-white/10 rounded-lg">
              <div className="text-xs text-white/40 mb-1">Recommendation</div>
              <div className="text-2xl font-bold text-white uppercase">{data.recommendation || 'HOLD'}</div>
              <div className="text-xs text-white/60 mt-1">{data.outlook || 'Neutral'}</div>
            </div>
          </div>

          {(marketData.business_summary || data.summary) && (
            <div className="p-6 bg-white/5 border border-white/10 rounded-xl space-y-4">
              {marketData.business_summary && (
                <div>
                  <h3 className="font-semibold text-white mb-2">Company Description</h3>
                  <p className="text-white/80 text-sm leading-relaxed">{marketData.business_summary}</p>
                </div>
              )}
              {data.summary && (
                <div>
                  <h3 className="font-semibold text-white mb-2">AI Summary</h3>
                  <p className="text-white/80 text-sm leading-relaxed">{data.summary}</p>
                </div>
              )}
            </div>
          )}

          <div className="p-6 bg-white/5 border border-white/10 rounded-xl">
            <h3 className="font-semibold text-white mb-4">Company Snapshot</h3>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <div className="p-3 bg-white/5 rounded-lg"><div className="text-xs text-white/40">Market Cap</div><div className="text-white">{formatValue(marketData.market_cap_formatted)}</div></div>
              <div className="p-3 bg-white/5 rounded-lg"><div className="text-xs text-white/40">Volume</div><div className="text-white">{formatValue(marketData.volume)}</div></div>
              <div className="p-3 bg-white/5 rounded-lg"><div className="text-xs text-white/40">Avg Volume</div><div className="text-white">{formatValue(marketData.avg_volume)}</div></div>
              <div className="p-3 bg-white/5 rounded-lg"><div className="text-xs text-white/40">Sector</div><div className="text-white">{formatValue(marketData.sector)}</div></div>
              <div className="p-3 bg-white/5 rounded-lg"><div className="text-xs text-white/40">Industry</div><div className="text-white">{formatValue(marketData.industry)}</div></div>
              <div className="p-3 bg-white/5 rounded-lg"><div className="text-xs text-white/40">P/E</div><div className="text-white">{formatValue(marketData.pe_ratio)}</div></div>
              <div className="p-3 bg-white/5 rounded-lg"><div className="text-xs text-white/40">Forward P/E</div><div className="text-white">{formatValue(marketData.forward_pe)}</div></div>
              <div className="p-3 bg-white/5 rounded-lg"><div className="text-xs text-white/40">EPS</div><div className="text-white">{formatValue(marketData.eps)}</div></div>
              <div className="p-3 bg-white/5 rounded-lg"><div className="text-xs text-white/40">Dividend Yield</div><div className="text-white">{formatPercent(marketData.dividend_yield ? marketData.dividend_yield * 100 : marketData.dividend_yield)}</div></div>
              <div className="p-3 bg-white/5 rounded-lg"><div className="text-xs text-white/40">Beta</div><div className="text-white">{formatValue(marketData.beta)}</div></div>
              <div className="p-3 bg-white/5 rounded-lg"><div className="text-xs text-white/40">52W High</div><div className="text-white">{formatCurrency(marketData['52w_high'] || marketData.fiftyTwoWeekHigh || 0, data.market)}</div></div>
              <div className="p-3 bg-white/5 rounded-lg"><div className="text-xs text-white/40">52W Low</div><div className="text-white">{formatCurrency(marketData['52w_low'] || marketData.fiftyTwoWeekLow || 0, data.market)}</div></div>
              <div className="p-3 bg-white/5 rounded-lg"><div className="text-xs text-white/40">Revenue</div><div className="text-white">{formatValue(marketData.revenue_formatted)}</div></div>
              <div className="p-3 bg-white/5 rounded-lg"><div className="text-xs text-white/40">Profit Margin</div><div className="text-white">{formatPercent(marketData.profit_margin ? marketData.profit_margin * 100 : marketData.profit_margin)}</div></div>
              <div className="p-3 bg-white/5 rounded-lg"><div className="text-xs text-white/40">6M Change</div><div className="text-white">{formatPercent(marketData.price_change_6m_pct)}</div></div>
              <div className="p-3 bg-white/5 rounded-lg"><div className="text-xs text-white/40">Target Mean</div><div className="text-white">{formatCurrency(marketData.target_mean_price || 0, data.market)}</div></div>
              <div className="p-3 bg-white/5 rounded-lg"><div className="text-xs text-white/40">Analyst Rec</div><div className="text-white">{formatValue(marketData.recommendation_key)}</div></div>
            </div>
          </div>

          <div className="p-6 bg-white/5 border border-white/10 rounded-xl">
            <h3 className="font-semibold text-white mb-4">Quarterly Snapshot</h3>
            <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
              <div className="p-3 bg-white/5 rounded-lg">
                <div className="text-xs text-white/40">Quarter End</div>
                <div className="text-white">{formatValue(marketData.quarter_end)}</div>
              </div>
              <div className="p-3 bg-white/5 rounded-lg">
                <div className="text-xs text-white/40">Revenue (Q)</div>
                <div className="text-white">{formatLarge(marketData.sales_q)}</div>
              </div>
              <div className="p-3 bg-white/5 rounded-lg">
                <div className="text-xs text-white/40">Revenue QoQ</div>
                <div className="text-white">{formatPercent(marketData.sales_q_var)}</div>
              </div>
              <div className="p-3 bg-white/5 rounded-lg">
                <div className="text-xs text-white/40">Net Profit (Q)</div>
                <div className="text-white">{formatLarge(marketData.net_profit_q)}</div>
              </div>
              <div className="p-3 bg-white/5 rounded-lg">
                <div className="text-xs text-white/40">Profit QoQ</div>
                <div className="text-white">{formatPercent(marketData.profit_q_var)}</div>
              </div>
            </div>
            <div className="mt-4">
              <div className="text-xs text-white/40 mb-2">Quarterly Revenue (Q1–Q4)</div>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                {(marketData.quarterly_revenue || []).slice(0, 4).map((item: any, idx: number) => (
                  <div key={`${item.quarter}-${idx}`} className="p-3 bg-white/5 rounded-lg">
                    <div className="text-xs text-white/40">{item.quarter}</div>
                    <div className="text-white">{formatLarge(item.revenue)}</div>
                    {item.period && <div className="text-[11px] text-white/40 mt-1">{item.period}</div>}
                  </div>
                ))}
                {(marketData.quarterly_revenue || []).length === 0 && (
                  <div className="text-white/40 text-sm col-span-full">Quarterly revenue not available.</div>
                )}
              </div>
            </div>
          </div>

          <div className="p-6 bg-white/5 border border-white/10 rounded-xl">
            <h3 className="font-semibold text-white mb-4">Investor Metrics (Yahoo Finance)</h3>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="p-4 bg-white/5 border border-white/10 rounded-lg">
                <div className="text-sm text-white/60 mb-3">Valuation</div>
                <div className="grid grid-cols-2 gap-3 text-sm">
                  <div><div className="text-xs text-white/40">P/E (Trailing)</div><div className="text-white">{formatRatio(marketData.pe_ratio)}</div></div>
                  <div><div className="text-xs text-white/40">P/E (Forward)</div><div className="text-white">{formatRatio(marketData.forward_pe)}</div></div>
                  <div><div className="text-xs text-white/40">PEG</div><div className="text-white">{formatRatio(marketData.peg_ratio)}</div></div>
                  <div><div className="text-xs text-white/40">P/B</div><div className="text-white">{formatRatio(marketData.price_to_book)}</div></div>
                  <div><div className="text-xs text-white/40">EV/EBITDA</div><div className="text-white">{formatRatio(marketData.ev_to_ebitda)}</div></div>
                  <div><div className="text-xs text-white/40">Enterprise Value</div><div className="text-white">{formatValue(marketData.enterprise_value)}</div></div>
                </div>
              </div>

              <div className="p-4 bg-white/5 border border-white/10 rounded-lg">
                <div className="text-sm text-white/60 mb-3">Financial Health</div>
                <div className="grid grid-cols-2 gap-3 text-sm">
                  <div><div className="text-xs text-white/40">Debt/Equity</div><div className="text-white">{formatRatio(marketData.debt_to_equity)}</div></div>
                  <div><div className="text-xs text-white/40">Current Ratio</div><div className="text-white">{formatRatio(marketData.current_ratio)}</div></div>
                  <div><div className="text-xs text-white/40">Free Cash Flow</div><div className="text-white">{formatValue(marketData.free_cashflow)}</div></div>
                </div>
              </div>

              <div className="p-4 bg-white/5 border border-white/10 rounded-lg">
                <div className="text-sm text-white/60 mb-3">Profitability</div>
                <div className="grid grid-cols-2 gap-3 text-sm">
                  <div><div className="text-xs text-white/40">ROE</div><div className="text-white">{formatPercent(marketData.roe ? marketData.roe * 100 : marketData.roe)}</div></div>
                  <div><div className="text-xs text-white/40">Operating Margin</div><div className="text-white">{formatPercent(marketData.operating_margins ? marketData.operating_margins * 100 : marketData.operating_margins)}</div></div>
                </div>
              </div>

              <div className="p-4 bg-white/5 border border-white/10 rounded-lg">
                <div className="text-sm text-white/60 mb-3">Dividends & Income</div>
                <div className="grid grid-cols-2 gap-3 text-sm">
                  <div><div className="text-xs text-white/40">Dividend Yield</div><div className="text-white">{formatPercent(marketData.dividend_yield ? marketData.dividend_yield * 100 : marketData.dividend_yield)}</div></div>
                  <div><div className="text-xs text-white/40">Payout Ratio</div><div className="text-white">{formatPercent(marketData.payout_ratio ? marketData.payout_ratio * 100 : marketData.payout_ratio)}</div></div>
                  <div><div className="text-xs text-white/40">Ex-Dividend</div><div className="text-white">{formatValue(marketData.ex_dividend_date)}</div></div>
                </div>
              </div>

              <div className="p-4 bg-white/5 border border-white/10 rounded-lg">
                <div className="text-sm text-white/60 mb-3">Risk & Volatility</div>
                <div className="grid grid-cols-2 gap-3 text-sm">
                  <div><div className="text-xs text-white/40">Beta</div><div className="text-white">{formatRatio(marketData.beta)}</div></div>
                  <div><div className="text-xs text-white/40">Short Ratio</div><div className="text-white">{formatRatio(marketData.short_ratio)}</div></div>
                  <div><div className="text-xs text-white/40">Short % Float</div><div className="text-white">{formatPercent(marketData.short_percent_float ? marketData.short_percent_float * 100 : marketData.short_percent_float)}</div></div>
                </div>
              </div>

              <div className="p-4 bg-white/5 border border-white/10 rounded-lg">
                <div className="text-sm text-white/60 mb-3">Analyst</div>
                <div className="grid grid-cols-2 gap-3 text-sm">
                  <div><div className="text-xs text-white/40">Target Mean</div><div className="text-white">{formatCurrency(marketData.target_mean_price || 0, data.market)}</div></div>
                  <div><div className="text-xs text-white/40">Recommendation</div><div className="text-white">{formatValue(marketData.recommendation_key)}</div></div>
                  <div><div className="text-xs text-white/40">Analyst Count</div><div className="text-white">{formatValue(marketData.analyst_count)}</div></div>
                </div>
              </div>
            </div>
          </div>

          <div className="p-6 bg-white/5 border border-white/10 rounded-xl">
            <h3 className="font-semibold text-white mb-4">Recent News</h3>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {(data.news?.articles || []).map((article: any, idx: number) => (
                <a
                  key={`${article.url}-${idx}`}
                  href={article.url}
                  target="_blank"
                  rel="noreferrer"
                  className="block p-4 bg-white/5 border border-white/10 rounded-lg hover:bg-white/10 transition"
                >
                  <div className="flex items-start justify-between gap-3">
                    <div>
                      <div className="text-white font-semibold">{article.title || 'Untitled'}</div>
                      <div className="text-xs text-white/50 mt-1">{article.source || 'DuckDuckGo'} • {article.published || ''}</div>
                    </div>
                    <ExternalLink size={16} className="text-white/40 shrink-0" />
                  </div>
                  {article.snippet && <div className="text-xs text-white/60 mt-3">{article.snippet}</div>}
                </a>
              ))}
              {(data.news?.articles || []).length === 0 && (
                <div className="text-white/40 text-sm">No recent DuckDuckGo news found.</div>
              )}
            </div>
          </div>

          <div className="p-6 bg-white/5 border border-white/10 rounded-xl">
            <h3 className="font-semibold text-white mb-2">Supply Chain (Experimental)</h3>
            <p className="text-xs text-white/50 mb-4">US: SEC filings. India: crawler over public sources.</p>
            {data.supply_chain?.status === 'error' && (
              <div className="text-xs text-red-400 mb-3">Supply chain fetch failed. Check server logs or SEC access.</div>
            )}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="bg-white/5 border border-white/10 rounded-lg p-4">
                <div className="text-sm text-white/60 mb-2">Customers</div>
                <div className="space-y-3">
                  {(data.supply_chain?.customers || []).map((c: any, idx: number) => (
                    <div key={`cust-${idx}`} className="p-3 rounded-lg bg-white/5 border border-white/10">
                      <div className="text-white font-semibold text-sm">{c.name}</div>
                      {c.evidence && <div className="text-xs text-white/60 mt-1">{c.evidence}</div>}
                      {c.source_url && (
                        <a href={c.source_url} target="_blank" rel="noreferrer" className="text-xs text-orange-300 inline-flex items-center gap-1 mt-2">
                          Source <ExternalLink size={12} />
                        </a>
                      )}
                    </div>
                  ))}
                  {(data.supply_chain?.customers || []).length === 0 && (
                    <div className="text-white/40 text-sm">No customer mentions found.</div>
                  )}
                </div>
              </div>
              <div className="bg-white/5 border border-white/10 rounded-lg p-4">
                <div className="text-sm text-white/60 mb-2">Suppliers</div>
                <div className="space-y-3">
                  {(data.supply_chain?.suppliers || []).map((s: any, idx: number) => (
                    <div key={`sup-${idx}`} className="p-3 rounded-lg bg-white/5 border border-white/10">
                      <div className="text-white font-semibold text-sm">{s.name}</div>
                      {s.evidence && <div className="text-xs text-white/60 mt-1">{s.evidence}</div>}
                      {s.source_url && (
                        <a href={s.source_url} target="_blank" rel="noreferrer" className="text-xs text-orange-300 inline-flex items-center gap-1 mt-2">
                          Source <ExternalLink size={12} />
                        </a>
                      )}
                    </div>
                  ))}
                  {(data.supply_chain?.suppliers || []).length === 0 && (
                    <div className="text-white/40 text-sm">No supplier mentions found.</div>
                  )}
                </div>
              </div>
            </div>
            <div className="mt-4 text-xs text-white/50">
              {(data.supply_chain?.notes || []).map((note: string, idx: number) => (
                <div key={`note-${idx}`}>• {note}</div>
              ))}
            </div>
            {data.supply_chain?.sources?.length ? (
              <div className="mt-4">
                <div className="text-xs text-white/50 mb-2">Sources</div>
                <div className="flex flex-wrap gap-2">
                  {data.supply_chain.sources.map((src: any, idx: number) => (
                    <a key={`src-${idx}`} href={src.url} target="_blank" rel="noreferrer" className="px-3 py-1 rounded-full bg-white/5 border border-white/10 text-xs text-white/60 hover:text-white">
                      {src.title || 'Source'}
                    </a>
                  ))}
                </div>
              </div>
            ) : null}
          </div>
        </div>
      )}
    </div>
  );
}
