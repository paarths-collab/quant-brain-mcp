import { useState, useEffect } from 'react';
import { IndianRupee, DollarSign, RefreshCw, Briefcase, TrendingUp, TrendingDown } from 'lucide-react';
import { investorProfileAPI, formatCurrency, getCurrencySymbol } from '@/api';

export default function Portfolio() {
    const [portfolio, setPortfolio] = useState<any>(null);
    const [loading, setLoading] = useState(true);
    const [market, setMarket] = useState<'IN' | 'US'>('IN');

    const fetchPortfolio = async () => {
        setLoading(true);
        try {
            const { data } = await investorProfileAPI.getPortfolio();
            setPortfolio(data);
        } catch (e) {
            console.error(e);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchPortfolio();
    }, []);

    const symbol = getCurrencySymbol(market);

    if (loading) return <div className="text-white">Loading...</div>;

    return (
        <div className="space-y-6">
            <div className="flex items-center justify-between">
                <div>
                    <h1 className="font-display text-3xl font-bold text-white">Portfolio</h1>
                    <p className="text-white/60">Detailed Holdings & Performance</p>
                </div>
                <button onClick={fetchPortfolio} className="p-2 bg-white/5 border border-white/10 rounded-lg hover:bg-white/10">
                    <RefreshCw className="w-4 h-4 text-white" />
                </button>
            </div>

            {!portfolio || !portfolio.holdings || portfolio.holdings.length === 0 ? (
                <div className="text-center py-20 text-white/40 border border-white/10 rounded-xl">
                    <Briefcase className="mx-auto mb-4 opacity-50" size={48} />
                    <h3 className="text-xl font-bold">No investments yet</h3>
                    <p>Use the Investment AI or Technical Analysis tools to find trades.</p>
                </div>
            ) : (
                <>
                    <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                        <div className="p-6 bg-white/5 border border-white/10 rounded-xl">
                            <div className="text-sm text-white/60 mb-2">Total Value</div>
                            <div className="text-3xl font-bold text-white">{formatCurrency(portfolio.total_value, market)}</div>
                        </div>
                        <div className="p-6 bg-white/5 border border-white/10 rounded-xl">
                            <div className="text-sm text-white/60 mb-2">Total Invested</div>
                            <div className="text-3xl font-bold text-white">{formatCurrency(portfolio.total_invested, market)}</div>
                        </div>
                        <div className="p-6 bg-white/5 border border-white/10 rounded-xl">
                            <div className="text-sm text-white/60 mb-2">Total P&L</div>
                            <div className={`text-3xl font-bold ${portfolio.total_pl >= 0 ? 'text-green-500' : 'text-red-500'}`}>
                                {portfolio.total_pl >= 0 ? '+' : ''}{formatCurrency(portfolio.total_pl, market)}
                                <span className="text-lg ml-2">({portfolio.total_pl_pct.toFixed(2)}%)</span>
                            </div>
                        </div>
                    </div>

                    <div className="bg-white/5 border border-white/10 rounded-xl overflow-hidden">
                        <table className="w-full text-left">
                            <thead className="bg-white/5">
                                <tr>
                                    <th className="p-4 text-white/60 font-medium">Symbol</th>
                                    <th className="p-4 text-white/60 font-medium text-right">Qty</th>
                                    <th className="p-4 text-white/60 font-medium text-right">Avg Price</th>
                                    <th className="p-4 text-white/60 font-medium text-right">LTP</th>
                                    <th className="p-4 text-white/60 font-medium text-right">Value</th>
                                    <th className="p-4 text-white/60 font-medium text-right">P&L</th>
                                </tr>
                            </thead>
                            <tbody>
                                {portfolio.holdings.map((h: any) => (
                                    <tr key={h.symbol} className="border-t border-white/5 hover:bg-white/5">
                                        <td className="p-4 font-bold text-white">{h.symbol}</td>
                                        <td className="p-4 text-right text-white font-mono">{h.quantity}</td>
                                        <td className="p-4 text-right text-white font-mono">{formatCurrency(h.avg_price, market)}</td>
                                        <td className="p-4 text-right text-white font-mono">{formatCurrency(h.current_price, market)}</td>
                                        <td className="p-4 text-right text-white font-mono">{formatCurrency(h.current_value, market)}</td>
                                        <td className={`p-4 text-right font-mono font-bold ${h.pl >= 0 ? 'text-green-500' : 'text-red-500'}`}>
                                            {h.pl >= 0 ? '+' : ''}{formatCurrency(h.pl, market)} <br />
                                            <span className="text-xs opacity-70">({h.pl_pct.toFixed(2)}%)</span>
                                        </td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                </>
            )}
        </div>
    );
}
