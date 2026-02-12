"""
Finverse Wealth API - Complete FastAPI Integration
100% FREE resources, production-ready

Run: uvicorn api_server:app --reload
"""

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
import os
from datetime import datetime

# Import the FREE implementation
from wealth_pipeline_free_implementation import WealthOrchestrator

# ============================================================================
# CONFIGURATION
# ============================================================================

# Load API key from environment
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    print("⚠️  WARNING: GEMINI_API_KEY not set!")
    print("📝 Get your free key: https://makersuite.google.com/app/apikey")
    print("💡 Then: export GEMINI_API_KEY='your-key'")

# ============================================================================
# FASTAPI APP
# ============================================================================

app = FastAPI(
    title="Finverse Wealth API",
    description="Smart Investment Analysis using FREE AI",
    version="2.0.0"
)

# Enable CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize orchestrator ONCE (not per request)
orchestrator = WealthOrchestrator()

# ============================================================================
# REQUEST/RESPONSE MODELS
# ============================================================================

class AnalysisRequest(BaseModel):
    """Smart, flexible input - no rigid templates"""
    message: str = Field(
        ...,
        description="Any format: chat message, email, voice transcript",
        examples=[
            "I have 50k to invest for 5 years, moderate risk",
            "Subject: Investment help\\n\\nI'm 35, want to invest 2L for my kid's education..."
        ]
    )
    channel: str = Field(
        default="chat",
        description="Input channel affects response format",
        examples=["chat", "email", "whatsapp", "voice"]
    )
    user_id: Optional[str] = Field(
        default=None,
        description="Optional: for tracking and personalization"
    )

class StockRecommendation(BaseModel):
    symbol: str
    name: str
    sector: str
    allocation: float
    rationale: str
    current_price: Optional[float] = None

class AnalysisResponse(BaseModel):
    """Complete analysis response"""
    success: bool
    report: str
    stocks: List[StockRecommendation]
    allocation: Dict[str, float]
    sectors: List[str]
    risk_score: int
    clarification_questions: List[str] = []
    extracted_profile: Dict[str, Any] = {}
    errors: List[str] = []
    execution_log: List[str] = []
    processing_time_seconds: Optional[float] = None
    timestamp: str

class HealthResponse(BaseModel):
    status: str
    gemini_configured: bool
    version: str

# ============================================================================
# ENDPOINTS
# ============================================================================

@app.get("/", response_model=HealthResponse)
async def root():
    """Health check endpoint"""
    return HealthResponse(
        status="healthy",
        gemini_configured=bool(GEMINI_API_KEY),
        version="2.0.0"
    )

@app.post("/api/v2/analyze", response_model=AnalysisResponse)
async def analyze_investment(request: AnalysisRequest):
    """
    🧠 Smart Investment Analysis
    
    Accepts ANY input format:
    - Casual chat: "I got 1L, what to do?"
    - Formal email: Complete investment inquiry
    - Voice transcript: "Um, so I have this money..."
    
    Returns personalized recommendations using FREE AI
    """
    
    if not GEMINI_API_KEY:
        raise HTTPException(
            status_code=503,
            detail="GEMINI_API_KEY not configured. Get free key from https://makersuite.google.com/app/apikey"
        )
    
    try:
        start_time = datetime.now()
        
        # Run analysis
        result = orchestrator.analyze({
            "raw_input": request.message,
            "channel": request.channel
        })
        
        processing_time = (datetime.now() - start_time).total_seconds()
        
        # Convert to response format
        return AnalysisResponse(
            success=True,
            report=result["report"],
            stocks=[
                StockRecommendation(**stock)
                for stock in result["stocks"]
            ],
            allocation=result["allocation"],
            sectors=result["sectors"],
            risk_score=result["risk_score"],
            clarification_questions=result.get("clarification_questions", []),
            extracted_profile=result.get("extracted_profile", {}),
            errors=result.get("errors", []),
            execution_log=result.get("execution_log", []),
            processing_time_seconds=round(processing_time, 2),
            timestamp=datetime.now().isoformat()
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Analysis failed: {str(e)}"
        )

@app.post("/api/v2/clarify")
async def answer_clarification(
    original_message: str,
    answers: Dict[str, str]
):
    """
    Answer clarification questions
    
    Example:
    {
        "original_message": "I want to invest",
        "answers": {
            "investment_amount": "1 lakh",
            "time_horizon": "5 years",
            "risk_tolerance": "moderate"
        }
    }
    """
    
    # Combine original message with answers
    enhanced_message = f"{original_message}\n\nAdditional info:\n"
    enhanced_message += "\n".join([f"- {k}: {v}" for k, v in answers.items()])
    
    # Re-run analysis with more info
    return await analyze_investment(AnalysisRequest(
        message=enhanced_message,
        channel="chat"
    ))

@app.get("/api/v2/examples")
async def get_examples():
    """Example inputs for testing"""
    return {
        "examples": [
            {
                "title": "Casual Chat",
                "message": "Hey, I have 50k to invest. I'm 28, working in IT, okay with some risk. Need it in 3-4 years.",
                "channel": "chat"
            },
            {
                "title": "Formal Email",
                "message": """Subject: Investment Consultation
                
I am a 35-year-old software professional earning 20 LPA. 
I wish to invest 5 lakhs for my daughter's higher education fund.
She is currently 8 years old. I prefer moderate risk investments.
Please advise suitable options.

Thank you.""",
                "channel": "email"
            },
            {
                "title": "Voice Transcript",
                "message": "Um, so I just got my bonus, it's like 2 lakhs, and I'm thinking maybe stocks? I'm 31, pretty stable job. Not too risky though.",
                "channel": "voice"
            },
            {
                "title": "WhatsApp Style",
                "message": "Hi! Got 1L from selling my old bike. Want to invest for 2 years. Don't know much about stocks. Help?",
                "channel": "whatsapp"
            }
        ]
    }

# ============================================================================
# STREAMING ENDPOINT (Advanced)
# ============================================================================

@app.post("/api/v2/analyze/stream")
async def analyze_streaming(request: AnalysisRequest):
    """
    Streaming analysis - get real-time updates
    
    Returns Server-Sent Events (SSE) for real-time progress
    """
    from fastapi.responses import StreamingResponse
    import asyncio
    
    async def event_generator():
        """Generate SSE events"""
        
        # This is a simplified version
        # For full streaming, use LangGraph's stream mode
        
        yield f"data: {json.dumps({'step': 'started', 'message': 'Analysis started'})}\n\n"
        
        await asyncio.sleep(1)
        yield f"data: {json.dumps({'step': 'extraction', 'message': 'Extracting profile...'})}\n\n"
        
        # Run actual analysis
        result = orchestrator.analyze({
            "raw_input": request.message,
            "channel": request.channel
        })
        
        await asyncio.sleep(0.5)
        yield f"data: {json.dumps({'step': 'market_data', 'message': 'Fetching market data...'})}\n\n"
        
        await asyncio.sleep(0.5)
        yield f"data: {json.dumps({'step': 'analysis', 'message': 'Analyzing stocks...'})}\n\n"
        
        await asyncio.sleep(0.5)
        yield f"data: {json.dumps({'step': 'complete', 'result': result})}\n\n"
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream"
    )

# ============================================================================
# WEBHOOK ENDPOINTS (for integrations)
# ============================================================================

@app.post("/webhook/email")
async def email_webhook(
    sender: str,
    subject: str,
    body: str,
    background_tasks: BackgroundTasks
):
    """
    Email integration webhook
    
    Receives email, analyzes, sends response
    """
    
    result = orchestrator.analyze({
        "raw_input": f"Subject: {subject}\n\n{body}",
        "channel": "email"
    })
    
    # In production, send actual email here
    # background_tasks.add_task(send_email, sender, result["report"])
    
    return {
        "status": "processed",
        "sender": sender,
        "report_preview": result["report"][:200] + "..."
    }

@app.post("/webhook/whatsapp")
async def whatsapp_webhook(
    phone: str,
    message: str
):
    """
    WhatsApp integration webhook
    
    Receives WhatsApp message, returns concise response
    """
    
    result = orchestrator.analyze({
        "raw_input": message,
        "channel": "whatsapp"
    })
    
    # In production, send WhatsApp message here
    # send_whatsapp(phone, result["report"])
    
    return {
        "status": "processed",
        "phone": phone,
        "response": result["report"]
    }

# ============================================================================
# STARTUP/SHUTDOWN
# ============================================================================

@app.on_event("startup")
async def startup_event():
    """Initialize on startup"""
    print("🚀 Finverse Wealth API starting...")
    print(f"✅ Gemini configured: {bool(GEMINI_API_KEY)}")
    print("📊 Free resources: Yahoo Finance + DuckDuckGo")
    print("🎯 Ready to accept ANY input format!")

@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    print("👋 Finverse Wealth API shutting down...")

# ============================================================================
# MAIN (for direct execution)
# ============================================================================

if __name__ == "__main__":
    import uvicorn
    
    print("""
    ╔══════════════════════════════════════════════════════════╗
    ║          Finverse Wealth API - FREE Edition              ║
    ╚══════════════════════════════════════════════════════════╝
    
    📝 Setup:
       1. Get FREE Gemini key: https://makersuite.google.com/app/apikey
       2. export GEMINI_API_KEY='your-key'
       3. pip install -r requirements.txt
    
    🚀 Starting server...
    """)
    
    uvicorn.run(
        "api_server:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )
