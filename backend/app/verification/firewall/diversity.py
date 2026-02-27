"""
Part 5 — Cross-Source Validation.
Adjust confidence when evidence is from single publisher/journal or low diversity.
Override label to CONTRADICTED when contradiction weight > support weight.
"""
import logging
from typing import Any, Dict, List, Tuple

from app.verification.constants import (
    MIN_DISTINCT_SOURCES_FOR_FULL_CONFIDENCE,
    FIREWALL_DIVERSITY_PENALTY,
)
from app.verification.schemas import (
    ConfidenceLabel,
    ScoredEvidence,
    VerificationResult,
)

logger = logging.getLogger(__name__)


def _distinct_sources_from_dicts(evidence_dicts: List[Dict[str, Any]]) -> Tuple[int, bool]:
    """
    Returns (distinct_source_count, all_same_publisher_or_journal).
    Uses paper_id as source; publisher and journal_name for same-source check.
    """
    sources: set = set()
    publishers: set = set()
    journals: set = set()
    for d in evidence_dicts:
        if not isinstance(d, dict):
            continue
        pid = d.get("paper_id") or ""
        if pid:
            sources.add(pid)
        pub = d.get("publisher")
        if pub:
            publishers.add(str(pub).strip().lower())
        j = d.get("journal_name")
        if j:
            journals.add(str(j).strip().lower())
    distinct = len(sources)
    all_same = (len(publishers) <= 1 and len(journals) <= 1) and (publishers or journals)
    return distinct, all_same


def _distinct_sources(scored: List[ScoredEvidence]) -> Tuple[int, bool]:
    """From List[ScoredEvidence]: (distinct_count, all_same_publisher_or_journal)."""
    dicts: List[Dict[str, Any]] = []
    for s in scored:
        dicts.append({
            "paper_id": s.retrieved.metadata.paper_id,
            "publisher": s.retrieved.metadata.publisher,
            "journal_name": s.retrieved.metadata.journal_name,
        })
    return _distinct_sources_from_dicts(dicts)


def adjust_confidence_for_diversity(
    evidence_list: List[ScoredEvidence],
    confidence_score: float,
    confidence_label: ConfidenceLabel,
) -> Tuple[float, ConfidenceLabel]:
    """
    - If all supporting papers from same publisher or same journal → lower confidence.
    - If evidence diversity < 2 distinct sources → downgrade confidence_label.
    - Returns (modified_confidence_score, modified_confidence_label).
    """
    if not evidence_list:
        return confidence_score, confidence_label
    distinct_count, all_same_source = _distinct_sources(evidence_list)
    new_score = confidence_score
    new_label = confidence_label
    if distinct_count < MIN_DISTINCT_SOURCES_FOR_FULL_CONFIDENCE:
        new_score = max(-1.0, confidence_score - FIREWALL_DIVERSITY_PENALTY)
        logger.debug(
            "DiversityAdjuster: distinct sources %s < %s, penalty applied",
            distinct_count, MIN_DISTINCT_SOURCES_FOR_FULL_CONFIDENCE,
        )
        if confidence_label == ConfidenceLabel.STRONG:
            new_label = ConfidenceLabel.MODERATE
        elif confidence_label == ConfidenceLabel.MODERATE:
            new_label = ConfidenceLabel.WEAK
    if all_same_source and distinct_count < 2:
        new_score = max(-1.0, new_score - FIREWALL_DIVERSITY_PENALTY)
        logger.info("DiversityAdjuster: all evidence from same publisher/journal, penalty applied")
    return new_score, new_label


class DiversityAdjuster:
    """
    Applies cross-source validation to VerificationResult:
    - Lower confidence when all evidence from same publisher/journal.
    - Downgrade confidence_label when evidence diversity < 2 distinct sources.
    - Override label to CONTRADICTED when contradiction weight > support weight.
    """

    def __init__(
        self,
        min_distinct_sources: int = MIN_DISTINCT_SOURCES_FOR_FULL_CONFIDENCE,
        diversity_penalty: float = FIREWALL_DIVERSITY_PENALTY,
    ):
        self.min_distinct_sources = min_distinct_sources
        self.diversity_penalty = diversity_penalty

    def adjust(self, result: VerificationResult) -> VerificationResult:
        """
        Returns a new VerificationResult with adjusted confidence_score and
        confidence_label. Uses result.scored_evidence (list of dicts).
        """
        evidence_dicts = [e for e in result.scored_evidence if isinstance(e, dict)]
        if not evidence_dicts:
            return result
        distinct_count, all_same_source = _distinct_sources_from_dicts(evidence_dicts)
        support_weight = 0.0
        contradict_weight = 0.0
        for d in evidence_dicts:
            cls = d.get("classification") or {}
            lab = (str(cls.get("classification") or "")).upper()
            score = float(d.get("evidence_score", 0))
            if "SUPPORT" in lab:
                support_weight += score
            elif "CONTRADICT" in lab:
                contradict_weight += score
        new_score = result.confidence_score
        new_label = result.confidence_label
        if contradict_weight > support_weight:
            new_label = ConfidenceLabel.CONTRADICTED
            denom = support_weight + contradict_weight + 1e-6
            new_score = max(-1.0, (support_weight - contradict_weight) / denom)
        else:
            if distinct_count < self.min_distinct_sources:
                new_score = max(-1.0, new_score - self.diversity_penalty)
                if result.confidence_label == ConfidenceLabel.STRONG:
                    new_label = ConfidenceLabel.MODERATE
                elif result.confidence_label == ConfidenceLabel.MODERATE:
                    new_label = ConfidenceLabel.WEAK
            if all_same_source and distinct_count < 2:
                new_score = max(-1.0, new_score - self.diversity_penalty)
        return VerificationResult(
            claim=result.claim,
            support_count=result.support_count,
            contradict_count=result.contradict_count,
            neutral_count=result.neutral_count,
            evidence_count=result.evidence_count,
            confidence_score=new_score,
            confidence_label=new_label,
            evidence_strength=result.evidence_strength,
            strongest_study_types=result.strongest_study_types,
            guardrail_triggered=result.guardrail_triggered,
            scored_evidence=result.scored_evidence,
        )
