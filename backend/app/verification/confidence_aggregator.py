"""
Phase 4 — Confidence Aggregation.
Aggregates scored evidence into final confidence score and structured JSON output.
"""
from collections import Counter
from typing import List, Optional

from app.verification.constants import (
    CONFIDENCE_EPSILON,
    CONFIDENCE_STRONG,
    CONFIDENCE_MODERATE_LO,
    CONFIDENCE_WEAK_LO,
    CONFIDENCE_INCONCLUSIVE,
    STUDY_TYPE_WEIGHTS,
)
from app.verification.schemas import (
    ConfidenceLabel,
    EvidenceLabel,
    ScoredEvidence,
    VerificationResult,
)


def _confidence_label(score: float) -> ConfidenceLabel:
    """Map numeric confidence to label. Contradiction handled by caller."""
    if score >= CONFIDENCE_STRONG:
        return ConfidenceLabel.STRONG
    if score >= CONFIDENCE_MODERATE_LO:
        return ConfidenceLabel.MODERATE
    if score >= CONFIDENCE_WEAK_LO:
        return ConfidenceLabel.WEAK
    return ConfidenceLabel.INCONCLUSIVE


def _evidence_strength_summary(
    scored: List[ScoredEvidence],
    support_count: int,
    contradict_count: int,
) -> str:
    """Build human-readable evidence strength, e.g. 'Strong (2 meta-analyses)'."""
    support_only = [s for s in scored if s.classification.classification == EvidenceLabel.SUPPORT]
    study_types: List[str] = []
    for s in support_only:
        st = s.retrieved.metadata.study_type
        if st:
            study_types.append(st.strip().lower())
    if not study_types:
        if support_count > 0:
            return f"Moderate ({support_count} supporting)"
        if contradict_count > 0:
            return f"Contradicted ({contradict_count} contradicting)"
        return "Inconclusive"
    cnt = Counter(study_types)
    # Prefer high-value types
    order = ["meta-analysis", "meta_analysis", "rct", "systematic review", "systematic_review", "cohort", "observational"]
    top = []
    for t in order:
        if t in cnt and cnt[t] > 0:
            top.append(f"{cnt[t]} {t.replace('_', ' ')}")
    if not top:
        top = [f"{v} {k}" for k, v in cnt.most_common(2)]
    return "Strong (" + ", ".join(top[:3]) + ")" if top else f"Moderate ({support_count} supporting)"


def aggregate(
    claim: str,
    scored_evidence: List[ScoredEvidence],
    *,
    guardrail_triggered: Optional[str] = None,
    include_scored_evidence_in_output: bool = True,
) -> VerificationResult:
    """
    Compute TotalSupport, TotalContradict, FinalConfidence, and build VerificationResult.

    FinalConfidence = (TotalSupport - TotalContradict) / (TotalSupport + TotalContradict + epsilon)
    """
    support_scores: List[float] = []
    contradict_scores: List[float] = []
    neutral_count = 0
    study_types_support: List[str] = []

    for s in scored_evidence:
        lab = s.classification.classification
        scr = s.evidence_score
        if lab == EvidenceLabel.SUPPORT:
            support_scores.append(scr)
            if s.retrieved.metadata.study_type:
                study_types_support.append(s.retrieved.metadata.study_type.strip().lower())
        elif lab == EvidenceLabel.CONTRADICT:
            contradict_scores.append(scr)
        else:
            neutral_count += 1

    total_support = sum(support_scores)
    total_contradict = sum(contradict_scores)
    denom = total_support + total_contradict + CONFIDENCE_EPSILON
    confidence_score = (total_support - total_contradict) / denom
    # Clamp to [-1, 1] for consistency (negative = net contradiction)
    confidence_score = max(-1.0, min(1.0, confidence_score))

    # Guardrail: if contradiction weight > support weight, label Contradicted
    if total_contradict > total_support and not guardrail_triggered:
        guardrail_triggered = "Contradiction weight exceeds support weight"
    confidence_label = _confidence_label(confidence_score)
    if guardrail_triggered and "Contradict" in guardrail_triggered:
        confidence_label = ConfidenceLabel.CONTRADICTED

    # Strongest study types (by weight, among supporting)
    type_to_weight = {k: v for k, v in STUDY_TYPE_WEIGHTS.items()}
    strongest = sorted(
        set(st for st in study_types_support if st),
        key=lambda t: type_to_weight.get(t.replace(" ", "_"), 0),
        reverse=True,
    )[:5]

    evidence_strength = _evidence_strength_summary(
        scored_evidence,
        len(support_scores),
        len(contradict_scores),
    )

    scored_dicts = [s.to_dict() for s in scored_evidence] if include_scored_evidence_in_output else []

    return VerificationResult(
        claim=claim,
        support_count=len(support_scores),
        contradict_count=len(contradict_scores),
        neutral_count=neutral_count,
        evidence_count=len(scored_evidence),
        confidence_score=confidence_score,
        confidence_label=confidence_label,
        evidence_strength=evidence_strength,
        strongest_study_types=strongest,
        guardrail_triggered=guardrail_triggered,
        scored_evidence=scored_dicts,
    )
