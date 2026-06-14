"""
PDF Text Extractor Module
Extracts text content from uploaded PDF files using pdfplumber.
"""

import pdfplumber
import io


def extract_text(uploaded_file) -> str:
    """
    Extract all text from an uploaded PDF file.
    
    Args:
        uploaded_file: A file-like object (e.g., Streamlit UploadedFile)
    
    Returns:
        Concatenated text from all pages of the PDF.
    """
    text = ""
    with pdfplumber.open(uploaded_file) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text + "\n\n"
    return text.strip()
