from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from pathlib import Path
import os

def convert_html_to_pdf(html_path: str, pdf_path: str) -> dict:
    try:
        import pdfkit
        pdfkit.from_file(html_path, pdf_path)
        return {"success": True, "error": None}
    except Exception as e:
         return {"success": False, "error": str(e)}

router = APIRouter(prefix="/api/reports", tags=["Reports"])

REPORTS_DIR = Path(__file__).parent.parent / "reports"
PORTFOLIO_REPORT_HTML = REPORTS_DIR / "portfolio_report.html"
PORTFOLIO_REPORT_PDF = REPORTS_DIR / "portfolio_report.pdf"

@router.get("/download/portfolio/pdf")
def download_portfolio_pdf():
    """
    Converts the latest portfolio_report.html to PDF and downloads it.
    """
    if not PORTFOLIO_REPORT_HTML.exists():
        raise HTTPException(status_code=404, detail="Portfolio report not found. Please run the analysis first.")
    
    # Convert to PDF
    result = convert_html_to_pdf(str(PORTFOLIO_REPORT_HTML), str(PORTFOLIO_REPORT_PDF))
    
    if not result.get("success"):
        raise HTTPException(status_code=500, detail=f"PDF Conversion Failed: {result.get('error')}")
        
    return FileResponse(
        path=str(PORTFOLIO_REPORT_PDF), 
        filename="portfolio_report.pdf", 
        media_type="application/pdf"
    )

@router.get("/view/portfolio")
def view_portfolio_html():
    """
    Serves the raw HTML report.
    """
    if not PORTFOLIO_REPORT_HTML.exists():
         raise HTTPException(status_code=404, detail="Portfolio report not found.")
    return FileResponse(str(PORTFOLIO_REPORT_HTML))
