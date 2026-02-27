---
name: Claim Verify metrics ELI10 doc
overview: Add a single markdown file that explains every Claim Verify metric and how it is calculated, in simple language suitable for a 10-year-old (short sentences, analogies, no jargon).
todos: []
isProject: false
---

# Claim Verify Metrics — Explained Like You're 10

## Goal

Create **one new markdown file** (e.g. `docs/CLAIM_VERIFY_METRICS_SIMPLE.md`) that explains all the metrics and calculations used in Claim Verify in very simple language: short sentences, everyday analogies, and step-by-step "how we get this number."

No code or backend changes—only this new doc.

---

## Source of truth (what to explain)

All formulas and numbers come from:

- [backend/app/verification/constants.py](backend/app/verification/constants.py) — weights, study-type list, thresholds, guardrails
- [backend/app/verification/evidence_scorer.py](backend/app/verification/evidence_scorer.py) — evidence score formula and the five sub-scores
- [backend/app/verification/confidence_aggregator.py](backend/app/verification/confidence_aggregator.py) — how we combine chunks into one final answer

Existing technical doc: [docs/CLAIM_VERIFY_METRICS.md](docs/CLAIM_VERIFY_METRICS.md) (for reference; the new file will be a simpler, kid-friendly version).

---

## Suggested structure of the new MD file

### 1. **What Claim Verify does (one paragraph)**

- You type a claim (one sentence). We look in your documents for bits that **support** it, **contradict** it, or don’t really say either way. Then we give you one simple answer: Strong / Moderate / Weak / etc.

### 2. **Step 1: Finding the right bits (similarity)**

- We turn your claim and every "chunk" of text into a kind of fingerprint (embedding).  
- We measure how **close** that chunk’s fingerprint is to the claim’s fingerprint (FAISS search → L2 distance).  
- We turn distance into a 0–1 score: **similarity = 1 / (1 + distance)**. Closer = bigger number.  
- **Simple analogy**: "Like finding the paragraphs in a book that talk about the same topic as your sentence."

### 3. **Step 2: Does this bit support or contradict? (classification)**

- For each chunk we ask the AI: does this text **support** the claim, **contradict** it, or is it **neutral**?  
- The AI answers only: SUPPORT, CONTRADICT, or NEUTRAL, plus a **confidence** (0–100%) for that choice.  
- **Simple analogy**: "Like a friend reading a paragraph and saying: Yes it backs you up / No it says the opposite / I’m not sure."

### 4. **Step 3: How strong is this bit? (evidence score)**

- Each chunk gets **one number from 0 to 1** (evidence score). Bigger = we trust that chunk more.  
- That number is a **mix of five things**, each scored 0–1 and then multiplied by a fixed "importance" (weight):


| What we look at        | Weight | How we get the 0–1 number (ELI10 version)                                                                                                                                         |
| ---------------------- | ------ | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Relevance to claim** | 30%    | The similarity from Step 1 (already 0–1). "How much does this paragraph talk about what you said?"                                                                                |
| **Study quality**      | 25%    | Type of source: meta-analysis = 1.0, RCT = 0.9, systematic review = 0.85, cohort = 0.7, observational = 0.6, blog = 0.2, unknown = 0.4. "Scientists trust some study types more." |
| **Citations**          | 20%    | If we know how many times the paper was cited: **log(1 + citations) / log(1 + 10000)** (capped at 1). "Lots of people quoting it = more trusted."                                 |
| **Recency**            | 15%    | **0.5^(years_ago / 10)**. Newer = higher (e.g. 0 years ago = 1, 10 years = 0.5, 20 years = 0.25). If we don’t know the year, we use 0.5. "Newer evidence often counts more."      |
| **Source reputation**  | 10%    | Top journals (Nature, Science, Lancet, etc.) = 1.0; known publishers (Springer, Elsevier, etc.) = 0.7; else 0.5. "Famous journals and publishers get more trust."                 |


- **Final evidence score** = (0.30 × relevance) + (0.25 × study quality) + (0.20 × citations) + (0.15 × recency) + (0.10 × source).  
- **Simple analogy**: "We give each paragraph a report card: how on-topic it is, how good the kind of study is, how famous the source is, how new it is, and how much people cite it."

### 5. **Step 4: One answer from all the bits (aggregation)**

- We **only** use chunks the AI said SUPPORT or CONTRADICT (neutral chunks don’t add to the balance).  
- **TotalSupport** = sum of the evidence scores of all SUPPORT chunks.  
- **TotalContradict** = sum of the evidence scores of all CONTRADICT chunks.  
- **Final confidence number** = (TotalSupport − TotalContradict) / (TotalSupport + TotalContradict + a tiny number).  
  - Result is between −1 and +1. Positive = more support than contradiction; negative = more contradiction.
- **Simple analogy**: "We add up the report-card scores of everyone who said Yes, and everyone who said No. Then we see: did the Yes team or the No team score higher?"

### 6. **Step 5: The label you see (Strong / Moderate / Weak / …)**

- We turn the final confidence number into a word:
  - **≥ 0.75** → Strong  
  - **0.55 to &lt; 0.75** → Moderate  
  - **0.4 to &lt; 0.55** → Weak  
  - **&lt; 0.4** → Inconclusive  
  - If TotalContradict &gt; TotalSupport → we **always** say **Contradicted** (no matter the number).  
  - If we found **fewer than 3 chunks** → we say **Insufficient Evidence** and don’t pretend we’re sure.
- **Simple analogy**: "Like a teacher saying: You did great (Strong), You did okay (Moderate), You barely passed (Weak), or We can’t tell yet (Inconclusive). And if most evidence says the opposite, we say Contradicted."

### 7. **Safety rules (guardrails)**

- If there are **no chunks** at all: we don’t make up an answer.  
- If there are **fewer than 3 chunks**: we say "Insufficient Evidence."  
- If **contradiction total &gt; support total**: we always show **Contradicted**.

---

## Tone and style for the file

- Short sentences.  
- One idea per paragraph where possible.  
- Use "we" (we look at… we add… we say…).  
- Analogies in quotes (e.g. "Like finding the paragraphs…").  
- No formulas in the main narrative; optional "For the curious" line with the exact formula if you want.  
- No need to mention FAISS, embeddings, or LLM by name—"we turn the claim into a fingerprint," "we ask the AI," etc. is enough.

---

## Deliverable

- **Single file**: e.g. `docs/CLAIM_VERIFY_METRICS_SIMPLE.md`.  
- **Sections**: Title → What Claim Verify does → Step 1 (similarity) → Step 2 (classification) → Step 3 (evidence score + table) → Step 4 (aggregation) → Step 5 (labels) → Guardrails.  
- **No code/config edits**; only this new markdown file.

