"""
# Citation Service

## What it does:
Service layer for citation extraction and management. Handles extracting citations
from LLM responses, mapping citations to chunks and page numbers, and citation formatting.

## How it works:
- Extracts citations from text (e.g., [[PaperName|p12]])
- Maps citations to actual chunks and page numbers
- Validates citations
- Formats citations for display

## What to include:
- extract_citations(text: str, chunks: List[Chunk]) -> List[Citation]
  - Parses citation markers from text
  - Maps to chunks and page numbers
  - Returns citation objects
  
- format_citation(citation: Citation) -> str
  - Formats citation for display
  - Returns formatted string (e.g., "PaperName (p. 12)")
  
- validate_citation(citation: Citation, chunks: List[Chunk]) -> bool
  - Validates citation references valid chunk/page
  - Returns True if valid
  
- get_citation_chunk(citation: Citation, chunks: List[Chunk]) -> Chunk
  - Finds chunk referenced by citation
  - Returns chunk object
"""

