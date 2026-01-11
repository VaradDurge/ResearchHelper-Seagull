"""
# Embeddings Module

## What it does:
Handles embedding generation for text chunks. Supports multiple embedding providers
(OpenAI, sentence-transformers, etc.). Converts text to vector embeddings for vector search.

## How it works:
- Provides embedding generation functions
- Supports multiple providers (configurable)
- Caches embeddings (optional)
- Handles batch embedding generation
- Returns normalized vectors

## What to include:
- generate_embedding(text: str) -> List[float]
  - Generates embedding for single text
  - Uses configured embedding model
  - Returns vector of specified dimensions
  
- generate_embeddings_batch(texts: List[str]) -> List[List[float]]
  - Generates embeddings for multiple texts
  - Handles batching for efficiency
  - Returns list of vectors
  
- get_embedding_dimensions() -> int
  - Returns embedding dimensions for current model
  
- Provider abstraction (OpenAI, sentence-transformers, etc.)
- Error handling for API failures
- Retry logic for transient errors
"""

