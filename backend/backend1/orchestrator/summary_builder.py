class SummaryBuilder:

    def build_summary(self, ticker, fundamental, technical, sentiment, risk_profile="moderate", market_pe=None):
        
        # Handle cases where agents return errors or None
        if not fundamental or "error" in fundamental:
             fundamental = {"revenue_growth_qtr_yoy": 0, "pe_ratio": 0, "roe": 0, "metrics": {}}
        if not technical or "error" in technical:
             technical = {"rsi": 50, "trend": "Neutral", "macd_signal": "Neutral"}
        if not sentiment or "error" in sentiment:
             sentiment = {"sentiment_score": 0.5, "bullish_signals": [], "bearish_signals": [], "risk_flags": [], "catalysts": []}

        fundamental_scored = self._score_fundamental(fundamental, market_pe)
        technical_scored = self._score_technical(technical)
        news_scored = self._score_news(sentiment)

        weights = self._get_weights(risk_profile)

        raw_score = (
            weights["fundamental"] * fundamental_scored["score"] +
            weights["technical"] * technical_scored["score"] +
            weights["sentiment"] * news_scored["score"]
        )
        
        # Risk Penalty (Beta/Volatility)
        risk_penalty = 0
        metrics = fundamental.get("metrics", {})
        beta = metrics.get("beta")
        if beta and beta > 1.5:
            risk_penalty += 0.5
            
        final_score = max(0, round(raw_score - risk_penalty, 2))
        
        # Calculate Confidence Score (Internal data integrity)
        confidence = 0.8 # Base confidence
        if fundamental_scored["score"] == 0 and technical_scored["score"] == 5:
             confidence -= 0.4 # Penalty for missing data
        if len(news_scored["reasons"]) < 2:
             confidence -= 0.1
             
        # Volatility check
        volatility = "Medium" 
        if news_scored["score"] < 4 or technical_scored["score"] < 4:
             volatility = "High"

        return {
            "ticker": ticker,
            "fundamental": fundamental_scored,
            "technical": technical_scored,
            "news": news_scored,
            "risk_profile": risk_profile,
            "final_score": final_score,
            "confidence": round(confidence, 2),
            "volatility": volatility,
            "market_context": market_pe # Pass through for LLM context
        }

    # ... _score_fundamental remains same ...

    def _score_technical(self, data):
        score = 5.0 # Start neutral
        reasons = []

        if not data or "error" in data:
            return {"score": 5.0, "reasons": ["Insufficient technical data"]}

        rsi = data.get("rsi", 50)
        
        # RSI Analysis
        if rsi < 30:
            score += 2.0
            reasons.append(f"Oversold (RSI {rsi:.0f})")
        elif rsi > 70:
            score -= 1.0
            reasons.append(f"Overbought (RSI {rsi:.0f})")
        
        # Trend Alignment: Price vs SMA50 vs SMA200
        price = data.get("price", 0)
        sma50 = data.get("sma50", 0)
        sma200 = data.get("sma200", 0)
        
        if price and sma50:
            if price > sma50:
                score += 1.0
                reasons.append("Price > SMA50 (Short-term Bull)")
            else:
                score -= 1.0
            
        if price and sma200:
            if price > sma200:
                 score += 1.0
                 reasons.append("Price > SMA200 (Long-term Bull)")
            else:
                 score -= 1.0
                 reasons.append("Price < SMA200 (Long-term Bear)")
        
        # MACD
        if data.get("macd_signal") == "Bullish":
            score += 1.5
            reasons.append("Positive MACD crossover")
        elif data.get("macd_signal") == "Bearish":
             score -= 1.5

        final_score = max(0, min(10, score))

        return {
            "score": round(final_score, 2),
            "reasons": reasons
        }

    def _score_news(self, news_data):
        # Institutional Damped News Scoring
        sent_score = news_data.get("sentiment_score", 0.5)
        
        # Map 0.5 -> 5.0. 0.0 -> 1.0. 1.0 -> 9.0.
        base_score = (sent_score - 0.5) * 8 + 5
        
        # Adjust based on institutional signal counts
        bull_count = len(news_data.get("bullish_signals", []))
        bear_count = len(news_data.get("bearish_signals", []))
        risk_count = len(news_data.get("risk_flags", []))
        
        # Signals impact
        score = base_score + (bull_count * 0.4) - (bear_count * 0.4) - (risk_count * 0.7)
        
        # Clamp to 0-10
        final_score = max(0, min(10, score))

        reasons = []
        reasons.extend(news_data.get("bullish_signals", [])[:2])
        reasons.extend(news_data.get("bearish_signals", [])[:2])
            
        return {
            "score": round(final_score, 2),
            "reasons": reasons,
            "catalysts": news_data.get("catalysts", []),
            "risk_flags": news_data.get("risk_flags", [])
        }

    def _score_fundamental(self, data, market_pe=None):
        score = 0
        reasons = []

        # Use new metrics structure if available, else flat
        metrics = data.get("metrics", {})
        rev_growth = metrics.get("revenue_growth_qtr_yoy") or data.get("revenue_growth") or 0
        pe = metrics.get("trailing_pe") or data.get("pe_ratio") or 100

        if rev_growth > 0.4:
            score += 3
            reasons.append(f"Exceptional revenue growth ({rev_growth*100:.1f}%)")
        elif rev_growth > 0.2:
            score += 2
            reasons.append(f"Solid revenue growth ({rev_growth*100:.1f}%)")
             
        if pe < 20 and pe > 0:
            score += 3
            reasons.append(f"Attractive Valuation (P/E {pe:.1f})")
        elif pe < 35 and pe > 0:
            score += 2
            reasons.append(f"Reasonable P/E ({pe:.1f})")
        elif pe < 60 and pe > 0:
            if rev_growth > 0.3:
                score += 1 # Slightly positive if high growth
                reasons.append(f"Elevated P/E ({pe:.1f}) justified by growth")
            else:
                score -= 1
                reasons.append(f"Elevated Valuation (P/E {pe:.1f})")
        elif pe > 60:
             score -= 2
             reasons.append(f"Rich Valuation (P/E {pe:.1f})")

        # ROE check - placeholder as not currently in FinancialAgent
        # if data.get("roe", 0) > 0.2:
        #    score += 2
        #    reasons.append("High return on equity")
            
        # Normalize to 0-10 scale approx
        final_score = max(0, min(10, score + 4)) # Base 4 points

        return {
            "score": round(final_score, 2),
            "reasons": reasons
        }

    def _get_weights(self, risk_profile):
        if risk_profile == "conservative":
            return {"fundamental": 0.6, "technical": 0.2, "sentiment": 0.2}
        if risk_profile == "aggressive":
            return {"fundamental": 0.3, "technical": 0.4, "sentiment": 0.3}
        # default moderate
        return {"fundamental": 0.5, "technical": 0.3, "sentiment": 0.2}
