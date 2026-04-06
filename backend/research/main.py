from fastapi import APIRouter, HTTPException, Body
from fastapi.responses import FileResponse
from .service import generate_research_report
from .core.groq_agent import GroqAgent
from backend.services.market_data import market_service
from typing import Dict, Any
from pathlib import Path
from datetime import datetime

REPORTS_DIR = Path(__file__).parent / "reports"
REPORTS_DIR.mkdir(exist_ok=True)

router = APIRouter(prefix="", tags=["Research Agent"])

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
        import quantstats as qs

        if not benchmark:
            benchmark = "^NSEI" if market and market.lower() == "india" else "SPY"

        price_df = market_service.get_history(symbol, period=range_period)
        if price_df is None or price_df.empty:
            raise HTTPException(status_code=400, detail=f"No market data found for {symbol}")

        returns = price_df["Close"].pct_change().dropna()
        returns_idx = pd.to_datetime(returns.index)
        if getattr(returns_idx, "tz", None) is not None:
            returns_idx = returns_idx.tz_convert(None)
        returns.index = returns_idx
        if returns.empty or len(returns) < 10:
            raise HTTPException(status_code=400, detail="Not enough return data to generate QuantStats report")

        benchmark_df = market_service.get_history(str(benchmark), period=range_period)
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
            "You are a senior technical analyst providing in-depth market insights and trading strategy. "
            "Use scholarly reasoning, brainstorm multiple scenarios, and explain your thesis with conviction. "
            "The provided context contains validated metrics from the page state. "
            "Use BOTH screenshot observations and context metrics, with context treated as trusted values.\n\n"
            "OUTPUT FORMAT (use markdown with narrative paragraphs, NOT bullet lists):\n\n"
            "## Market State & Analysis\n"
            "Write 2-3 paragraphs explaining the current market condition. Start with the state (Bullish/Bearish/Sideways) "
            "and confidence, then elaborate on WHY the structure supports this view. Reference key technical levels "
            "(support/resistance), price action, RSI, and multi-timeframe bias. Explain the macro thesis: are higher highs "
            "and higher lows forming? Is momentum sustained or diverging? What invalidation levels matter?\n\n"
            "## Trend Diagnosis & Reasoning\n"
            "Write 2-3 paragraphs analyzing the trend strength. Explain the evidence for or against trend continuation. "
            "Discuss how RSI aligns with price action, whether volume supports the move, and where the trend becomes invalid. "
            "Be explicit about what could break this thesis.\n\n"
            "## Trading Strategy Brainstorm\n"
            "Write 2-3 paragraphs exploring multiple tactical approaches. Brainstorm 3-4 distinct setups or strategies "
            "(scalp, swing, position) that could work from this level. For each, outline the entry logic, where stops belong, "
            "and realistic profit targets based on the visible structure. Explain why each setup has merit and what could invalidate it.\n\n"
            "## Risk Assessment\n"
            "Write 2-3 paragraphs detailing downside scenarios. Identify 3-4 specific risks: What volume/price action kills "
            "the bullish case? What external factors (breadth, sector rotation, volatility) could reverse the thesis? "
            "At what price do you cut losses? What candle patterns or indicator divergences are red flags?\n\n"
            "## Action Plan\n"
            "Write 1-2 paragraphs with immediate, concrete next steps. Define your trade verdict (BUY/HOLD/SELL with conviction), "
            "entry zones, stop placement, and target pricing. Be specific: mention exact support/resistance levels and percentage moves.\n\n"
            "Rules:\n"
            "- Prefer narrative paragraphs over lists; use prose to connect reasoning\n"
            "- Show your work: explain technical reasoning, not just conclusions\n"
            "- Brainstorm alternatives; acknowledge uncertainty where it exists\n"
            "- Do NOT output generic 'not visible' for fields in context; use provided validated data\n"
            "- Do not invent metrics or prices not visible in screenshot or context\n"
            "- Be precise, authoritative, and concise\n\n"
            f"Context:\nSymbol: {symbol}\nMarket: {market}\nData context: {context}"
        )
    elif source == "global_page_analyzer":
        prompt = (
            "You are a senior market analyst reviewing a full-page investment dashboard screenshot. "
            "Write a concise, meaningful narrative for a user, not a raw extraction dump.\n\n"
            "OUTPUT FORMAT (use markdown):\n"
            "## Executive View\n"
            "Write one short paragraph (3-5 sentences) covering: overall market tone, whether data is complete/incomplete, and the most important directional takeaway.\n\n"
            "## Recommendation\n"
            "Write one short paragraph with: Verdict (BUY/HOLD/SELL), confidence (Low/Medium/High), and one-line thesis embedded naturally in prose.\n\n"
            "## Evidence From Screen\n"
            "Write one paragraph summarizing visible movers and breadth. Mention at most 6 symbols total: strongest gainers, weakest losers, and 1-2 mixed/flat names. "
            "Do not list every symbol on screen.\n\n"
            "## QuantStats Fit\n"
            "Write one paragraph on whether a QuantStats report is appropriate now, and include benchmark alignment (SPY for US, ^NSEI for India).\n\n"
            "## Risks\n"
            "Write exactly 3 bullet points with concrete downside risks based only on visible evidence.\n\n"
            "## Next Steps\n"
            "Write exactly 3 numbered, practical steps that are specific and immediately actionable.\n\n"
            "Rules:\n"
            "- Prefer paragraphs over long bullet dumps\n"
            "- If values are missing, mention data gaps briefly in prose (avoid repeating 'not visible' many times)\n"
            "- Use only what is visible in screenshot + provided context\n"
            "- Do not invent numbers or indicators not visible\n\n"
            f"Context:\nSymbol: {symbol}\nMarket: {market}\nData context: {context}"
        )
    else:
        prompt = (
            "You are a senior equity research analyst reviewing a dashboard screenshot. "
            "Provide a structured report for a trader with clear narrative paragraphs and concise evidence.\n\n"
            "OUTPUT FORMAT (use markdown):\n"
            "## Recommendation\n"
            "Write one paragraph with verdict (BUY/HOLD/SELL), confidence, and one-line thesis.\n\n"
            "## What Is Visible\n"
            "Write one paragraph summarizing what is visible. Mention only the most relevant symbols/moves; do not dump every row.\n\n"
            "## QuantStats Fit Check\n"
            "Write one short paragraph on whether current visible setup supports generating a QuantStats report now, and mention benchmark alignment (SPY for US, ^NSEI for India).\n\n"
            "## Risk Signals\n"
            "Write exactly 3 concise bullet points with specific downside risks from visible data.\n\n"
            "## Action Plan\n"
            "Write exactly 3 numbered immediate next steps.\n\n"
            "Rules:\n"
            "- Use only what is visible in the screenshot + provided context\n"
            "- Prefer paragraph narrative over long bullet lists\n"
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
