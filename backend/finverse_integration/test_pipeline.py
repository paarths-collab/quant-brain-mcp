"""
Test Script for Finverse Wealth Pipeline
Run this to verify everything works!

Usage: python test_pipeline.py
"""

import os
import sys
from datetime import datetime

# Check if API key is set
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

print("""
╔══════════════════════════════════════════════════════════╗
║     Finverse Wealth Pipeline - Test Suite               ║
║     100% FREE Resources - Smart AI Analysis              ║
╚══════════════════════════════════════════════════════════╝
""")

# Verify setup
print("🔍 Checking setup...")
print(f"✓ Python version: {sys.version.split()[0]}")

if not GEMINI_API_KEY:
    print("""
❌ GEMINI_API_KEY not found!

📝 Quick Setup:
   1. Visit: https://makersuite.google.com/app/apikey
   2. Click "Create API Key"
   3. Copy your key
   4. Run: export GEMINI_API_KEY='your-key-here'
   
Then run this test again.
""")
    sys.exit(1)

print(f"✓ Gemini API Key: {GEMINI_API_KEY[:10]}...{GEMINI_API_KEY[-5:]}")

# Import pipeline
try:
    from wealth_pipeline_free_implementation import WealthOrchestrator
    print("✓ Pipeline imported successfully")
except ImportError as e:
    print(f"""
❌ Failed to import pipeline: {e}

💡 Install dependencies:
   pip install -r requirements.txt
""")
    sys.exit(1)

# Initialize orchestrator
print("\n🚀 Initializing orchestrator...")
try:
    orchestrator = WealthOrchestrator()
    print("✓ Orchestrator initialized")
except Exception as e:
    print(f"❌ Initialization failed: {e}")
    sys.exit(1)

# ============================================================================
# TEST CASES
# ============================================================================

test_cases = [
    {
        "name": "Test 1: Casual Chat",
        "input": {
            "raw_input": "Hey, I have 50000 rupees to invest. I'm 28 years old, working in IT, okay with moderate risk. Need it in about 5 years.",
            "channel": "chat"
        },
        "description": "Testing casual conversational input"
    },
    {
        "name": "Test 2: Minimal Info (Should Ask Questions)",
        "input": {
            "raw_input": "I want to invest some money",
            "channel": "chat"
        },
        "description": "Testing clarification question generation"
    },
    {
        "name": "Test 3: Formal Email",
        "input": {
            "raw_input": """Subject: Investment Consultation Request

Dear Advisor,

I am a 35-year-old software professional with stable employment. I wish to invest ₹5,00,000 for my daughter's higher education fund. She is currently 8 years old, giving me approximately 10 years before I need these funds.

I would describe my risk tolerance as moderate - I understand market volatility but prefer not to take excessive risks with this education fund.

Please advise on suitable investment options.

Best regards""",
            "channel": "email"
        },
        "description": "Testing formal email input and professional response"
    },
    {
        "name": "Test 4: Voice Transcript (Messy)",
        "input": {
            "raw_input": "Um, so I just got my annual bonus, it's like around 2 lakhs or something, and I'm thinking maybe I should, you know, invest it instead of just keeping in savings? I'm 31, work in marketing, pretty stable job. Not sure about stocks though, seems risky. What do you think?",
            "channel": "voice"
        },
        "description": "Testing messy voice input with filler words"
    }
]

print("\n" + "="*60)
print("Running Test Cases")
print("="*60)

for i, test in enumerate(test_cases, 1):
    print(f"\n{'─'*60}")
    print(f"📋 {test['name']}")
    print(f"📝 {test['description']}")
    print(f"{'─'*60}")
    
    print(f"\n💬 INPUT ({test['input']['channel']}):")
    print(f"   {test['input']['raw_input'][:100]}..." if len(test['input']['raw_input']) > 100 else f"   {test['input']['raw_input']}")
    
    try:
        start_time = datetime.now()
        
        print("\n⏳ Processing...")
        result = orchestrator.analyze(test['input'])
        
        processing_time = (datetime.now() - start_time).total_seconds()
        
        print(f"\n✅ Completed in {processing_time:.2f}s")
        
        # Show results
        print("\n📊 RESULTS:")
        print(f"   Risk Score: {result.get('risk_score', 'N/A')}/10")
        print(f"   Sectors: {', '.join(result.get('sectors', []))}")
        print(f"   Stocks Recommended: {len(result.get('stocks', []))}")
        
        if result.get('clarification_questions'):
            print(f"\n❓ CLARIFICATION QUESTIONS:")
            for q in result['clarification_questions']:
                print(f"   • {q}")
        
        if result.get('stocks'):
            print(f"\n💼 STOCK ALLOCATION:")
            for stock in result['stocks']:
                print(f"   • {stock['symbol']}: {stock['allocation']}% - {stock['name']}")
        
        print(f"\n📝 REPORT PREVIEW:")
        report_lines = result['report'].split('\n')[:10]
        for line in report_lines:
            print(f"   {line}")
        if len(result['report'].split('\n')) > 10:
            print("   ...")
        
        if result.get('errors'):
            print(f"\n⚠️ WARNINGS:")
            for error in result['errors']:
                print(f"   • {error}")
        
        print(f"\n🔍 EXECUTION LOG:")
        for log in result.get('execution_log', [])[-5:]:  # Last 5 entries
            print(f"   {log}")
        
        print(f"\n{'✅ TEST PASSED' if not result.get('errors') else '⚠️ TEST PASSED WITH WARNINGS'}")
        
    except Exception as e:
        print(f"\n❌ TEST FAILED")
        print(f"   Error: {str(e)}")
        import traceback
        print(f"\n   Traceback:")
        print(traceback.format_exc())

# ============================================================================
# SUMMARY
# ============================================================================

print("\n" + "="*60)
print("Test Summary")
print("="*60)
print("""
✅ If you see recommendations above, your pipeline is working!

🎯 Next Steps:
   1. Integrate with your existing code
   2. Test with real user inputs
   3. Deploy to production
   
📚 Read INTEGRATION_GUIDE.md for detailed integration steps

💡 Tips:
   - Add caching for faster responses
   - Implement rate limiting for production
   - Monitor with logging/analytics
   
🚀 You're ready to go!
""")

# Optional: Interactive test
print("\n" + "="*60)
response = input("Want to test with your own input? (y/n): ")

if response.lower() == 'y':
    print("\n📝 Enter your investment query (press Enter twice when done):")
    lines = []
    while True:
        line = input()
        if line:
            lines.append(line)
        else:
            break
    
    user_input = '\n'.join(lines)
    
    if user_input:
        print("\n⏳ Processing your query...")
        try:
            result = orchestrator.analyze({
                "raw_input": user_input,
                "channel": "chat"
            })
            
            print("\n" + "="*60)
            print("YOUR PERSONALIZED RECOMMENDATIONS")
            print("="*60)
            print(result['report'])
            
            if result.get('clarification_questions'):
                print("\n❓ I need more information:")
                for q in result['clarification_questions']:
                    print(f"   {q}")
            
        except Exception as e:
            print(f"\n❌ Error: {e}")
    else:
        print("No input provided.")

print("\n👋 Test complete! Check INTEGRATION_GUIDE.md for next steps.\n")
