"""
Evidence Confidence Scoring Engine — Constants and weight hierarchies.
Research-grade thresholds and study-type weights.
"""
from typing import Dict

# ---------------------------------------------------------------------------
# Study type weight hierarchy (evidence quality)
# ---------------------------------------------------------------------------
STUDY_TYPE_WEIGHTS: Dict[str, float] = {
    "meta_analysis": 1.0,
    "meta-analysis": 1.0,
    "systematic_review": 0.85,
    "systematic review": 0.85,
    "rct": 0.9,
    "randomized_controlled_trial": 0.9,
    "randomized controlled trial": 0.9,
    "cohort": 0.7,
    "cohort_study": 0.7,
    "observational": 0.6,
    "observational_study": 0.6,
    "case_control": 0.65,
    "case-control": 0.65,
    "cross_sectional": 0.55,
    "cross-sectional": 0.55,
    "review": 0.75,
    "narrative_review": 0.7,
    "blog": 0.2,
    "opinion": 0.25,
    "preprint": 0.5,
    "unknown": 0.4,
}

DEFAULT_STUDY_TYPE_WEIGHT = 0.4

# ---------------------------------------------------------------------------
# Evidence score component weights (must sum to 1.0 for normalized score in [0,1])
# ---------------------------------------------------------------------------
W_SEMANTIC_SIMILARITY = 0.30
W_STUDY_TYPE = 0.25
W_CITATION = 0.20
W_RECENCY = 0.15
W_SOURCE_CREDIBILITY = 0.10

EVIDENCE_WEIGHTS = {
    "semantic_similarity": W_SEMANTIC_SIMILARITY,
    "study_type": W_STUDY_TYPE,
    "citation": W_CITATION,
    "recency": W_RECENCY,
    "source_credibility": W_SOURCE_CREDIBILITY,
}

# ---------------------------------------------------------------------------
# Recency decay: half-life in years (exponential decay)
# ---------------------------------------------------------------------------
RECENCY_HALF_LIFE_YEARS = 10.0
CURRENT_YEAR = 2025  # configurable

# ---------------------------------------------------------------------------
# Citation score: log normalization cap (max citations expected in corpus)
# ---------------------------------------------------------------------------
MAX_CITATION_FOR_NORM = 10_000.0

# ---------------------------------------------------------------------------
# Confidence label thresholds
# ---------------------------------------------------------------------------
CONFIDENCE_STRONG = 0.75
CONFIDENCE_MODERATE_HI = 0.75
CONFIDENCE_MODERATE_LO = 0.55
CONFIDENCE_WEAK_HI = 0.55
CONFIDENCE_WEAK_LO = 0.4
CONFIDENCE_INCONCLUSIVE = 0.4

# ---------------------------------------------------------------------------
# Guardrails
# ---------------------------------------------------------------------------
MIN_EVIDENCE_COUNT = 3
CONFIDENCE_EPSILON = 1e-6  # avoid division by zero in aggregation

# ---------------------------------------------------------------------------
# Journal / source credibility: whitelist gets 1.0, else impact-factor proxy or 0.5
# Placeholder: extend with real journal list or API (e.g. Scimago).
# ---------------------------------------------------------------------------
HIGH_CREDIBILITY_JOURNALS = frozenset({
    "nature", "science", "cell", "lancet", "nejm", "bmj", "jama",
    "plos medicine", "annals of internal medicine", "nature medicine",
    "nature communications", "pnas", "the bmj",
})
MEDIUM_CREDIBILITY_PUBLISHERS = frozenset({
    "springer", "elsevier", "wiley", "taylor & francis", "sage",
    "oxford university press", "cambridge university press", "acs",
})

# ---------------------------------------------------------------------------
# Research Hallucination Firewall — configurable thresholds (Part 2)
# ---------------------------------------------------------------------------
MIN_AVG_SIMILARITY = 0.45
MIN_TOTAL_EVIDENCE_WEIGHT = 1.5
MIN_DISTINCT_SOURCES_FOR_FULL_CONFIDENCE = 2
FIREWALL_DIVERSITY_PENALTY = 0.15  # subtract from confidence when single source
