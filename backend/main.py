from pathlib import Path
from dotenv import load_dotenv

# Load .env file from backend folder
env_path = Path(__file__).parent / ".env"
load_dotenv(env_path)

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.routes.market import router as market_router
from backend.routes.peers import router as peers_router
from backend.routes.fundamentals import router as fundamentals_router
from backend.routes.sectors import router as sectors_router
from backend.routes.macro import router as macro_router
from backend.routes.network import router as network_router
from backend.routes.backtest import router as backtest_router
from backend.routes.research import router as research_router
from backend.routes.social import router as social_router
from backend.routes.eia_routes import router as eia_router
from backend.routes.insights_routes import router as insights_router
from backend.routes.reports_routes import router as reports_router
from backend.routes.fred_routes import router as fred_router
from backend.routes.treemap import router as treemap_router
from backend.routes.sentiment import router as sentiment_router
from backend.finverse_integration.routes.wealth_routes import router as wealth_router

app = FastAPI(title="Boomerang Backend")

# Configure CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(market_router)
app.include_router(peers_router)
app.include_router(fundamentals_router)
app.include_router(sectors_router)
app.include_router(macro_router)
app.include_router(network_router)
app.include_router(backtest_router)
app.include_router(research_router)
app.include_router(social_router)
app.include_router(eia_router)
app.include_router(insights_router)
app.include_router(reports_router)
app.include_router(fred_router)
app.include_router(treemap_router)
app.include_router(sentiment_router)
app.include_router(wealth_router)

@app.get("/")
def health():
    return {"status": "ok"}
