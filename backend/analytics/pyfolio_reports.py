"""
Analytics module for generating comprehensive performance reports using PyFolio.
This module integrates with the existing backtesting framework to provide detailed 
tear sheets and performance analysis.
"""

import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import quantstats as qs
import warnings
warnings.filterwarnings('ignore')

def generate_pyfolio_tear_sheet(portfolio_returns: pd.Series, benchmark_returns: pd.Series = None, 
                                title: str = "Strategy Performance Analysis"):
    """
    Generate a comprehensive PyFolio-style tear sheet for strategy performance.
    
    Args:
        portfolio_returns (pd.Series): Daily portfolio returns
        benchmark_returns (pd.Series, optional): Daily benchmark returns for comparison
        title (str): Title for the report
        
    Returns:
        dict: Dictionary containing performance metrics and plots
    """
    try:
        # Generate HTML report using quantstats (since pyfolio might have installation issues)
        import tempfile
        import os
        
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.html') as tmp_file:
            tmp_filename = tmp_file.name
        
        # Generate comprehensive report
        if benchmark_returns is not None and not benchmark_returns.empty:
            qs.reports.html(portfolio_returns, benchmark=benchmark_returns, 
                          output=tmp_filename, title=title)
        else:
            qs.reports.html(portfolio_returns, output=tmp_filename, title=title)
        
        # Extract key metrics using quantstats
        metrics = {
            'total_return': qs.stats.cagr(portfolio_returns),
            'volatility': qs.stats.volatility(portfolio_returns),
            'sharpe': qs.stats.sharpe(portfolio_returns),
            'max_drawdown': qs.stats.max_drawdown(portfolio_returns),
            'calmar': qs.stats.calmar(portfolio_returns),
            'sortino': qs.stats.sortino(portfolio_returns),
            'omega': qs.stats.omega(portfolio_returns),
            'win_rate': qs.stats.wins(portfolio_returns),
            'avg_win': qs.stats.avg_win(portfolio_returns),
            'avg_loss': qs.stats.avg_loss(portfolio_returns),
            'profit_ratio': qs.stats.profit_factor(portfolio_returns)
        }
        
        return {
            'metrics': metrics,
            'report_path': tmp_filename,
            'plot': generate_performance_chart(portfolio_returns, benchmark_returns, title)
        }
    
    except Exception as e:
        print(f"Error generating PyFolio tear sheet: {e}")
        return {'error': str(e)}

def generate_performance_chart(portfolio_returns: pd.Series, benchmark_returns: pd.Series = None, 
                              title: str = "Performance Comparison"):
    """
    Generate an interactive performance chart comparing strategy vs benchmark.
    
    Args:
        portfolio_returns (pd.Series): Daily portfolio returns
        benchmark_returns (pd.Series, optional): Daily benchmark returns
        title (str): Chart title
        
    Returns:
        plotly.graph_objects.Figure: Interactive performance chart
    """
    try:
        # Calculate cumulative returns
        portfolio_cumulative = (1 + portfolio_returns).cumprod()
        benchmark_cumulative = (1 + benchmark_returns).cumprod() if benchmark_returns is not None and not benchmark_returns.empty else None
        
        # Create subplots
        fig = make_subplots(
            rows=3, cols=1,
            shared_xaxes=True,
            vertical_spacing=0.05,
            subplot_titles=['Cumulative Returns', 'Drawdown', 'Daily Returns'],
            row_heights=[0.5, 0.25, 0.25]
        )
        
        # Cumulative returns plot
        fig.add_trace(
            go.Scatter(
                x=portfolio_cumulative.index,
                y=portfolio_cumulative.values,
                name='Strategy',
                line=dict(color='blue', width=2)
            ),
            row=1, col=1
        )
        
        if benchmark_cumulative is not None:
            fig.add_trace(
                go.Scatter(
                    x=benchmark_cumulative.index,
                    y=benchmark_cumulative.values,
                    name='Benchmark',
                    line=dict(color='red', width=2, dash='dash')
                ),
                row=1, col=1
            )
        
        # Calculate drawdown
        portfolio_equity = (1 + portfolio_returns).cumprod()
        rolling_max = portfolio_equity.expanding().max()
        drawdown = (portfolio_equity - rolling_max) / rolling_max
        
        fig.add_trace(
            go.Scatter(
                x=drawdown.index,
                y=drawdown.values * 100,  # Convert to percentage
                name='Drawdown',
                fill='tozeroy',
                fillcolor='rgba(255, 0, 0, 0.2)',
                line=dict(color='red', width=1)
            ),
            row=2, col=1
        )
        
        # Daily returns plot
        fig.add_trace(
            go.Bar(
                x=portfolio_returns.index,
                y=portfolio_returns.values * 100,  # Convert to percentage
                name='Daily Returns',
                marker_color=['green' if x >= 0 else 'red' for x in portfolio_returns.values],
                opacity=0.6
            ),
            row=3, col=1
        )
        
        # Update layout
        fig.update_layout(
            title_text=title,
            height=800,
            showlegend=True,
            hovermode='x unified'
        )
        
        # Update y-axis titles
        fig.update_yaxes(title_text='Cumulative Return', row=1, col=1)
        fig.update_yaxes(title_text='Drawdown (%)', row=2, col=1)
        fig.update_yaxes(title_text='Daily Return (%)', row=3, col=1)
        fig.update_xaxes(title_text='Date', row=3, col=1)
        
        return fig
    
    except Exception as e:
        print(f"Error generating performance chart: {e}")
        # Return a simple chart in case of error
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=portfolio_returns.index,
            y=(1 + portfolio_returns).cumprod(),
            name='Strategy Returns'
        ))
        fig.update_layout(title=title, xaxis_title='Date', yaxis_title='Cumulative Return')
        return fig

def create_strategy_comparison_report(strategy_returns_dict: dict, benchmark_returns: pd.Series = None):
    """
    Create a comparison report for multiple strategies.
    
    Args:
        strategy_returns_dict (dict): Dictionary of {strategy_name: returns_series}
        benchmark_returns (pd.Series, optional): Benchmark returns for comparison
        
    Returns:
        dict: Comparison metrics and visualization
    """
    try:
        comparison_metrics = {}
        
        for strategy_name, returns in strategy_returns_dict.items():
            metrics = {
                'total_return': qs.stats.cagr(returns),
                'volatility': qs.stats.volatility(returns),
                'sharpe': qs.stats.sharpe(returns),
                'max_drawdown': qs.stats.max_drawdown(returns),
                'sortino': qs.stats.sortino(returns),
                'win_rate': qs.stats.wins(returns)
            }
            comparison_metrics[strategy_name] = metrics
        
        # Create comparison chart
        fig = go.Figure()
        
        # Plot cumulative returns for each strategy
        for strategy_name, returns in strategy_returns_dict.items():
            cumulative_returns = (1 + returns).cumprod()
            fig.add_trace(go.Scatter(
                x=cumulative_returns.index,
                y=cumulative_returns.values,
                name=strategy_name,
                line=dict(width=2)
            ))
        
        # Add benchmark if provided
        if benchmark_returns is not None and not benchmark_returns.empty:
            benchmark_cumulative = (1 + benchmark_returns).cumprod()
            fig.add_trace(go.Scatter(
                x=benchmark_cumulative.index,
                y=benchmark_cumulative.values,
                name='Benchmark',
                line=dict(color='black', dash='dash', width=2)
            ))
        
        fig.update_layout(
            title='Strategy Performance Comparison',
            xaxis_title='Date',
            yaxis_title='Cumulative Return',
            hovermode='x unified'
        )
        
        return {
            'comparison_metrics': comparison_metrics,
            'comparison_chart': fig
        }
    
    except Exception as e:
        print(f"Error creating strategy comparison report: {e}")
        return {'error': str(e)}

def generate_risk_metrics(returns: pd.Series, confidence_level: float = 0.05):
    """
    Calculate advanced risk metrics for the strategy.
    
    Args:
        returns (pd.Series): Daily returns
        confidence_level (float): Confidence level for VaR calculation (default 5%)
        
    Returns:
        dict: Risk metrics
    """
    try:
        risk_metrics = {
            'var': qs.stats.var(returns, sigma=confidence_level),  # Value at Risk
            'cvar': qs.stats.cvar(returns, sigma=confidence_level),  # Conditional VaR
            'volatility': qs.stats.volatility(returns),
            'downside_deviation': qs.stats.down(returns, target=0),
            'ulcer_index': qs.stats.ulcer(returns),
            'tail_ratio': qs.stats.risk_tail_ratio(returns),
            'skew': qs.stats.skew(returns),
            'kurtosis': qs.stats.kurtosis(returns)
        }
        
        return risk_metrics
    
    except Exception as e:
        print(f"Error calculating risk metrics: {e}")
        return {'error': str(e)}

def generate_trade_analysis(trades_df: pd.DataFrame):
    """
    Analyze trade-level performance metrics.
    
    Args:
        trades_df (pd.DataFrame): DataFrame with trade information
        
    Returns:
        dict: Trade analysis metrics
    """
    try:
        if trades_df.empty:
            return {}
        
        # Calculate trade metrics
        total_trades = len(trades_df)
        
        # For backtesting.py trades format: Size is positive for long, negative for short
        winning_trades = trades_df[trades_df['PnL'] > 0] if 'PnL' in trades_df.columns else 0
        losing_trades = trades_df[trades_df['PnL'] < 0] if 'PnL' in trades_df.columns else 0
        
        avg_win = winning_trades['PnL'].mean() if len(winning_trades) > 0 else 0
        avg_loss = abs(losing_trades['PnL'].mean()) if len(losing_trades) > 0 else 0
        win_rate = len(winning_trades) / total_trades if total_trades > 0 else 0
        profit_factor = (winning_trades['PnL'].sum() / abs(losing_trades['PnL'].sum())) if len(losing_trades) > 0 and losing_trades['PnL'].sum() != 0 else float('inf')
        
        return {
            'total_trades': total_trades,
            'winning_trades': len(winning_trades),
            'losing_trades': len(losing_trades),
            'win_rate': win_rate,
            'avg_win': avg_win,
            'avg_loss': avg_loss,
            'profit_factor': profit_factor
        }
    
    except Exception as e:
        print(f"Error in trade analysis: {e}")
        return {'error': str(e)}
        
# Backward compatibility function to match existing interface
def generate_quantstats_report(portfolio_returns: pd.Series, benchmark_returns: pd.Series = None, 
                             output_file="portfolio_report.html", title="Portfolio Performance Report"):
    """
    Backward-compatible function to generate QuantStats report.
    """
    try:
        if benchmark_returns is not None and not benchmark_returns.empty:
            qs.reports.html(portfolio_returns, benchmark=benchmark_returns, 
                          output=output_file, title=title)
        else:
            qs.reports.html(portfolio_returns, output=output_file, title=title)
        return output_file
    except Exception as e:
        print(f"Error generating QuantStats report: {e}")
        return None