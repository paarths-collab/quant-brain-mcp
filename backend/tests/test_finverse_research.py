from backend.services.research_service import generate_research_report
import os

def test_finverse_integration():
    print("Testing Finverse-integrated Research Agent for AAPL...")
    
    # Check if Keys are present (warn if not, but run anyway to see fallback)
    if not os.getenv("GEMINI_API_KEY"):
        print("WARNING: GEMINI_API_KEY not found. Expect fallback report.")
        
    result = generate_research_report("AAPL")
    
    if "error" in result:
        print(f"Error: {result['error']}")
    else:
        print(f"Success! Report generated for {result['companyName']}")
        print(f"Sentiment Score: {result.get('meta', {}).get('sentiment')}")
        print(f"Research Source: {result.get('meta', {}).get('research_source')}")
        print("--- Report Preview ---")
        print(result['report'][:500] + "...")

if __name__ == "__main__":
    test_finverse_integration()
