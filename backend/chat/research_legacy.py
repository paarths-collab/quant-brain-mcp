from fastapi import APIRouter, HTTPException, Body
from fastapi.responses import FileResponse
from .core.research_service import generate_research_report
from .core.groq_agent import GroqAgent
from typing import Dict, Any
from pathlib import Path
from datetime import datetime

REPORTS_DIR = Path(__file__).parent.parent / "reports"
REPORTS_DIR.mkdir(exist_ok=True)

router = APIRouter(prefix="/api/research", tags=["Research Agent"])

@router.post("/analyze")
def analyze_stock(
    payload: Dict[str, str] = Body(...)
):
    """
    Generates an AI Research Report for a consolidated symbol.
    Payload: {"symbol": "AAPL"}
    """
    symbol = payload.get("symbol")
    if not symbol:
        raise HTTPException(status_code=400, detail="Symbol is required")
        
    try:
        report = generate_research_report(symbol)
        if "error" in report:
             raise HTTPException(status_code=400, detail=report["error"])
        return report
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/report")
def generate_research_report_file(payload: Dict[str, Any] = Body(...)):
    symbol = payload.get("symbol")
    market = payload.get("market")
    report_format = payload.get("format", "quantstats")
    range_period = payload.get("range", "1y")
    benchmark = payload.get("benchmark")
    if not symbol:
        raise HTTPException(status_code=400, detail="Symbol is required")

    if market and market.lower() == "india" and ".NS" not in symbol.upper() and ".BO" not in symbol.upper():
        symbol = f"{symbol}.NS"

    safe_symbol = symbol.replace(".", "_")

    if report_format != "quantstats":
        raise HTTPException(status_code=400, detail="Only 'quantstats' report format is supported.")
    try:
        import pandas as pd
        import yfinance as yf
        import quantstats as qs

        if not benchmark:
            benchmark = "^NSEI" if market and market.lower() == "india" else "SPY"

        price_df = yf.Ticker(symbol).history(period=range_period)
        if price_df is None or price_df.empty:
            raise HTTPException(status_code=400, detail=f"No market data found for {symbol}")

        returns = price_df["Close"].pct_change().dropna()
        returns_idx = pd.to_datetime(returns.index)
        if getattr(returns_idx, "tz", None) is not None:
            returns_idx = returns_idx.tz_convert(None)
        returns.index = returns_idx
        if returns.empty or len(returns) < 10:
            raise HTTPException(status_code=400, detail="Not enough return data to generate QuantStats report")

        benchmark_df = yf.Ticker(str(benchmark)).history(period=range_period)
        benchmark_returns = None
        if benchmark_df is not None and not benchmark_df.empty:
            benchmark_returns = benchmark_df["Close"].pct_change().dropna()
            benchmark_idx = pd.to_datetime(benchmark_returns.index)
            if getattr(benchmark_idx, "tz", None) is not None:
                benchmark_idx = benchmark_idx.tz_convert(None)
            benchmark_returns.index = benchmark_idx
            if benchmark_returns is not None and not benchmark_returns.empty:
                aligned_idx = returns.index.intersection(benchmark_returns.index)
                if len(aligned_idx) >= 10:
                    returns = returns.loc[aligned_idx]
                    benchmark_returns = benchmark_returns.loc[aligned_idx]
                else:
                    benchmark_returns = None

        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        filename = f"quantstats_research_{safe_symbol}_{timestamp}.html"
        filepath = REPORTS_DIR / filename

        qs.reports.html(
            returns,
            benchmark=benchmark_returns,
            output=str(filepath),
            title=f"QuantStats Research Report - {symbol}",
            download_filename=filename,
        )

        return {
            "success": True,
            "filename": filename,
            "downloadUrl": f"/research/report/download/{filename}",
        }
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        print(f"Error generating QuantStats report for {symbol}: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"QuantStats report generation failed: {str(e)}")


@router.post("/interpret-image")
def interpret_research_image(payload: Dict[str, Any] = Body(...)):
    """Analyze a screenshot of the research page and return an analyst-style report."""
    symbol = payload.get("symbol")
    market = payload.get("market", "us")
    image_data_url = payload.get("imageDataUrl")
    context = payload.get("context", {})

    if not symbol:
        raise HTTPException(status_code=400, detail="Symbol is required")
    if not image_data_url:
        raise HTTPException(status_code=400, detail="imageDataUrl is required")

    source = str(context.get("source", "")).strip().lower() if isinstance(context, dict) else ""

    if source == "technical_page_screenshot":
        prompt = (
            "You are a senior technical analyst reviewing a trading dashboard screenshot. "
            "The provided context contains validated metrics from the page state. "
            "Use BOTH screenshot observations and context metrics, with context treated as trusted values when present.\n\n"
            "OUTPUT FORMAT (use markdown):\n"
            "## Market State\n"
            "- State: Bullish / Bearish / Sideways\n"
            "- Subtype: Strong / Weak / Range / Choppy\n"
            "- Confidence: <number>%\n"
            "- Reason: 1 sentence based on structure\n\n"
            "## Metrics Snapshot\n"
            "- Symbol\n"
            "- Price\n"
            "- 1D Change %\n"
            "- RSI(14)\n"
            "- MTF Bias\n"
            "- Resistance Levels (R1/R2)\n"
            "- Support Levels (S1/S2)\n\n"
            "## Trend Diagnosis\n"
            "- 3 bullet points explaining trend strength/weakness and invalidation conditions\n\n"
            "## Trade Plan\n"
            "- Verdict: BUY / HOLD / SELL\n"
            "- Action: one line\n"
            "- Entry zone\n"
            "- Stop loss\n"
            "- Target 1 and Target 2\n\n"
            "## Risk Notes\n"
            "- 3 concise risk points\n\n"
            "Rules:\n"
            "- Do NOT output generic 'not visible' for fields already present in context\n"
            "- Be precise and concise\n"
            "- Do not invent values missing from BOTH screenshot and context\n\n"
            f"Context:\nSymbol: {symbol}\nMarket: {market}\nData context: {context}"
        )
    else:
        prompt = (
            "You are a senior equity research analyst reviewing a dashboard screenshot. "
            "Extract all visible values and provide a structured report for a trader.\n\n"
            "OUTPUT FORMAT (use markdown):\n"
            "## Recommendation\n"
            "- Verdict: BUY / HOLD / SELL\n"
            "- Confidence: Low / Medium / High\n"
            "- One-line thesis\n\n"
            "## What Is Visible\n"
            "- Company / symbol / price / trend / sentiment / recommendation values exactly as seen\n"
            "- Mention any values not readable as 'not visible'\n\n"
            "## QuantStats Fit Check\n"
            "- Whether visible momentum/risk setup supports generating a quantstats report now\n"
            "- Mention benchmark alignment (SPY for US, ^NSEI for India)\n\n"
            "## Risk Signals\n"
            "- 3 specific downside risks from visible data\n\n"
            "## Action Plan\n"
            "- Immediate next 3 steps for the user\n\n"
            "Rules:\n"
            "- Use only what is visible in the screenshot + provided context\n"
            "- Be precise and concise\n"
            "- Do not invent metrics that are not visible\n\n"
            f"Context:\nSymbol: {symbol}\nMarket: {market}\nData context: {context}"
        )

    llm = GroqAgent()
    requested_model = payload.get("imageModel") or "meta-llama/llama-4-scout-17b-16e-instruct"
    allowed_models = {
        "meta-llama/llama-4-scout-17b-16e-instruct",
        "llama-3.2-11b-vision-preview",
    }
    model = requested_model if requested_model in allowed_models else "meta-llama/llama-4-scout-17b-16e-instruct"

    analysis = llm.generate_vision_response(
        prompt=prompt,
        image_data_url=image_data_url,
        model=model,
        temperature=0.2,
    )

    if not analysis or analysis.lower().startswith("error"):
        raise HTTPException(status_code=502, detail="AI screenshot analysis failed. Check GROQ_API_KEY and retry.")

    return {"analysis": analysis}


@router.get("/report/download/{filename}")
def download_research_report(filename: str):
    file_path = REPORTS_DIR / filename
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Report not found")
    if filename.endswith(".html"):
        media_type = "text/html"
    else:
        media_type = "application/pdf"
    return FileResponse(path=str(file_path), filename=filename, media_type=media_type)
