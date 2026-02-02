from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import os
from dotenv import load_dotenv

# Load Env
load_dotenv()

# Import Workflow
try:
    from .main_workflow import build_graph
except ImportError:
    build_graph = None

from .routes.wealth_routes import router as wealth_router

app = FastAPI(title="Autonomous Wealth Manager")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(wealth_router)

class UserInput(BaseModel):
    raw_input: str
    market: str = Field(default="US", description="Target market: US or IN")

@app.post("/analyze")
async def analyze_portfolio(data: UserInput):
    if not build_graph:
        raise HTTPException(status_code=500, detail="Workflow not initialized")
    
    workflow = build_graph()
    initial_state = {
        "raw_input": data.raw_input,
        "market": data.market, # Direct injection from UI
        "messages": [],
        "errors": []
    }
    
    try:
        final_state = workflow.invoke(initial_state)
        return {
            "report": final_state.get("investment_report", "No Report Generated"),
            "logs": final_state.get("messages", []),
            "errors": final_state.get("errors", [])
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
