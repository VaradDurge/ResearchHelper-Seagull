"""
PDF Parser Utility
Extracts text and metadata from PDF files using PyPDF2.
"""
from typing import List, Optional, Dict, Any
from dataclasses import dataclass
from pathlib import Path
import PyPDF2
import logging

logger = logging.getLogger(__name__)


@dataclass
class Page:
    """Represents a single page from a PDF"""
    page_number: int
    text: str


@dataclass
class PDFMetadata:
    """PDF metadata"""
    title: Optional[str] = None
    authors: Optional[List[str]] = None
    abstract: Optional[str] = None
    publication_date: Optional[str] = None
    doi: Optional[str] = None


@dataclass
class PDFData:
    """Complete PDF data structure"""
    pages: List[Page]
    metadata: PDFMetadata


def parse_pdf(pdf_path: str) -> PDFData:
    """
    Extract text from PDF file page by page.
    
    Args:
        pdf_path: Path to the PDF file
        
    Returns:
        PDFData containing pages and metadata
        
    Raises:
        Exception: If PDF cannot be read or is corrupted
    """
    pages = []
    metadata = PDFMetadata()
    
    try:
        with open(pdf_path, 'rb') as file:
            pdf_reader = PyPDF2.PdfReader(file)
            
            # Extract metadata from PDF
            pdf_info = pdf_reader.metadata
            if pdf_info:
                if pdf_info.title:
                    metadata.title = pdf_info.title
                if pdf_info.author:
                    # Author can be a string or list
                    if isinstance(pdf_info.author, str):
                        metadata.authors = [pdf_info.author]
                    elif isinstance(pdf_info.author, list):
                        metadata.authors = pdf_info.author
                if pdf_info.subject:
                    # Sometimes abstract is in subject
                    metadata.abstract = pdf_info.subject
            
            # Extract text from each page
            for page_num, page in enumerate(pdf_reader.pages, start=1):
                try:
                    text = page.extract_text()
                    # Clean up text - remove excessive whitespace
                    text = ' '.join(text.split())
                    pages.append(Page(page_number=page_num, text=text))
                except Exception as e:
                    logger.warning(f"Error extracting text from page {page_num}: {str(e)}")
                    # Add empty page if extraction fails
                    pages.append(Page(page_number=page_num, text=""))
            
            # If no title in metadata, try to extract from first page
            if not metadata.title and pages:
                first_page_text = pages[0].text
                # Try to find title in first few lines
                lines = first_page_text.split('\n')[:5]
                if lines:
                    metadata.title = lines[0].strip()[:200]  # Limit title length
                    
    except PyPDF2.errors.PdfReadError as e:
        raise Exception(f"Error reading PDF file: {str(e)}")
    except Exception as e:
        raise Exception(f"Error parsing PDF: {str(e)}")
    
    return PDFData(pages=pages, metadata=metadata)


def get_abstract_and_conclusion_text(pdf_data: PDFData, conclusion_pages: int = 3) -> str:
    """
    Concatenate abstract (from metadata) and conclusion (last N pages) for intelligence extraction.
    """
    parts = []
    if pdf_data.metadata.abstract and pdf_data.metadata.abstract.strip():
        parts.append(pdf_data.metadata.abstract.strip())
    if pdf_data.pages:
        last_pages = pdf_data.pages[-conclusion_pages:] if len(pdf_data.pages) >= conclusion_pages else pdf_data.pages
        conclusion_text = " ".join(p.text for p in last_pages if p.text.strip())
        if conclusion_text:
            parts.append(conclusion_text)
    return "\n\n".join(parts) if parts else ""


def get_full_pdf_text_first_chars(pdf_data: PDFData, max_chars: int = 2000) -> str:
    """
    Get the first max_chars of full PDF text (all pages concatenated). Used as fallback when abstract+conclusion is too short.
    """
    if not pdf_data.pages:
        return ""
    full = " ".join(p.text for p in pdf_data.pages if p.text.strip())
    return full[:max_chars] if full else ""


def extract_metadata(pdf_path: str) -> PDFMetadata:
    """
    Extract only metadata from PDF file.
    
    Args:
        pdf_path: Path to the PDF file
        
    Returns:
        PDFMetadata object
    """
    pdf_data = parse_pdf(pdf_path)
    return pdf_data.metadata
