from xhtml2pdf import pisa
import os

def convert_html_to_pdf(source_html_path: str, output_pdf_path: str) -> dict:
    """
    Converts an HTML file to PDF using xhtml2pdf.
    This is a pure Python library and does not require external binaries.
    
    Args:
        source_html_path (str): Absolute path to the source HTML file.
        output_pdf_path (str): Absolute path where the PDF should be saved.
        
    Returns:
        dict: {"success": bool, "error": str}
    """
    try:
        if not os.path.exists(source_html_path):
            return {"success": False, "error": f"Source file not found: {source_html_path}"}

        # Open input and output files
        with open(source_html_path, "r", encoding="utf-8") as source_file:
            source_html = source_file.read()
            
        with open(output_pdf_path, "wb") as output_file:
            # Convert HTML to PDF
            pisa_status = pisa.CreatePDF(
                source_html,                # the HTML to convert
                dest=output_file            # file handle to recieve result
            )

        if pisa_status.err:
            return {"success": False, "error": "xhtml2pdf conversion error."}
            
        if os.path.exists(output_pdf_path):
            return {"success": True, "path": output_pdf_path}
        else:
             return {"success": False, "error": "PDF file was not created."}

    except Exception as e:
        return {"success": False, "error": str(e)}
