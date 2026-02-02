# File: utils/visualization.py

import plotly.graph_objects as go
import pandas as pd
# import streamlit as st
from plotly.subplots import make_subplots
from typing import Dict, Any, List
from config import CURRENCY_SYMBOLS


def create_price_chart(df, stock_name, currency_symbol="$", title_suffix=""):
    """
    Creates an enhanced candlestick price chart with fast and slow SMAs.
    
    Args:
        df (pd.DataFrame): DataFrame with OHLCV and indicator data
        stock_name (str): Name of the stock to display in the title
        currency_symbol (str): Currency symbol to use in the y-axis (default: $)
        title_suffix (str): Optional suffix to add to the title
    """
    fig = go.Figure()
    
    # Add candlestick chart
    fig.add_trace(go.Candlestick(
        x=df.index, 
        open=df['Open'], 
        high=df['High'], 
        low=df['Low'], 
        close=df['Close'], 
        name='Price'
    ))
    
    # Safely add indicators if they exist in the data
    if 'trend_sma_fast' in df.columns:
        fig.add_trace(go.Scatter(
            x=df.index, 
            y=df['trend_sma_fast'], 
            name='Fast SMA', 
            line=dict(color='orange', width=1.5),
            hovertemplate='%{y}<extra>Fast SMA</extra>'
        ))
    
    if 'trend_sma_slow' in df.columns:
        fig.add_trace(go.Scatter(
            x=df.index, 
            y=df['trend_sma_slow'], 
            name='Slow SMA', 
            line=dict(color='purple', width=1.5),
            hovertemplate='%{y}<extra>Slow SMA</extra>'
        ))
    
    # Add Bollinger Bands if they exist
    if 'volatility_bbh' in df.columns and 'volatility_bbl' in df.columns:
        fig.add_trace(go.Scatter(
            x=df.index, 
            y=df['volatility_bbh'], 
            name='Bollinger Upper', 
            line=dict(color='lightblue', width=1, dash='dash'),
            hovertemplate='%{y}<extra>Bollinger Upper</extra>'
        ))
        fig.add_trace(go.Scatter(
            x=df.index, 
            y=df['volatility_bbl'], 
            name='Bollinger Lower', 
            line=dict(color='lightblue', width=1, dash='dash'),
            fill='tonexty',  # Fill between upper and lower band
            fillcolor='rgba(173, 216, 230, 0.2)',
            hovertemplate='%{y}<extra>Bollinger Lower</extra>'
        ))
    
    title = f'<b>{stock_name} Price Chart & Indicators'
    if title_suffix:
        title += f' {title_suffix}</b>'
    else:
        title += '</b>'
    
    fig.update_layout(
        title_text=title,
        yaxis_title=f'Price ({currency_symbol})',
        xaxis_rangeslider_visible=False,
        hovermode='x unified',
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )
    return fig


def create_equity_curve_chart(data, title_suffix="", currency_symbol="$"):
    """
    Creates an enhanced equity curve chart.
    
    Args:
        data (pd.Series or pd.DataFrame): Equity curve data
        title_suffix (str): Optional suffix to add to the title
        currency_symbol (str): Currency symbol to use in the y-axis
    """
    fig = go.Figure()
    
    # Convert to Series if DataFrame with single column
    if isinstance(data, pd.DataFrame):
        if len(data.columns) == 1:
            series_data = data.iloc[:, 0]
        else:
            # If multiple columns, take the first one
            series_data = data.iloc[:, 0]
    else:
        series_data = data
    
    fig.add_trace(go.Scatter(
        x=series_data.index, 
        y=series_data, 
        name='Equity Curve',
        line=dict(color='blue', width=2),
        hovertemplate='%{y:,.2f}<extra>Equity</extra>'
    ))
    
    # Calculate and add max drawdown annotation if possible
    if len(series_data) > 0 and series_data.max() > 0:
        # Find the peak and the lowest point after it (max drawdown)
        rolling_max = series_data.expanding().max()
        drawdown = (series_data - rolling_max) / rolling_max
        
        # Find the date of maximum drawdown
        max_drawdown_date = drawdown.idxmin()
        max_drawdown_value = drawdown.min()
        
        # Add annotation for max drawdown
        fig.add_annotation(
            x=max_drawdown_date,
            y=series_data[max_drawdown_date],
            text=f'Max Drawdown: {max_drawdown_value:.2%}',
            showarrow=True,
            arrowhead=1,
            ax=-50,
            ay=-50
        )
    
    title = '<b>Equity Curve'
    if title_suffix:
        title += f' - {title_suffix}</b>'
    else:
        title += '</b>'
        
    fig.update_layout(
        title_text=title,
        yaxis_title=f'Portfolio Value ({currency_symbol})',
        xaxis_title='Date',
        hovermode='x unified',
        hovertemplate='<b>%{x}</b><br>' +
                     'Value: %{y:,.2f}<extra></extra>'
    )
    return fig


def create_strategy_comparison_chart(portfolio_data, benchmark_data=None, strategy_name="Strategy", benchmark_name="Benchmark", currency_symbol="$"):
    """
    Creates a comparison chart between strategy and benchmark performance.
    
    Args:
        portfolio_data (pd.Series): Strategy equity curve data
        benchmark_data (pd.Series): Benchmark equity curve data
        strategy_name (str): Name of the strategy
        benchmark_name (str): Name of the benchmark
        currency_symbol (str): Currency symbol to use in the y-axis
    """
    fig = go.Figure()
    
    fig.add_trace(go.Scatter(
        x=portfolio_data.index,
        y=portfolio_data,
        name=strategy_name,
        line=dict(color='blue', width=2),
        hovertemplate='%{y:,.2f}<extra>' + strategy_name + '</extra>'
    ))
    
    if benchmark_data is not None and not benchmark_data.empty:
        fig.add_trace(go.Scatter(
            x=benchmark_data.index,
            y=benchmark_data,
            name=benchmark_name,
            line=dict(color='red', width=2, dash='dash'),
            hovertemplate='%{y:,.2f}<extra>' + benchmark_name + '</extra>'
        ))
    
    fig.update_layout(
        title_text=f'<b>{strategy_name} vs {benchmark_name}</b>',
        yaxis_title=f'Portfolio Value ({currency_symbol})',
        xaxis_title='Date',
        hovermode='x unified',
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )
    return fig


def create_rsi_chart(df):
    """
    Creates an RSI indicator chart.
    
    Args:
        df (pd.DataFrame): DataFrame with momentum_rsi column
    """
    if 'momentum_rsi' not in df.columns:
        return None
        
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=df.index, 
        y=df['momentum_rsi'], 
        name='RSI', 
        line=dict(color='purple', width=1.5)
    ))
    
    # Add RSI reference lines at 30 (oversold) and 70 (overbought)
    fig.add_hline(y=30, line_dash="dash", line_color="red", annotation_text="Oversold (30)")
    fig.add_hline(y=70, line_dash="dash", line_color="red", annotation_text="Overbought (70)")
    fig.add_hline(y=50, line_dash="dot", line_color="gray", annotation_text="Neutral (50)")
    
    fig.update_layout(
        title_text='<b>Relative Strength Index (RSI)</b>',
        yaxis_title='RSI',
        xaxis_title='Date',
        yaxis=dict(range=[0, 100])
    )
    return fig


def create_macd_chart(df):
    """
    Creates a MACD indicator chart.
    
    Args:
        df (pd.DataFrame): DataFrame with MACD-related columns
    """
    required_cols = ['trend_macd', 'trend_macd_signal']
    if not all(col in df.columns for col in required_cols):
        return None
    
    fig = make_subplots(specs=[[{"secondary_y": True}]])
    
    # Add MACD line
    fig.add_trace(
        go.Scatter(x=df.index, y=df['trend_macd'], name='MACD Line', line=dict(color='blue')),
        secondary_y=False,
    )
    
    # Add MACD signal line
    fig.add_trace(
        go.Scatter(x=df.index, y=df['trend_macd_signal'], name='Signal Line', line=dict(color='red')),
        secondary_y=False,
    )
    
    # Calculate MACD histogram if available
    if 'trend_macd_histogram' in df.columns:
        colors = ['green' if val >= 0 else 'red' for val in df['trend_macd_histogram']]
        fig.add_trace(
            go.Bar(x=df.index, y=df['trend_macd_histogram'], name='MACD Histogram', marker_color=colors, opacity=0.6),
            secondary_y=True,
        )
    elif 'trend_macd' in df.columns and 'trend_macd_signal' in df.columns:
        histogram = df['trend_macd'] - df['trend_macd_signal']
        colors = ['green' if val >= 0 else 'red' for val in histogram]
        fig.add_trace(
            go.Bar(x=df.index, y=histogram, name='MACD Histogram', marker_color=colors, opacity=0.6),
            secondary_y=True,
        )
    
    fig.update_layout(
        title_text='<b>MACD Indicator</b>',
        xaxis_title='Date'
    )
    fig.update_yaxes(title_text="MACD", secondary_y=False)
    fig.update_yaxes(title_text="Histogram", secondary_y=True)
    
    return fig


def plot_backtest_comparison(results_df: pd.DataFrame, return_col: str = 'Return [%]') -> go.Figure:
    """Enhanced backtest comparison plot with better formatting."""
    if results_df.empty or return_col not in results_df.columns:
        # ...
        results_df[return_col] = pd.to_numeric(results_df[return_col], errors='coerce')
    # ... use return_col throughout the function ..
    results_df.dropna(subset=['Total Return %'], inplace=True)
    
    results_df = results_df.sort_values('Total Return %', ascending=True)
    
    colors = ['#059669' if x > 0 else '#f43f5e' for x in results_df['Total Return %']]
    
    import plotly.express as px
    fig = px.bar(
        results_df,
        x='Total Return %',
        y='Strategy',
        color='Ticker',
        barmode='group',
        orientation='h',
        title='Strategy Performance Comparison by Ticker',
        labels={'Return [%]': 'Total Return (%)', 'Strategy': 'Strategy Name'},
        text_auto='.2f'
    )
    fig.update_traces(marker_color=colors, textposition='outside')
    fig.update_layout(yaxis={'categoryorder':'total ascending'})
    return fig


def create_price_and_equity_chart(backtest_df: pd.DataFrame, trades: List[Dict[str, Any]], ticker: str, strategy_name: str, currency_symbol: str = "$") -> go.Figure:
    """
    Creates a professional, multi-layered chart showing price, signals, and equity curve with dynamic currency.
    Enhanced version with tooltips and better formatting.
    """
    if backtest_df.empty:
        return go.Figure()

    fig = make_subplots(specs=[[{"secondary_y": True}]])

    # Check if we have OHLC data before trying to plot candlestick
    required_ohlc_cols = ['Open', 'High', 'Low', 'Close']
    has_ohlc_data = all(col in backtest_df.columns for col in required_ohlc_cols)
    
    if has_ohlc_data:
        # Double-check that the data is not empty to ensure columns exist
        if not backtest_df.empty:
            fig.add_trace(
                go.Candlestick(
                    x=backtest_df.index,
                    open=backtest_df['Open'],
                    high=backtest_df['High'],
                    low=backtest_df['Low'],
                    close=backtest_df['Close'],
                    name=f'{ticker} Price'
                ),
                secondary_y=False,
            )
    elif 'Close' in backtest_df.columns:
        # Fallback to line chart if we only have Close data
        if not backtest_df.empty:
            fig.add_trace(
                go.Scatter(
                    x=backtest_df.index,
                    y=backtest_df['Close'],
                    name=f'{ticker} Price',
                    line=dict(color='skyblue')
                ),
                secondary_y=False,
            )
    # If we have neither OHLC nor Close data, we'll just plot the equity curve

    # Check for both possible equity column names
    equity_col = None
    if 'Equity' in backtest_df.columns:
        equity_col = 'Equity'
    elif 'Equity_Curve' in backtest_df.columns:
        equity_col = 'Equity_Curve'
        
    if equity_col and not backtest_df.empty:
        fig.add_trace(
            go.Scatter(
                x=backtest_df.index, y=backtest_df[equity_col], 
                name='Equity Curve', line=dict(color='purple', dash='dot'),
                hovertemplate='%{y:,.2f}<extra>Equity</extra>'
            ),
            secondary_y=True,
        )

    # Convert trades to DataFrame and handle different trade formats
    if isinstance(trades, list) and trades and len(trades) > 0:
        trades_df = pd.DataFrame(trades)
        if not trades_df.empty:
            # Check if the trades DataFrame has the expected columns
            if 'type' in trades_df.columns and 'date' in trades_df.columns and 'price' in trades_df.columns:
                buy_signals = trades_df[trades_df['type'] == 'BUY']
                sell_signals = trades_df[trades_df['type'] == 'SELL']
                if not buy_signals.empty:
                    fig.add_trace(
                        go.Scatter(
                            x=buy_signals['date'], y=buy_signals['price'], mode='markers', 
                            name='Buy Signal', marker=dict(color='#059669', size=10, symbol='triangle-up'),
                            hovertemplate='<b>BUY</b><br>%{x}<br>Price: %{y}<extra></extra>'
                        ),
                        secondary_y=False,
                    )
                if not sell_signals.empty:
                    fig.add_trace(
                        go.Scatter(
                            x=sell_signals['date'], y=sell_signals['price'], mode='markers', 
                            name='Sell Signal', marker=dict(color='#f43f5e', size=10, symbol='triangle-down'),
                            hovertemplate='<b>SELL</b><br>%{x}<br>Price: %{y}<extra></extra>'
                        ),
                        secondary_y=False,
                    )
            # Alternative: Check if trades are from backtesting.py library format (with Size, EntryPrice, etc.)
            elif 'Size' in trades_df.columns and 'EntryPrice' in trades_df.columns:
                buy_signals = trades_df[trades_df['Size'] > 0]  # Positive size indicates buy
                sell_signals = trades_df[trades_df['Size'] < 0]  # Negative size indicates sell
                if not buy_signals.empty:
                    fig.add_trace(
                        go.Scatter(
                            x=buy_signals.index, y=buy_signals['EntryPrice'], mode='markers', 
                            name='Buy Signal', marker=dict(color='#059669', size=10, symbol='triangle-up'),
                            hovertemplate='<b>BUY</b><br>%{x}<br>Price: %{y}<extra></extra>'
                        ),
                        secondary_y=False,
                    )
                if not sell_signals.empty:
                    fig.add_trace(
                        go.Scatter(
                            x=sell_signals.index, y=sell_signals['EntryPrice'], mode='markers', 
                            name='Sell Signal', marker=dict(color='#f43f5e', size=10, symbol='triangle-down'),
                            hovertemplate='<b>SELL</b><br>%{x}<br>Price: %{y}<extra></extra>'
                        ),
                        secondary_y=False,
                    )

    fig.update_layout(
        title_text=f"{ticker} Backtest: {strategy_name}",
        xaxis_title="Date",
        yaxis_title=f"Price ({currency_symbol})",
        yaxis2_title=f"Equity ({currency_symbol})",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )
    fig.update_xaxes(rangeslider_visible=False)
    
    return fig


def create_strategy_specific_chart(backtest_df: pd.DataFrame, trades: List[Dict[str, Any]], ticker: str, strategy_name: str, currency_symbol: str = "$") -> go.Figure:
    """
    Creates strategy-specific visualizations with appropriate indicators and signals.
    """
    if backtest_df.empty:
        return go.Figure()

    # Create subplots: primary for price/candles, secondary for equity curve
    fig = make_subplots(
        rows=2, cols=1,
        shared_xaxes=True,
        vertical_spacing=0.05,
        row_heights=[0.7, 0.3],
        specs=[[{"secondary_y": False}], [{"secondary_y": False}]]
    )
    
    # Check if we have OHLC data
    required_ohlc_cols = ['Open', 'High', 'Low', 'Close']
    has_ohlc_data = all(col in backtest_df.columns for col in required_ohlc_cols)
    
    if has_ohlc_data:
        # Add candlestick chart to primary subplot
        fig.add_trace(
            go.Candlestick(
                x=backtest_df.index,
                open=backtest_df['Open'],
                high=backtest_df['High'],
                low=backtest_df['Low'],
                close=backtest_df['Close'],
                name=f'{ticker} Price',
                increasing_line_color='green',
                decreasing_line_color='red'
            ),
            row=1, col=1
        )
    elif 'Close' in backtest_df.columns:
        # Fallback to line chart if we only have Close data
        fig.add_trace(
            go.Scatter(
                x=backtest_df.index,
                y=backtest_df['Close'],
                name=f'{ticker} Price',
                line=dict(color='blue')
            ),
            row=1, col=1
        )

    # Add strategy-specific indicators based on strategy name
    strategy_lower = strategy_name.lower()
    
    if 'ema' in strategy_lower or 'crossover' in strategy_lower:
        # Add EMAs if available
        if 'EMA_Fast' in backtest_df.columns:
            fig.add_trace(
                go.Scatter(
                    x=backtest_df.index,
                    y=backtest_df['EMA_Fast'],
                    name='Fast EMA',
                    line=dict(color='orange', width=1.5, dash='dash')
                ),
                row=1, col=1
            )
        if 'EMA_Slow' in backtest_df.columns:
            fig.add_trace(
                go.Scatter(
                    x=backtest_df.index,
                    y=backtest_df['EMA_Slow'],
                    name='Slow EMA',
                    line=dict(color='purple', width=1.5, dash='dash')
                ),
                row=1, col=1
            )
    
    elif 'breakout' in strategy_lower:
        # Add breakout levels
        if 'Breakout_High' in backtest_df.columns:
            fig.add_trace(
                go.Scatter(
                    x=backtest_df.index,
                    y=backtest_df['Breakout_High'],
                    name='Breakout High',
                    line=dict(color='red', width=1.5, dash='dash')
                ),
                row=1, col=1
            )
        if 'Breakout_Low' in backtest_df.columns:
            fig.add_trace(
                go.Scatter(
                    x=backtest_df.index,
                    y=backtest_df['Breakout_Low'],
                    name='Breakout Low',
                    line=dict(color='green', width=1.5, dash='dash')
                ),
                row=1, col=1
            )
    
    elif 'rsi' in strategy_lower:
        # Add RSI line if available
        if 'momentum_rsi' in backtest_df.columns:
            fig.add_trace(
                go.Scatter(
                    x=backtest_df.index,
                    y=backtest_df['momentum_rsi'],
                    name='RSI',
                    line=dict(color='purple', width=2)
                ),
                row=1, col=1
            )
            # Add RSI reference lines
            fig.add_hline(y=70, line_dash="dash", line_color="red", row=1, col=1, annotation_text="Overbought (70)")
            fig.add_hline(y=30, line_dash="dash", line_color="red", row=1, col=1, annotation_text="Oversold (30)")
    
    elif 'macd' in strategy_lower:
        # Add MACD lines if available
        if 'trend_macd' in backtest_df.columns:
            fig.add_trace(
                go.Scatter(
                    x=backtest_df.index,
                    y=backtest_df['trend_macd'],
                    name='MACD',
                    line=dict(color='blue', width=2)
                ),
                row=1, col=1
            )
        if 'trend_macd_signal' in backtest_df.columns:
            fig.add_trace(
                go.Scatter(
                    x=backtest_df.index,
                    y=backtest_df['trend_macd_signal'],
                    name='Signal',
                    line=dict(color='red', width=2)
                ),
                row=1, col=1
            )
    
    elif 'channel' in strategy_lower:
        # Add channel lines if available
        if 'channel_upper' in backtest_df.columns:
            fig.add_trace(
                go.Scatter(
                    x=backtest_df.index,
                    y=backtest_df['channel_upper'],
                    name='Upper Channel',
                    line=dict(color='red', width=1.5, dash='dash')
                ),
                row=1, col=1
            )
        if 'channel_lower' in backtest_df.columns:
            fig.add_trace(
                go.Scatter(
                    x=backtest_df.index,
                    y=backtest_df['channel_lower'],
                    name='Lower Channel',
                    line=dict(color='green', width=1.5, dash='dash')
                ),
                row=1, col=1
            )
    
    elif 'support' in strategy_lower or 'resistance' in strategy_lower:
        # Add support/resistance lines if available
        if 'support_level' in backtest_df.columns:
            fig.add_trace(
                go.Scatter(
                    x=backtest_df.index,
                    y=backtest_df['support_level'],
                    name='Support',
                    line=dict(color='green', width=2, dash='dash')
                ),
                row=1, col=1
            )
        if 'resistance_level' in backtest_df.columns:
            fig.add_trace(
                go.Scatter(
                    x=backtest_df.index,
                    y=backtest_df['resistance_level'],
                    name='Resistance',
                    line=dict(color='red', width=2, dash='dash')
                ),
                row=1, col=1
            )

    # Add equity curve to secondary subplot
    equity_col = None
    if 'Equity' in backtest_df.columns:
        equity_col = 'Equity'
    elif 'Equity_Curve' in backtest_df.columns:
        equity_col = 'Equity_Curve'
        
    if equity_col and not backtest_df.empty:
        fig.add_trace(
            go.Scatter(
                x=backtest_df.index, 
                y=backtest_df[equity_col], 
                name='Equity Curve',
                line=dict(color='purple', width=2)
            ),
            row=2, col=1
        )

    # Add trade markers
    if isinstance(trades, list) and trades and len(trades) > 0:
        trades_df = pd.DataFrame(trades)
        if not trades_df.empty:
            if 'type' in trades_df.columns and 'date' in trades_df.columns and 'price' in trades_df.columns:
                buy_signals = trades_df[trades_df['type'] == 'BUY']
                sell_signals = trades_df[trades_df['type'] == 'SELL']
                
                if not buy_signals.empty:
                    fig.add_trace(
                        go.Scatter(
                            x=buy_signals['date'], 
                            y=buy_signals['price'], 
                            mode='markers', 
                            name='Buy Signal', 
                            marker=dict(color='#059669', size=12, symbol='triangle-up'),
                            hovertemplate='<b>BUY</b><br>%{x}<br>Price: %{y}<extra></extra>'
                        ),
                        row=1, col=1
                    )
                if not sell_signals.empty:
                    fig.add_trace(
                        go.Scatter(
                            x=sell_signals['date'], 
                            y=sell_signals['price'], 
                            mode='markers', 
                            name='Sell Signal', 
                            marker=dict(color='#f43f5e', size=12, symbol='triangle-down'),
                            hovertemplate='<b>SELL</b><br>%{x}<br>Price: %{y}<extra></extra>'
                        ),
                        row=1, col=1
                    )
            elif 'Size' in trades_df.columns and 'EntryPrice' in trades_df.columns:
                buy_signals = trades_df[trades_df['Size'] > 0]
                sell_signals = trades_df[trades_df['Size'] < 0]
                
                if not buy_signals.empty:
                    fig.add_trace(
                        go.Scatter(
                            x=buy_signals.index, 
                            y=buy_signals['EntryPrice'], 
                            mode='markers', 
                            name='Buy Signal', 
                            marker=dict(color='#059669', size=12, symbol='triangle-up'),
                            hovertemplate='<b>BUY</b><br>%{x}<br>Price: %{y}<extra></extra>'
                        ),
                        row=1, col=1
                    )
                if not sell_signals.empty:
                    fig.add_trace(
                        go.Scatter(
                            x=sell_signals.index, 
                            y=sell_signals['EntryPrice'], 
                            mode='markers', 
                            name='Sell Signal', 
                            marker=dict(color='#f43f5e', size=12, symbol='triangle-down'),
                            hovertemplate='<b>SELL</b><br>%{x}<br>Price: %{y}<extra></extra>'
                        ),
                        row=1, col=1
                    )

    # Update layout
    fig.update_layout(
        title_text=f"{ticker} - {strategy_name}",
        showlegend=True,
        height=700,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        xaxis_rangeslider_visible=False
    )
    fig.update_yaxes(title_text=f"Price ({currency_symbol})", row=1, col=1)
    fig.update_yaxes(title_text=f"Equity ({currency_symbol})", row=2, col=1)
    fig.update_xaxes(title_text="Date", row=2, col=1)
    
    return fig


def create_performance_metrics_cards(summary: dict) -> Dict[str, float]:
    """
    Extract and format performance metrics for display in cards.
    """
    metrics = {}
    
    # Map common metrics from the summary
    if 'Total Return %' in summary:
        metrics['Total Return %'] = float(summary['Total Return %']) if isinstance(summary['Total Return %'], (int, float, str)) else 0.0
    
    if 'Sharpe Ratio' in summary:
        metrics['Sharpe Ratio'] = float(summary['Sharpe Ratio']) if isinstance(summary['Sharpe Ratio'], (int, float, str)) else 0.0
        
    if 'Max Drawdown %' in summary:
        metrics['Max Drawdown %'] = float(summary['Max Drawdown %']) if isinstance(summary['Max Drawdown %'], (int, float, str)) else 0.0
    
    if 'Number of Trades' in summary or '# Trades' in summary:
        key = 'Number of Trades' if 'Number of Trades' in summary else '# Trades'
        metrics['# Trades'] = int(float(summary[key])) if isinstance(summary[key], (int, float, str)) else 0
    
    # Add other common metrics if available
    if 'CAGR %' in summary:
        metrics['CAGR %'] = float(summary['CAGR %']) if isinstance(summary['CAGR %'], (int, float, str)) else 0.0
        
    if 'Win Rate %' in summary:
        metrics['Win Rate %'] = float(summary['Win Rate %']) if isinstance(summary['Win Rate %'], (int, float, str)) else 0.0
    
    if 'Sortino Ratio' in summary:
        metrics['Sortino Ratio'] = float(summary['Sortino Ratio']) if isinstance(summary['Sortino Ratio'], (int, float, str)) else 0.0
        
    return metrics


def visualize_strategy_performance(returns: pd.Series) -> Dict[str, float]:
    """
    Calculate comprehensive performance metrics using quantstats.
    """
    try:
        import quantstats as qs
        
        # Calculate various metrics using quantstats
        metrics = {
            'Total Return %': float(qs.stats.compsum(returns)) * 100 if len(returns) > 0 else 0.0,
            'CAGR %': float(qs.stats.cagr(returns)) * 100,
            'Sharpe Ratio': float(qs.stats.sharpe(returns)) if len(returns) > 0 else 0.0,
            'Max Drawdown %': float(qs.stats.max_drawdown(returns)) * 100,
            'Volatility %': float(qs.stats.volatility(returns, annualize=True)) * 100,
            'Win Rate %': float(qs.stats.wins(returns)) * 100 if len(returns) > 0 else 0.0,
            'Sortino Ratio': float(qs.stats.sortino(returns)) if len(returns) > 0 else 0.0,
            'Calmar Ratio': float(qs.stats.calmar(returns)) if len(returns) > 0 else 0.0
        }
        
        # Replace NaN values with 0
        for key, value in metrics.items():
            if pd.isna(value):
                metrics[key] = 0.0
                
        return metrics
        
    except Exception as e:
        print(f"Error in visualize_strategy_performance: {e}")
        return {}


def create_fibonacci_retracement_chart(backtest_df: pd.DataFrame, trades: List[Dict[str, Any]], ticker: str, currency_symbol: str = "$") -> go.Figure:
    """
    Create a specialized chart for Fibonacci retracement strategy with retracement levels.
    """
    if backtest_df.empty:
        return go.Figure()

    fig = go.Figure()

    # Add candlestick chart
    required_ohlc_cols = ['Open', 'High', 'Low', 'Close']
    has_ohlc_data = all(col in backtest_df.columns for col in required_ohlc_cols)
    
    if has_ohlc_data:
        fig.add_trace(
            go.Candlestick(
                x=backtest_df.index,
                open=backtest_df['Open'],
                high=backtest_df['High'],
                low=backtest_df['Low'],
                close=backtest_df['Close'],
                name=f'{ticker} Price',
                increasing_line_color='green',
                decreasing_line_color='red'
            )
        )
    elif 'Close' in backtest_df.columns:
        fig.add_trace(
            go.Scatter(
                x=backtest_df.index,
                y=backtest_df['Close'],
                name=f'{ticker} Price',
                line=dict(color='blue')
            )
        )

    # Add Fibonacci levels if available (assumed to exist as columns like fibonacci_236, fibonacci_382, etc.)
    fibonacci_levels = ['fibonacci_0', 'fibonacci_236', 'fibonacci_382', 'fibonacci_5', 'fibonacci_618', 'fibonacci_786', 'fibonacci_1']
    for level in fibonacci_levels:
        if level in backtest_df.columns:
            fig.add_trace(
                go.Scatter(
                    x=backtest_df.index,
                    y=backtest_df[level],
                    name=level.replace('fibonacci_', 'Fib ').upper(),
                    line=dict(dash='dash'),
                    opacity=0.6
                )
            )

    # Add trade markers
    if isinstance(trades, list) and trades and len(trades) > 0:
        trades_df = pd.DataFrame(trades)
        if not trades_df.empty:
            if 'type' in trades_df.columns and 'date' in trades_df.columns and 'price' in trades_df.columns:
                buy_signals = trades_df[trades_df['type'] == 'BUY']
                sell_signals = trades_df[trades_df['type'] == 'SELL']
                
                if not buy_signals.empty:
                    fig.add_trace(
                        go.Scatter(
                            x=buy_signals['date'], 
                            y=buy_signals['price'], 
                            mode='markers', 
                            name='Buy Signal', 
                            marker=dict(color='#059669', size=12, symbol='triangle-up'),
                            hovertemplate='<b>BUY</b><br>%{x}<br>Price: %{y}<extra></extra>'
                        )
                    )
                if not sell_signals.empty:
                    fig.add_trace(
                        go.Scatter(
                            x=sell_signals['date'], 
                            y=sell_signals['price'], 
                            mode='markers', 
                            name='Sell Signal', 
                            marker=dict(color='#f43f5e', size=12, symbol='triangle-down'),
                            hovertemplate='<b>SELL</b><br>%{x}<br>Price: %{y}<extra></extra>'
                        )
                    )

    fig.update_layout(
        title_text=f"{ticker} - Fibonacci Retracement Strategy",
        yaxis_title=f"Price ({currency_symbol})",
        xaxis_rangeslider_visible=False,
        hovermode='x unified',
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )
    
    return fig


def create_pairs_trading_chart(backtest_df: pd.DataFrame, trades: List[Dict[str, Any]], ticker: str, currency_symbol: str = "$") -> go.Figure:
    """
    Create a specialized chart for pairs trading strategy showing spread and z-score.
    """
    if backtest_df.empty:
        return go.Figure()

    fig = make_subplots(
        rows=3, cols=1,
        shared_xaxes=True,
        vertical_spacing=0.05,
        row_heights=[0.4, 0.3, 0.3],
        subplot_titles=[f'{ticker} Price Chart', 'Spread', 'Z-Score']
    )

    # Add candlestick chart for primary asset
    required_ohlc_cols = ['Open', 'High', 'Low', 'Close']
    has_ohlc_data = all(col in backtest_df.columns for col in required_ohlc_cols)
    
    if has_ohlc_data:
        fig.add_trace(
            go.Candlestick(
                x=backtest_df.index,
                open=backtest_df['Open'],
                high=backtest_df['High'],
                low=backtest_df['Low'],
                close=backtest_df['Close'],
                name=f'{ticker} Price',
                increasing_line_color='green',
                decreasing_line_color='red'
            ),
            row=1, col=1
        )
    elif 'Close' in backtest_df.columns:
        fig.add_trace(
            go.Scatter(
                x=backtest_df.index,
                y=backtest_df['Close'],
                name=f'{ticker} Price',
                line=dict(color='blue')
            ),
            row=1, col=1
        )

    # Add spread chart if available
    if 'spread' in backtest_df.columns:
        fig.add_trace(
            go.Scatter(
                x=backtest_df.index,
                y=backtest_df['spread'],
                name='Spread',
                line=dict(color='purple')
            ),
            row=2, col=1
        )
        
        # Add mean reversion bands if available
        if 'spread_mean' in backtest_df.columns:
            fig.add_trace(
                go.Scatter(
                    x=backtest_df.index,
                    y=backtest_df['spread_mean'],
                    name='Spread Mean',
                    line=dict(color='orange', dash='dash')
                ),
                row=2, col=1
            )
        if 'spread_upper' in backtest_df.columns:
            fig.add_trace(
                go.Scatter(
                    x=backtest_df.index,
                    y=backtest_df['spread_upper'],
                    name='Upper Band',
                    line=dict(color='red', dash='dash')
                ),
                row=2, col=1
            )
        if 'spread_lower' in backtest_df.columns:
            fig.add_trace(
                go.Scatter(
                    x=backtest_df.index,
                    y=backtest_df['spread_lower'],
                    name='Lower Band',
                    line=dict(color='green', dash='dash')
                ),
                row=2, col=1
            )

    # Add z-score chart if available
    if 'z_score' in backtest_df.columns:
        fig.add_trace(
            go.Scatter(
                x=backtest_df.index,
                y=backtest_df['z_score'],
                name='Z-Score',
                line=dict(color='blue')
            ),
            row=3, col=1
        )
        # Add z-score threshold lines
        fig.add_hline(y=2, line_dash="dash", line_color="red", row=3, col=1, annotation_text="Upper Threshold (2)")
        fig.add_hline(y=-2, line_dash="dash", line_color="red", row=3, col=1, annotation_text="Lower Threshold (-2)")
        fig.add_hline(y=0, line_dash="dash", line_color="gray", row=3, col=1, annotation_text="Mean (0)")

    # Add trade markers to primary chart
    if isinstance(trades, list) and trades and len(trades) > 0:
        trades_df = pd.DataFrame(trades)
        if not trades_df.empty:
            if 'type' in trades_df.columns and 'date' in trades_df.columns and 'price' in trades_df.columns:
                buy_signals = trades_df[trades_df['type'] == 'BUY']
                sell_signals = trades_df[trades_df['type'] == 'SELL']
                
                if not buy_signals.empty:
                    fig.add_trace(
                        go.Scatter(
                            x=buy_signals['date'], 
                            y=buy_signals['price'], 
                            mode='markers', 
                            name='Buy Signal', 
                            marker=dict(color='#059669', size=10, symbol='triangle-up'),
                            hovertemplate='<b>BUY</b><br>%{x}<br>Price: %{y}<extra></extra>'
                        ),
                        row=1, col=1
                    )
                if not sell_signals.empty:
                    fig.add_trace(
                        go.Scatter(
                            x=sell_signals['date'], 
                            y=sell_signals['price'], 
                            mode='markers', 
                            name='Sell Signal', 
                            marker=dict(color='#f43f5e', size=10, symbol='triangle-down'),
                            hovertemplate='<b>SELL</b><br>%{x}<br>Price: %{y}<extra></extra>'
                        ),
                        row=1, col=1
                    )

    fig.update_layout(
        title_text=f"{ticker} - Pairs Trading Strategy",
        showlegend=True,
        height=800,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )
    fig.update_yaxes(title_text=f"Price ({currency_symbol})", row=1, col=1)
    fig.update_yaxes(title_text="Spread", row=2, col=1)
    fig.update_yaxes(title_text="Z-Score", row=3, col=1)
    fig.update_xaxes(title_text="Date", row=3, col=1)
    
    return fig


def create_rsi_strategy_chart(backtest_df: pd.DataFrame, trades: List[Dict[str, Any]], ticker: str, currency_symbol: str = "$") -> go.Figure:
    """
    Create a specialized chart for RSI strategy with RSI indicator and overbought/oversold zones.
    """
    if backtest_df.empty:
        return go.Figure()

    fig = make_subplots(
        rows=2, cols=1,
        shared_xaxes=True,
        vertical_spacing=0.05,
        row_heights=[0.7, 0.3],
        subplot_titles=[f'{ticker} Price Chart', 'RSI Indicator']
    )

    # Add candlestick chart
    required_ohlc_cols = ['Open', 'High', 'Low', 'Close']
    has_ohlc_data = all(col in backtest_df.columns for col in required_ohlc_cols)
    
    if has_ohlc_data:
        fig.add_trace(
            go.Candlestick(
                x=backtest_df.index,
                open=backtest_df['Open'],
                high=backtest_df['High'],
                low=backtest_df['Low'],
                close=backtest_df['Close'],
                name=f'{ticker} Price',
                increasing_line_color='green',
                decreasing_line_color='red'
            ),
            row=1, col=1
        )
    elif 'Close' in backtest_df.columns:
        fig.add_trace(
            go.Scatter(
                x=backtest_df.index,
                y=backtest_df['Close'],
                name=f'{ticker} Price',
                line=dict(color='blue')
            ),
            row=1, col=1
        )

    # Add RSI line if available
    if 'momentum_rsi' in backtest_df.columns:
        fig.add_trace(
            go.Scatter(
                x=backtest_df.index,
                y=backtest_df['momentum_rsi'],
                name='RSI',
                line=dict(color='purple', width=2)
            ),
            row=2, col=1
        )
        
        # Add RSI reference lines
        fig.add_hline(y=70, line_dash="dash", line_color="red", row=2, col=1, annotation_text="Overbought (70)")
        fig.add_hline(y=30, line_dash="dash", line_color="red", row=2, col=1, annotation_text="Oversold (30)")
        fig.add_hline(y=50, line_dash="dash", line_color="gray", row=2, col=1, annotation_text="Neutral (50)")
        
        # Add overbought/oversold zones
        fig.add_hrect(y0=70, y1=100, line_width=0, fillcolor="red", opacity=0.1, row=2, col=1)
        fig.add_hrect(y0=0, y1=30, line_width=0, fillcolor="green", opacity=0.1, row=2, col=1)

    # Add trade markers
    if isinstance(trades, list) and trades and len(trades) > 0:
        trades_df = pd.DataFrame(trades)
        if not trades_df.empty:
            if 'type' in trades_df.columns and 'date' in trades_df.columns and 'price' in trades_df.columns:
                buy_signals = trades_df[trades_df['type'] == 'BUY']
                sell_signals = trades_df[trades_df['type'] == 'SELL']
                
                if not buy_signals.empty:
                    fig.add_trace(
                        go.Scatter(
                            x=buy_signals['date'], 
                            y=buy_signals['price'], 
                            mode='markers', 
                            name='Buy Signal', 
                            marker=dict(color='#059669', size=10, symbol='triangle-up'),
                            hovertemplate='<b>BUY</b><br>%{x}<br>Price: %{y}<extra></extra>'
                        ),
                        row=1, col=1
                    )
                if not sell_signals.empty:
                    fig.add_trace(
                        go.Scatter(
                            x=sell_signals['date'], 
                            y=sell_signals['price'], 
                            mode='markers', 
                            name='Sell Signal', 
                            marker=dict(color='#f43f5e', size=10, symbol='triangle-down'),
                            hovertemplate='<b>SELL</b><br>%{x}<br>Price: %{y}<extra></extra>'
                        ),
                        row=1, col=1
                    )

    fig.update_layout(
        title_text=f"{ticker} - RSI Strategy",
        showlegend=True,
        height=700,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )
    fig.update_yaxes(title_text=f"Price ({currency_symbol})", row=1, col=1)
    fig.update_yaxes(title_text="RSI", row=2, col=1)
    fig.update_xaxes(title_text="Date", row=2, col=1)
    
    return fig


def create_momentum_strategy_chart(backtest_df: pd.DataFrame, trades: List[Dict[str, Any]], ticker: str, currency_symbol: str = "$") -> go.Figure:
    """
    Create a specialized chart for momentum strategy with momentum indicators.
    """
    if backtest_df.empty:
        return go.Figure()

    fig = make_subplots(
        rows=2, cols=1,
        shared_xaxes=True,
        vertical_spacing=0.05,
        row_heights=[0.7, 0.3],
        subplot_titles=[f'{ticker} Price Chart', 'Momentum Indicators']
    )

    # Add candlestick chart
    required_ohlc_cols = ['Open', 'High', 'Low', 'Close']
    has_ohlc_data = all(col in backtest_df.columns for col in required_ohlc_cols)
    
    if has_ohlc_data:
        fig.add_trace(
            go.Candlestick(
                x=backtest_df.index,
                open=backtest_df['Open'],
                high=backtest_df['High'],
                low=backtest_df['Low'],
                close=backtest_df['Close'],
                name=f'{ticker} Price',
                increasing_line_color='green',
                decreasing_line_color='red'
            ),
            row=1, col=1
        )
    elif 'Close' in backtest_df.columns:
        fig.add_trace(
            go.Scatter(
                x=backtest_df.index,
                y=backtest_df['Close'],
                name=f'{ticker} Price',
                line=dict(color='blue')
            ),
            row=1, col=1
        )

    # Add momentum indicators if available
    momentum_cols = [col for col in backtest_df.columns if 'momentum' in col.lower()]
    colors = ['blue', 'red', 'green', 'orange', 'purple', 'brown']
    for i, col in enumerate(momentum_cols):
        fig.add_trace(
            go.Scatter(
                x=backtest_df.index,
                y=backtest_df[col],
                name=col,
                line=dict(color=colors[i % len(colors)], width=1.5)
            ),
            row=2, col=1
        )

    # Add trade markers
    if isinstance(trades, list) and trades and len(trades) > 0:
        trades_df = pd.DataFrame(trades)
        if not trades_df.empty:
            if 'type' in trades_df.columns and 'date' in trades_df.columns and 'price' in trades_df.columns:
                buy_signals = trades_df[trades_df['type'] == 'BUY']
                sell_signals = trades_df[trades_df['type'] == 'SELL']
                
                if not buy_signals.empty:
                    fig.add_trace(
                        go.Scatter(
                            x=buy_signals['date'], 
                            y=buy_signals['price'], 
                            mode='markers', 
                            name='Buy Signal', 
                            marker=dict(color='#059669', size=10, symbol='triangle-up'),
                            hovertemplate='<b>BUY</b><br>%{x}<br>Price: %{y}<extra></extra>'
                        ),
                        row=1, col=1
                    )
                if not sell_signals.empty:
                    fig.add_trace(
                        go.Scatter(
                            x=sell_signals['date'], 
                            y=sell_signals['price'], 
                            mode='markers', 
                            name='Sell Signal', 
                            marker=dict(color='#f43f5e', size=10, symbol='triangle-down'),
                            hovertemplate='<b>SELL</b><br>%{x}<br>Price: %{y}<extra></extra>'
                        ),
                        row=1, col=1
                    )

    fig.update_layout(
        title_text=f"{ticker} - Momentum Strategy",
        showlegend=True,
        height=700,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )
    fig.update_yaxes(title_text=f"Price ({currency_symbol})", row=1, col=1)
    fig.update_yaxes(title_text="Indicator Value", row=2, col=1)
    fig.update_xaxes(title_text="Date", row=2, col=1)
    
    return fig