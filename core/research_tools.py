"""Tools available to internal researchers: no mutations or orchestration."""
ALLOWED_TOOLS = (
    "get_quote", "get_company_profile", "get_news", "build_trade_plan", "scan_watchlist",
    "analyze_momentum", "analyze_technical_levels", "analyze_trend", "analyze_volatility",
    "analyze_volume", "analyze_statistics", "generate_optimized_verdict",
    "backtest_macd_momentum", "backtest_macd_trend_follower", "backtest_mean_reversion_rsi_bb",
    "backtest_rsi_mean_reversion", "backtest_sma_crossover", "backtest_trend_crossover",
    "backtest_volatility_breakout", "find_sector_stock_pipeline_tool", "analyze_sector_intelligence_tool",
)
