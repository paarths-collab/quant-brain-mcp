import re

class TickerExtractor:

    def extract(self, text):
         # Matches 2-5 uppercase letters, surrounded by word boundaries
        pattern = r"\b[A-Z]{2,5}\b"
        
        # Common false positives to filter out
        stopwords = {"THE", "AND", "FOR", "INC", "LTD", "PLC", "CORP", "CO", "NEW", "YORK", "USD", "GBP", "EUR", "CEO", "CFO", "CTO", "AI", "URL", "HTTP", "HTTPS", "WWW", "COM", "ORG", "NET"}
        
        candidates = list(set(re.findall(pattern, text)))
        
        # Filter stopwords
        filtered = [c for c in candidates if c not in stopwords]
        
        return filtered
