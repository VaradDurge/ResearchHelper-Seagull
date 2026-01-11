"""
# Text Processing Utility

## What it does:
Utility functions for text cleaning, normalization, and processing. Used throughout
the application for text preprocessing.

## How it works:
- Provides text cleaning functions
- Handles normalization (unicode, whitespace, etc.)
- Provides text analysis utilities

## What to include:
- clean_text(text: str) -> str
  - Removes extra whitespace
  - Normalizes unicode
  - Removes special characters (optional)
  
- normalize_whitespace(text: str) -> str
  - Normalizes whitespace (multiple spaces to single)
  - Handles line breaks
  
- extract_sentences(text: str) -> List[str]
  - Splits text into sentences
  - Uses sentence tokenization
  
- extract_keywords(text: str, top_k: int) -> List[str]
  - Extracts keywords from text (optional)
  - Uses TF-IDF or similar
  
- remove_citations(text: str) -> str
  - Removes citation markers (optional, for some processing)
"""

