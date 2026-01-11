"""
# Vector Database Module

## What it does:
Abstraction layer for vector database operations. Supports multiple vector DB providers
(Pinecone, Qdrant, Weaviate, etc.). Handles indexing, searching, and managing vectors.

## How it works:
- Provides abstract interface for vector DB operations
- Supports multiple providers (configurable via config)
- Handles connection management
- Provides search and indexing functions

## What to include:
- connect() - Connect to vector DB
- create_index(index_name: str, dimensions: int) - Create vector index
- upsert_vectors(index_name: str, vectors: List[Vector]) - Insert/update vectors
  - Vector: id, embedding, metadata (paper_id, chunk_id, text, page_number)
- search(index_name: str, query_vector: List[float], top_k: int) -> List[SearchResult]
  - Returns: id, score, metadata
- delete_vectors(index_name: str, vector_ids: List[str]) - Delete vectors
- get_vector(index_name: str, vector_id: str) -> Vector - Get single vector
- Provider implementations: PineconeClient, QdrantClient, etc.
- Error handling and connection retry logic
"""

