"""
Intent Router - Analyzes user messages and determines which pipelines to trigger
"""
import os
import re
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum


class PipelineType(str, Enum):
    """Available pipeline types"""
    EMOTION = "emotion"          # Emotional trading advisor
    STOCK_INFO = "stock_info"    # Stock fundamentals, price, news
    INTENT = "intent"            # What does user want to achieve?
    WEALTH = "wealth"            # Long-term wealth management advice
    COMBINED = "combined"        # Run multiple pipelines


@dataclass
class UserIntent:
    """Parsed user intent"""
    raw_message: str
    detected_ticker: Optional[str] = None
    detected_market: str = "US"
    pipelines_needed: List[PipelineType] = field(default_factory=list)
    clarification_needed: bool = False
    clarification_question: Optional[str] = None
    user_emotion: Optional[str] = None
    confidence: float = 0.0
    context: Dict = field(default_factory=dict)


class IntentRouter:
    """
    Analyzes user messages and routes to appropriate pipelines.
    Works with AutoGen for human-in-the-loop clarification.
    """
    
    # Emotion-related keywords
    EMOTION_KEYWORDS = {
        "panic": ["panic", "scared", "fear", "crash", "dump", "sell everything", "blood", "disaster"],
        "fomo": ["fomo", "missing out", "everyone buying", "mooning", "to the moon", "regret not buying"],
        "greed": ["all in", "yolo", "leverage", "margin", "double down"],
        "anxiety": ["worried", "anxious", "nervous", "sleepless", "cant sleep", "stress"],
        "revenge": ["revenge", "make back", "recover losses", "get even"]
    }
    
    # Stock info keywords
    STOCK_INFO_KEYWORDS = [
        "price", "chart", "fundamental", "pe ratio", "earnings", "revenue",
        "dividend", "analyst", "target", "buy or sell", "good investment",
        "worth buying", "undervalued", "overvalued", "news", "what happened",
        "buy", "sell", "holding", "position",
        "why is", "why did", "falling", "down", "drop", "decline", "slump", "plunge"
    ]
    
    # Wealth/planning keywords
    WEALTH_KEYWORDS = [
        "portfolio", "allocate", "allocation", "retire", "retirement", "long term",
        "savings", "wealth", "diversify", "etf", "index fund",
        "monthly invest", "sip", "dca", "dollar cost", "planning", "plan"
    ]
    
    # Ticker patterns
    TICKER_PATTERNS = [
        r'\b([A-Z]{1,5})\b',  # US tickers: AAPL, MSFT
        r'\b([A-Z]{2,})\.(NS|BO)\b',  # Indian: RELIANCE.NS, TCS.BO
        r'\b([A-Z]+(?:BANK|FIN|IT|AUTO|PHARMA)?)\b',  # Indian names
    ]
    
    # Common Indian stocks mapping
    INDIAN_STOCKS = {
        "reliance": "RELIANCE",
        "tcs": "TCS", 
        "infosys": "INFY",
        "infy": "INFY",
        "hdfc": "HDFCBANK",
        "hdfc bank": "HDFCBANK",
        "icici": "ICICIBANK",
        "sbi": "SBIN",
        "wipro": "WIPRO",
        "tata motors": "TATAMOTORS",
        "tata steel": "TATASTEEL",
        "bharti": "BHARTIARTL",
        "airtel": "BHARTIARTL",
        "kotak": "KOTAKBANK",
        "axis": "AXISBANK",
        "maruti": "MARUTI",
        "bajaj": "BAJFINANCE",
        "asian paints": "ASIANPAINT",
        "hul": "HINDUNILVR",
        "itc": "ITC",
        "sunpharma": "SUNPHARMA",
        "titan": "TITAN",
        "ultratech": "ULTRACEMCO",
        "adani": "ADANIENT",
        "ongc": "ONGC",
        "ntpc": "NTPC",
        "powergrid": "POWERGRID",
        "coalindia": "COALINDIA",
    }
    
    # Common words to exclude when looking for tickers
    EXCLUDE_WORDS = {
        "I", "A", "THE", "IT", "IS", "BE", "TO", "OF", "AND", "IN", "FOR", "ON", "AT", "BY", "OR", "AN", "AS", "SO", "UP", "IF", "MY", "DO", "GO", "NO", "WE", "US", "AM", "PM", "OK", "ALL", "ETF", "IPO",
        "BUY", "SELL", "HOLD", "HELP", "NEED", "WANT", "HAVE", "HAS", "HAD", "GOT", "GET", "CAN", "WILL", "WOULD", "SHOULD", "COULD", "MUST", "MAY", "MIGHT",
        "WHAT", "WHERE", "WHEN", "WHY", "HOW", "WHO", "WHICH", "THAT", "THIS", "THESE", "THOSE",
        "NOT", "NOW", "RIGHT", "JUST", "ONLY", "ALSO", "BUT", "YET", "STILL", "BACK",
        "GOOD", "BAD", "BEST", "WORST", "BETTER", "WORSE", "HIGH", "LOW", "BIG", "SMALL",
        "MARKET", "STOCK", "SHARE", "TRADE", "PRICE", "COST", "VALUE", "MONEY", "CASH", "FUND", "PORTFOLIO",
        "PANIC", "CRASH", "DUMP", "PUMP", "DEAL", "LOSS", "PROFIT", "GAIN", "RISK", "SAFE",
        "LONG", "SHORT", "CALL", "PUT", "OPTION", "FUTURE", "INDEX", "SECTOR",
        "REALLY", "VERY", "MUCH", "MANY", "ALOT", "LOT", "BIT", "LITTLE",
        "THANKS", "PLEASE", "SORRY", "HELLO", "HI", "HEY", "DEAR", "SIR", "MADAM",
        "TODAY", "TOMORROW", "YESTERDAY", "WEEK", "MONTH", "YEAR", "DAY",
        "INVEST", "INVESTING", "INVESTMENT", "TRADING", "TRADER", "BROKER",
        "ACCOUNT", "BANK", "WALLET", "SAVING", "CHECKING", "CREDIT", "DEBIT",
        "IM", "IVE", "ID", "ILL", "DONT", "DOESNT", "DIDNT", "WONT", "CANT", "ISNT", "ARENT", "WASN", "WEREN",
        "ABOUT", "ABOVE", "BELOW", "UNDER", "OVER", "THROUGH", "INTO", "ONTO", "FROM",
        "WITH", "WITHOUT", "WITHIN", "BETWEEN", "AMONG", "AROUND", "AGAINST", "DURING",
        "BUILD", "MAKE", "CREATE", "START", "BEGIN", "END", "STOP", "FINISH", "DONE",
        "KEEP", "STAY", "LEAVE", "CHANGE", "MOVE", "SWITCH", "TRANSFER",
        "LOOK", "SEE", "WATCH", "HEAR", "LISTEN", "TALK", "SPEAK", "SAY", "TELL", "ASK",
        "THINK", "KNOW", "UNDERSTAND", "BELIEVE", "FEEL", "HOPE", "WISH",
    }

    def __init__(self):
        self.conversation_history: List[Dict] = []
        
    def analyze(self, message: str, context: Optional[Dict] = None) -> UserIntent:
        """
        Analyze user message and determine intent + required pipelines.
        
        Returns UserIntent with:
        - Detected ticker (if any)
        - Which pipelines to run
        - Whether clarification is needed
        - Confidence score
        """
        message_lower = message.lower()
        intent = UserIntent(raw_message=message, context=context or {})
        
        # Step 1: Detect ticker
        ticker, market = self._extract_ticker(message)
        intent.detected_ticker = ticker
        intent.detected_market = market
        
        # Step 2: Detect emotional state
        emotion = self._detect_emotion(message_lower)
        if emotion:
            intent.user_emotion = emotion
            intent.pipelines_needed.append(PipelineType.EMOTION)
            intent.confidence += 0.3
        
        # Step 3: Check for stock info request
        if self._wants_stock_info(message_lower):
            intent.pipelines_needed.append(PipelineType.STOCK_INFO)
            intent.confidence += 0.25
        
        # Step 4: Check for wealth/planning request
        if self._wants_wealth_advice(message_lower):
            intent.pipelines_needed.append(PipelineType.WEALTH)
            intent.confidence += 0.25
        
        # Step 5: If no clear intent, may need clarification
        if not intent.pipelines_needed:
            if ticker:
                # Default to stock analysis when a ticker is present
                intent.pipelines_needed.append(PipelineType.STOCK_INFO)
                intent.confidence = max(intent.confidence, 0.55)
            else:
                intent.pipelines_needed.append(PipelineType.INTENT)
                intent.clarification_needed = True
                intent.clarification_question = self._generate_clarification(message, ticker)
                intent.confidence = 0.2
        
        # Step 6: If multiple pipelines, mark as combined
        if len(intent.pipelines_needed) > 1:
            intent.pipelines_needed.insert(0, PipelineType.COMBINED)
        
        # Boost confidence if ticker was found
        if ticker:
            intent.confidence = min(1.0, intent.confidence + 0.2)
        
        return intent
    
    def _extract_ticker(self, message: str) -> Tuple[Optional[str], str]:
        """Extract stock ticker and detect market"""
        message_lower = message.lower()

        # Highest-confidence explicit symbol extraction.
        # Examples: IREDA.NS, TCS.BO, BRK.B
        dotted_match = re.search(r'\b([A-Za-z][A-Za-z0-9]{0,14})\.(NS|BO|[A-Za-z])\b', message, flags=re.IGNORECASE)
        if dotted_match:
            base = dotted_match.group(1).upper()
            suffix = dotted_match.group(2).upper()
            if suffix in {"NS", "BO"}:
                return f"{base}.{suffix}", "IN"
            return f"{base}.{suffix}", "US"
        
        # Check for known Indian stocks first
        for name, ticker in self.INDIAN_STOCKS.items():
            # Check for exact word match of the name
            if re.search(r'\b' + re.escape(name) + r'\b', message_lower):
                return ticker, "IN"
            # Check if the ticker itself appears as a word
            if re.search(r'\b' + re.escape(ticker.lower()) + r'\b', message_lower):
                return ticker, "IN"
        
        # Check for .NS or .BO suffix (Indian)
        indian_match = re.search(r'\b([A-Z][A-Z0-9]{1,14})\.(NS|BO)\b', message.upper())
        if indian_match:
            return f"{indian_match.group(1)}.{indian_match.group(2)}", "IN"
        
        # Check for Indian market indicators
        is_indian_context = any(x in message_lower for x in ["nse", "bse", "nifty", "sensex", "india", "indian", "rupee", "₹"])
        
        if is_indian_context:
            # Look for ticker in Indian context
            # In Indian context, we might be more lenient or look for specific Indian patterns
            # But let's first check for standard uppercase tickers
            ticker_match = re.search(r'\b([A-Z]{3,10})\b', message) # Case sensitive search first
            if ticker_match:
                candidate = ticker_match.group(1)
                if candidate.upper() not in self.EXCLUDE_WORDS:
                    return candidate, "IN"
        
        # US market - look for standard tickers
        # Strategy 1: Look for UPPERCASE words in mixed-case messages
        # valid tickers are usually 2-5 chars
        
        # Get all potential token candidates
        tokens = re.findall(r'\b[A-Za-z][A-Za-z0-9]{0,14}\b', message)
        
        candidates = []
        for token in tokens:
            # Remove non-alpha for checking
            clean = re.sub(r'[^A-Za-z]', '', token)
            if not clean:
                continue
                
            upper_clean = clean.upper()
            
            # Skip excluded words
            if upper_clean in self.EXCLUDE_WORDS:
                continue
                
            # Must be 2-5 chars for US tickers usually, sometimes 1 (C, F)
            if 1 <= len(clean) <= 5:
                # If the original token was fully uppercase and length > 1 (avoid single "I" or "A")
                if token.isupper() and len(token) >= 2:
                    return upper_clean, "US"
                # Or if it's a known single letter ticker like 'F' (Ford) or 'C' (Citi) AND uppercase
                if token.isupper() and len(token) == 1 and token not in ["I", "A"]:
                     return upper_clean, "US"
                     
                candidates.append(upper_clean)

        # Strategy 2: If no strict uppercase match found, but we have candidates that are NOT common words
        # This is riskier (e.g. "stock" vs "STOCK"), but we have a big exclude list now.
        for cand in candidates:
             if cand not in self.EXCLUDE_WORDS:
                 # Additional check: 3+ chars are safer guesses for lowercase inputs
                 if len(cand) >= 3:
                     # Only return if we didn't find a market context for IN
                     return cand, "US"
        
        return None, "US"
    
    def _detect_emotion(self, message: str) -> Optional[str]:
        """Detect emotional state from message"""
        for emotion, keywords in self.EMOTION_KEYWORDS.items():
            for keyword in keywords:
                if keyword in message:
                    return emotion
        return None
    
    def _wants_stock_info(self, message: str) -> bool:
        """Check if user wants stock information"""
        return any(kw in message for kw in self.STOCK_INFO_KEYWORDS)
    
    def _wants_wealth_advice(self, message: str) -> bool:
        """Check if user wants wealth/portfolio advice"""
        return any(kw in message for kw in self.WEALTH_KEYWORDS)
    
    def _generate_clarification(self, message: str, ticker: Optional[str]) -> str:
        """Generate a clarification question"""
        if ticker:
            return f"I see you mentioned {ticker}. What would you like to know?\n\n" \
                   f"1️⃣ **Stock Analysis** - Price, fundamentals, news\n" \
                   f"2️⃣ **Emotional Check** - Am I making a panic/FOMO decision?\n" \
                   f"3️⃣ **Full Report** - Complete analysis with recommendation\n\n" \
                   f"Just reply with the number or describe what you need!"
        else:
            return "I'd love to help! Could you tell me:\n\n" \
                   "1️⃣ Which **stock or ticker** are you interested in?\n" \
                   "2️⃣ Are you looking for **analysis**, **emotional guidance**, or **portfolio advice**?\n\n" \
                   "Example: 'Should I buy AAPL?' or 'I'm panicking about my TSLA position'"

    def parse_clarification_response(self, response: str, original_intent: UserIntent) -> UserIntent:
        """
        Parse user's response to clarification question.
        
        Key logic:
        - Menu selection (1, 2, 3) sets the pipeline type
        - If stock_info/emotion selected but no ticker, ask for ticker
        - If ticker provided, extract it and proceed
        """
        response_lower = response.lower().strip()
        
        # Helper to check if ticker-required pipeline needs a ticker
        def needs_ticker_for_pipeline(pipelines: List[PipelineType], ticker: Optional[str]) -> bool:
            ticker_required = [PipelineType.STOCK_INFO, PipelineType.EMOTION, PipelineType.COMBINED]
            return any(p in ticker_required for p in pipelines) and not ticker
        
        # Check for numbered response (menu selection)
        if response_lower in ["1", "one", "stock", "analysis", "info"]:
            original_intent.pipelines_needed = [PipelineType.STOCK_INFO]
            original_intent.confidence = 0.9
            
            # Check if we still need a ticker
            if not original_intent.detected_ticker:
                original_intent.clarification_needed = True
                original_intent.clarification_question = (
                    "Great! Which **stock or ticker** would you like me to analyze?\n\n"
                    "Examples: `AAPL`, `TSLA`, `RELIANCE`, `TCS`"
                )
            else:
                original_intent.clarification_needed = False
            
        elif response_lower in ["2", "two", "emotion", "emotional", "panic", "fomo"]:
            original_intent.pipelines_needed = [PipelineType.EMOTION]
            original_intent.confidence = 0.9
            
            # Emotion pipeline also needs a ticker
            if not original_intent.detected_ticker:
                original_intent.clarification_needed = True
                original_intent.clarification_question = (
                    "I'll help you check for emotional bias. Which **stock** are you concerned about?\n\n"
                    "Examples: `AAPL`, `TSLA`, `RELIANCE`"
                )
            else:
                original_intent.clarification_needed = False
            
        elif response_lower in ["3", "three", "full", "complete", "all", "everything"]:
            original_intent.pipelines_needed = [PipelineType.COMBINED, PipelineType.STOCK_INFO, PipelineType.EMOTION]
            original_intent.confidence = 0.95
            
            if not original_intent.detected_ticker:
                original_intent.clarification_needed = True
                original_intent.clarification_question = (
                    "I'll run a full analysis. Which **stock** should I analyze?\n\n"
                    "Examples: `AAPL`, `TSLA`, `RELIANCE`, `TCS`"
                )
            else:
                original_intent.clarification_needed = False
        
        elif response_lower in ["wealth", "portfolio", "retirement", "invest", "investing"]:
            # Wealth pipeline doesn't require a specific ticker
            original_intent.pipelines_needed = [PipelineType.WEALTH]
            original_intent.clarification_needed = False
            original_intent.confidence = 0.9
        
        else:
            # Try to extract a ticker from the response
            ticker, market = self._extract_ticker(response)
            if ticker:
                original_intent.detected_ticker = ticker
                original_intent.detected_market = market
                original_intent.clarification_needed = False
                original_intent.confidence = 0.85
                
                # If no pipeline was set yet, default to stock_info
                if not original_intent.pipelines_needed:
                    original_intent.pipelines_needed = [PipelineType.STOCK_INFO]
            else:
                # Re-analyze with new context
                new_intent = self.analyze(response, context={"previous": original_intent.raw_message})
                if new_intent.detected_ticker and not original_intent.detected_ticker:
                    original_intent.detected_ticker = new_intent.detected_ticker
                    original_intent.detected_market = new_intent.detected_market
                if new_intent.pipelines_needed:
                    original_intent.pipelines_needed = new_intent.pipelines_needed
                    original_intent.confidence = new_intent.confidence
                
                # Final check: do we still need something?
                original_intent.clarification_needed = needs_ticker_for_pipeline(
                    original_intent.pipelines_needed, 
                    original_intent.detected_ticker
                )
                if original_intent.clarification_needed:
                    original_intent.clarification_question = (
                        "I'm not sure which stock you mean. Could you provide a **ticker symbol**?\n\n"
                        "Examples: `AAPL`, `TSLA`, `GOOGL`, `RELIANCE`, `TCS`"
                    )
        
        return original_intent


# Singleton instance
_router: Optional[IntentRouter] = None

def get_intent_router() -> IntentRouter:
    """Get singleton IntentRouter instance"""
    global _router
    if _router is None:
        _router = IntentRouter()
    return _router
