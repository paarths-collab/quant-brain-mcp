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
