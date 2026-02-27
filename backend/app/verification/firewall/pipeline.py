"""
Part 6 — Architecture Integration.
FirewallVerificationPipeline composes VerificationGate → Engine flow → DiversityAdjuster
→ SelfCheckValidator → StructuredOutputEnforcer without replacing the existing engine.
"""
import logging
from typing import Any, Dict, List, Optional

from app.verification.constants import MIN_EVIDENCE_COUNT
from app.verification.schemas import (
    ClassificationResult,
    ConfidenceLabel,
    EvidenceLabel,
    ScoredEvidence,
    VerificationResult,
)
from app.verification.engine import VerificationEngine
from app.verification.confidence_aggregator import aggregate
from app.verification.firewall.gate import VerificationGate, STATUS_BLOCKED
from app.verification.firewall.diversity import DiversityAdjuster
from app.verification.firewall.self_check import SelfCheckValidator
from app.verification.firewall.structured_output import StructuredOutputEnforcer
from app.verification.firewall.metrics import FirewallMetrics

logger = logging.getLogger(__name__)


class FirewallVerificationPipeline:
    """
    Full pipeline with Research Hallucination Firewall:

    User Query
      → EvidenceRetriever (via engine)
      → VerificationGate (block if 0 results, low count, low similarity/weight)
      → EvidenceScorer + ClaimClassifier (existing)
      → ConfidenceAggregator (existing)
      → DiversityAdjuster (cross-source validation, contradiction override)
      → SelfCheckValidator (second-pass checks; block if failed)
      → StructuredOutputEnforcer (JSON-only, no free text)
      → Final Response

    Does not modify existing VerificationEngine; uses its components and extends.
    """

    def __init__(
        self,
        top_k: int = 10,
        workspace_id: Optional[str] = None,
        user_id: Optional[str] = None,
        min_evidence_count: int = MIN_EVIDENCE_COUNT,
        use_self_check_llm: bool = True,
        metrics: Optional[FirewallMetrics] = None,
    ):
        self.engine = VerificationEngine(
            top_k=top_k,
            workspace_id=workspace_id,
            user_id=user_id,
            min_evidence_count=min_evidence_count,
        )
        self.gate = VerificationGate(min_evidence_count=min_evidence_count)
        self.diversity_adjuster = DiversityAdjuster()
        self.self_check = SelfCheckValidator(use_llm=use_self_check_llm)
        self.enforcer = StructuredOutputEnforcer()
        self.metrics = metrics or FirewallMetrics()

    def verify_through_firewall(
        self,
        claim: str,
        paper_ids: Optional[List[str]] = None,
        include_scored_evidence: bool = True,
    ) -> Dict[str, Any]:
        """
        Run claim verification through the full firewall pipeline.
        Returns either:
        - Blocked response: {"status": "BLOCKED", "reason": "...", "retrieved_count": N, ...}
        - Success response: structured dict with claim, support_count, confidence_score,
          evidence_summary, verification_status, etc. (and optionally full scored_evidence).
        """
        retrieved_list = self.engine.retriever.retrieve(claim, paper_ids=paper_ids)
        gate_result = self.gate.check_retrieval(retrieved_list)

        if gate_result.status == STATUS_BLOCKED:
            self.metrics.record_blocked(reason=gate_result.reason or "gate")
            self.metrics.log_rejected_query(
                claim=claim,
                reason=gate_result.reason or "gate",
                retrieved_count=gate_result.retrieved_count,
                extra={"avg_similarity": gate_result.avg_similarity},
            )
            return {
                "status": "BLOCKED",
                "reason": gate_result.reason,
                "retrieved_count": gate_result.retrieved_count,
                "avg_similarity": gate_result.avg_similarity,
                "total_evidence_weight": gate_result.total_evidence_weight,
            }

        scored_evidence: List[ScoredEvidence] = []
        for r in retrieved_list:
            score_val, components = self.engine.scorer.score(r)
            clf = self.engine.classifier.classify(claim, r)
            if not clf:
                clf = ClassificationResult(EvidenceLabel.NEUTRAL, 0.5, "Classification unavailable.")
            scored_evidence.append(
                ScoredEvidence(retrieved=r, classification=clf, evidence_score=score_val, score_components=components)
            )

        gate_after = self.gate.check_after_scoring(scored_evidence)
        if gate_after.status == STATUS_BLOCKED:
            self.metrics.record_blocked(reason=gate_after.reason or "gate_after_scoring")
            self.metrics.log_rejected_query(
                claim=claim,
                reason=gate_after.reason or "gate_after_scoring",
                retrieved_count=gate_after.retrieved_count,
            )
            return {
                "status": "BLOCKED",
                "reason": gate_after.reason,
                "retrieved_count": gate_after.retrieved_count,
                "avg_similarity": gate_after.avg_similarity,
                "total_evidence_weight": gate_after.total_evidence_weight,
            }

        if len(scored_evidence) < self.engine.min_evidence_count:
            result = aggregate(
                claim,
                scored_evidence,
                guardrail_triggered=(
                    f"Insufficient evidence: {len(scored_evidence)} chunks (minimum {self.engine.min_evidence_count})."
                ),
                include_scored_evidence_in_output=include_scored_evidence,
            )
            result = VerificationResult(
                claim=result.claim,
                support_count=result.support_count,
                contradict_count=result.contradict_count,
                neutral_count=result.neutral_count,
                evidence_count=result.evidence_count,
                confidence_score=result.confidence_score,
                confidence_label=ConfidenceLabel.INSUFFICIENT_EVIDENCE,
                evidence_strength=result.evidence_strength,
                strongest_study_types=result.strongest_study_types,
                guardrail_triggered=result.guardrail_triggered,
                scored_evidence=result.scored_evidence,
            )
        else:
            result = aggregate(
                claim,
                scored_evidence,
                include_scored_evidence_in_output=include_scored_evidence,
            )

        result = self.diversity_adjuster.adjust(result)
        self.metrics.record_contradiction_heavy(result)
        self.metrics.record_low_diversity(result, scored_evidence)

        self_check_result = self.self_check.validate(result)
        if not self_check_result.self_check_passed:
            self.metrics.record_self_check_failure(self_check_result.issues)
            self.metrics.log_rejected_query(
                claim=claim,
                reason="Self-check failed",
                retrieved_count=result.evidence_count,
                extra={"issues": self_check_result.issues},
            )
            return {
                "status": "BLOCKED",
                "reason": "Self-check failed",
                "self_check_issues": self_check_result.issues,
                "retrieved_count": result.evidence_count,
            }

        structured = self.enforcer.enforce_from_result(result)
        if include_scored_evidence:
            structured["scored_evidence"] = result.scored_evidence
        structured["evidence_count"] = result.evidence_count
        structured["evidence_strength"] = result.evidence_strength
        structured["strongest_study_types"] = result.strongest_study_types
        structured["guardrail_triggered"] = result.guardrail_triggered
        structured["neutral_count"] = result.neutral_count
        self.metrics.record_success()
        return structured
