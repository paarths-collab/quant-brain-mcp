class PositionSizingService:

    def calculate(self, capital, entry_price, stop_loss):
        if entry_price == stop_loss:
             return {
                "capital": capital,
                "risk_per_trade": 0.0,
                "position_size_shares": 0,
                "error": "Entry price equals stop loss"
            }
        
        # Risk 2% of capital per trade
        risk_per_trade = capital * 0.02
        risk_per_share = abs(entry_price - stop_loss)

        if risk_per_share == 0:
             return {
                "capital": capital,
                "risk_per_trade": risk_per_trade,
                "position_size_shares": 0
             }

        shares = risk_per_trade / risk_per_share

        return {
            "capital": capital,
            "risk_per_trade": risk_per_trade,
            "position_size_shares": int(shares)
        }
