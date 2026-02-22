import { Shield, AlertTriangle } from 'lucide-react';
import type { QuantData } from '@/hooks/useQuantStream';

export const RiskGauge = ({ data }: { data: QuantData['risk_engine'] }) => {
    if (!data) return null;

    const { VaR, CVaR, Max_Drawdown, Stress_Test } = data;

    return (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {/* Left: Risk Metrics */}
            <div className="bg-black/50 border border-orange-500/20 rounded-2xl p-6">
                <div className="flex items-center gap-2 mb-6">
                    <Shield className="text-orange-300" size={20} />
                    <h3 className="font-bold text-white">Risk Engine</h3>
                </div>

                <div className="space-y-4">
                    <div className="flex justify-between items-center pb-2 border-b border-white/5">
                        <span className="text-white/60 text-sm">Value at Risk (95%)</span>
                        <span className="font-mono font-bold text-red-400">{(VaR * 100).toFixed(2)}%</span>
                    </div>
                    <div className="flex justify-between items-center pb-2 border-b border-white/5">
                        <span className="text-white/60 text-sm">Conditional VaR (Expected Shortfall)</span>
                        <span className="font-mono font-bold text-red-500">{(CVaR * 100).toFixed(2)}%</span>
                    </div>
                    <div className="flex justify-between items-center">
                        <span className="text-white/60 text-sm">Max Drawdown (1Y)</span>
                        <span className="font-mono font-bold text-orange-400">{(Max_Drawdown * 100).toFixed(2)}%</span>
                    </div>
                </div>
            </div>

            {/* Right: Stress Test */}
            <div className="bg-black/50 border border-orange-500/20 rounded-2xl p-6 relative overflow-hidden">
                <AlertTriangle className="absolute -top-4 -right-4 text-orange-500/10" size={100} />
                <div className="relative z-10">
                    <div className="text-[11px] font-bold text-orange-300 uppercase tracking-[0.18em] mb-2">Stress Test</div>
                    <h3 className="text-xl font-bold text-white mb-4">Market Crash (-20%)</h3>

                    <div className="flex items-end gap-4">
                        <div>
                            <div className="text-sm text-white/50">Projected Loss</div>
                            <div className="text-3xl font-bold text-red-400 font-mono">-${Stress_Test?.loss?.toFixed(2)}</div>
                        </div>
                        <div className="mb-1">
                            <div className="text-xs text-white/40">Price Impact</div>
                            <div className="text-sm font-mono text-white/80">${Stress_Test?.original_price?.toFixed(2)} → ${Stress_Test?.stressed_price?.toFixed(2)}</div>
                        </div>
                    </div>

                    <div className="mt-4 pt-4 border-t border-orange-500/15 text-xs text-white/40">
                        *Simulation assumes instant -20% gap down with current holdings.
                    </div>
                </div>
            </div>
        </div>
    );
};
