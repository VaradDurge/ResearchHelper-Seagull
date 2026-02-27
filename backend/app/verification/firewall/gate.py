"""
Part 1 & 2 — No Generation Without Retrieval + Minimum Evidence Threshold.
VerificationGate: blocks generation when retrieval is insufficient or low quality.
"""
import logging
from typing import List, Optional

from app.verification.constants import (
    MIN_EVIDENCE_COUNT,
    MIN_AVG_SIMILARITY,
    MIN_TOTAL_EVIDENCE_WEIGHT,
)
from app.verification.schemas import GateResult, RetrievedEvidence, ScoredEvidence

logger = logging.getLogger(__name__)

STATUS_ALLOW = "ALLOW"
STATUS_BLOCKED = "BLOCKED"

REASON_ZERO_RESULTS = "No evidence retrieved"
REASON_INSUFFICIENT_COUNT = "Insufficient evidence"
REASON_LOW_SIMILARITY = "Similarity scores below threshold"
REASON_LOW_EVIDENCE_WEIGHT = "Total evidence weight below threshold"


class VerificationGate:
    """
    Wrapper to block generation when:
    - Retrieval returns 0 results
    - retrieved_count < minimum threshold (e.g. 3)
    - Average similarity score < MIN_AVG_SIMILARITY
    - Total evidence weight < MIN_TOTAL_EVIDENCE_WEIGHT (when scored evidence available)

    Returns structured GateResult: ALLOW or BLOCKED with reason and retrieved_count.
    """

    def __init__(
        self,
        min_evidence_count: int = MIN_EVIDENCE_COUNT,
        min_avg_similarity: float = MIN_AVG_SIMILARITY,
        min_total_evidence_weight: float = MIN_TOTAL_EVIDENCE_WEIGHT,
    ):
        self.min_evidence_count = min_evidence_count
        self.min_avg_similarity = min_avg_similarity
        self.min_total_evidence_weight = min_total_evidence_weight

    def check_retrieval(
        self,
        retrieved_list: List[RetrievedEvidence],
    ) -> GateResult:
        """
        Validate retrieval before any scoring/classification.
        Use after EvidenceRetriever.retrieve(); if BLOCKED, do not run scorer/classifier/aggregator.
        """
        count = len(retrieved_list)
        if count == 0:
            logger.info("VerificationGate: BLOCKED — zero results")
            return GateResult(
                status=STATUS_BLOCKED,
                reason=REASON_ZERO_RESULTS,
                retrieved_count=0,
                avg_similarity=None,
                total_evidence_weight=None,
            )
        if count < self.min_evidence_count:
            avg_sim = sum(r.similarity_score for r in retrieved_list) / count
            logger.info(
                "VerificationGate: BLOCKED — insufficient evidence count=%s (min=%s)",
                count, self.min_evidence_count,
            )
            return GateResult(
                status=STATUS_BLOCKED,
                reason=REASON_INSUFFICIENT_COUNT,
                retrieved_count=count,
                avg_similarity=round(avg_sim, 4),
                total_evidence_weight=None,
            )
        avg_similarity = sum(r.similarity_score for r in retrieved_list) / count
        if avg_similarity < self.min_avg_similarity:
            logger.info(
                "VerificationGate: BLOCKED — avg similarity %.4f < %.4f",
                avg_similarity, self.min_avg_similarity,
            )
            return GateResult(
                status=STATUS_BLOCKED,
                reason=REASON_LOW_SIMILARITY,
                retrieved_count=count,
                avg_similarity=round(avg_similarity, 4),
                total_evidence_weight=None,
            )
        return GateResult(
            status=STATUS_ALLOW,
            reason=None,
            retrieved_count=count,
            avg_similarity=round(avg_similarity, 4),
            total_evidence_weight=None,
        )

    def check_after_scoring(
        self,
        scored_evidence: List[ScoredEvidence],
    ) -> GateResult:
        """
        Optional: validate after scoring (before confidence aggregation).
        Rejects low-quality retrieval when total evidence weight is below threshold.
        """
        count = len(scored_evidence)
        if count == 0:
            return GateResult(
                status=STATUS_BLOCKED,
                reason=REASON_ZERO_RESULTS,
                retrieved_count=0,
                avg_similarity=None,
                total_evidence_weight=0.0,
            )
        if count < self.min_evidence_count:
            total_weight = sum(s.evidence_score for s in scored_evidence)
            avg_sim = sum(s.retrieved.similarity_score for s in scored_evidence) / count
            return GateResult(
                status=STATUS_BLOCKED,
                reason=REASON_INSUFFICIENT_COUNT,
                retrieved_count=count,
                avg_similarity=round(avg_sim, 4),
                total_evidence_weight=round(total_weight, 4),
            )
        total_weight = sum(s.evidence_score for s in scored_evidence)
        if total_weight < self.min_total_evidence_weight:
            avg_sim = sum(s.retrieved.similarity_score for s in scored_evidence) / count
            logger.info(
                "VerificationGate: BLOCKED — total evidence weight %.4f < %.4f",
                total_weight, self.min_total_evidence_weight,
            )
            return GateResult(
                status=STATUS_BLOCKED,
                reason=REASON_LOW_EVIDENCE_WEIGHT,
                retrieved_count=count,
                avg_similarity=round(avg_sim, 4),
                total_evidence_weight=round(total_weight, 4),
            )
        avg_sim = sum(s.retrieved.similarity_score for s in scored_evidence) / count
        if avg_sim < self.min_avg_similarity:
            return GateResult(
                status=STATUS_BLOCKED,
                reason=REASON_LOW_SIMILARITY,
                retrieved_count=count,
                avg_similarity=round(avg_sim, 4),
                total_evidence_weight=round(total_weight, 4),
            )
        return GateResult(
            status=STATUS_ALLOW,
            reason=None,
            retrieved_count=count,
            avg_similarity=round(avg_sim, 4),
            total_evidence_weight=round(total_weight, 4),
        )

    def blocked_response_json(self, gate_result: GateResult) -> dict:
        """Structured JSON for API when generation is blocked (Part 1)."""
        return {
            "status": STATUS_BLOCKED,
            "reason": gate_result.reason or "Insufficient evidence",
            "retrieved_count": gate_result.retrieved_count,
            "avg_similarity": gate_result.avg_similarity,
            "total_evidence_weight": gate_result.total_evidence_weight,
        }
