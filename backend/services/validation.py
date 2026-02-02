from __future__ import annotations
import pandas as pd
from typing import Tuple, Optional

# --- TODO: Future Fact-Checking Layer ---
'''
Future enhancement ideas for a news validation/fact-checking layer:

1. Source Reliability Scoring:
   - Predefine a dictionary of "trusted sources" with scores (e.g., {"Reuters": 0.9, "Bloomberg": 0.9, "WSJ": 0.85}).
   - Score news items based on their source.

2. Cross-Verification:
   - If the same news event (using NLP entity extraction) appears in multiple trusted outlets, increase its reliability score.

3. AI Fact-Check Agent:
   - Create a new agent that uses an LLM (like Gemini) with a specific prompt to evaluate a news claim.
   - Example Prompt: "Given the following financial news headline and summary, assess its likely veracity on a scale of 0 to 1 and provide a brief justification. Cross-reference with known market events. Headline: '...' Summary: '...'"
'''

# ===================================================================
#                      TECHNICAL SIGNAL FUNCTIONS
# ===================================================================

def sma_crossover_signal(df: pd.DataFrame) -> str:
    """
    Calculates a simple SMA crossover signal.
      - BUY if SMA50 crosses above SMA200 (golden cross).
      - SELL if SMA50 crosses below SMA200 (death cross).
      - HOLD otherwise.
    """
    # Ensure required columns and data length
    required_cols = ['SMA_50', 'SMA_200']
    if df.empty or not all(col in df.columns for col in required_cols):
        return "HOLD"
    if len(df) < 2:
        return "HOLD"

    # Use .iloc for safe positional access
    s50_last = df['SMA_50'].iloc[-1]
    s50_prev = df['SMA_50'].iloc[-2]
    s200_last = df['SMA_200'].iloc[-1]
    s200_prev = df['SMA_200'].iloc[-2]

    # Check for NaN values before comparison
    if pd.isna(s50_last) or pd.isna(s50_prev) or pd.isna(s200_last) or pd.isna(s200_prev):
        return "HOLD"

    # Golden Cross (Buy Signal)
    if s50_prev <= s200_prev and s50_last > s200_last:
        return "BUY"
    
    # Death Cross (Sell Signal)
    if s50_prev >= s200_prev and s50_last < s200_last:
        return "SELL"
        
    return "HOLD"

def rsi_filter(df: pd.DataFrame, rsi_col: str = 'momentum_rsi', lower: int = 30, upper: int = 70) -> str:
    """
    Returns the state of the RSI indicator (Oversold, Overbought, or OK).
    """
    if df.empty or rsi_col not in df.columns or df[rsi_col].dropna().empty:
        return "UNKNOWN"
    
    last_rsi = df[rsi_col].dropna().iloc[-1]
    
    if last_rsi < lower:
        return "OVERSOLD"
    if last_rsi > upper:
        return "OVERBOUGHT"
    return "OK"

def atr_stop_levels(df: pd.DataFrame, atr_col: str = 'volatility_atr', atr_mult: float = 2.0) -> Tuple[Optional[float], Optional[float]]:
    """
    Calculates dynamic stop-loss and take-profit levels based on the Average True Range (ATR).
    """
    if df.empty or 'Close' not in df.columns or atr_col not in df.columns:
        return (None, None)
        
    last_close = df["Close"].iloc[-1]
    last_atr = df[atr_col].iloc[-1]

    if pd.isna(last_close) or pd.isna(last_atr):
        return (None, None)

    stop_loss = last_close - (atr_mult * last_atr)
    take_profit = last_close + (2 * atr_mult * last_atr)  # Standard 2:1 Reward:Risk ratio
    
    return round(stop_loss, 2), round(take_profit, 2)