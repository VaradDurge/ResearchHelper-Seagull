"""
Phase 1 — Evidence Retrieval Upgrade.
Retrieves chunks with semantic similarity score and enriched metadata.
Similarity score is stored alongside metadata and passed downstream for scoring.
"""
import logging
from typing import List, Optional

from app.config import settings
from app.core.embeddings import generate_embedding
from app.core.vector_db import get_vector_db
from app.verification.schemas import EvidenceMetadata, RetrievedEvidence

logger = logging.getLogger(__name__)


def _metadata_from_chunk(chunk: dict) -> EvidenceMetadata:
    """Build EvidenceMetadata from FAISS search result chunk."""
    meta = chunk.get("metadata") or {}
    # Optional enrichment fields (may be absent until enrichment pipeline runs)
    pub_date = meta.get("publication_date")
    year = None
    if isinstance(pub_date, str) and len(pub_date) >= 4:
        try:
            year = int(pub_date[:4])
        except ValueError:
            pass
    elif isinstance(pub_date, int):
        year = pub_date
    if year is None:
        year = meta.get("publication_year")

    return EvidenceMetadata(
        paper_id=meta.get("paper_id", "unknown"),
        paper_title=meta.get("paper_title", "Unknown"),
        page_number=int(meta.get("page_number") or 0),
        chunk_index=int(meta.get("chunk_index") or 0),
        text=meta.get("text", ""),
        publication_year=year,
        citation_count=meta.get("citation_count"),
        journal_name=meta.get("journal_name"),
        study_type=meta.get("study_type"),
        publisher=meta.get("publisher"),
        doi=meta.get("doi"),
        vector_id=meta.get("vector_id") or meta.get("faiss_id"),
    )


class EvidenceRetriever:
    """
    Retrieves evidence chunks for a claim with similarity scores and metadata.
    Output is suitable for downstream scoring and classification.
    """

    def __init__(
        self,
        top_k: int = 10,
        workspace_id: Optional[str] = None,
        user_id: Optional[str] = None,
    ):
        self.top_k = top_k
        self.workspace_id = workspace_id
        self.user_id = user_id

    def retrieve(
        self,
        claim: str,
        paper_ids: Optional[List[str]] = None,
    ) -> List[RetrievedEvidence]:
        """
        Retrieve top-k chunks for the claim. Each result includes:
        - semantic similarity score (from FAISS, already computed as 1/(1+distance))
        - distance (L2)
        - full metadata (with optional publication_year, citation_count, journal_name, study_type, publisher, DOI)
        """
        vector_db = get_vector_db(
            index_path=settings.vector_db_path,
            dimension=settings.embedding_dimension,
        )
        query_vector = generate_embedding(claim)
        raw = vector_db.search(
            query_vector,
            top_k=self.top_k,
            paper_ids=paper_ids,
            workspace_id=self.workspace_id,
            user_id=self.user_id,
        )
        results: List[RetrievedEvidence] = []
        for hit in raw:
            similarity = hit.get("score", 0.0)
            distance = hit.get("distance", 0.0)
            metadata = _metadata_from_chunk(hit)
            eid = hit.get("id") or metadata.vector_id or f"{metadata.paper_id}_{metadata.page_number}_{metadata.chunk_index}"
            results.append(
                RetrievedEvidence(
                    similarity_score=similarity,
                    distance=distance,
                    metadata=metadata,
                    id=eid,
                )
            )
        return results
