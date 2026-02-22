import yfinance as yf

class TradeLevelsService:

    def calculate(self, ticker, action):
        try:
            # Using period="5d" to get recent price, taking last close
            stock = yf.Ticker(ticker)
            hist = stock.history(period="5d")
            
            if hist.empty:
                return {
                    "entry_price": 0.0,
                    "stop_loss": 0.0,
                    "target_price": 0.0,
                    "risk_reward_ratio": 0.0,
                    "error": "No data found"
                }
                
            price = hist["Close"].iloc[-1]

            if action == "BUY":
                stop_loss = price * 0.95
                target = price * 1.10
            elif action == "SELL":
                stop_loss = price * 1.05
                target = price * 0.90
            else:
                # Default / Hold
                return {
                    "entry_price": float(price),
                    "stop_loss": 0.0,
                    "target_price": 0.0,
                    "risk_reward_ratio": 0.0
                }

            if abs(price - stop_loss) == 0:
                rr_ratio = 0.0
            else:
                rr_ratio = abs((target - price) / (price - stop_loss))

            return {
                "entry_price": float(price),
                "stop_loss": float(stop_loss),
                "target_price": float(target),
                "risk_reward_ratio": float(rr_ratio)
            }
        except Exception as e:
            return {
                "entry_price": 0.0,
                "stop_loss": 0.0,
                "target_price": 0.0,
                "risk_reward_ratio": 0.0,
                "error": str(e)
            }
