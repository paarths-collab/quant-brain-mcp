import unittest
import os
import json
import sys
# Add project root
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

from backend.services.sector_resolver import SectorResolver

class TestSectorResolver(unittest.TestCase):
    
    def setUp(self):
        self.resolver = SectorResolver()
        # Clear external data to isolate tests
        self.resolver.sector_map = {}
        self.resolver.metadata_cache = {}

        # Mock metadata for deterministic testing
        self.resolver.metadata_cache = {
            "TEST1": {"sector": "Technology", "industry": "Software - Infrastructure"},
            "TEST2": {"sector": "Technology", "industry": "Information Technology Services"},
            "TEST3": {"sector": "Industrials", "industry": "Consulting Services"},
            "TEST4": {"sector": "Technology", "industry": "IT Consulting & Other Services"},
            "INFY.NS": {"sector": "Technology", "industry": "Information Technology Services"},
            "TCS.NS": {"sector": "Technology", "industry": "Information Technology Services"}
        }

    def test_direct_match(self):
        # We inject a fake map entry
        self.resolver.sector_map["fake_index"] = ["ABC", "DEF"]
        result = self.resolver.resolve_sector("fake_index")
        self.assertEqual(result, ["ABC", "DEF"])

    def test_metadata_match_simple(self):
        # Should match "Technology"
        result = self.resolver.resolve_sector("Technology")
        self.assertIn("TEST1", result)
        self.assertIn("INFY.NS", result)

    def test_metadata_match_complex(self):
        # "IT Consulting"
        # Should match "Information Technology Services" (IT matches Technology? No. "IT" matches "IT"?)
        # Wait, my logic is: 
        # m_sector = "Technology", m_industry = "Information Technology Services"
        # search terms = ["it", "consulting"]
        # "it" in "information technology services"? No. "technology" != "it".
        # "consulting" in "information technology services"? No.
        
        # Adjust test data to match what yfinance returns or what I expect
        # "IT Consulting & Other Services" -> matches "IT" and "Consulting"
        
        result = self.resolver.resolve_sector("IT Consulting")
        self.assertIn("TEST4", result)
        # TEST3 "Consulting Services" -> matches "Consulting", but not "IT"
        # If strict "all terms" logic:
        # "IT" in "Consulting Services"? No.
        self.assertNotIn("TEST3", result) 

    def test_fallback_logic(self):
        # Force a case with 0 matches
        # e.g. "Biology"
        # We need to mock web_search to avoid actual calls
        
        class MockWebSearch:
            def search_sector(self, query):
                return ["WEB_MATCH_1", "WEB_MATCH_2"]
        
        self.resolver.web_search = MockWebSearch()
        
        result = self.resolver.resolve_sector("Biology")
        self.assertIn("WEB_MATCH_1", result)
        self.assertIn("WEB_MATCH_2", result)

if __name__ == '__main__':
    unittest.main()
