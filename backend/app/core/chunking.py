"""
# Chunking Module

## What it does:
Handles text chunking strategies for splitting papers into smaller chunks for embedding
and retrieval. Supports multiple chunking strategies.

## How it works:
- Provides chunking functions for different strategies
- Splits text into overlapping chunks
- Preserves page numbers and metadata
- Handles different chunk sizes and overlap

## What to include:
- chunk_text(text: str, page_number: int, chunk_size: int, overlap: int) -> List[Chunk]
  - Splits text into chunks
  - Preserves page number in metadata
  - Returns chunks with: text, chunk_index, page_number, start_char, end_char
  
- chunk_by_sentences(text: str, page_number: int, max_chunk_size: int) -> List[Chunk]
  - Chunks by sentences (respects sentence boundaries)
  
- chunk_by_paragraphs(text: str, page_number: int) -> List[Chunk]
  - Chunks by paragraphs
  
- chunk_with_sliding_window(text: str, page_number: int, window_size: int, stride: int) -> List[Chunk]
  - Sliding window chunking with overlap
  
- Chunk metadata: paper_id, page_number, chunk_index, text, char_range
"""

