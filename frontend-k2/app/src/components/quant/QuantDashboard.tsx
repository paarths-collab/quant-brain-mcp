import { useQuantStream } from '@/hooks/useQuantStream';
import { StrategyPanel } from './StrategyPanel';
import { RiskGauge } from './RiskGauge';
import { StockChart } from './StockChart';
import { BacktestChart } from './BacktestChart';
import { MonteCarloChart } from './MonteCarloChart';
import { DrawdownChart } from './DrawdownChart';
import { VolatilityChart } from './VolatilityChart';
import { ReturnsHistogram } from './ReturnsHistogram';

export const QuantDashboard = () => {
    const { data, isConnected, error } = useQuantStream();

    // Important UX: keep the last `data` rendered even if the socket disconnects,
    // otherwise the dashboard "goes blank" after a request completes / on WS hiccups.
    if (!data) {
        if (error) return <div className="text-red-400 bg-red-900/20 p-4 rounded-xl border border-red-500/20">WebSocket Error: {error}</div>;
        if (!isConnected) return <div className="text-white/40 animate-pulse text-center py-10">Connecting to Quant Neural Core...</div>
        return <div className="text-blue-400 animate-pulse text-center py-10">Awaiting Market Data Stream...</div>;
    }

    if (!data.strategy?.best_strategy) return <div className="text-white/40 text-center py-10">Send a query with a ticker (e.g. “analyze NVDA”) to load charts.</div>;

    return (
        <div className="space-y-6 animate-in fade-in slide-in-from-bottom-4 duration-500">
            {(!isConnected || error) && (
                <div className="text-amber-300 bg-amber-900/10 border border-amber-500/20 rounded-xl p-3 text-xs">
                    {error ? `WebSocket issue: ${error}` : "WebSocket disconnected. Reconnecting…"}
                </div>
            )}
            {/* Ticker & Signal Header */}
            <div className="flex items-center justify-between bg-black/50 border border-orange-500/20 rounded-2xl p-4 shadow-[0_0_0_1px_rgba(249,115,22,0.10),0_0_60px_rgba(249,115,22,0.06)]">
                <div className="flex items-center gap-4">
                    <div className="w-3 h-3 bg-orange-400 rounded-full animate-pulse shadow-[0_0_12px_rgba(249,115,22,0.85)]" />
                    <div className="text-xl font-bold font-fraunces text-white">{data.financial?.ticker || "WAITING"}</div>
                    <div className="font-mono text-white/60">${data.financial?.price?.toFixed(2)}</div>
                </div>
                <div className="flex gap-4">
                    <div className="text-right">
                        <div className="text-[10px] uppercase text-white/40">Action</div>
                        <div className={`font-bold ${data.strategy?.trade_levels?.action === "BUY" ? "text-green-400" : "text-white"}`}>
                            {data.strategy?.trade_levels?.action || "HOLD"}
                        </div>
                    </div>
                    <div className="text-right px-4 border-l border-white/10">
                        <div className="text-[10px] uppercase text-white/40">Entry</div>
                        <div className="font-mono text-white">${data.strategy?.trade_levels?.entry_price?.toFixed(2)}</div>
                    </div>
                </div>
            </div>

            {/* Unified Orange Theme Dashboard (all charts together) */}
            <div className="grid grid-cols-1 xl:grid-cols-12 gap-6">
                <div className="xl:col-span-4">
                    <StrategyPanel data={data.strategy} />
                </div>

                <div className="xl:col-span-8">
                    <StockChart data={data.strategy.best_strategy} />
                </div>

                <div className="xl:col-span-4">
                    <BacktestChart data={data.strategy.best_strategy} />
                </div>
                <div className="xl:col-span-4">
                    <DrawdownChart data={data.strategy.best_strategy} />
                </div>
                <div className="xl:col-span-4">
                    <VolatilityChart data={data.strategy.best_strategy} />
                </div>

                <div className="xl:col-span-6">
                    <MonteCarloChart data={data.strategy.monte_carlo} />
                </div>
                <div className="xl:col-span-6">
                    <ReturnsHistogram data={data.strategy.best_strategy} />
                </div>

                <div className="xl:col-span-8">
                    <RiskGauge data={data.risk_engine} />
                </div>

                <div className="xl:col-span-4 bg-black/50 border border-orange-500/20 rounded-2xl p-6">
                    <div className="text-[11px] font-bold text-orange-300 uppercase tracking-[0.18em] mb-3">Position Sizing</div>
                    <div className="flex justify-between items-end">
                        <div>
                            <div className="text-3xl font-bold text-white font-mono">{data.strategy?.position_sizing?.position_size_shares}</div>
                            <div className="text-xs text-white/50">Shares Recommended</div>
                        </div>
                        <div className="text-right">
                            <div className="text-xs text-white/40">Risk Amount</div>
                            <div className="text-sm font-mono text-red-300">-${data.strategy?.position_sizing?.risk_amount?.toFixed(2)}</div>
                        </div>
                    </div>
                    <div className="mt-4 pt-4 border-t border-orange-500/10 text-xs text-white/40">
                        Based on entry/stop distance and fixed-risk sizing.
                    </div>
                </div>
            </div>
        </div>
    );
};
