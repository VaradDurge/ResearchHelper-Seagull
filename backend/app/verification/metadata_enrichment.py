"""
Phase 1 — Metadata enrichment pipeline design.
Store similarity score alongside metadata; pass downstream for scoring.
Optional: extract and store publication_year, citation_count, journal_name, study_type, publisher, DOI.
"""
import logging
from typing import Any, Dict, List, Optional

from app.config import settings
from app.core.vector_db import get_vector_db
from app.db.mongo import get_papers_collection

logger = logging.getLogger(__name__)

# Keys we attach to chunk metadata for evidence scoring
EVIDENCE_METADATA_KEYS = [
    "publication_year",
    "citation_count",
    "journal_name",
    "study_type",
    "publisher",
    "doi",
    "publication_date",
]


def _year_from_date(value: Any) -> Optional[int]:
    if value is None:
        return None
    if isinstance(value, int):
        return value if 1900 <= value <= 2100 else None
    s = str(value).strip()
    if len(s) >= 4:
        try:
            return int(s[:4])
        except ValueError:
            pass
    return None


def get_paper_level_metadata(paper_id: str) -> Dict[str, Any]:
    """
    Load paper-level metadata from MongoDB for enrichment.
    Returns dict with publication_year, doi, and optionally citation_count, journal_name, study_type, publisher
    when stored on the paper document.
    """
    papers = get_papers_collection()
    doc = papers.find_one({"paper_id": paper_id})
    if not doc:
        return {}
    out: Dict[str, Any] = {}
    if doc.get("doi"):
        out["doi"] = doc["doi"]
    pub_date = doc.get("publication_date")
    if pub_date is not None:
        year = _year_from_date(pub_date)
        if year is not None:
            out["publication_year"] = year
        out["publication_date"] = pub_date
    # Optional: when you add these to the paper schema or a separate enrichment collection
    for key in ("citation_count", "journal_name", "study_type", "publisher"):
        if doc.get(key) is not None:
            out[key] = doc[key]
    metadata = doc.get("metadata") or {}
    for key in ("citation_count", "journal_name", "study_type", "publisher"):
        if key in metadata and out.get(key) is None:
            out[key] = metadata[key]
    return out


def enrich_chunk_metadata_from_paper(paper_id: str, chunk_metadata: Dict[str, Any]) -> Dict[str, Any]:
    """Merge paper-level metadata into chunk metadata. Does not overwrite existing chunk values."""
    paper_meta = get_paper_level_metadata(paper_id)
    merged = dict(chunk_metadata)
    for key, value in paper_meta.items():
        if value is not None and merged.get(key) is None:
            merged[key] = value
    return merged


def update_vector_db_metadata_for_paper(paper_id: str) -> int:
    """
    Update all FAISS chunk metadata for a paper with paper-level metadata from MongoDB.
    Call after DOI import or when paper metadata is updated.
    Returns number of chunk metadata entries updated.
    """
    vector_db = get_vector_db(
        index_path=settings.vector_db_path,
        dimension=settings.embedding_dimension,
    )
    paper_meta = get_paper_level_metadata(paper_id)
    if not paper_meta:
        return 0
    updated = 0
    for faiss_id, meta in list(vector_db.metadata.items()):
        if meta.get("paper_id") != paper_id:
            continue
        for key, value in paper_meta.items():
            if value is not None and meta.get(key) is None:
                vector_db.metadata[faiss_id][key] = value
                updated += 1
    if updated:
        vector_db.save_index()
    return updated


def enrich_metadata_at_ingestion(
    chunk_metadata: Dict[str, Any],
    paper_metadata: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    At ingestion time, merge optional paper_metadata into each chunk's metadata.
    If paper_metadata is None, ingestion can later call update_vector_db_metadata_for_paper(paper_id)
    when DOI/metadata is available.
    """
    if not paper_metadata:
        return chunk_metadata
    merged = dict(chunk_metadata)
    year = _year_from_date(paper_metadata.get("publication_date"))
    if year is not None:
        merged["publication_year"] = year
    for key in ("doi", "citation_count", "journal_name", "study_type", "publisher"):
        if paper_metadata.get(key) is not None:
            merged[key] = paper_metadata[key]
    return merged
