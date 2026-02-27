"""
Structured data types for the Evidence Confidence Scoring Engine.
JSON-serializable outputs only; no free-form prose.
"""
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class EvidenceLabel(str, Enum):
    SUPPORT = "SUPPORT"
    CONTRADICT = "CONTRADICT"
    NEUTRAL = "NEUTRAL"


class ConfidenceLabel(str, Enum):
    STRONG = "Strong"
    MODERATE = "Moderate"
    WEAK = "Weak"
    INCONCLUSIVE = "Inconclusive"
    CONTRADICTED = "Contradicted"
    INSUFFICIENT_EVIDENCE = "Insufficient Evidence"


@dataclass
class EvidenceMetadata:
    """Metadata for one retrieved chunk (from FAISS + optional enrichment)."""
    paper_id: str
    paper_title: str
    page_number: int
    chunk_index: int
    text: str
    # Optional enrichment fields (defaults when missing)
    publication_year: Optional[int] = None
    citation_count: Optional[int] = None
    journal_name: Optional[str] = None
    study_type: Optional[str] = None
    publisher: Optional[str] = None
    doi: Optional[str] = None
    vector_id: Optional[str] = None


@dataclass
class RetrievedEvidence:
    """One evidence item as returned by retrieval (with similarity)."""
    similarity_score: float
    distance: float
    metadata: EvidenceMetadata
    id: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "similarity_score": self.similarity_score,
            "distance": self.distance,
            "paper_id": self.metadata.paper_id,
            "paper_title": self.metadata.paper_title,
            "page_number": self.metadata.page_number,
            "chunk_index": self.metadata.chunk_index,
            "text": self.metadata.text,
            "publication_year": self.metadata.publication_year,
            "citation_count": self.metadata.citation_count,
            "journal_name": self.metadata.journal_name,
            "study_type": self.metadata.study_type,
            "publisher": self.metadata.publisher,
            "doi": self.metadata.doi,
        }


@dataclass
class ClassificationResult:
    """LLM classification for one chunk: SUPPORT / CONTRADICT / NEUTRAL."""
    classification: EvidenceLabel
    confidence: float
    reason: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "classification": self.classification.value,
            "confidence": round(self.confidence, 4),
            "reason": self.reason,
        }


@dataclass
class ScoredEvidence:
    """One evidence chunk with classification and composite evidence score."""
    retrieved: RetrievedEvidence
    classification: ClassificationResult
    evidence_score: float
    score_components: Optional[Dict[str, float]] = None

    def to_dict(self) -> Dict[str, Any]:
        d: Dict[str, Any] = {
            "evidence_score": round(self.evidence_score, 4),
            "classification": self.classification.to_dict(),
            "similarity_score": self.retrieved.similarity_score,
            "paper_id": self.retrieved.metadata.paper_id,
            "paper_title": self.retrieved.metadata.paper_title,
            "page_number": self.retrieved.metadata.page_number,
            "chunk_index": self.retrieved.metadata.chunk_index,
            "text": self.retrieved.metadata.text[:500] + "..." if len(self.retrieved.metadata.text) > 500 else self.retrieved.metadata.text,
        }
        if self.score_components:
            d["score_components"] = {k: round(v, 4) for k, v in self.score_components.items()}
        return d


@dataclass
class VerificationResult:
    """Final structured output of the Verification Engine."""
    claim: str
    support_count: int
    contradict_count: int
    neutral_count: int
    evidence_count: int
    confidence_score: float
    confidence_label: ConfidenceLabel
    evidence_strength: str
    strongest_study_types: List[str]
    guardrail_triggered: Optional[str] = None
    scored_evidence: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "claim": self.claim,
            "support_count": self.support_count,
            "contradict_count": self.contradict_count,
            "neutral_count": self.neutral_count,
            "evidence_count": self.evidence_count,
            "confidence_score": round(self.confidence_score, 4),
            "confidence_label": self.confidence_label.value,
            "evidence_strength": self.evidence_strength,
            "strongest_study_types": self.strongest_study_types,
            "guardrail_triggered": self.guardrail_triggered,
            "scored_evidence": self.scored_evidence,
        }


# ---------------------------------------------------------------------------
# Research Hallucination Firewall — structured output & gate schemas
# ---------------------------------------------------------------------------
class VerificationStatus(str, Enum):
    """Canonical verification status for structured firewall output."""
    VERIFIED = "VERIFIED"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"
    CONTRADICTED = "CONTRADICTED"


@dataclass
class GateResult:
    """Result of VerificationGate: ALLOW to proceed or BLOCKED with reason."""
    status: str  # "ALLOW" | "BLOCKED"
    reason: Optional[str] = None
    retrieved_count: int = 0
    avg_similarity: Optional[float] = None
    total_evidence_weight: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "status": self.status,
            "reason": self.reason,
            "retrieved_count": self.retrieved_count,
            "avg_similarity": round(self.avg_similarity, 4) if self.avg_similarity is not None else None,
            "total_evidence_weight": round(self.total_evidence_weight, 4) if self.total_evidence_weight is not None else None,
        }


@dataclass
class EvidenceSummaryItem:
    """One line in evidence_summary for structured output (no free text)."""
    paper_id: str
    label: str  # SUPPORT | CONTRADICT | NEUTRAL
    evidence_score: float
    doi: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "paper_id": self.paper_id,
            "label": self.label,
            "evidence_score": round(self.evidence_score, 4),
            "doi": self.doi,
        }


@dataclass
class SelfCheckResult:
    """Result of SelfCheckValidator second-pass LLM check."""
    self_check_passed: bool
    issues: List[str]

    def to_dict(self) -> Dict[str, Any]:
        return {"self_check_passed": self.self_check_passed, "issues": self.issues}
