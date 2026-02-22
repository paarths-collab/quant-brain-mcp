import { useState, useEffect, useRef, useCallback } from 'react';

export type QuantData = {
    financial: {
        ticker: string;
        price: number;
    };
    strategy: {
        regime: {
            regime: string;
            volatility: number;
            trend_signal: string;
        };
        best_strategy: {
            strategy: string;
            signal: string;
            return: number;
            win_rate: number;
            last_signal: number;
            equity_curve: Array<{ time: string; value: number }>;
            signals: Array<{ time: string; type: string; price: number }>;
            price_data: Array<{
                time: string;
                open: number;
                high: number;
                low: number;
                close: number;
                volume: number;
            }>;
        };
        all_strategies: Array<{
            strategy: string;
            return: number;
            win_rate: number;
        }>;
        ai_reasoning: string;
        trade_levels: {
            action: string;
            entry_price: number;
            stop_loss: number;
            take_profit: number;
        };
        position_sizing: {
            position_size_shares: number;
            risk_amount: number;
        };
        monte_carlo: {
            expected_price: number;
            worst_case: number;
            best_case: number;
            simulation_paths: number[][]; // Array of arrays of prices
            days?: number;
        };
    };
    risk_engine: {
        VaR: number;
        CVaR: number;
        Max_Drawdown: number;
        Stress_Test: {
            loss: number;
            stressed_price: number;
            original_price: number;
        }
    };
    report?: string;
};

const DEFAULT_API_BASE =
  (import.meta.env.VITE_API_BASE_URL || import.meta.env.VITE_API_BASE || 'http://127.0.0.1:8001').replace(/\/$/, '');

const DEFAULT_WS_URL = `${DEFAULT_API_BASE.replace(/^http/i, 'ws')}/ws/live`;

export const useQuantStream = (url: string = DEFAULT_WS_URL) => {
    const [data, setData] = useState<QuantData | null>(null);
    const [isConnected, setIsConnected] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const ws = useRef<WebSocket | null>(null);
    const reconnectTimer = useRef<number | null>(null);
    const reconnectAttempts = useRef(0);
    const shouldReconnect = useRef(true);
    const connectRef = useRef<() => void>(() => {});

    const connect = useCallback(() => {
        try {
            console.log("Attempting WebSocket connection to:", url);
            if (reconnectTimer.current) {
                window.clearTimeout(reconnectTimer.current);
                reconnectTimer.current = null;
            }

            if (ws.current && (ws.current.readyState === WebSocket.OPEN || ws.current.readyState === WebSocket.CONNECTING)) {
                try { ws.current.close(); } catch { /* noop */ }
            }

            ws.current = new WebSocket(url);

            ws.current.onopen = () => {
                console.log("Quant Stream Connected Successfully");
                setIsConnected(true);
                setError(null);
                reconnectAttempts.current = 0;
            };

            ws.current.onmessage = (event) => {
                try {
                    const parsed = JSON.parse(event.data);
                    setData(parsed);
                } catch (e) {
                    console.error("Parse Error", e);
                }
            };

            ws.current.onclose = (event) => {
                console.log("Quant Stream Disconnected", event.code, event.reason);
                setIsConnected(false);

                if (!shouldReconnect.current) return;

                // Exponential backoff (1s → 2s → 4s … max 15s)
                const attempt = reconnectAttempts.current++;
                const delay = Math.min(15000, 1000 * Math.pow(2, attempt));
                reconnectTimer.current = window.setTimeout(() => {
                    connectRef.current();
                }, delay);
            };

            ws.current.onerror = (err) => {
                console.error("WebSocket Error Details:", err);
                setError("Connection Failed - Check Console");
            };

        } catch (err) {
            console.error("WebSocket Init Error:", err);
            setError("Failed to initialize WebSocket");
        }
    }, [url]);

    const sendQuery = (query: string, ticker?: string) => {
        if (ws.current && ws.current.readyState === WebSocket.OPEN) {
            ws.current.send(JSON.stringify({ query, ticker }));
        } else {
            setError("Socket not open");
        }
    };

    useEffect(() => {
        shouldReconnect.current = true;
        connectRef.current = connect;
        // Defer connect to avoid "setState-in-effect" lint false positives.
        const t = window.setTimeout(() => {
            if (shouldReconnect.current) connectRef.current();
        }, 0);
        return () => {
            shouldReconnect.current = false;
            window.clearTimeout(t);
            if (reconnectTimer.current) {
                window.clearTimeout(reconnectTimer.current);
                reconnectTimer.current = null;
            }
            ws.current?.close();
        };
    }, [connect]);

    return { data, isConnected, error, sendQuery };
};
