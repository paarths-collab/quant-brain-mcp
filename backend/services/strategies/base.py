
from abc import ABC, abstractmethod
from typing import Dict, Any
import pandas as pd

class Strategy(ABC):
    name: str = "Base Strategy"

    @property
    def parameters(self) -> Dict[str, Any]:
        """Return the current parameters of the strategy."""
        return {}

    @abstractmethod
    def generate_signals(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        Core logic to generate signals. 
        Must return DataFrame with 'signal', 'entry_long', 'entry_short' columns.
        """
        pass

    def analyze(self, data: pd.DataFrame) -> Dict[str, Any]:
        """
        Standardized execution method for the API.
        Returns a dictionary structure ready for the frontend.
        """
        if data.empty:
            return {"error": "No data provided"}

        try:
            # Run the strategy logic
            df_signals = self.generate_signals(data)
            
            # Extract signals for JSON response
            signals = []
            
            # We only care about non-zero signals for the marker list
            # But for the chart, we might want the full series. 
            # Let's return the key markers.
            
            # Filter for actual trades/signals
            # signal: 1 (Buy), -1 (Sell), 0 (Hold/None)
            
            signal_events = df_signals[df_signals['signal'] != 0].copy()
            
            for index, row in signal_events.iterrows():
                signals.append({
                    "date": index.isoformat(),
                    "type": "BUY" if row['signal'] > 0 else "SELL",
                    "price": row['Close'],
                    "metadata": {
                        "entry_price": row.get('entry_long') if row['signal'] > 0 else row.get('entry_short')
                    }
                })

            # Calculate latest sentiment/meta
            latest_signal = df_signals['signal'].iloc[-1]
            latest_mood = "BULLISH" if latest_signal > 0 else "BEARISH" if latest_signal < 0 else "NEUTRAL"

            return {
                "name": self.name,
                "parameters": self.parameters,
                "signals": signals,
                "meta": {
                    "last_updated": data.index[-1].isoformat(),
                    "current_mood": latest_mood,
                    "signal_count": len(signals)
                },
                # Optional: return the indicator values for plotting (e.g., SMA lines)
                # This depends on the specific strategy adding columns to df_signals
                "indicators": self._extract_indicators(df_signals) 
            }
            
        except Exception as e:
            return {"error": str(e)}

    def _extract_indicators(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        Helper to extract common indicator columns if they exist.
        Strategies can override this to return specific line data.
        """
        indicators = {}
        # Example: if SMA columns exist, extract them
        for col in df.columns:
            if col.lower().startswith(('sma', 'ema', 'rsi', 'upper', 'lower', 'donchian')):
                # Convert series to list of {time, value} for lightweight-charts
                indicators[col] = [
                    {"time": date.isoformat(), "value": val} 
                    for date, val in df[col].dropna().items()
                ]
        return indicators
