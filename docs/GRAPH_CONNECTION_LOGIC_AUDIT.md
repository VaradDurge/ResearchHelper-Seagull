# Graph Connection Logic — Audit & Semantic Standard

## STEP 1 — All Connection Rules (Before Fix)

### Simple graph (`graph_service.build_graph`)

| Rule | Condition | Current value | Location |
|------|-----------|---------------|----------|
| **Citation** | Paper A metadata references DOI of Paper B | — | `_cited_dois_from_metadata` + `doi_to_ids` |
| **Title citation** | Paper A reference text (last N pages) contains Paper B title | — | `_add_title_citation_edges_from_index` |
| **Embedding similarity** | `cosine(centroid_a, centroid_b) >= threshold` | **0.0** (effectively off) | `SIMILARITY_THRESHOLD = 0.0` |
| **Fallback (aggressive)** | If `len(links) == 0`: connect **every** paper pair with fake similarity 0.7 | Always when no other links | `if len(nodes) >= 2 and len(links) == 0` |

### Intelligence graph (`intelligence_graph_service.build_workspace_graph`)

| Rule | Condition | Current value | Location |
|------|-----------|---------------|----------|
| **Similarity** | `cosine(embedding_a, embedding_b) >= threshold` | **0.0** initial, then lowered by 0.05 until edges appear | `SIMILARITY_THRESHOLD_INITIAL = 0.0`, loop down to `SIMILARITY_THRESHOLD_MIN = 0.0` |
| **Keyword overlap** | `|keywords_a ∩ keywords_b| >= KEYWORD_OVERLAP_MIN` | **1** | `KEYWORD_OVERLAP_MIN = 1` |
| **Keywords source** | Intel keywords + **title words** (length >= 4, no stopwords) | Title adds generic words | `_title_to_keywords` + intel `keywords` |
| **Citation** | Same as simple (DOI refs + title-in-refs) | — | `_cited_dois_from_metadata` |
| **Contradiction** | Claim verification: SUPPORT vs CONTRADICT pair | — | `_get_contradiction_edges` |
| **Fallback guarantee** | If paper has **zero** paper–paper links: connect to “best” by similarity, or **first other paper** | Creates fake edges | “Guarantee: every paper has at least one paper–paper link” |

**No** document-type classification (research vs LOR vs resume). All documents use the same embedding and keyword overlap.

---

## STEP 2 — Logical Weaknesses

- **Very weak similarity threshold (0.0)**  
  Any non-negative similarity connects papers → unrelated docs (e.g. LOR vs Neural Network) can link.

- **Overlap >= 1**  
  One shared word (e.g. “application”, “development”) is enough → meaningless links.

- **Generic keyword contamination**  
  Title words like “development”, “application”, “research”, “learning”, “system”, “method” appear across domains; overlap is not semantic.

- **Title word extraction naive**  
  Only filters by length >= 4; no academic stopword list.

- **Fallback connection logic**  
  - Simple: if no links at all, connect every pair with weight 0.7 → full clique.  
  - Intelligence: if a paper has no paper–paper link, connect to “best” similarity or first other paper → artificial density.

- **No document-type layer**  
  Resumes, LORs, and research papers all in same embedding/keyword network → LOR can connect to ML papers via generic words or low similarity.

---

## STEP 3 — Correct Semantic Standard

A **paper–paper connection** should exist **only** if at least one of:

1. **Embedding similarity > 0.70**
2. **Meaningful keyword overlap >= 3** (after removing academic stopwords / corpus junk)
3. **Direct citation** (DOI or title-in-references)
4. **Verified contradiction** (claim verification SUPPORT vs CONTRADICT)

**Not** sufficient on their own:

- Same year  
- Same upload date  
- One weak/generic keyword  
- Fallback “ensure at least one link” or “connect isolated node”

---

## STEP 4 — Fallback Philosophy

- **Before:** “Connect isolated node to something” (guarantee at least one link).  
- **After:** “Isolated nodes remain isolated.” Disconnected nodes are acceptable; no forced density.

---

## STEP 5 — Non-Research Documents (Future)

- Add classification: research paper vs resume vs letter vs personal.  
- If type != research: exclude from embedding-similarity network; allow only direct textual overlap (e.g. LOR ↔ Resume) if desired.  
- Not implemented in this pass; logic is prepared for stricter thresholds so research-only connections are meaningful.

**If LOR still connects to Neural Network after strict filtering:** embeddings may be polluted by generic/biography text. Restrict embedding input to **abstract only** (exclude acknowledgements, references, full-body LOR text). This is a semantic/threshold and input-scope issue, not a UI issue.

---

## STEP 6 — Keyword Hygiene

- Before overlap count: remove **academic stopwords** and **high-frequency generic** terms (e.g. development, application, analysis, research, learning, system, method).  
- Only **meaningful, domain-specific** tokens count.  
- Implemented via `_ACADEMIC_STOPWORDS` and `_meaningful_keywords()` in intelligence graph.

---

## STEP 7 — Recomputed Graph Decision (Implemented)

**Connect A–B only if:**

- `similarity_score > 0.70` **OR**
- `meaningful_keyword_overlap >= 3` **OR**
- `citation_exists` **OR**
- `contradiction_exists`

**No** fallback, no year cluster, no forced density.

---

## STEP 8 — Expected After Strict Logic

- **LOR_Draft** ↔ **Varad_RESUME**: only if we add explicit “textual overlap” or document-type rule (e.g. both non-research); otherwise may stay isolated.  
- **LOR_Draft** ↔ **Neural Network paper**: **no** connection (no strong similarity, no 3+ meaningful keywords, no citation, no contradiction).  
- **Neural Network paper**: connects only to ML-relevant papers (high similarity or real keyword overlap).

---

## STEP 9 — Graph Philosophy

- Graph should represent **semantic truth**, not visual completeness.  
- Sparse, possibly disconnected nodes are acceptable.  
- Academic graphs are sparse by nature.
