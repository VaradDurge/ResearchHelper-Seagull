"""
# RAG (Retrieval-Augmented Generation) Module

## What it does:
Implements the RAG pipeline: retrieves relevant chunks from vector DB, builds prompt with
context and citations, generates answer using LLM. Core component used by chat and tools.

## How it works:
- Retrieves relevant chunks using vector search
- Reranks results (optional)
- Builds prompt with retrieved context and citations
- Calls LLM to generate answer
- Extracts citations from response
- Returns answer with citations and retrieved chunks

## What to include:
- retrieve(query: str, paper_ids: List[str], top_k: int) -> List[Chunk]
  - Searches vector DB for relevant chunks
  - Filters by paper_ids
  - Returns top_k most relevant chunks
  
- generate_answer(query: str, chunks: List[Chunk], **kwargs) -> RAGResponse
  - Builds prompt with query and chunks
  - Calls LLM to generate answer
  - Extracts citations from response
  - Returns: answer, citations, retrieved_chunks
  
- build_prompt(query: str, chunks: List[Chunk]) -> str
  - Constructs prompt with system instructions, context, and query
  - Includes citation markers [[PaperName|p12]]
  
- extract_citations(response: str, chunks: List[Chunk]) -> List[Citation]
  - Parses citations from LLM response
  - Maps citations to chunks and page numbers
  
- Reranking (optional, using cross-encoder)
"""

