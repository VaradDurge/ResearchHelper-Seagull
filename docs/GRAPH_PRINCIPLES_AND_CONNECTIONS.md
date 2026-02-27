# How the Graphs Are Resulted — Principles and Connections (In Depth)

This doc explains **on what principles** the graphs work, **how connections are made**, and **how the final result is produced** from data to screen.

---

## 1. Two graph modes and when each is used

The app has **two graph backends**. The frontend chooses one per load:

| Mode | When used | What it shows |
|------|-----------|----------------|
| **Intelligence graph** | API `GET /graph/workspace/intelligence` returns `has_intelligence: true` **and** at least one node | Papers + methods + datasets + concepts; many link types (similarity, keyword overlap, citation, contradiction, uses_method, uses_dataset, has_concept). |
| **Simple graph** | Otherwise (no intelligence data, or API failure) | Papers only; citation + similarity (+ frontend-added year_cluster). |

**Principle:** The graph is **not** a pre-stored network. It is **computed on demand** from:

- **Simple:** MongoDB `papers` + FAISS (chunk metadata + centroids).
- **Intelligence:** MongoDB `papers` + `paper_intelligence` + (for contradiction) `claim_verifications`; optionally FAISS for citation-by-title.

So "how the graph is resulted" = **which API runs** → **which service builds nodes/links** → **what the frontend draws**.

---

## 2. Core principles

1. **Workspace scoping**  
   Every graph is for **one workspace**. Nodes and links are built only from data that belongs to that `workspace_id` (papers, intelligence docs, claim runs, FAISS metadata).

2. **Nodes = entities; links = relationships**  
   - **Simple:** Nodes = papers. Links = “cites” or “is similar to”.
   - **Intelligence:** Nodes = papers + methods + datasets + concepts. Links = “uses method”, “uses dataset”, “has concept”, “similar to”, “keyword overlap”, “cites”, “contradicts”.

3. **No stored “graph” table**  
   Edges are **derived** each time from:
   - Paper metadata (DOI, references),
   - Embeddings (FAISS chunk centroids for simple; paper-level embeddings in `paper_intelligence` for intelligence),
   - Extracted fields (keywords, methods, datasets for intelligence),
   - Claim verification results (for contradiction only).

4. **Density and fallbacks**  
   So that the graph is never a set of isolated points:
   - **Simple:** Backend can add fallback similarity links between all papers if there are no links; frontend then adds **year_cluster** and **minimum 2 connections** per node.
   - **Intelligence:** Backend guarantees **at least one paper–paper link** per paper when there are ≥2 papers (link to “nearest” by embedding or first other paper).

---

## 3. Simple graph — how it is resulted

### 3.1 Node set

- **Source:** `papers` collection, `find({ workspace_id }).sort(upload_date, -1).limit(500)`.
- **One node per paper:** `id = paper_id`, `label = title`, `type = "paper"`, `year` from publication_date (first 4-digit year in string).

So the **set of nodes** is exactly the set of papers in the workspace (up to 500).

### 3.2 Connection 1: Citation (DOI-based)

- **Principle:** “Paper A cites paper B” if A’s **metadata** says it references B’s **DOI**.
- **How:**
  1. Build a map: DOI → list of paper IDs (from each paper’s `doi` in the workspace).
  2. For each paper A, read `metadata.references` / `metadata.cited_dois` / `metadata.dois_referenced` (list or comma/semicolon-separated string).
  3. For each cited DOI, look up which workspace papers have that DOI.
  4. For each such paper B (B ≠ A), add a **citation** link: source = A, target = B.
- **Data source:** Only MongoDB paper documents (metadata). No FAISS here.

### 3.3 Connection 2: Citation (title-based, from FAISS)

- **Principle:** “Paper A cites paper B” if the **text of A’s last few pages** (where references usually are) **contains B’s title** as a substring.
- **How:**
  1. From FAISS **metadata** (not the vectors), for the given `workspace_id`, collect per paper the **text** of chunks that lie in the **last few pages** (e.g. last 4 pages) of that paper.
  2. Build a map: paper_id → concatenated reference-region text (lowercased).
  3. For each pair (A, B), A ≠ B: if B’s title (≥ 10 chars, lowercased) is a **substring** of A’s reference text, add **citation** A → B.
- **Data source:** FAISS chunk metadata (`workspace_id`, `paper_id`, `page_number`, `text`). No vector search.

### 3.4 Connection 3: Similarity (simple graph)

- **Principle:** “Paper A is similar to paper B” if their **semantic representations** are close. Representation = **centroid** of all chunk embeddings of that paper in FAISS (same workspace).
- **How:**
  1. **Centroids:** For each vector in FAISS metadata with matching `workspace_id`, get the vector by index, group by `paper_id`, and **average** the vectors per paper → one centroid per paper.
  2. For every **pair** of papers that have a centroid, compute **cosine similarity** between the two centroids.
  3. If similarity ≥ **threshold** (e.g. 0.75, or 0 for “show all”), add a **similarity** link with `weight = round(sim, 4)`.
- **Data source:** FAISS index (vectors) + metadata (workspace_id, paper_id). So **chunk-level embeddings** (from ingestion) are what drive this; no `paper_intelligence` here.

### 3.5 Fallback (simple graph)

- If after the above there are **≥ 2 nodes** but **zero links** (e.g. no centroids, no citations), the backend adds a **similarity** link between **every pair** of papers (weight 0.7) so the graph always has some edges.

### 3.6 Frontend “dense” layer (simple graph only)

- **Input:** Backend response = list of nodes + list of links (citation + similarity + fallback).
- **buildDenseConnections** (frontend):
  1. Keep all backend links; assign `distance` for the force layout (e.g. similarity → 80 + (1−weight)×120).
  2. **Same-year:** For each publication **year**, connect every pair of papers with that year by an extra link of type **year_cluster** (weight 0.5), subject to a cap per node.
  3. **Minimum degree:** For any node with &lt; 2 connections, add **year_cluster** links to other nodes (prefer same year) until it has at least 2, again with a cap.
- **Clustering:** Louvain community detection on this dense link set → each node gets a `clusterId` (for “Show Clusters”).
- **Filtering:** User can restrict to “Citation”, “Similarity”, or “Year cluster”; similarity links can be filtered by a minimum weight (e.g. ≥ 0.65). Only links that pass the filter are drawn.

So for **simple graph**, the “result” is:  
**Backend** (nodes from papers, links from DOI citation + title citation + centroid similarity + fallback) → **Frontend** (dense year_cluster + min 2 links, clustering, filter) → **Force-directed layout** → **Screen**.

---

## 4. Intelligence graph — how it is resulted

### 4.1 Node set

- **Papers:** Same as simple (from `papers` by `workspace_id`), but each node carries extra fields from `paper_intelligence` (main_problem, methods_used, key_findings, datasets_used, keywords, domain, claims) for the side panel.
- **Methods:** Deduplicated by **normalized label** (lowercase, collapsed spaces). One node per unique method string; id like `method:normalized_label`, type `"method"`.
- **Datasets:** Same idea; id `dataset:normalized_label`, type `"dataset"`.
- **Concepts:** From **keywords**; id `concept:normalized_label`, type `"concept"`. Each concept node has a **paper_count** = how many papers have that keyword. If **paper_count === 1**, the node is marked **research gap** (unique concept).

Only papers that have at least one **valid** `paper_intelligence` document (with `workspace_id` and at least embedding or keywords or main_problem) are used. Methods/datasets/concepts are created from those papers’ extracted data.

### 4.2 Paper–entity connections (paper → method, dataset, concept)

- **uses_method:** From `paper_intelligence.methods_used`. For each method string (up to 15 per paper), ensure a method node exists, then add link paper → method.
- **uses_dataset:** From `paper_intelligence.datasets_used` (up to 10 per paper).
- **has_concept:** From `paper_intelligence.keywords` (up to 15 per paper). For each keyword, ensure a concept node exists, add link paper → concept, and increment that concept’s **paper_count**. After all links, any concept with **paper_count === 1** gets **is_research_gap = true**.

So **connections** here mean: “this paper **uses** this method/dataset” and “this paper **has** this concept (keyword)”. Principles: **extraction-driven** (LLM output) and **deduplication by normalized label**.

### 4.3 Paper–paper connection 1: Similarity (intelligence)

- **Principle:** Same idea as simple — “semantically similar” — but the representation is the **paper-level embedding** stored in `paper_intelligence` (from abstract+conclusion), **not** FAISS chunk centroids.
- **How:**
  1. Collect `embedding_vector` from each `paper_intelligence` doc (same workspace) that has a non-empty vector.
  2. For every pair of papers that have an embedding, compute **cosine similarity**.
  3. If similarity ≥ **threshold** (starts at 0.5, can step down to 0.25), add **similarity** link with weight = round(sim, 4).
- **Data source:** Only `paper_intelligence.embedding_vector`. FAISS is not used.

### 4.4 Paper–paper connection 2: Keyword overlap (intelligence)

- **Principle:** “Paper A and paper B share thematic terms” → link them. Terms = LLM **keywords** plus **title-derived** words (length ≥ 4).
- **How:**
  1. For each paper, build a set of normalized keywords (from `paper_intelligence.keywords`) and add significant words from the **title**.
  2. For each pair of papers, **overlap** = size of intersection of these sets.
  3. If overlap ≥ **1** (configurable), add **keyword_overlap** link with weight = min(1, overlap/10).
- **Data source:** `paper_intelligence.keywords` + paper title. So connections are driven by **extracted + title** terms.

### 4.5 Paper–paper connection 3: Citation (intelligence)

- **Principle:** Same as simple — DOI in metadata + title in reference text.
- **How:** Same logic as simple graph (DOI map + FAISS last-pages text). Link type **citation**.

### 4.6 Paper–paper connection 4: Contradiction (intelligence)

- **Principle:** “Paper A and paper B disagree on a claim” when, in a **claim verification** run, some evidence from A was classified **SUPPORT** and some from B **CONTRADICT** (or vice versa).
- **How:**
  1. From MongoDB `claim_verifications`, take runs for this `workspace_id` (e.g. latest 200).
  2. Keep only runs where `result.contradict_count > 0`.
  3. For each run, scan `result.scored_evidence`: each item has `paper_id` and classification (SUPPORT / CONTRADICT / NEUTRAL). Build two sets: `support_ids`, `contradict_ids` (paper IDs in the workspace).
  4. For each (support_paper, contradict_paper), add a **contradiction** link (weight 1.0), deduplicated by unordered pair.
- **Data source:** Only `claim_verifications` (from the Claim Verify feature). No embeddings or extraction here.

### 4.7 Guarantee: at least one paper–paper link per paper

- **Principle:** Avoid isolated paper nodes when there are at least 2 papers.
- **How:** After all the above links, for each paper that still has **zero** paper–paper links (similarity, keyword_overlap, citation, contradiction), add one **keyword_overlap** link to the “best” other paper (by embedding similarity if both have embeddings, else first other paper).

### 4.8 Dense guarantee (methods/concepts)

- Each paper is ensured **at least one** **uses_method** edge (if it has any methods) and **at least two** **has_concept** edges (if it has keywords), by adding missing links to methods/concepts already in the graph.

### 4.9 How the intelligence graph is “resulted”

- **Backend:** Build paper + method + dataset + concept nodes; add all link types above; set **research_gap** on concepts with paper_count 1. Return nodes + links + `has_intelligence: true`.
- **Frontend:** If the backend returned 0 links but ≥2 paper nodes, it can add **fallback** links (e.g. same-year or min 1 connection) so something is drawn. Then force-directed layout, colors by type, side panel by node type.
- **Contradiction mode:** When toggled on, the frontend **filters** the same link list to only **contradiction** links; the underlying data and principles are unchanged.

So for **intelligence graph**, the result is:  
**Backend** (nodes from papers + extracted methods/datasets/concepts, links from similarity + keyword_overlap + citation + contradiction + guarantees) → **Frontend** (optional fallback if 0 links, filter for contradiction mode) → **Layout** → **Screen**.

---

## 5. Summary: principles and data flow

| Principle | Simple graph | Intelligence graph |
|-----------|--------------|---------------------|
| **What is a node?** | Paper only. | Paper + method + dataset + concept. |
| **What is a connection?** | “Cites” (DOI or title) or “similar to” (centroid). | “Uses method/dataset”, “has concept”, “similar to”, “keyword overlap”, “cites”, “contradicts”. |
| **Where do links come from?** | Paper metadata + FAISS (text + centroids). | `paper_intelligence` (embeddings, keywords, methods, datasets) + paper metadata + FAISS (citation) + `claim_verifications`. |
| **How is “similar” defined?** | Cosine similarity of **chunk centroids** (FAISS). | Cosine similarity of **paper-level embeddings** (MongoDB). |
| **How are “related” papers connected beyond similarity?** | Citation (DOI/title). Frontend adds year_cluster + min 2 links. | Keyword overlap, citation, contradiction; backend guarantee + optional frontend fallback. |
| **What ensures no isolated nodes?** | Backend fallback (all-pairs similarity if 0 links) + frontend year_cluster and min 2 links. | Backend guarantee (one paper–paper link per paper) + frontend fallback if 0 links. |

So: **graphs are resulted** by (1) choosing the backend (intelligence vs simple) from the workspace and presence of valid `paper_intelligence`, (2) computing nodes and links from the tables and indexes above using these rules, and (3) letting the frontend add density/fallbacks and layout so that the final picture is a connected, interpretable graph of papers (and optionally methods/datasets/concepts) and their relationships.
