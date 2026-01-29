"""
Vector Database Module
FAISS-based vector database for storing and searching embeddings.
"""
from typing import List, Optional, Dict, Any
import faiss
import numpy as np
import pickle
import os
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


class FAISSVectorDB:
    """FAISS-based vector database implementation"""
    
    def __init__(self, index_path: Optional[str] = None, dimension: int = 384):
        """
        Initialize FAISS vector database.
        
        Args:
            index_path: Optional path to save/load index from disk
            dimension: Dimension of embeddings (default 384 for all-MiniLM-L6-v2)
        """
        self.index_path = index_path
        self.dimension = dimension
        self.index: Optional[faiss.Index] = None
        self.metadata: Dict[str, Dict[str, Any]] = {}  # vector_id -> metadata mapping
        
        # Initialize index
        self._initialize_index()
        
        # Load existing index if path provided
        if index_path and os.path.exists(index_path):
            self.load_index()
    
    def _initialize_index(self):
        """Initialize a new FAISS index"""
        # Use L2 (Euclidean) distance index
        # For normalized embeddings, L2 is equivalent to cosine distance
        self.index = faiss.IndexFlatL2(self.dimension)
        logger.info(f"Initialized FAISS index with dimension {self.dimension}")
    
    def upsert_vectors(
        self,
        vectors: List[List[float]],
        vector_ids: List[str],
        metadata_list: List[Dict[str, Any]]
    ):
        """
        Insert or update vectors in the index.
        
        Args:
            vectors: List of embedding vectors
            vector_ids: List of unique IDs for each vector
            metadata_list: List of metadata dictionaries for each vector
        """
        if not vectors:
            return
        
        if len(vectors) != len(vector_ids) or len(vectors) != len(metadata_list):
            raise ValueError("vectors, vector_ids, and metadata_list must have the same length")
        
        # Convert to numpy array
        vectors_array = np.array(vectors, dtype=np.float32)
        
        # Check if index needs to be created
        if self.index is None:
            self._initialize_index()
        
        # Add vectors to index
        self.index.add(vectors_array)
        
        # Store metadata
        start_id = len(self.metadata)
        for i, (vector_id, metadata) in enumerate(zip(vector_ids, metadata_list)):
            # FAISS assigns sequential IDs, so we map them to our vector_ids
            faiss_id = str(start_id + i)
            self.metadata[faiss_id] = {
                **metadata,
                "vector_id": vector_id,
                "faiss_id": faiss_id
            }
        
        logger.info(f"Upserted {len(vectors)} vectors to FAISS index")
    
    def search(
        self,
        query_vector: List[float],
        top_k: int = 10,
        paper_ids: Optional[List[str]] = None,
        user_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Search for similar vectors.
        
        Args:
            query_vector: Query embedding vector
            top_k: Number of results to return
            paper_ids: Optional list of paper IDs to filter by
            
        Returns:
            List of search results with id, score, and metadata
        """
        if self.index is None or self.index.ntotal == 0:
            return []
        
        # Convert query to numpy array
        query_array = np.array([query_vector], dtype=np.float32)
        
        # Search
        k = min(top_k, self.index.ntotal)
        distances, indices = self.index.search(query_array, k)
        
        results = []
        for i, (distance, idx) in enumerate(zip(distances[0], indices[0])):
            if idx == -1:  # FAISS returns -1 for invalid indices
                continue
            
            faiss_id = str(idx)
            if faiss_id not in self.metadata:
                continue
            
            metadata = self.metadata[faiss_id].copy()
            
            # Filter by paper_ids if provided
            if paper_ids and metadata.get("paper_id") not in paper_ids:
                continue
            # Filter by user_id if provided
            if user_id and metadata.get("user_id") != user_id:
                continue
            
            # Convert distance to similarity score (lower distance = higher similarity)
            # For normalized vectors with L2, we can use 1 / (1 + distance) as similarity
            similarity = 1.0 / (1.0 + float(distance))
            
            results.append({
                "id": metadata.get("vector_id", faiss_id),
                "score": similarity,
                "distance": float(distance),
                "metadata": metadata
            })
        
        # Sort by score (descending)
        results.sort(key=lambda x: x["score"], reverse=True)
        return results[:top_k]
    
    def delete_vectors(self, vector_ids: List[str]):
        """
        Delete vectors from the index.
        Note: FAISS doesn't support efficient deletion, so we rebuild the index.
        
        Args:
            vector_ids: List of vector IDs to delete
        """
        if not vector_ids or self.index is None:
            return
        
        # Remove from metadata
        faiss_ids_to_remove = []
        for faiss_id, metadata in self.metadata.items():
            if metadata.get("vector_id") in vector_ids:
                faiss_ids_to_remove.append(faiss_id)
        
        for faiss_id in faiss_ids_to_remove:
            del self.metadata[faiss_id]
        
        # Rebuild index without deleted vectors
        if self.metadata:
            # Get all remaining vectors and rebuild
            remaining_vectors = []
            remaining_metadata = []
            
            # We need to store vectors separately to rebuild
            # For now, we'll mark as deleted but keep in index
            # (FAISS limitation - proper deletion requires rebuilding)
            logger.warning("FAISS deletion is limited - vectors marked as deleted in metadata")
        else:
            # If all deleted, reinitialize
            self._initialize_index()

    def delete_by_paper_id(self, paper_id: str):
        """Delete all vectors for a specific paper."""
        if self.index is None:
            return
        faiss_ids_to_remove = [
            fid for fid, meta in self.metadata.items() if meta.get("paper_id") == paper_id
        ]
        for fid in faiss_ids_to_remove:
            del self.metadata[fid]
        logger.info(f"Deleted {len(faiss_ids_to_remove)} vectors for paper {paper_id}")

    def save_index(self):
        """Save the index and metadata to disk"""
        if not self.index_path:
            return
        
        try:
            # Create directory if it doesn't exist
            os.makedirs(os.path.dirname(self.index_path) if os.path.dirname(self.index_path) else ".", exist_ok=True)
            
            # Save FAISS index
            faiss.write_index(self.index, self.index_path)
            
            # Save metadata
            metadata_path = self.index_path + ".metadata"
            with open(metadata_path, "wb") as f:
                pickle.dump(self.metadata, f)
            
            logger.info(f"Saved FAISS index to {self.index_path}")
        except Exception as e:
            logger.error(f"Error saving FAISS index: {str(e)}")
    
    def load_index(self):
        """Load the index and metadata from disk"""
        if not self.index_path or not os.path.exists(self.index_path):
            return
        
        try:
            # Load FAISS index
            self.index = faiss.read_index(self.index_path)
            
            # Load metadata
            metadata_path = self.index_path + ".metadata"
            if os.path.exists(metadata_path):
                with open(metadata_path, "rb") as f:
                    self.metadata = pickle.load(f)
            
            logger.info(f"Loaded FAISS index from {self.index_path}")
        except Exception as e:
            logger.error(f"Error loading FAISS index: {str(e)}")
            self._initialize_index()


# Global instance
_vector_db: Optional[FAISSVectorDB] = None


def get_vector_db(index_path: Optional[str] = None, dimension: int = 384) -> FAISSVectorDB:
    """
    Get or create the global vector database instance.
    
    Args:
        index_path: Optional path to save/load index
        dimension: Embedding dimension
        
    Returns:
        FAISSVectorDB instance
    """
    global _vector_db
    if _vector_db is None:
        _vector_db = FAISSVectorDB(index_path=index_path, dimension=dimension)
    return _vector_db


def connect(index_path: Optional[str] = None, dimension: int = 384):
    """Connect to vector database (alias for get_vector_db)"""
    return get_vector_db(index_path=index_path, dimension=dimension)
