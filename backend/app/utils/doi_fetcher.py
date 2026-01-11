"""
# DOI Fetcher Utility

## What it does:
Fetches paper metadata and PDF from DOI. Uses DOI resolution APIs to get paper information
and download PDF.

## How it works:
- Resolves DOI to get paper information
- Fetches metadata from DOI API (Crossref, DataCite, etc.)
- Downloads PDF from available sources
- Returns paper metadata and PDF file

## What to include:
- fetch_from_doi(doi: str) -> DOIData
  - Resolves DOI
  - Fetches metadata (title, authors, abstract, etc.)
  - Downloads PDF (from publisher, arXiv, etc.)
  - Returns: metadata, pdf_file (bytes or file path)
  
- resolve_doi(doi: str) -> Dict
  - Calls DOI resolution API (Crossref, etc.)
  - Returns paper metadata
  
- download_pdf(doi: str, metadata: Dict) -> bytes
  - Finds PDF URL from metadata
  - Downloads PDF
  - Returns PDF file bytes
  
- Handles different DOI providers
- Error handling (DOI not found, PDF not available)
- Rate limiting for API calls
"""

