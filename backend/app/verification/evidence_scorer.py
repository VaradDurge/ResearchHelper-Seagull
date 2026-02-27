"""
Phase 2 — Evidence Scoring Formula.
Composite score: semantic_similarity + study_type + citation + recency + source_credibility.
"""
import math
from typing import Dict, Optional

from app.verification.constants import (
    CURRENT_YEAR,
    DEFAULT_STUDY_TYPE_WEIGHT,
    EVIDENCE_WEIGHTS,
    MAX_CITATION_FOR_NORM,
    RECENCY_HALF_LIFE_YEARS,
    STUDY_TYPE_WEIGHTS,
    HIGH_CREDIBILITY_JOURNALS,
    MEDIUM_CREDIBILITY_PUBLISHERS,
)
from app.verification.schemas import EvidenceMetadata, RetrievedEvidence


def _study_type_weight(study_type: Optional[str]) -> float:
    if not study_type:
        return DEFAULT_STUDY_TYPE_WEIGHT
    key = study_type.strip().lower().replace(" ", "_")
    return STUDY_TYPE_WEIGHTS.get(key, STUDY_TYPE_WEIGHTS.get(study_type.strip().lower(), DEFAULT_STUDY_TYPE_WEIGHT))


def _citation_score(citation_count: Optional[int], max_citation: float = MAX_CITATION_FOR_NORM) -> float:
    """Normalized: log(1 + citation_count) / log(1 + max_citation). Clamped to [0, 1]."""
    if citation_count is None or citation_count <= 0:
        return 0.0
    return min(1.0, math.log(1 + citation_count) / math.log(1 + max_citation))


def _recency_score(publication_year: Optional[int], current_year: int = CURRENT_YEAR) -> float:
    """
    Exponential decay: 0.5^((current_year - publication_year) / half_life).
    Older = lower score. Missing year = 0.5 (neutral).
    """
    if publication_year is None:
        return 0.5
    if publication_year > current_year:
        return 1.0
    years_ago = current_year - publication_year
    return math.pow(0.5, years_ago / RECENCY_HALF_LIFE_YEARS)


def _source_credibility(journal_name: Optional[str], publisher: Optional[str]) -> float:
    """
    Journal whitelist = 1.0, medium publishers = 0.7, unknown = 0.5.
    """
    if journal_name:
        j = journal_name.strip().lower()
        if j in HIGH_CREDIBILITY_JOURNALS:
            return 1.0
        # Partial match for "Nature X", "Lancet Y"
        for h in HIGH_CREDIBILITY_JOURNALS:
            if h in j or j in h:
                return 0.9
    if publisher:
        p = publisher.strip().lower()
        if p in MEDIUM_CREDIBILITY_PUBLISHERS:
            return 0.7
    return 0.5


def compute_evidence_score(
    chunk_metadata: EvidenceMetadata,
    similarity_score: float,
    *,
    max_citation: float = MAX_CITATION_FOR_NORM,
    current_year: int = CURRENT_YEAR,
    weights: Optional[Dict[str, float]] = None,
) -> tuple[float, Dict[str, float]]:
    """
    Compute composite evidence score for one chunk.

    EvidenceScore = w1 * semantic_similarity
                 + w2 * study_type_weight
                 + w3 * citation_score
                 + w4 * recency_score
                 + w5 * source_credibility

    Returns:
        (score, components_dict) with score in [0, 1] and component breakdown.
    """
    w = weights or EVIDENCE_WEIGHTS
    s_sem = similarity_score
    s_study = _study_type_weight(chunk_metadata.study_type)
    s_cite = _citation_score(chunk_metadata.citation_count, max_citation)
    s_rec = _recency_score(chunk_metadata.publication_year, current_year)
    s_src = _source_credibility(chunk_metadata.journal_name, chunk_metadata.publisher)

    score = (
        w["semantic_similarity"] * s_sem
        + w["study_type"] * s_study
        + w["citation"] * s_cite
        + w["recency"] * s_rec
        + w["source_credibility"] * s_src
    )
    components = {
        "semantic_similarity": s_sem,
        "study_type_weight": s_study,
        "citation_score": s_cite,
        "recency_score": s_rec,
        "source_credibility": s_src,
    }
    return score, components


class EvidenceScorer:
    """Applies compute_evidence_score to retrieved evidence."""

    def __init__(
        self,
        max_citation: float = MAX_CITATION_FOR_NORM,
        current_year: int = CURRENT_YEAR,
        weights: Optional[Dict[str, float]] = None,
    ):
        self.max_citation = max_citation
        self.current_year = current_year
        self.weights = weights or EVIDENCE_WEIGHTS

    def score(self, retrieved: RetrievedEvidence) -> tuple[float, Dict[str, float]]:
        return compute_evidence_score(
            retrieved.metadata,
            retrieved.similarity_score,
            max_citation=self.max_citation,
            current_year=self.current_year,
            weights=self.weights,
        )
