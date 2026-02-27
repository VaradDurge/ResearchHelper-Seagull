# Evidence Confidence Scoring Engine

Structured scientific claim verification: retrieve → classify → score → aggregate. Output is JSON only; no summarization.

## Architecture

```
EvidenceRetriever → [RetrievedEvidence]
       ↓
EvidenceScorer + ClaimClassifier → [ScoredEvidence]
       ↓
ConfidenceAggregator → VerificationResult (JSON)
```

- **EvidenceRetriever**: FAISS search by claim embedding; returns chunks with `similarity_score` and metadata (publication_year, citation_count, journal_name, study_type, publisher, DOI when available).
- **EvidenceScorer**: `EvidenceScore = w1*semantic + w2*study_type + w3*citation + w4*recency + w5*source_credibility`.
- **ClaimClassifier**: LLM classifies each chunk as SUPPORT / CONTRADICT / NEUTRAL; JSON-only response.
- **ConfidenceAggregator**: `FinalConfidence = (TotalSupport - TotalContradict) / (TotalSupport + TotalContradict + ε)`; labels Strong/Moderate/Weak/Inconclusive/Contradicted/Insufficient Evidence.
- **VerificationEngine**: Orchestrates pipeline and guardrails (min evidence, no answer without evidence, contradiction override).

## Phase 1 — Retrieval & metadata

- Similarity score is stored in each search result (`score`, `distance`) and passed downstream.
- Chunk metadata may include: `publication_year`, `citation_count`, `journal_name`, `study_type`, `publisher`, `doi`.
- Enrichment: `metadata_enrichment.enrich_metadata_at_ingestion()` at ingest; `update_vector_db_metadata_for_paper(paper_id)` after paper metadata is updated (e.g. DOI lookup).

## Phase 2 — Evidence score

- `compute_evidence_score(chunk_metadata, similarity_score)` in `evidence_scorer.py`.
- Weights: semantic 0.30, study_type 0.25, citation 0.20, recency 0.15, source_credibility 0.10.
- Study type hierarchy: meta_analysis=1.0, RCT=0.9, systematic_review=0.85, cohort=0.7, observational=0.6, blog=0.2.
- Citation: `log(1 + count) / log(1 + max_citation)`.
- Recency: exponential decay by publication year.
- Source: journal whitelist / publisher list.

## Phase 3 — Classification

- Prompt in `claim_classifier.CLASSIFICATION_PROMPT_TEMPLATE`.
- Response must be JSON: `{"classification": "SUPPORT"|"CONTRADICT"|"NEUTRAL", "confidence": float, "reason": "..."}`.
- Parser strips markdown and extracts first JSON object to avoid hallucination.

## Phase 4 — Aggregation

- Thresholds: ≥0.75 Strong, 0.55–0.75 Moderate, 0.4–0.55 Weak, <0.4 Inconclusive; Contradicted when TotalContradict > TotalSupport.

## Phase 5 — Guardrails

- `evidence_count < 3` → Insufficient Evidence.
- `TotalContradict > TotalSupport` → Contradicted.
- No answer without evidence (return structured result with zero counts and guardrail message).
- No summarization: only structured JSON.

## Example final JSON output

```json
{
  "claim": "Coffee reduces anxiety in adults",
  "support_count": 7,
  "contradict_count": 2,
  "neutral_count": 1,
  "evidence_count": 10,
  "confidence_score": 0.74,
  "confidence_label": "Moderate",
  "evidence_strength": "Strong (2 meta-analyses, 3 RCTs)",
  "strongest_study_types": ["meta_analysis", "rct", "systematic_review"],
  "guardrail_triggered": null,
  "scored_evidence": [
    {
      "evidence_score": 0.82,
      "classification": {"classification": "SUPPORT", "confidence": 0.91, "reason": "Meta-analysis reports significant reduction in anxiety scores."},
      "similarity_score": 0.88,
      "paper_id": "...",
      "paper_title": "...",
      "page_number": 3,
      "chunk_index": 1,
      "text": "...",
      "score_components": {
        "semantic_similarity": 0.88,
        "study_type_weight": 1.0,
        "citation_score": 0.65,
        "recency_score": 0.72,
        "source_credibility": 0.9
      }
    }
  ]
}
```

## Evaluation metrics (suggestions)

- **Support detection**: Treat SUPPORT as positive class. Precision = TP/(TP+FP), Recall = TP/(TP+FN), F1. Requires gold labels per chunk (human or curated).
- **Contradiction detection**: Same for CONTRADICT; can report per-class F1.
- **Confidence calibration**: Compare `confidence_score` to binary gold (supported vs not); plot reliability diagram; compute ECE (expected calibration error).
- **Ranking**: Correlation between evidence_score and human relevance/strength (e.g. Spearman).
- **End-to-end**: Claim-level gold (supported / contradicted / inconclusive); accuracy and macro F1 of `confidence_label` vs gold.
