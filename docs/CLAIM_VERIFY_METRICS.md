# Claim Verify — All Metrics Explained

This document explains **every metric** used in the Evidence Confidence Scoring Engine: what it is, how it’s computed, and where you see it.

---

## 1. High-level flow

```
Your claim  →  Retrieve chunks  →  Classify each chunk  →  Score each chunk  →  Aggregate  →  Final result
                    ↓                      ↓                      ↓                    ↓
            similarity_score         SUPPORT/CONTRADICT/      evidence_score      confidence_score
                                         NEUTRAL                  (0–1)              + label
```

So there are **three layers** of numbers:

1. **Per-chunk classification** (SUPPORT / CONTRADICT / NEUTRAL) + optional confidence  
2. **Per-chunk evidence score** (0–1), built from five sub-metrics  
3. **Overall result**: support/contradict/neutral counts, **confidence score**, and **confidence label**

---

## 2. Semantic similarity (retrieval)

**What it is**  
How relevant the **text of a chunk** is to your **claim** in embedding space (meaning, not keywords).

**How it’s computed**  
- Your claim is turned into a vector (embedding).  
- Each stored chunk has a vector.  
- FAISS finds the nearest chunks by **L2 distance** \(d\).  
- We convert distance to a 0–1 score: **similarity = 1 / (1 + d)**.  
  - Closer (smaller \(d\)) → higher similarity (closer to 1).  
  - Far (large \(d\)) → lower similarity (closer to 0).

**Where you see it**  
- It’s one of the five ingredients of the **evidence score** (see below).  
- In “Show chunk details,” the per-chunk number (e.g. **0.37**) is the **evidence score** for that chunk; similarity is one of its components (you’d see it in `score_components` if we exposed it in the UI).

**Why it matters**  
Retrieval is claim-specific: only chunks that are semantically close to the claim get pulled in and scored.

---

## 3. Classification: SUPPORT / CONTRADICT / NEUTRAL

**What it is**  
For **each retrieved chunk**, an LLM answers: does this piece of text **support** the claim, **contradict** it, or is it **neutral** (irrelevant or ambiguous)?

**How it’s computed**  
- One LLM call per chunk.  
- Prompt: “Given the claim and this evidence text, classify as SUPPORT, CONTRADICT, or NEUTRAL.”  
- Model returns **classification** and a **confidence** (0–1) for that classification.  
- No free-form summary—only this structured label.

**Where you see it**  
- **Result summary**: “Support: 2 · Contradict: 1 · Neutral: 1.”  
- **Per paper**: “Supports” / “Mostly supports” / “Mostly contradicts” / “Neutral” and “Support: X · Contradict: Y · Neutral: Z.”  
- **Per chunk** (in “Show chunk details”): each row shows SUPPORT / CONTRADICT / NEUTRAL with an icon.

**Why it matters**  
This is what turns “relevant text” into “evidence for or against” the claim. The rest of the pipeline (scoring and aggregation) uses these labels.

---

## 4. Evidence score (per chunk) — the five components

Each chunk gets a single **evidence score** between **0 and 1**. It is a **weighted sum** of five sub-metrics. Higher = stronger evidence (in terms of quality and relevance), regardless of whether the chunk supports or contradicts.

**Formula**

```
evidence_score = w1×semantic_similarity + w2×study_type_weight + w3×citation_score + w4×recency_score + w5×source_credibility
```

Default weights (sum to 1.0):

| Component            | Weight | Meaning |
|---------------------|--------|--------|
| semantic_similarity  | 0.30   | How relevant the chunk is to the claim (from FAISS). |
| study_type_weight   | 0.25   | How strong the **study design** is (e.g. RCT vs blog). |
| citation_score      | 0.20   | How much the **source** is cited (impact). |
| recency_score       | 0.15   | How **recent** the source is (year). |
| source_credibility  | 0.10   | **Journal/publisher** reputation. |

If metadata is missing (e.g. no journal, no year), that component uses a **default** (e.g. 0.5 for recency, 0.4 for study type, 0.5 for source credibility), so the score is still defined.

---

### 4.1 Study type weight

**What it is**  
A number 0–1 that ranks **type of source** by typical evidence strength (hierarchy of evidence).

**How it’s computed**  
- We look at the chunk/paper metadata field **study_type** (when present).  
- It’s mapped to a fixed weight, e.g.:

  - **Meta-analysis** → 1.0  
  - **RCT (randomized controlled trial)** → 0.9  
  - **Systematic review** → 0.85  
  - **Cohort** → 0.7  
  - **Observational** → 0.6  
  - **Case-control** → 0.65  
  - **Review** → 0.75  
  - **Blog / opinion** → 0.2–0.25  
  - **Unknown / missing** → 0.4  

**Where you see it**  
- Inside the **evidence score** (and in backend `score_components` as `study_type_weight`).  
- In the **evidence strength** line (e.g. “Strong (2 meta-analyses)”) we summarize which study types contributed.

**Why it matters**  
Not all evidence is equal: a meta-analysis is weighted more than a blog when combining into the final picture.

---

### 4.2 Citation score

**What it is**  
A 0–1 score for “how much this source is cited” (proxy for impact).

**How it’s computed**  
- Uses metadata **citation_count** (when available).  
- Formula: **citation_score = log(1 + citation_count) / log(1 + max_citation)**.  
- `max_citation` is a cap (e.g. 10,000) so that even very highly cited papers don’t dominate; score is clamped to at most 1.  
- If there’s no citation count, **citation_score = 0**.

**Where you see it**  
- Contributes to the **evidence score** (and to `score_components` in the backend).

**Why it matters**  
Highly cited work is often more influential and vetted; this down-weights obscure or uncited sources.

---

### 4.3 Recency score

**What it is**  
A 0–1 score for “how recent is the source” (newer = higher, older = lower).

**How it’s computed**  
- Uses **publication_year** from metadata (or derived from publication_date).  
- **Exponential decay**: `recency_score = 0.5^((current_year - publication_year) / half_life)`.  
- Half-life is 10 years: after 10 years, score halves; after 20 years, it’s 1/4, etc.  
- If year is missing → **0.5** (neutral).  
- If year is in the future → **1.0**.

**Where you see it**  
- Inside the **evidence score** (and in `score_components`).

**Why it matters**  
Newer evidence often reflects updated methods and consensus; old papers can be superseded.

---

### 4.4 Source credibility

**What it is**  
A 0–1 score for **journal/publisher** reputation.

**How it’s computed**  
- If **journal name** is in a high-prestige whitelist (e.g. Nature, Science, Lancet, NEJM, BMJ, JAMA, etc.) → **1.0** (or 0.9 for partial match).  
- Else if **publisher** is in a medium list (e.g. Springer, Elsevier, Wiley, Oxford, Cambridge) → **0.7**.  
- Otherwise → **0.5**.

**Where you see it**  
- Inside the **evidence score** (and in `score_components`).

**Why it matters**  
Peer-reviewed, reputable venues get more weight than unknown or low-quality outlets.

---

## 5. Aggregation: from chunks to one result

After every chunk is **classified** and **scored**, we aggregate to a single verdict.

**Definitions**

- **TotalSupport** = sum of **evidence_score** over all chunks classified as **SUPPORT**.  
- **TotalContradict** = sum of **evidence_score** over all chunks classified as **CONTRADICT**.  
- Neutral chunks’ scores are **not** added into either sum (they don’t push the balance up or down).

**Final confidence score (formula)**

```
confidence_score = (TotalSupport - TotalContradict) / (TotalSupport + TotalContradict + ε)
```

- **ε** is a tiny constant to avoid division by zero.  
- Result is in **[-1, 1]** (we clamp it):  
  - **Positive** → more supporting than contradicting evidence.  
  - **Negative** → more contradicting than supporting.  
  - **Near 0** → tie or mostly neutral.

So the number you see as **“Confidence: X%”** in the UI is this balance, often scaled to a 0–100% display (e.g. mapping the [-1,1] value to a percentage).

---

## 6. Confidence label (Strong / Moderate / Weak / Inconclusive / Contradicted)

**What it is**  
A **verbal label** for the overall result, so you don’t have to interpret the raw number alone.

**How it’s computed**  
We compare **confidence_score** (and sometimes guardrails) to fixed thresholds:

| Label                  | Condition |
|------------------------|-----------|
| **Strong**             | confidence_score ≥ 0.75 |
| **Moderate**           | 0.55 ≤ confidence_score < 0.75 |
| **Weak**               | 0.4 ≤ confidence_score < 0.55 |
| **Inconclusive**       | confidence_score < 0.4 (and not contradicted) |
| **Contradicted**       | TotalContradict > TotalSupport (overrides the number) |
| **Insufficient Evidence** | Fewer than 3 chunks retrieved (guardrail) |

**Where you see it**  
- Big colored label at the top of the result (e.g. “Moderate”, “Strong”).  
- In “Recent in this workspace” for each run.  
- In the **evidence strength** line we combine this with study-type info (e.g. “Strong (2 meta-analyses)”).

**Why it matters**  
Quick, interpretable answer: “Should I trust this claim?” without reading formulas.

---

## 7. Evidence strength (text summary)

**What it is**  
A short **sentence** that summarizes both the **confidence** and the **type** of supporting evidence (e.g. meta-analyses, RCTs).

**How it’s computed**  
- We look at chunks classified as **SUPPORT**.  
- We count their **study_type** (e.g. “meta_analysis”, “rct”).  
- We build a phrase like “Strong (2 meta-analyses, 1 RCT)” or “Moderate (3 supporting).”  
- If there’s mostly contradiction, we might say “Contradicted (X contradicting).”

**Where you see it**  
- In the result card, under the confidence label and counts: the line like “Strong (2 meta-analyses)” or “Moderate (4 supporting).”

**Why it matters**  
It tells you not only “how much” evidence (confidence) but “what kind” (study design), which matters for scientific claims.

---

## 8. Guardrails (rules that override normal output)

These are **safety/logic rules**, not metrics, but they change what you see:

| Rule | Effect |
|------|--------|
| **Fewer than 3 chunks** | We don’t call the result “Strong/Moderate/…” — we return **Insufficient Evidence** and may explain that there weren’t enough chunks. |
| **No chunks at all** | We never invent an answer; we return something like “No evidence retrieved” and no confidence. |
| **TotalContradict > TotalSupport** | The label is forced to **Contradicted** even if the numeric score would otherwise give another label. |

So the **metrics** (counts, confidence score, evidence score) are still computed where possible, but the **final label** and sometimes the messaging are overridden by these rules.

---

## 9. Where each metric appears in the UI (quick map)

| Metric / concept | Where you see it |
|------------------|------------------|
| **Support / Contradict / Neutral counts** | Result card: “Support: X · Contradict: Y · Neutral: Z” |
| **Confidence score** | “Confidence: X%” in the result card |
| **Confidence label** | Big label: Strong / Moderate / Weak / Inconclusive / Contradicted / Insufficient Evidence |
| **Evidence strength** | Text line under the label, e.g. “Strong (2 meta-analyses)” |
| **Per-paper verdict** | Each paper card: “Supports” / “Mostly supports” / “Neutral” / “Mostly contradicts” |
| **Per-paper counts** | On each paper card: “Support: X · Contradict: Y · Neutral: Z” and “avg score” |
| **Per-chunk classification** | In “Show chunk details”: SUPPORT / CONTRADICT / NEUTRAL with icon |
| **Per-chunk evidence score** | In “Show chunk details”: the number (e.g. 0.37) next to each chunk |
| **Strongest study types** | Optional line in result, e.g. “Strongest study types: meta_analysis, rct” |

---

## 10. Short “cheat sheet”

- **Similarity** = how relevant the chunk text is to the claim (0–1).  
- **Classification** = SUPPORT / CONTRADICT / NEUTRAL per chunk (from LLM).  
- **Evidence score** = weighted mix of: similarity + study type + citations + recency + source credibility (0–1 per chunk).  
- **TotalSupport / TotalContradict** = sum of evidence scores of supporting vs contradicting chunks.  
- **Confidence score** = (Support − Contradict) / (Support + Contradict), in [-1, 1].  
- **Confidence label** = Strong / Moderate / Weak / Inconclusive / Contradicted / Insufficient Evidence from thresholds and guardrails.  
- **Evidence strength** = human-readable summary of confidence + study types (e.g. “Strong (2 meta-analyses)”).

If you want to go deeper on one metric (e.g. only recency or only study type), we can do a follow-up doc or add tooltips in the UI for each number.
