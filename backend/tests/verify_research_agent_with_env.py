import os
import sys
from dotenv import load_dotenv

# Load .env from root
load_dotenv(".env")

# Verify key is loaded
key = os.getenv("GEMINI_API_KEY")
if not key:
    print("❌ Check: GEMINI_API_KEY not found in environment after loading .env")
else:
    print("✅ Check: GEMINI_API_KEY loaded successfully (starts with {})".format(key[:4]))

# Add backend to path so imports work
sys.path.append(os.path.join(os.getcwd(), 'backend'))

from backend.services.research_service import generate_research_report

def test_research():
    print("Testing Research Agent for AAPL...")
    result = generate_research_report("AAPL")
    
    if "error" in result:
        print(f"Error: {result['error']}")
    else:
        print(f"Success! Report generated for {result['companyName']}")
        print("--- Report Preview ---")
        print(result['report'][:500] + "...")

if __name__ == "__main__":
    test_research()
