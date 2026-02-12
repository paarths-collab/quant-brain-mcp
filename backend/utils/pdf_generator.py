"""
PDF generator using WeasyPrint.
Converts HTML files to PDF without external binaries.
"""
import os

def convert_html_to_pdf(source_html_path: str, output_pdf_path: str) -> dict:
    """
    Converts an HTML file to PDF using WeasyPrint.

    Args:
        source_html_path: Absolute path to the source HTML file.
        output_pdf_path: Absolute path where the PDF should be saved.

    Returns:
        dict: {"success": bool, "error": str}
    """
    try:
        if not os.path.exists(source_html_path):
            return {"success": False, "error": f"Source file not found: {source_html_path}"}

        from weasyprint import HTML
        HTML(filename=source_html_path).write_pdf(output_pdf_path)

        if os.path.exists(output_pdf_path):
            return {"success": True, "path": output_pdf_path}
        else:
            return {"success": False, "error": "PDF file was not created."}

    except ImportError:
        return {
            "success": False,
            "error": "weasyprint is not installed. Run: pip install weasyprint"
        }
    except Exception as e:
        return {"success": False, "error": str(e)}
