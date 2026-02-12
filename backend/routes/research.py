from fastapi import APIRouter, HTTPException, Body
from fastapi.responses import FileResponse
from backend.services.research_service import generate_research_report
from backend.services.stock_sentiment_service import analyze_stock_sentiment
from backend.utils.pdf_generator import convert_html_to_pdf
from typing import Dict, Any
from pathlib import Path
from datetime import datetime
import html

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


def _build_research_html(data: Dict[str, Any]) -> str:
    market_data = data.get("market_data", {})
    news = data.get("news", {}).get("articles", [])
    supply_chain = data.get("supply_chain", {})

    def esc(val: Any) -> str:
        if val is None:
            return "-"
        return html.escape(str(val))

    news_items = "".join(
        f"<li><strong>{esc(n.get('title'))}</strong> - {esc(n.get('source'))}<br/>"
        f"<a href='{esc(n.get('url'))}'>{esc(n.get('url'))}</a></li>"
        for n in news[:8]
    ) or "<li>No recent news found.</li>"

    customers = "".join(
        f"<li><strong>{esc(c.get('name'))}</strong><br/>{esc(c.get('evidence'))}</li>"
        for c in supply_chain.get("customers", [])[:8]
    ) or "<li>No customer mentions found.</li>"

    suppliers = "".join(
        f"<li><strong>{esc(s.get('name'))}</strong><br/>{esc(s.get('evidence'))}</li>"
        for s in supply_chain.get("suppliers", [])[:8]
    ) or "<li>No supplier mentions found.</li>"

    return f"""
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <title>AI Research Report - {esc(data.get('symbol'))}</title>
  <style>
    body {{ font-family: Arial, sans-serif; color: #111; padding: 24px; }}
    h1 {{ margin: 0 0 8px; }}
    h2 {{ margin-top: 24px; }}
    .muted {{ color: #555; font-size: 12px; }}
    .grid {{ display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 12px; }}
    .card {{ border: 1px solid #ddd; padding: 12px; border-radius: 8px; }}
    ul {{ padding-left: 18px; }}
    a {{ color: #0b6efd; }}
  </style>
</head>
<body>
  <h1>AI Research Report</h1>
  <div class="muted">Generated {esc(datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC'))}</div>
  <h2>{esc(data.get('symbol'))} - {esc(data.get('name'))}</h2>
  <div class="grid">
    <div class="card"><strong>Price</strong><br/>{esc(data.get('price'))}</div>
    <div class="card"><strong>Recommendation</strong><br/>{esc(data.get('recommendation'))}</div>
    <div class="card"><strong>Outlook</strong><br/>{esc(data.get('outlook'))}</div>
    <div class="card"><strong>Sentiment</strong><br/>{esc(data.get('sentiment'))}</div>
  </div>

  <h2>Summary</h2>
  <p>{esc(data.get('summary'))}</p>

  <h2>Company Snapshot</h2>
  <div class="grid">
    <div class="card"><strong>Market Cap</strong><br/>{esc(market_data.get('market_cap_formatted'))}</div>
    <div class="card"><strong>Sector</strong><br/>{esc(market_data.get('sector'))}</div>
    <div class="card"><strong>Industry</strong><br/>{esc(market_data.get('industry'))}</div>
    <div class="card"><strong>P/E</strong><br/>{esc(market_data.get('pe_ratio'))}</div>
    <div class="card"><strong>Forward P/E</strong><br/>{esc(market_data.get('forward_pe'))}</div>
    <div class="card"><strong>EPS</strong><br/>{esc(market_data.get('eps'))}</div>
    <div class="card"><strong>Dividend Yield</strong><br/>{esc(market_data.get('dividend_yield'))}</div>
    <div class="card"><strong>Beta</strong><br/>{esc(market_data.get('beta'))}</div>
    <div class="card"><strong>52W High</strong><br/>{esc(market_data.get('52w_high'))}</div>
    <div class="card"><strong>52W Low</strong><br/>{esc(market_data.get('52w_low'))}</div>
    <div class="card"><strong>Revenue</strong><br/>{esc(market_data.get('revenue_formatted'))}</div>
    <div class="card"><strong>6M Change %</strong><br/>{esc(market_data.get('price_change_6m_pct'))}</div>
  </div>

  <h2>Recent News</h2>
  <ul>{news_items}</ul>

  <h2>Supply Chain (Experimental)</h2>
  <h3>Customers</h3>
  <ul>{customers}</ul>
  <h3>Suppliers</h3>
  <ul>{suppliers}</ul>
</body>
</html>
    """


@router.post("/report")
def generate_research_report_file(payload: Dict[str, Any] = Body(...)):
    symbol = payload.get("symbol")
    market = payload.get("market")
    report_format = payload.get("format", "pdf")
    html_filename = payload.get("html_filename")
    html_path_raw = payload.get("html_path")
    if not symbol:
        raise HTTPException(status_code=400, detail="Symbol is required")

    if market and market.lower() == "india" and ".NS" not in symbol.upper() and ".BO" not in symbol.upper():
        symbol = f"{symbol}.NS"

    safe_symbol = symbol.replace(".", "_")

    if report_format == "html":
        data = analyze_stock_sentiment(symbol)
        if data.get("error"):
            raise HTTPException(status_code=400, detail=data.get("error"))

        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        html_filename = f"research_{safe_symbol}_{timestamp}.html"
        html_path = REPORTS_DIR / html_filename

        html_content = _build_research_html(data)
        html_path.write_text(html_content, encoding="utf-8")

        return {
            "success": True,
            "filename": html_filename,
            "downloadUrl": f"/api/research/report/download/{html_filename}"
        }

    if report_format != "pdf":
        raise HTTPException(status_code=400, detail="Invalid format. Use 'html' or 'pdf'.")

    html_path = None
    if html_path_raw:
        try:
            candidate = Path(html_path_raw).resolve()
            reports_root = REPORTS_DIR.resolve()
            if reports_root in candidate.parents or candidate == reports_root:
                html_path = candidate
            else:
                raise HTTPException(status_code=400, detail="html_path must be inside reports directory.")
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Invalid html_path: {e}")

    if html_path is None and not html_filename:
        raise HTTPException(status_code=400, detail="html_filename is required for PDF conversion.")

    if html_path is None:
        html_path = REPORTS_DIR / html_filename
    if not html_path.exists():
        raise HTTPException(status_code=404, detail="HTML report not found. Generate HTML first.")

    pdf_filename = html_path.name.replace(".html", ".pdf")
    pdf_path = REPORTS_DIR / pdf_filename

    result = convert_html_to_pdf(str(html_path), str(pdf_path))
    if not result.get("success"):
        html_download = f"/api/research/report/download/{html_path.name}"
        return {
            "success": False,
            "filename": html_path.name,
            "downloadUrl": html_download,
            "warning": result.get("error", "PDF conversion failed. Downloading HTML instead.")
        }

    return {
        "success": True,
        "filename": pdf_filename,
        "downloadUrl": f"/api/research/report/download/{pdf_filename}"
    }


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
