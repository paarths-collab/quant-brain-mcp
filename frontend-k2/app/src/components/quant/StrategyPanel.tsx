import { Activity, Brain, TrendingUp, Minus, Cpu } from 'lucide-react';
import type { QuantData } from '@/hooks/useQuantStream';

export const StrategyPanel = ({ data }: { data: QuantData['strategy'] }) => {
    if (!data) return null;

    const { regime, best_strategy, ai_reasoning, all_strategies } = data;

    return (
        <div className="bg-black/50 border border-orange-500/20 rounded-2xl p-6 space-y-6 shadow-[0_0_0_1px_rgba(249,115,22,0.08),0_0_40px_rgba(249,115,22,0.05)]">
            {/* Header: Market Regime */}
            <div className="flex justify-between items-start">
                <div>
                    <div className="text-[11px] font-bold text-orange-300 uppercase tracking-[0.18em] mb-1">Market Regime</div>
                    <div className="text-2xl font-bold font-fraunces text-white flex items-center gap-2">
                        {regime.regime === 'Bullish Trending' && <TrendingUp className="text-green-500" />}
                        {regime.regime === 'Sideways / Bearish' && <Minus className="text-yellow-500" />}
                        {regime.regime === 'High Volatility' && <Activity className="text-red-500" />}
                        {regime.regime}
                    </div>
                    <div className="text-sm text-white/50 mt-1">
                        Volatility: {(regime.volatility * 100).toFixed(1)}% | Trend: {regime.trend_signal}
                    </div>
                </div>
                <div className="text-right">
                    <div className="px-3 py-1 bg-orange-500/10 text-orange-200 rounded-full text-xs font-bold border border-orange-500/20 flex items-center gap-2">
                        <Cpu size={14} className="text-orange-300" /> AI Meta-Controller
                    </div>
                </div>
            </div>

            {/* AI Decision Block */}
            <div className="bg-gradient-to-br from-orange-500/15 via-black to-black border border-orange-500/20 rounded-xl p-5 relative overflow-hidden">
                <Brain className="absolute top-4 right-4 text-orange-500/15" size={64} />
                <div className="relative z-10">
                    <div className="text-[11px] text-orange-200 font-bold uppercase tracking-[0.18em] mb-2">Strategy Selection</div>
                    <div className="text-3xl font-bold text-white mb-2">{best_strategy.strategy}</div>
                    <div className="text-sm text-white/75 italic leading-relaxed">"{ai_reasoning}"</div>
                </div>
            </div>

            {/* Strategy Comparison Table */}
            <div className="space-y-3">
                <div className="text-xs font-bold text-white/40 uppercase">Performance Matrix</div>
                <div className="space-y-2">
                    {all_strategies.map(s => (
                        <div key={s.strategy} className={`flex justify-between items-center p-3 rounded-lg border ${s.strategy === best_strategy.strategy ? 'bg-orange-500/10 border-orange-500/25' : 'bg-black/30 border-white/5'}`}>
                            <div className="flex items-center gap-3">
                                <div className={`w-2 h-2 rounded-full ${s.strategy === best_strategy.strategy ? 'bg-orange-400 shadow-[0_0_12px_rgba(249,115,22,0.65)]' : 'bg-white/20'}`} />
                                <span className="font-bold text-sm text-white">{s.strategy}</span>
                            </div>
                            <div className="flex gap-4 text-xs">
                                <div className="text-right">
                                    <div className="text-white/40">Return</div>
                                    <div className={s.return >= 0 ? 'text-green-400' : 'text-red-400'}>{s.return.toFixed(2)}%</div>
                                </div>
                                <div className="text-right">
                                    <div className="text-white/40">Win Rate</div>
                                    <div className="text-orange-200">{s.win_rate.toFixed(0)}%</div>
                                </div>
                            </div>
                        </div>
                    ))}
                </div>
            </div>
        </div>
    );
};
