"""
# PDF Parser Utility

## What it does:
Extracts text and metadata from PDF files. Handles different PDF formats and
extracts page-wise text with page numbers.

## How it works:
- Uses PDF parsing library (PyPDF2, pdfplumber, or pymupdf)
- Extracts text page by page
- Extracts metadata (title, authors, etc.)
- Handles errors (corrupted PDFs, encrypted PDFs)

## What to include:
- parse_pdf(pdf_path: str) -> PDFData
  - Extracts text from PDF
  - Returns: pages (List[Page]), metadata (PDFMetadata)
  
- Page: page_number, text, images (optional)
- PDFMetadata: title, authors, abstract, publication_date, doi
  
- extract_metadata(pdf_path: str) -> PDFMetadata
  - Extracts metadata from PDF
  - Uses PDF metadata or first page parsing
  
- Handles different PDF libraries
- Error handling for corrupted/encrypted PDFs
- Text cleaning (remove extra whitespace, normalize)
"""

