"""
Part 7 — Logging & Monitoring.
Block rate, evidence sufficiency rate, self-check failure rate.
Evaluation metrics: hallucination reduction, false positive verification, confidence calibration.
"""
import logging
import time
from dataclasses import dataclass, field
from typing import List, Optional

from app.verification.schemas import ScoredEvidence, VerificationResult

logger = logging.getLogger(__name__)


@dataclass
class FirewallMetrics:
    """
    In-process metrics for the Research Hallucination Firewall.
    Production: wire to Prometheus/StatsD or persist to DB.
    """

    blocked_count: int = 0
    success_count: int = 0
    self_check_failure_count: int = 0
    contradiction_heavy_count: int = 0
    low_diversity_count: int = 0
    total_queries: int = 0
    blocked_reasons: dict = field(default_factory=dict)
    self_check_issues_sample: List[List[str]] = field(default_factory=list)
    _rejected_query_log: List[dict] = field(default_factory=list)
    _max_rejected_log: int = 500

    def record_blocked(self, reason: Optional[str] = None) -> None:
        self.total_queries += 1
        self.blocked_count += 1
        key = reason or "unknown"
        self.blocked_reasons[key] = self.blocked_reasons.get(key, 0) + 1
        logger.info("FirewallMetrics: blocked (reason=%s)", reason)

    def record_success(self) -> None:
        self.total_queries += 1
        self.success_count += 1

    def record_self_check_failure(self, issues: List[str]) -> None:
        self.self_check_failure_count += 1
        self.self_check_issues_sample = (self.self_check_issues_sample + [issues])[-10:]
        logger.warning("FirewallMetrics: self-check failed, issues=%s", issues)

    def record_contradiction_heavy(self, result: VerificationResult) -> None:
        if result.confidence_label.value == "Contradicted":
            self.contradiction_heavy_count += 1
            logger.info(
                "FirewallMetrics: contradiction-heavy response claim=%s",
                result.claim[:80],
            )

    def record_low_diversity(
        self,
        result: VerificationResult,
        scored_evidence: List[ScoredEvidence],
    ) -> None:
        papers = set()
        for s in scored_evidence:
            papers.add(s.retrieved.metadata.paper_id or "")
        if len(papers) < 2 and result.evidence_count > 0:
            self.low_diversity_count += 1
            logger.info(
                "FirewallMetrics: low diversity (distinct sources=1) claim=%s",
                result.claim[:80],
            )

    def log_rejected_query(
        self,
        claim: str,
        reason: str,
        retrieved_count: int = 0,
        extra: Optional[dict] = None,
    ) -> None:
        entry = {
            "ts": time.time(),
            "claim": claim[:200],
            "reason": reason,
            "retrieved_count": retrieved_count,
            **(extra or {}),
        }
        self._rejected_query_log.append(entry)
        if len(self._rejected_query_log) > self._max_rejected_log:
            self._rejected_query_log = self._rejected_query_log[-self._max_rejected_log :]

    @property
    def block_rate(self) -> float:
        if self.total_queries == 0:
            return 0.0
        return self.blocked_count / self.total_queries

    @property
    def evidence_sufficiency_rate(self) -> float:
        if self.total_queries == 0:
            return 0.0
        return self.success_count / self.total_queries

    @property
    def self_check_failure_rate(self) -> float:
        attempted = self.success_count + self.self_check_failure_count
        if attempted == 0:
            return 0.0
        return self.self_check_failure_count / attempted

    def snapshot(self) -> dict:
        return {
            "block_rate": round(self.block_rate, 4),
            "evidence_sufficiency_rate": round(self.evidence_sufficiency_rate, 4),
            "self_check_failure_rate": round(self.self_check_failure_rate, 4),
            "blocked_count": self.blocked_count,
            "success_count": self.success_count,
            "self_check_failure_count": self.self_check_failure_count,
            "contradiction_heavy_count": self.contradiction_heavy_count,
            "low_diversity_count": self.low_diversity_count,
            "total_queries": self.total_queries,
            "blocked_reasons": dict(self.blocked_reasons),
        }

    # --- Evaluation metrics (for offline analysis) ---

    @staticmethod
    def evaluation_hallucination_reduction(
        baseline_unsupported_count: int,
        firewall_unsupported_count: int,
        total_eval_claims: int,
    ) -> dict:
        """
        Hallucination reduction: compare rate of unsupported answers before/after firewall.
        """
        if total_eval_claims == 0:
            return {"baseline_rate": 0.0, "firewall_rate": 0.0, "reduction": 0.0}
        b_rate = baseline_unsupported_count / total_eval_claims
        f_rate = firewall_unsupported_count / total_eval_claims
        reduction = (b_rate - f_rate) / b_rate if b_rate > 0 else 0.0
        return {
            "baseline_unsupported_rate": round(b_rate, 4),
            "firewall_unsupported_rate": round(f_rate, 4),
            "reduction_ratio": round(reduction, 4),
        }

    @staticmethod
    def evaluation_false_positive_verification(
        gold_negative_count: int,
        predicted_positive_count: int,
        total_gold_negative: int,
    ) -> dict:
        """False positive verification: when gold says not verified, how often did we say verified."""
        if total_gold_negative == 0:
            return {"fp_verification_rate": 0.0}
        return {
            "fp_verification_rate": round(predicted_positive_count / total_gold_negative, 4),
            "gold_negative_total": total_gold_negative,
        }

    @staticmethod
    def evaluation_confidence_calibration(
        bins: List[tuple],
        expected_accuracy_per_bin: List[float],
    ) -> dict:
        """
        Confidence calibration: per confidence bin, compare mean predicted confidence
        to actual accuracy. ECE = expected calibration error.
        """
        if not bins or len(bins) != len(expected_accuracy_per_bin):
            return {"ece": 0.0, "bins": []}
        ece = 0.0
        n = sum(b[0] for b in bins)  # total samples per bin
        if n == 0:
            return {"ece": 0.0, "bins": []}
        for (count, mean_conf), acc in zip(bins, expected_accuracy_per_bin):
            ece += (count / n) * abs(mean_conf - acc)
        return {
            "ece": round(ece, 4),
            "bins": [
                {"count": b[0], "mean_confidence": b[1], "accuracy": a}
                for b, a in zip(bins, expected_accuracy_per_bin)
            ],
        }
