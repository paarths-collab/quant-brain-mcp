import math
import pandas as pd
import numpy as np
from typing import Dict, Any, List, Optional
from .core.market_data_service import fetch_candles
from .core.strategy_adapter import get_strategy


def _safe_number(value: Any) -> Optional[float]:
    try:
        val = float(value)
    except Exception:
        return None
    return val if math.isfinite(val) else None


def _resolve_market(symbol: str, market: str) -> str:
    m = (market or "us").lower()
    s = (symbol or "").upper()
    if s.endswith(".NS") or s.endswith(".BO"):
        return "india"
    return m


def _fetch_candles_with_fallback(
    symbol: str,
    interval: str,
    range_period: str,
    start_date: Optional[str],
    end_date: Optional[str],
    market: str,
) -> List[Dict[str, Any]]:
    effective_market = _resolve_market(symbol, market)
    candles = fetch_candles(
        symbol,
        interval,
        range_period,
        start=start_date,
        end=end_date,
        market=effective_market,
    )
    if candles:
        return candles

    # If market was likely wrong, retry once with the alternate market.
    alternate = "india" if effective_market == "us" else "us"
    return fetch_candles(
        symbol,
        interval,
        range_period,
        start=start_date,
        end=end_date,
        market=alternate,
    )


def prepare_candles_df(candles: List[Dict]) -> pd.DataFrame:
    df = pd.DataFrame(candles)
    df.rename(columns={
        "date": "Date",
        "open": "Open",
        "high": "High",
        "low": "Low",
        "close": "Close",
        "volume": "Volume"
    }, inplace=True)
    return df


def _compute_equity_from_signals(res_df: pd.DataFrame, initial_capital: float, strategy_name: str) -> pd.DataFrame:
    df = res_df.copy()
    stateful_strategies = {
        "momentum",
        "mean_reversion",
        "rsi_reversal",
        "rsi_momentum",
    }
    if strategy_name in stateful_strategies:
        df['position'] = df['signal'].shift(1).fillna(0)
    else:
        df['position'] = df['signal'].replace(0, np.nan).ffill().shift(1).fillna(0)
    df['pct_change'] = df['Close'].pct_change().fillna(0)
    df['strategy_returns'] = df['position'] * df['pct_change']
    df['equity'] = initial_capital * (1 + df['strategy_returns']).cumprod()
    df['peak'] = df['equity'].cummax()
    df['drawdown'] = (df['equity'] - df['peak']) / df['peak']
    return df


def run_backtest_on_df(
    df: pd.DataFrame,
    strategy_name: str,
    initial_capital: float = 100000,
    **params
) -> pd.DataFrame:
    strategy = get_strategy(strategy_name, **params)
    res_df = strategy.generate_signals(df.copy())
    return _compute_equity_from_signals(res_df, initial_capital, strategy_name)


def _compute_drawdown_duration(drawdown_series: pd.Series) -> int:
    max_duration = 0
    current = 0
    for val in drawdown_series.fillna(0).tolist():
        if val < 0:
            current += 1
            max_duration = max(max_duration, current)
        else:
            current = 0
    return int(max_duration)


def _trade_reason(strategy_name: str, side: str) -> str:
    reasons = {
        "ema_crossover": {
            "entry_long": "Fast EMA crossed above slow EMA",
            "entry_short": "Fast EMA crossed below slow EMA",
            "exit_long": "Fast EMA crossed below slow EMA",
            "exit_short": "Fast EMA crossed above slow EMA",
        },
        "macd": {
            "entry_long": "MACD crossed above signal line",
            "entry_short": "MACD crossed below signal line",
            "exit_long": "MACD crossed below signal line",
            "exit_short": "MACD crossed above signal line",
        },
        "mean_reversion": {
            "entry_long": "Price fell below lower band",
            "exit_long": "Price reverted back above mean",
            "entry_short": "Price rose above upper band",
            "exit_short": "Price reverted back below mean",
        },
        "momentum": {
            "entry_long": "Momentum turned positive",
            "exit_long": "Momentum turned negative",
        },
        "rsi_reversal": {
            "entry_long": "RSI crossed above lower threshold",
            "exit_long": "RSI crossed below upper threshold",
        },
        "rsi_momentum": {
            "entry_long": "RSI crossed above lower threshold with trend filter",
            "exit_long": "RSI crossed below upper threshold",
        },
    }
    return reasons.get(strategy_name, {}).get(side, "Signal triggered")


def _extract_trades(res_df: pd.DataFrame, strategy_name: str) -> List[Dict[str, Any]]:
    trades: List[Dict[str, Any]] = []
    positions = res_df['position'].fillna(0).tolist()
    current_trade = None
    entry_index = None

    for i in range(len(res_df)):
        row = res_df.iloc[i]
        pos = positions[i]
        prev_pos = positions[i - 1] if i > 0 else 0

        if prev_pos == 0 and pos != 0:
            side = "long" if pos > 0 else "short"
            current_trade = {
                "side": side,
                "entryDate": str(row['Date']),
                "entryPrice": _safe_number(row['Close']),
                "entryReason": _trade_reason(strategy_name, f"entry_{side}")
            }
            entry_index = i
            continue

        if prev_pos != 0 and pos == 0 and current_trade:
            exit_price = _safe_number(row['Close'])
            entry_price = current_trade.get("entryPrice")
            side = current_trade.get("side", "long")
            pnl = None
            pnl_pct = None
            if entry_price is not None and exit_price is not None:
                if side == "long":
                    pnl = exit_price - entry_price
                else:
                    pnl = entry_price - exit_price
                pnl_pct = (pnl / entry_price) * 100 if entry_price else None

            trades.append({
                **current_trade,
                "exitDate": str(row['Date']),
                "exitPrice": exit_price,
                "exitReason": _trade_reason(strategy_name, f"exit_{side}"),
                "pnl": _safe_number(pnl),
                "pnlPct": _safe_number(pnl_pct),
                "duration": int(i - (entry_index or i))
            })
            current_trade = None
            entry_index = None
            continue

        if prev_pos != 0 and pos != 0 and pos != prev_pos and current_trade:
            exit_price = _safe_number(row['Close'])
            entry_price = current_trade.get("entryPrice")
            side = current_trade.get("side", "long")
            pnl = None
            pnl_pct = None
            if entry_price is not None and exit_price is not None:
                if side == "long":
                    pnl = exit_price - entry_price
                else:
                    pnl = entry_price - exit_price
                pnl_pct = (pnl / entry_price) * 100 if entry_price else None

            trades.append({
                **current_trade,
                "exitDate": str(row['Date']),
                "exitPrice": exit_price,
                "exitReason": _trade_reason(strategy_name, f"exit_{side}"),
                "pnl": _safe_number(pnl),
                "pnlPct": _safe_number(pnl_pct),
                "duration": int(i - (entry_index or i))
            })

            new_side = "long" if pos > 0 else "short"
            current_trade = {
                "side": new_side,
                "entryDate": str(row['Date']),
                "entryPrice": _safe_number(row['Close']),
                "entryReason": _trade_reason(strategy_name, f"entry_{new_side}")
            }
            entry_index = i

    return trades


def _compute_advanced_trade_metrics(trades: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Compute advanced trade-level metrics."""
    if not trades:
        return {
            "profitFactor": None, "expectancy": None, "sqn": None,
            "avgWin": None, "avgLoss": None,
            "maxConsecutiveWins": 0, "maxConsecutiveLosses": 0,
            "bestTrade": None, "worstTrade": None,
        }

    pnls = [t.get('pnlPct', 0) or 0 for t in trades]
    wins = [p for p in pnls if p > 0]
    losses = [p for p in pnls if p < 0]

    gross_profit = sum(wins) if wins else 0
    gross_loss = abs(sum(losses)) if losses else 0
    profit_factor = _safe_number(gross_profit / gross_loss) if gross_loss > 0 else None

    avg_win = _safe_number(np.mean(wins)) if wins else 0
    avg_loss = _safe_number(np.mean(losses)) if losses else 0
    n = len(pnls)
    win_rate = len(wins) / n if n > 0 else 0
    loss_rate = 1 - win_rate
    expectancy = _safe_number(win_rate * avg_win + loss_rate * avg_loss)

    std_pnl = float(np.std(pnls)) if len(pnls) > 1 else 0
    sqn = _safe_number((np.mean(pnls) / std_pnl) * np.sqrt(n)) if std_pnl > 0 else None

    # Max consecutive wins / losses
    max_con_w, max_con_l, cur_w, cur_l = 0, 0, 0, 0
    for p in pnls:
        if p > 0:
            cur_w += 1; cur_l = 0
            max_con_w = max(max_con_w, cur_w)
        elif p < 0:
            cur_l += 1; cur_w = 0
            max_con_l = max(max_con_l, cur_l)
        else:
            cur_w = 0; cur_l = 0

    return {
        "profitFactor": round(profit_factor, 2) if profit_factor is not None else None,
        "expectancy": round(expectancy, 2) if expectancy is not None else None,
        "sqn": round(sqn, 2) if sqn is not None else None,
        "avgWin": round(avg_win, 2) if avg_win else None,
        "avgLoss": round(avg_loss, 2) if avg_loss else None,
        "maxConsecutiveWins": max_con_w,
        "maxConsecutiveLosses": max_con_l,
        "bestTrade": round(max(pnls), 2) if pnls else None,
        "worstTrade": round(min(pnls), 2) if pnls else None,
    }


def _run_monte_carlo(returns: pd.Series, simulations: int = 1000, initial_capital: float = 100000) -> Dict[str, Any]:
    """Run Monte Carlo simulation with VaR, CVaR, and full simulation paths."""
    if returns.empty:
        return {"simulations": 0, "histogram": [], "percentiles": {}, "riskMetrics": {}, "simulationPaths": [], "percentilePaths": {}}

    clean = returns.dropna().values
    if len(clean) == 0:
        return {"simulations": 0, "histogram": [], "percentiles": {}, "riskMetrics": {}, "simulationPaths": [], "percentilePaths": {}}

    n_steps = len(clean)
    # Downsample to max 50 points for charting
    max_points = 50
    step_size = max(1, n_steps // max_points)
    sample_indices = list(range(0, n_steps, step_size))
    if sample_indices[-1] != n_steps - 1:
        sample_indices.append(n_steps - 1)

    sim_returns = []
    sim_max_drawdowns = []
    all_equity_curves = []  # Store all simulation paths

    for _ in range(simulations):
        sample = np.random.choice(clean, size=n_steps, replace=True)
        total = (1 + sample).prod() - 1
        sim_returns.append(total * 100)

        # Full equity curve for this simulation
        equity = np.cumprod(1 + sample)
        peak = np.maximum.accumulate(equity)
        dd = ((equity - peak) / peak).min() * 100
        sim_max_drawdowns.append(dd)

        # Downsample the equity curve
        sampled = equity[sample_indices]
        all_equity_curves.append(sampled)

    sim_arr = np.array(sim_returns)
    equity_matrix = np.array(all_equity_curves)  # shape: (simulations, n_sample_points)

    # Build simulation paths for charting (all paths) — in dollar values
    simulation_paths = []
    for i in range(simulations):
        path = [round(float(equity_matrix[i, j]) * initial_capital, 2) for j in range(len(sample_indices))]
        simulation_paths.append(path)

    # Compute percentile paths across all simulations at each time step — in dollar values
    percentile_paths = {}
    for pct_name, pct_val in [("p5", 5), ("p25", 25), ("p50", 50), ("p75", 75), ("p95", 95)]:
        pct_curve = np.percentile(equity_matrix, pct_val, axis=0)
        percentile_paths[pct_name] = [round(float(v) * initial_capital, 2) for v in pct_curve]

    bins = 30
    counts, edges = np.histogram(sim_arr, bins=bins)
    histogram = []
    for i in range(len(counts)):
        mid = (edges[i] + edges[i + 1]) / 2
        histogram.append({
            "return": _safe_number(mid),
            "count": int(counts[i])
        })

    percentiles = {
        "p5": _safe_number(np.percentile(sim_arr, 5)),
        "p10": _safe_number(np.percentile(sim_arr, 10)),
        "p25": _safe_number(np.percentile(sim_arr, 25)),
        "p50": _safe_number(np.percentile(sim_arr, 50)),
        "p75": _safe_number(np.percentile(sim_arr, 75)),
        "p90": _safe_number(np.percentile(sim_arr, 90)),
        "p95": _safe_number(np.percentile(sim_arr, 95)),
    }

    # VaR and CVaR at 95% confidence
    var_95 = float(np.percentile(sim_arr, 5))  # 5th percentile = 95% VaR
    cvar_95 = float(sim_arr[sim_arr <= var_95].mean()) if (sim_arr <= var_95).any() else var_95
    ruin_count = int((sim_arr < -50).sum())  # Ruin = losing > 50%
    median_dd = float(np.median(sim_max_drawdowns))

    return {
        "simulations": simulations,
        "histogram": histogram,
        "percentiles": percentiles,
        "riskMetrics": {
            "var95": _safe_number(round(var_95, 2)),
            "cvar95": _safe_number(round(cvar_95, 2)),
            "ruinProbability": round((ruin_count / simulations) * 100, 2),
            "medianMaxDrawdown": _safe_number(round(median_dd, 2)),
            "worstCase": _safe_number(round(float(sim_arr.min()), 2)),
            "bestCase": _safe_number(round(float(sim_arr.max()), 2)),
            "meanReturn": _safe_number(round(float(sim_arr.mean()), 2)),
        },
        "simulationPaths": simulation_paths,
        "percentilePaths": percentile_paths,
        "pathSteps": len(sample_indices),
    }

def run_backtest_service(
    symbol: str,
    strategy_name: str,
    range_period: str = "1y",
    interval: str = "1d",
    market: str = "us",
    initial_capital: float = 100000,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    **params
) -> Dict[str, Any]:
    """
    Runs a backtest for a given strategy and symbol.
    Returns D3-ready equity curve, drawdown, and signals.
    """
    # 1. Fetch Data
    # fetch_candles returns list of dictionaries. Convert to DataFrame.
    candles = _fetch_candles_with_fallback(
        symbol=symbol,
        interval=interval,
        range_period=range_period,
        start_date=start_date,
        end_date=end_date,
        market=market,
    )
    if not candles:
        return {"error": f"No data found for symbol '{symbol}' in market '{market}'. Try a valid ticker or switch market."}

    df = prepare_candles_df(candles)
    
    # Ensure Date is index if needed or keep as column. 
    # Strategies might need reset index or not. 
    # EMACrossoverStrategy expects columns.
    
    # 2. Initialize Strategy
    try:
        res_df = run_backtest_on_df(df, strategy_name, initial_capital=initial_capital, **params)
    except Exception as e:
        return {"error": f"Strategy error: {str(e)}"}
    
    # 5. Format for Frontend
    # Need lists for charts: {date, equity}, {date, drawdown}
    chart_data = []
    trade_signals = []
    
    for idx, row in res_df.iterrows():
        # Ensure date is string
        date_str = str(row['Date'])
        
        data_point = {
            "date": date_str,
            "equity": round(row['equity'], 2),
            "drawdown": round(row['drawdown'] * 100, 2), # Percentage
            "close": row['Close']
        }
        
        # Add all other numeric columns (indicators) to data_point
        # Exclude standard columns we already handled or don't want
        exclude_cols = {'Date', 'Open', 'High', 'Low', 'Close', 'Volume', 'equity', 'drawdown', 'strategy_returns', 'peak', 'pct_change', 'position', 'signal'}
        
        for col in res_df.columns:
            if col not in exclude_cols:
                val = row[col]
                # Check if numeric
                if isinstance(val, (int, float, np.number)):
                    # Check for nan/inf
                    if not math.isnan(val) and not math.isinf(val):
                        data_point[col] = val
                    else:
                        data_point[col] = None
        
        chart_data.append(data_point)
        
        if 'signal' in row:
            if row['signal'] == 1:
                trade_signals.append({"date": date_str, "type": "buy", "price": _safe_number(row['Close'])})
            elif row['signal'] == -1:
                trade_signals.append({"date": date_str, "type": "sell", "price": _safe_number(row['Close'])})

    # Summary Metrics
    total_return = ((res_df['equity'].iloc[-1] - initial_capital) / initial_capital) * 100
    max_drawdown = res_df['drawdown'].min() * 100
    
    # Calculate additional metrics
    returns = res_df['strategy_returns']
    sharpe_ratio = (returns.mean() / returns.std()) * np.sqrt(252) if returns.std() != 0 else 0
    downside = returns[returns < 0]
    sortino_ratio = (returns.mean() / downside.std()) * np.sqrt(252) if downside.std() != 0 else 0
    annual_volatility = float(returns.std() * np.sqrt(252) * 100) if returns.std() != 0 else 0

    periods = max(len(res_df), 1)
    annual_return = (res_df['equity'].iloc[-1] / initial_capital) ** (252 / periods) - 1 if periods > 1 else 0
    calmar_ratio = annual_return / abs(res_df['drawdown'].min()) if res_df['drawdown'].min() != 0 else 0
    max_dd_duration = _compute_drawdown_duration(res_df['drawdown'])

    # Time in market
    positions = res_df['position'].fillna(0)
    time_in_market = round((positions != 0).sum() / len(positions) * 100, 1) if len(positions) > 0 else 0

    trades = _extract_trades(res_df, strategy_name)
    total_trades = len(trades)
    win_rate = 0.0
    if total_trades > 0:
        wins = len([t for t in trades if (t.get('pnl') or 0) > 0])
        win_rate = (wins / total_trades) * 100

    # Advanced trade metrics
    adv = _compute_advanced_trade_metrics(trades)
    
    return {
        "symbol": symbol,
        "strategy": strategy_name,
        "metrics": {
            "totalReturn": round(total_return, 2),
            "maxDrawdown": round(max_drawdown, 2),
            "sharpeRatio": round(sharpe_ratio, 2),
            "sortinoRatio": round(sortino_ratio, 2),
            "calmarRatio": round(calmar_ratio, 2),
            "maxDrawdownDuration": max_dd_duration,
            "winRate": round(win_rate, 1),
            "totalTrades": total_trades,
            "initialCapital": initial_capital,
            "finalEquity": round(res_df['equity'].iloc[-1], 2),
            "annualVolatility": round(annual_volatility, 2),
            "timeInMarket": time_in_market,
            "profitFactor": adv["profitFactor"],
            "expectancy": adv["expectancy"],
            "sqn": adv["sqn"],
            "avgWin": adv["avgWin"],
            "avgLoss": adv["avgLoss"],
            "maxConsecutiveWins": adv["maxConsecutiveWins"],
            "maxConsecutiveLosses": adv["maxConsecutiveLosses"],
            "bestTrade": adv["bestTrade"],
            "worstTrade": adv["worstTrade"],
        },
        "chartData": chart_data,
        "trades": trades,
        "equity_curve": [{**d, "value": d["equity"], "benchmark": d["close"]} for d in chart_data],
        "monteCarlo": _run_monte_carlo(returns, initial_capital=initial_capital)
    }


def run_multi_strategy_backtest(
    symbol: str,
    strategy_names: List[str],
    range_period: str = "1y",
    interval: str = "1d",
    market: str = "us",
    initial_capital: float = 100000,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    params_dict: Dict[str, Dict] = None
) -> Dict[str, Any]:
    """
    Runs backtest for multiple strategies and compares them.
    Returns combined equity curves and per-strategy metrics.
    """
    if params_dict is None:
        params_dict = {}
    
    # Fetch data once
    candles = _fetch_candles_with_fallback(
        symbol=symbol,
        interval=interval,
        range_period=range_period,
        start_date=start_date,
        end_date=end_date,
        market=market,
    )
    if not candles:
        return {"error": f"No data found for symbol '{symbol}' in market '{market}'. Try a valid ticker or switch market."}
        
    df = pd.DataFrame(candles)
    df.rename(columns={
        "date": "Date",
        "open": "Open", 
        "high": "High", 
        "low": "Low", 
        "close": "Close", 
        "volume": "Volume"
    }, inplace=True)
    
    strategy_results = {}
    combined_chart_data = []
    
    # Generate color palette for strategies
    colors = ['#3b82f6', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6', '#ec4899']
    
    for idx, strategy_name in enumerate(strategy_names):
        params = params_dict.get(strategy_name, {})
        
        try:
            strategy = get_strategy(strategy_name, **params)
            res_df = strategy.generate_signals(df.copy())
            res_df = _compute_equity_from_signals(res_df, initial_capital, strategy_name)
            
            # Calculate metrics
            total_return = ((res_df['equity'].iloc[-1] - initial_capital) / initial_capital) * 100
            max_drawdown = res_df['drawdown'].min() * 100
            returns = res_df['strategy_returns']
            sharpe_ratio = (returns.mean() / returns.std()) * np.sqrt(252) if returns.std() != 0 else 0
            downside = returns[returns < 0]
            sortino_ratio = (returns.mean() / downside.std()) * np.sqrt(252) if downside.std() != 0 else 0
            annual_volatility = float(returns.std() * np.sqrt(252) * 100) if returns.std() != 0 else 0

            periods = max(len(res_df), 1)
            annual_return = (res_df['equity'].iloc[-1] / initial_capital) ** (252 / periods) - 1 if periods > 1 else 0
            calmar_ratio = annual_return / abs(res_df['drawdown'].min()) if res_df['drawdown'].min() != 0 else 0
            max_dd_duration = _compute_drawdown_duration(res_df['drawdown'])

            # Time in market
            positions = res_df['position'].fillna(0)
            time_in_market = round((positions != 0).sum() / len(positions) * 100, 1) if len(positions) > 0 else 0

            trades = _extract_trades(res_df, strategy_name)
            total_trades = len(trades)
            win_rate = 0.0
            if total_trades > 0:
                wins = len([t for t in trades if (t.get('pnl') or 0) > 0])
                win_rate = (wins / total_trades) * 100

            # Advanced trade metrics
            adv = _compute_advanced_trade_metrics(trades)
            
            strategy_results[strategy_name] = {
                "name": strategy_name,
                "color": colors[idx % len(colors)],
                "metrics": {
                    "totalReturn": round(total_return, 2),
                    "maxDrawdown": round(max_drawdown, 2),
                    "sharpeRatio": round(sharpe_ratio, 2),
                    "sortinoRatio": round(sortino_ratio, 2),
                    "calmarRatio": round(calmar_ratio, 2),
                    "maxDrawdownDuration": max_dd_duration,
                    "winRate": round(win_rate, 1),
                    "totalTrades": total_trades,
                    "finalEquity": round(res_df['equity'].iloc[-1], 2),
                    "annualVolatility": round(annual_volatility, 2),
                    "timeInMarket": time_in_market,
                    "profitFactor": adv["profitFactor"],
                    "expectancy": adv["expectancy"],
                    "sqn": adv["sqn"],
                    "avgWin": adv["avgWin"],
                    "avgLoss": adv["avgLoss"],
                    "maxConsecutiveWins": adv["maxConsecutiveWins"],
                    "maxConsecutiveLosses": adv["maxConsecutiveLosses"],
                    "bestTrade": adv["bestTrade"],
                    "worstTrade": adv["worstTrade"],
                },
                "trades": trades,
                "monteCarlo": _run_monte_carlo(returns, initial_capital=initial_capital),
                "equityCurve": [
                    {"date": str(row['Date']), "value": round(row['equity'], 2)}
                    for _, row in res_df.iterrows()
                ]
            }
            
        except Exception as e:
            strategy_results[strategy_name] = {
                "name": strategy_name,
                "error": str(e),
                "metrics": None
            }
    
    # Build combined chart data (merge all equity curves)
    # Use first strategy's dates as reference
    first_valid = None
    for name, result in strategy_results.items():
        if "equityCurve" in result:
            first_valid = result
            break
    
    if first_valid:
        for i, point in enumerate(first_valid["equityCurve"]):
            data_point = {"date": point["date"]}
            for name, result in strategy_results.items():
                if "equityCurve" in result and i < len(result["equityCurve"]):
                    data_point[name] = result["equityCurve"][i]["value"]
            combined_chart_data.append(data_point)
    
    # Rank strategies by total return
    ranked = sorted(
        [(name, res["metrics"]["totalReturn"]) 
         for name, res in strategy_results.items() 
         if res.get("metrics")],
        key=lambda x: x[1],
        reverse=True
    )
    
    return {
        "symbol": symbol,
        "mode": "multi_strategy",
        "strategies": strategy_results,
        "combinedChartData": combined_chart_data,
        "ranking": [{"strategy": name, "return": ret} for name, ret in ranked],
        "initialCapital": initial_capital
    }


def generate_backtest_report(
    symbol: str,
    strategies: List[str],
    results: Dict[str, Any],
    report_format: str = "html"
) -> Dict[str, Any]:
    """
    Generates a downloadable backtest report.
    Returns HTML or CSV content.
    """
    from datetime import datetime
    from pathlib import Path
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    reports_dir = Path(__file__).parent.parent / "reports"
    reports_dir.mkdir(exist_ok=True)
    
    if report_format == "csv":
        return generate_csv_report(symbol, strategies, results, reports_dir, timestamp)
    if report_format == "pdf":
        html_result = generate_html_report(symbol, strategies, results, reports_dir, timestamp)
        if html_result.get("error"):
            return html_result

        html_filename = html_result.get("filename")
        if not html_filename:
            return {"error": "HTML report generation failed."}

        html_path = reports_dir / html_filename
        pdf_filename = html_filename.replace(".html", ".pdf")
        pdf_path = reports_dir / pdf_filename

        from backend.utils.pdf_generator import convert_html_to_pdf

        conversion = convert_html_to_pdf(str(html_path), str(pdf_path))
        if not conversion.get("success"):
            return {"error": conversion.get("error", "PDF conversion failed.")}

        return {
            "success": True,
            "filename": pdf_filename,
            "downloadUrl": f"/api/backtest/report/download/{pdf_filename}"
        }

    return generate_html_report(symbol, strategies, results, reports_dir, timestamp)


def generate_csv_report(
    symbol: str,
    strategies: List[str],
    results: Dict[str, Any],
    reports_dir,
    timestamp: str
) -> Dict[str, Any]:
    """Generate CSV format backtest report."""
    import csv
    import io
    
    filename = f"backtest_{symbol}_{timestamp}.csv"
    filepath = reports_dir / filename
    
    try:
        with open(filepath, 'w', newline='') as csvfile:
            writer = csv.writer(csvfile)
            
            # Header
            writer.writerow(['Backtest Report'])
            writer.writerow(['Symbol', symbol])
            writer.writerow(['Generated', timestamp])
            writer.writerow(['Strategies', ', '.join(strategies)])
            writer.writerow([])
            
            # Check if multi-strategy or single
            if results.get('mode') == 'multi_strategy':
                # Multi-strategy results
                writer.writerow(['Strategy Comparison'])
                writer.writerow(['Strategy', 'Total Return %', 'Max Drawdown %', 'Sharpe Ratio', 'Trades', 'Final Equity'])
                
                for strat_id, strat_data in results.get('strategies', {}).items():
                    if strat_data.get('metrics'):
                        m = strat_data['metrics']
                        writer.writerow([
                            strat_id,
                            m.get('totalReturn', 0),
                            m.get('maxDrawdown', 0),
                            m.get('sharpeRatio', 0),
                            m.get('totalTrades', 0),
                            m.get('finalEquity', 0)
                        ])
                
                # Ranking
                writer.writerow([])
                writer.writerow(['Ranking'])
                for i, rank in enumerate(results.get('ranking', []), 1):
                    writer.writerow([f"#{i}", rank['strategy'], f"{rank['return']}%"])
            else:
                # Single strategy
                metrics = results.get('metrics', {})
                writer.writerow(['Metrics'])
                writer.writerow(['Total Return', f"{metrics.get('totalReturn', 0)}%"])
                writer.writerow(['Sharpe Ratio', metrics.get('sharpeRatio', 0)])
                writer.writerow(['Max Drawdown', f"{metrics.get('maxDrawdown', 0)}%"])
                writer.writerow(['Win Rate', f"{metrics.get('winRate', 0)}%"])
                writer.writerow(['Total Trades', metrics.get('totalTrades', 0)])
                writer.writerow(['Final Equity', metrics.get('finalEquity', 0)])
        
        return {
            "success": True,
            "filename": filename,
            "downloadUrl": f"/api/backtest/report/download/{filename}"
        }
    except Exception as e:
        return {"error": str(e)}


def generate_html_report(
    symbol: str,
    strategies: List[str],
    results: Dict[str, Any],
    reports_dir,
    timestamp: str
) -> Dict[str, Any]:
    """Generate HTML format backtest report."""
    from datetime import datetime
    
    filename = f"backtest_{symbol}_{timestamp}.html"
    filepath = reports_dir / filename
    
    try:
        is_multi = results.get('mode') == 'multi_strategy'
        
        # Build metrics table
        if is_multi:
            metrics_html = "<h2>Strategy Comparison</h2><table><tr><th>Strategy</th><th>Return</th><th>Max DD</th><th>Sharpe</th><th>Trades</th><th>Final Value</th></tr>"
            for strat_id, strat_data in results.get('strategies', {}).items():
                if strat_data.get('metrics'):
                    m = strat_data['metrics']
                    ret_class = 'positive' if m.get('totalReturn', 0) >= 0 else 'negative'
                    metrics_html += f"""
                    <tr>
                        <td><strong>{strat_id}</strong></td>
                        <td class="{ret_class}">{m.get('totalReturn', 0):+.2f}%</td>
                        <td class="negative">{m.get('maxDrawdown', 0):.2f}%</td>
                        <td>{m.get('sharpeRatio', 0):.2f}</td>
                        <td>{m.get('totalTrades', 0)}</td>
                        <td>${m.get('finalEquity', 0):,.2f}</td>
                    </tr>
                    """
            metrics_html += "</table>"
            
            # Ranking
            ranking_html = "<h2>🏆 Strategy Ranking</h2><ol>"
            for rank in results.get('ranking', []):
                ret_class = 'positive' if rank['return'] >= 0 else 'negative'
                ranking_html += f"<li><strong>{rank['strategy']}</strong>: <span class='{ret_class}'>{rank['return']:+.2f}%</span></li>"
            ranking_html += "</ol>"
        else:
            metrics = results.get('metrics', {})
            ret_class = 'positive' if float(metrics.get('totalReturn', 0)) >= 0 else 'negative'
            metrics_html = f"""
            <h2>Performance Metrics</h2>
            <div class="metrics-grid">
                <div class="metric"><span class="label">Total Return</span><span class="value {ret_class}">{metrics.get('totalReturn', 0)}%</span></div>
                <div class="metric"><span class="label">Sharpe Ratio</span><span class="value">{metrics.get('sharpeRatio', 0)}</span></div>
                <div class="metric"><span class="label">Max Drawdown</span><span class="value negative">{metrics.get('maxDrawdown', 0)}%</span></div>
                <div class="metric"><span class="label">Win Rate</span><span class="value">{metrics.get('winRate', 0)}%</span></div>
                <div class="metric"><span class="label">Total Trades</span><span class="value">{metrics.get('totalTrades', 0)}</span></div>
                <div class="metric"><span class="label">Final Value</span><span class="value">${metrics.get('finalEquity', metrics.get('finalValue', 0)):,.2f}</span></div>
            </div>
            """
            ranking_html = ""
        
        html_content = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Backtest Report - {symbol}</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ 
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: #0a0a0b; 
            color: #fff; 
            padding: 40px; 
            line-height: 1.6;
        }}
        .container {{ max-width: 900px; margin: 0 auto; }}
        h1 {{ font-size: 32px; margin-bottom: 8px; }}
        .subtitle {{ color: #71717a; margin-bottom: 32px; }}
        h2 {{ font-size: 20px; margin: 32px 0 16px; color: #a1a1aa; }}
        .meta {{ display: flex; gap: 24px; margin-bottom: 32px; padding: 20px; background: #18181b; border-radius: 12px; }}
        .meta-item {{ display: flex; flex-direction: column; gap: 4px; }}
        .meta-label {{ font-size: 12px; color: #71717a; text-transform: uppercase; }}
        .meta-value {{ font-size: 16px; font-weight: 600; }}
        table {{ width: 100%; border-collapse: collapse; margin: 16px 0; }}
        th, td {{ padding: 12px 16px; text-align: left; border-bottom: 1px solid #27272a; }}
        th {{ background: #18181b; font-weight: 600; color: #a1a1aa; }}
        tr:hover {{ background: #18181b; }}
        .positive {{ color: #22c55e; }}
        .negative {{ color: #ef4444; }}
        .metrics-grid {{ display: grid; grid-template-columns: repeat(3, 1fr); gap: 16px; }}
        .metric {{ padding: 20px; background: #18181b; border-radius: 12px; border: 1px solid #27272a; }}
        .metric .label {{ display: block; font-size: 12px; color: #71717a; margin-bottom: 8px; text-transform: uppercase; }}
        .metric .value {{ font-size: 24px; font-weight: 700; }}
        ol {{ padding-left: 24px; }}
        ol li {{ padding: 8px 0; font-size: 16px; }}
        .footer {{ margin-top: 48px; padding-top: 24px; border-top: 1px solid #27272a; color: #71717a; font-size: 12px; text-align: center; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>📊 Backtest Report</h1>
        <p class="subtitle">Automated strategy performance analysis</p>
        
        <div class="meta">
            <div class="meta-item">
                <span class="meta-label">Symbol</span>
                <span class="meta-value">{symbol}</span>
            </div>
            <div class="meta-item">
                <span class="meta-label">Strategies</span>
                <span class="meta-value">{', '.join(strategies)}</span>
            </div>
            <div class="meta-item">
                <span class="meta-label">Generated</span>
                <span class="meta-value">{datetime.now().strftime('%B %d, %Y %H:%M')}</span>
            </div>
            <div class="meta-item">
                <span class="meta-label">Initial Capital</span>
                <span class="meta-value">${results.get('initialCapital', 100000):,.2f}</span>
            </div>
        </div>
        
        {ranking_html}
        {metrics_html}
        
        <div class="footer">
            <p>Generated by Arbiter Trading Platform • {datetime.now().year}</p>
        </div>
    </div>
</body>
</html>
        """
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        return {
            "success": True,
            "filename": filename,
            "downloadUrl": f"/api/backtest/report/download/{filename}"
        }
    except Exception as e:
        return {"error": str(e)}
