import yfinance as yf
import pandas as pd
import numpy as np
import quantstats as qs
import logging
from config import METRIC_EXPLANATIONS

logger = logging.getLogger(__name__)


def get_benchmark_returns(symbol: str, start: str, end: str) -> pd.Series:
    """
    Fetches benchmark returns for comparison against strategy performance.
    
    Args:
        symbol (str): Benchmark symbol (e.g., 'SPY', '^GSPC')
        start (str): Start date in 'YYYY-MM-DD' format
        end (str): End date in 'YYYY-MM-DD' format
        
    Returns:
        pd.Series: Series of benchmark daily returns
    """
    logger.info(f"Fetching benchmark data for {symbol} from {start} to {end}...")
    try:
        benchmark_data = yf.download(symbol, start=start, end=end, progress=False, auto_adjust=True)
        if benchmark_data.empty:
            logger.warning(f"No benchmark data found for {symbol}.")
            return pd.Series(dtype=float)
            
        return benchmark_data['Close'].pct_change().dropna()
        
    except Exception as e:
        logger.error(f"Failed to fetch benchmark data for {symbol}: {e}")
        return pd.Series(dtype=float)


def calculate_beta(portfolio_returns: pd.Series, benchmark_returns: pd.Series) -> float:
    """
    Calculates the beta of the portfolio relative to the benchmark.
    Beta measures the portfolio's sensitivity to market movements.
    
    Args:
        portfolio_returns (pd.Series): Portfolio daily returns
        benchmark_returns (pd.Series): Benchmark daily returns
        
    Returns:
        float: Beta value
    """
    returns = pd.concat([portfolio_returns, benchmark_returns], axis=1).dropna()
    returns.columns = ['portfolio', 'benchmark']
    
    if len(returns) == 0:
        return np.nan
    
    covariance = returns['portfolio'].cov(returns['benchmark'])
    variance = returns['benchmark'].var()
    return np.nan if variance == 0 else covariance / variance


def calculate_alpha(portfolio_returns: pd.Series, benchmark_returns: pd.Series, risk_free_rate: float = 0.02) -> float:
    """
    Calculates the alpha of the portfolio relative to the benchmark.
    Alpha measures the excess return of the portfolio over its expected return.
    
    Args:
        portfolio_returns (pd.Series): Portfolio daily returns
        benchmark_returns (pd.Series): Benchmark daily returns
        risk_free_rate (float): Annual risk-free rate (default 2%)
        
    Returns:
        float: Alpha value
    """
    if len(portfolio_returns) == 0 or len(benchmark_returns) == 0:
        return np.nan
    
    # Convert annual risk-free rate to daily
    daily_rf = (1 + risk_free_rate) ** (1 / 252) - 1
    
    portfolio_excess = portfolio_returns.mean() * 252 - risk_free_rate
    benchmark_excess = benchmark_returns.mean() * 252 - risk_free_rate
    beta = calculate_beta(portfolio_returns, benchmark_returns)
    
    alpha = portfolio_excess - (beta * benchmark_excess)
    return alpha * 100  # Convert to percentage


def calculate_information_ratio(portfolio_returns: pd.Series, benchmark_returns: pd.Series) -> float:
    """
    Calculates the information ratio of the portfolio.
    Measures excess return relative to benchmark per unit of tracking error.
    
    Args:
        portfolio_returns (pd.Series): Portfolio daily returns
        benchmark_returns (pd.Series): Benchmark daily returns
        
    Returns:
        float: Information ratio
    """
    if portfolio_returns is None or benchmark_returns is None:
        return np.nan
        
    if len(portfolio_returns) == 0 or len(benchmark_returns) == 0:
        return np.nan
    
    # Align the indices to ensure proper subtraction
    aligned_data = pd.concat([portfolio_returns, benchmark_returns], axis=1, join='inner')
    if aligned_data.empty or aligned_data.shape[1] < 2:
        return np.nan
    
    aligned_portfolio = aligned_data.iloc[:, 0]
    aligned_benchmark = aligned_data.iloc[:, 1]
    
    excess_returns = aligned_portfolio - aligned_benchmark
    if len(excess_returns) == 0:
        return np.nan
    
    # Calculate standard deviation and handle potential Series issues
    excess_std = excess_returns.std()
    
    # Check if std() returned a scalar value and handle appropriately
    try:
        excess_std_scalar = float(excess_std)
        # Use np.isnan to safely check if the scalar value is NaN
        if np.isnan(excess_std_scalar) or excess_std_scalar == 0.0:
            return np.nan
    except (TypeError, ValueError):
        # If conversion to float fails, std() may have returned something unexpected
        return np.nan
    
    tracking_error = excess_std_scalar * np.sqrt(252)
    excess_return = float(excess_returns.mean()) * 252
    
    if tracking_error == 0:
        return np.nan
    
    return excess_return / tracking_error


def calculate_all_metrics(portfolio_returns: pd.Series, benchmark_returns: pd.Series) -> dict:
    """
    Calculates comprehensive performance and risk metrics for the portfolio.
    
    Args:
        portfolio_returns (pd.Series): Portfolio daily returns
        benchmark_returns (pd.Series): Benchmark daily returns
        
    Returns:
        dict: Dictionary containing retail and institutional metrics
    """
    if len(portfolio_returns) == 0:
        return {"retail": {}, "institutional": {}, "explanations": METRIC_EXPLANATIONS}
    
    # Retail metrics - focus on simple, understandable measures
    retail_metrics = {
        "Total Return %": (portfolio_returns.sum() + 1) ** (252 / len(portfolio_returns)) - 1 if len(portfolio_returns) > 0 else 0,
        "CAGR %": qs.stats.cagr(portfolio_returns) * 100,
        "Max Drawdown %": qs.stats.max_drawdown(portfolio_returns) * 100,
        "Sharpe Ratio": qs.stats.sharpe(portfolio_returns),
        "Alpha %": calculate_alpha(portfolio_returns, benchmark_returns),
        "Win Rate %": (portfolio_returns > 0).sum() / len(portfolio_returns) * 100 if len(portfolio_returns) > 0 else 0
    }
    
    # Align portfolio and benchmark returns for metrics that require both
    if len(portfolio_returns) > 0 and len(benchmark_returns) > 0:
        aligned_data = pd.concat([portfolio_returns, benchmark_returns], axis=1, join='inner')
        if aligned_data.empty or aligned_data.shape[1] < 2:
            aligned_portfolio = pd.Series(dtype=float)
            aligned_benchmark = pd.Series(dtype=float)
        else:
            aligned_portfolio = aligned_data.iloc[:, 0]
            aligned_benchmark = aligned_data.iloc[:, 1]
    else:
        aligned_portfolio = pd.Series(dtype=float) if len(portfolio_returns) == 0 else portfolio_returns
        aligned_benchmark = pd.Series(dtype=float) if len(benchmark_returns) == 0 else benchmark_returns

    # Institutional metrics - more sophisticated risk measures
    institutional_metrics = {
        "Sortino Ratio": qs.stats.sortino(portfolio_returns),
        "Calmar Ratio": qs.stats.calmar(portfolio_returns),
        "Volatility (ann.) %": qs.stats.volatility(portfolio_returns, annualize=True) * 100,
        "Skew": qs.stats.skew(portfolio_returns),
        "Kurtosis": qs.stats.kurtosis(portfolio_returns),
        "Value at Risk (VaR) %": qs.stats.var(portfolio_returns) * 100,
        "Conditional VaR (cVaR) %": qs.stats.cvar(portfolio_returns) * 100,
        "Beta (vs. Benchmark)": calculate_beta(aligned_portfolio, aligned_benchmark),
        "Information Ratio": calculate_information_ratio(aligned_portfolio, aligned_benchmark),
        "Correlation with Benchmark": aligned_portfolio.corr(aligned_benchmark) if len(aligned_portfolio) > 0 and len(aligned_benchmark) > 0 else np.nan
    }
    
    # Round metrics to 2 decimal places for display
    retail_metrics = {k: round(v, 2) if isinstance(v, (int, float)) else v for k, v in retail_metrics.items()}
    institutional_metrics = {k: round(v, 2) if isinstance(v, (int, float)) else v for k, v in institutional_metrics.items()}
    
    return {
        "retail": retail_metrics,
        "institutional": institutional_metrics,
        "explanations": METRIC_EXPLANATIONS
    }


def get_metric_explanation(metric_name: str) -> str:
    """
    Returns an explanation for a given metric name.
    
    Args:
        metric_name (str): Name of the metric
        
    Returns:
        str: Explanation of the metric
    """
    return METRIC_EXPLANATIONS.get(metric_name, f"Explanation for {metric_name} not available.")


def generate_quantstats_report(portfolio_returns: pd.Series, benchmark_returns: pd.Series, output_file="portfolio_report.html"):
    """
    Generates a comprehensive HTML report using QuantStats.
    
    Args:
        portfolio_returns (pd.Series): Portfolio daily returns
        benchmark_returns (pd.Series): Benchmark daily returns
        output_file (str): Path to save the HTML report
    """
    try:
        qs.reports.html(
            portfolio_returns, 
            benchmark=benchmark_returns, 
            output=output_file, 
            title="Portfolio Performance Report"
        )
        logger.info(f"Successfully generated QuantStats report to {output_file}")
    except Exception as e:
        logger.error(f"Could not generate QuantStats report: {e}")


def compare_strategy_performance(strategy_returns: pd.Series, benchmark_returns: pd.Series) -> dict:
    """
    Compares strategy performance against benchmark with detailed metrics.
    
    Args:
        strategy_returns (pd.Series): Strategy daily returns
        benchmark_returns (pd.Series): Benchmark daily returns
        
    Returns:
        dict: Comparison metrics
    """
    if len(strategy_returns) == 0 or len(benchmark_returns) == 0:
        return {}
    
    strategy_cagr = qs.stats.cagr(strategy_returns) * 100
    benchmark_cagr = qs.stats.cagr(benchmark_returns) * 100
    
    strategy_max_dd = qs.stats.max_drawdown(strategy_returns) * 100
    benchmark_max_dd = qs.stats.max_drawdown(benchmark_returns) * 100
    
    strategy_sharpe = qs.stats.sharpe(strategy_returns)
    benchmark_sharpe = qs.stats.sharpe(benchmark_returns)
    
    outperformance = strategy_cagr - benchmark_cagr
    
    comparison = {
        "Strategy CAGR %": round(strategy_cagr, 2),
        "Benchmark CAGR %": round(benchmark_cagr, 2),
        "Outperformance %": round(outperformance, 2),
        "Strategy Max Drawdown %": round(strategy_max_dd, 2),
        "Benchmark Max Drawdown %": round(benchmark_max_dd, 2),
        "Strategy Sharpe Ratio": round(strategy_sharpe, 2),
        "Benchmark Sharpe Ratio": round(benchmark_sharpe, 2),
        "Alpha %": round(calculate_alpha(strategy_returns, benchmark_returns), 2),
        "Beta": round(calculate_beta(strategy_returns, benchmark_returns), 2)
    }
    
    return comparison