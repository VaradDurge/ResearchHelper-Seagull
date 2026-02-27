"""
Evidence Confidence Scoring Engine — claim-level verification.
Structured scientific verification: retrieve → classify → score → aggregate.
"""
from app.verification.engine import VerificationEngine
from app.verification.schemas import (
    ConfidenceLabel,
    EvidenceLabel,
    VerificationResult,
)
from app.verification.evidence_scorer import compute_evidence_score

__all__ = [
    "VerificationEngine",
    "VerificationResult",
    "ConfidenceLabel",
    "EvidenceLabel",
    "compute_evidence_score",
]
