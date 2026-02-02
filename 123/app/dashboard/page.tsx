"use client";

import { motion } from "framer-motion";
import { TrendingUp, TrendingDown, Activity, DollarSign, BarChart3, Loader2 } from "lucide-react";
import { useEffect, useState } from "react";

interface IndexData {
    name: string;
    symbol: string;
    price: number;
    change: number;
    changePercent: number;
    isPositive: boolean;
}

export default function DashboardPage() {
    const [indices, setIndices] = useState<IndexData[]>([]);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        const fetchMarketData = async () => {
            try {
                // Fetch from our new backend endpoint
                const res = await fetch("http://localhost:8000/api/market/overview");
                if (!res.ok) throw new Error("Failed to fetch data");
                const data = await res.json();
                setIndices(data.indices || []);
            } catch (error) {
                console.error("Error fetching market data:", error);
            } finally {
                setLoading(false);
            }
        };

        fetchMarketData();
    }, []);

    // Helper to format price
    const formatPrice = (price: number) => {
        return new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' }).format(price);
    };

    // Helper to get icon based on symbol
    const getIcon = (symbol: string) => {
        if (symbol === "^GSPC") return <BarChart3 />; // S&P 500
        if (symbol === "^IXIC") return <Activity />; // Nasdaq
        if (symbol === "^DJI") return <DollarSign />; // Dow
        if (symbol === "^RUT") return <TrendingDown />; // Russell (Just reusing icon for variety, strictly could use others)
        return <Activity />;
    };

    return (
        <div className="space-y-6">
            {/* Header */}
            <div className="flex items-center justify-between">
                <div>
                    <h1 className="text-2xl font-bold text-white">Market Overview</h1>
                    <p className="text-gray-400 text-sm">Real-time global market data</p>
                </div>
                <div className="flex items-center gap-3">
                    <span className="flex items-center gap-2 px-3 py-1 rounded-full bg-green-500/10 text-green-400 text-xs border border-green-500/20">
                        <Activity size={12} />
                        Market Open
                    </span>
                    <span className="text-xs text-gray-500">Last updated: Just now</span>
                </div>
            </div>

            {/* Key Metrics Grid */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
                {loading ? (
                    // Loading Skeletons
                    [...Array(4)].map((_, i) => (
                        <div key={i} className="glass-panel p-4 h-24 animate-pulse flex items-center justify-center">
                            <Loader2 className="animate-spin text-blue-500" />
                        </div>
                    ))
                ) : (
                    indices.map((idx, i) => (
                        <MetricCard
                            key={idx.symbol}
                            title={idx.name}
                            value={formatPrice(idx.price)}
                            change={`${idx.isPositive ? "+" : ""}${idx.changePercent.toFixed(2)}%`}
                            trend={idx.isPositive ? "up" : "down"}
                            icon={getIcon(idx.symbol)}
                            index={i}
                        />
                    ))
                )}
                {/* Fallback if no data */}
                {!loading && indices.length === 0 && (
                    <div className="col-span-full text-center text-gray-500 py-4">
                        Unable to load market data. Ensure backend is running.
                    </div>
                )}
            </div>

            {/* Main Glass Panel Section (Placeholder for Chart) */}
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 h-96">
                <div className="lg:col-span-2 glass-panel p-6 flex flex-col">
                    <h3 className="text-lg font-semibold mb-4 text-blue-100">Market Performance</h3>
                    <div className="flex-1 rounded-lg bg-white/5 border border-white/5 flex items-center justify-center text-gray-500">
                        [Interactive Chart Placeholder]
                    </div>
                </div>

                <div className="glass-panel p-6 flex flex-col">
                    <h3 className="text-lg font-semibold mb-4 text-blue-100">Top Movers</h3>
                    <div className="space-y-3">
                        <MoverRow ticker="NVDA" name="NVIDIA Corp" change="+3.5%" price="678.90" />
                        <MoverRow ticker="AMD" name="Advanced Micro" change="+2.1%" price="178.20" />
                        <MoverRow ticker="TSLA" name="Tesla Inc" change="-1.4%" price="198.50" />
                        <MoverRow ticker="AAPL" name="Apple Inc" change="+0.2%" price="188.30" />
                    </div>
                </div>
            </div>
        </div>
    );
}

function MetricCard({ title, value, change, trend, icon, index }: any) {
    const isUp = trend === "up";
    return (
        <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: index * 0.1 }}
            className="glass-panel p-4 hover:bg-white/5 transition-colors cursor-pointer"
        >
            <div className="flex justify-between items-start mb-2">
                <div className="p-2 rounded-lg bg-white/5 text-gray-400">
                    {icon}
                </div>
                <span className={`flex items-center text-xs font-medium px-2 py-0.5 rounded ${isUp ? 'bg-green-500/10 text-green-400' : 'bg-red-500/10 text-red-400'}`}>
                    {isUp ? <TrendingUp size={12} className="mr-1" /> : <TrendingDown size={12} className="mr-1" />}
                    {change}
                </span>
            </div>
            <div>
                <p className="text-gray-400 text-xs uppercase tracking-wider">{title}</p>
                <h3 className="text-2xl font-bold text-white mt-1">{value}</h3>
            </div>
        </motion.div>
    );
}

function MoverRow({ ticker, name, change, price }: any) {
    const isPositive = change.startsWith("+");
    return (
        <div className="flex items-center justify-between p-3 rounded-lg hover:bg-white/5 transition-colors">
            <div className="flex items-center gap-3">
                <div className="w-8 h-8 rounded-full bg-blue-500/20 text-blue-400 flex items-center justify-center text-xs font-bold">
                    {ticker[0]}
                </div>
                <div>
                    <p className="font-bold text-sm text-white">{ticker}</p>
                    <p className="text-xs text-gray-400">{name}</p>
                </div>
            </div>
            <div className="text-right">
                <p className="text-sm font-medium text-white">${price}</p>
                <p className={`text-xs ${isPositive ? 'text-green-400' : 'text-red-400'}`}>{change}</p>
            </div>
        </div>
    );
}
