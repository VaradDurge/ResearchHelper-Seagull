"""
Phase 5 & 6 — Guardrails and Verification Engine.
Orchestrates EvidenceRetriever → EvidenceScorer + ClaimClassifier → ConfidenceAggregator.
Enforces: min evidence count, contradicted label, no answer without evidence, no summarization.
"""
import logging
from typing import List, Optional

from app.verification.constants import MIN_EVIDENCE_COUNT
from app.verification.schemas import (
    ClassificationResult,
    ConfidenceLabel,
    EvidenceLabel,
    ScoredEvidence,
    VerificationResult,
)
from app.verification.evidence_retriever import EvidenceRetriever
from app.verification.evidence_scorer import EvidenceScorer
from app.verification.claim_classifier import ClaimClassifier
from app.verification.confidence_aggregator import aggregate

logger = logging.getLogger(__name__)


class VerificationEngine:
    """
    End-to-end Evidence Confidence Scoring Engine for a single atomic claim.
    Output is structured JSON only; no summarization.
    """

    def __init__(
        self,
        top_k: int = 10,
        workspace_id: Optional[str] = None,
        user_id: Optional[str] = None,
        min_evidence_count: int = MIN_EVIDENCE_COUNT,
    ):
        self.retriever = EvidenceRetriever(top_k=top_k, workspace_id=workspace_id, user_id=user_id)
        self.scorer = EvidenceScorer()
        self.classifier = ClaimClassifier()
        self.min_evidence_count = min_evidence_count

    def verify(
        self,
        claim: str,
        paper_ids: Optional[List[str]] = None,
        include_scored_evidence: bool = True,
    ) -> VerificationResult:
        """
        Given one atomic claim:
        1) Retrieve relevant evidence (with similarity + metadata)
        2) Classify each chunk (SUPPORT / CONTRADICT / NEUTRAL)
        3) Score each piece of evidence
        4) Aggregate into final confidence
        5) Apply guardrails
        6) Return structured JSON (no paragraphs).
        """
        retrieved_list = self.retriever.retrieve(claim, paper_ids=paper_ids)

        # Guardrail: never generate answer without evidence
        if not retrieved_list:
            return VerificationResult(
                claim=claim,
                support_count=0,
                contradict_count=0,
                neutral_count=0,
                evidence_count=0,
                confidence_score=0.0,
                confidence_label=ConfidenceLabel.INSUFFICIENT_EVIDENCE,
                evidence_strength="No evidence retrieved.",
                strongest_study_types=[],
                guardrail_triggered="No evidence retrieved. Cannot verify without evidence.",
                scored_evidence=[],
            )

        # Score + classify each chunk
        scored_evidence: List[ScoredEvidence] = []
        for r in retrieved_list:
            score_val, components = self.scorer.score(r)
            clf = self.classifier.classify(claim, r)
            if not clf:
                clf = ClassificationResult(EvidenceLabel.NEUTRAL, 0.5, "Classification unavailable.")
            scored_evidence.append(
                ScoredEvidence(retrieved=r, classification=clf, evidence_score=score_val, score_components=components)
            )

        # Guardrail: insufficient evidence count
        if len(scored_evidence) < self.min_evidence_count:
            result = aggregate(
                claim,
                scored_evidence,
                guardrail_triggered=(
                    f"Insufficient evidence: {len(scored_evidence)} chunks (minimum {self.min_evidence_count})."
                ),
                include_scored_evidence_in_output=include_scored_evidence,
            )
            result.confidence_label = ConfidenceLabel.INSUFFICIENT_EVIDENCE
            return result

        # Aggregate (contradiction guardrail handled inside aggregate)
        return aggregate(
            claim,
            scored_evidence,
            include_scored_evidence_in_output=include_scored_evidence,
        )
