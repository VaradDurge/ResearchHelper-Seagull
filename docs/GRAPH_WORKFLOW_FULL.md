# Graph Workflow — End-to-End (Upload to Display)

This document describes **every step and factor** in the graph system: from uploading a paper to how nodes and connections are determined, including contradiction mode, unique concepts (research gap) in red, and all display logic.

---

## 1. Paper upload and what gets stored

### 1.1 Upload API

- **Endpoint:** `POST /api/v1/papers/`
- **Auth:** JWT required. Workspace comes from `X-Workspace-Id` header or the user’s active workspace in the DB.
- **Flow:**
  1. Validate PDF, size, non-empty.
  2. Save file to disk (`upload_dir`), generate a UUID `paper_id`.
  3. Call **ingestion** (`ingest_pdf`) with `pdf_path`, `paper_id`, `workspace_id`, `user_id`, `original_filename`.
  4. **Save paper** to MongoDB `papers` collection (title, authors, abstract, `workspace_id`, `paper_id`, upload_date, etc.).
  5. **Start background thread** for **intelligence extraction** (does not block the response).
  6. Broadcast `paper_added` over WebSocket to the workspace (excluding the uploader).

### 1.2 Ingestion (synchronous)

- **Service:** `ingestion_service.ingest_pdf`
- **Steps:**
  1. **Parse PDF** → page-wise text + metadata (title, authors, abstract).
  2. **Chunk text** per page (chunk_size, overlap) → list of `Chunk` (text, page_number, paper_id, chunk_index, …).
  3. **Generate embeddings** for all chunk texts (batch) → same count of vectors.
  4. **Vector DB (FAISS):**
     - For each chunk: `vector_id = "{paper_id}_chunk_{chunk_index}_page_{page_number}"`.
     - Metadata per vector: `paper_id`, `paper_title`, `user_id`, `workspace_id`, `page_number`, `text`, chunk fields.
  5. **Upsert** vectors into FAISS and **save index** to disk (`vector_db_path` + `.metadata`).

So after upload we have:

- **MongoDB `papers`:** one document per paper (`paper_id`, `workspace_id`, title, authors, abstract, metadata, upload_date, …).
- **FAISS index:** one vector per chunk; metadata includes `workspace_id`, `paper_id`, `page_number`, `text`.

### 1.3 Intelligence extraction (background, after upload)

- **Entry:** `intelligence_extraction.run_intelligence_extraction(paper_id, pdf_path, workspace_id, title, abstract)`
- **Steps:**
  1. Parse PDF again; get **abstract + conclusion** text via `get_abstract_and_conclusion_text`. If missing, prepend `abstract` from metadata if provided.
  2. **Paper-level embedding:** one vector for (abstract + conclusion) text — either local embedding model or OpenAI, depending on `paper_embedding_provider`. Stored only in MongoDB, not in FAISS.
  3. **LLM extraction:** prompt with title + text; JSON with `main_problem`, `methods_used`, `key_findings`, `datasets_used`, `keywords`, `domain`, `claims`.
  4. **Store in MongoDB `paper_intelligence`:** one document per paper: `paper_id`, `embedding_vector`, `main_problem`, `methods_used`, `key_findings`, `datasets_used`, `keywords`, `domain`, `claims`, `extracted_at`. Upsert by `paper_id`.

If extraction fails, we still upsert a minimal `paper_intelligence` document (e.g. empty fields) so the graph can later show the paper with fallbacks.

---

## 2. Claim verification and contradiction data

Contradiction edges in the **intelligence graph** come from **Claim Verify**, not from upload.

- **Endpoint:** `POST /api/v1/verification/claim` (body: claim text, optional paper_ids).
- **Flow:** Verification engine runs (retrieve chunks → score → classify each chunk as SUPPORT / CONTRADICT / NEUTRAL → aggregate). Result includes `contradict_count` and `scored_evidence`.
- **Persistence:** Each run is stored in MongoDB `claim_verifications`:
  - `workspace_id`, `user_id`, `claim`, `created_at`
  - `result`: full API response, including `contradict_count` and `scored_evidence`.
- **`scored_evidence`** is a list of objects. Each has:
  - `paper_id` (from chunk metadata)
  - `classification`: object with `classification`: `"SUPPORT"` | `"CONTRADICT"` | `"NEUTRAL"` (or legacy `label`).

The **intelligence graph** uses this collection only to build **contradiction edges** between papers (see Section 4.4).

---

## 3. Which graph is used: API and workspace

### 3.1 Frontend load order

1. **Workspace:** Graph runs only when `activeWorkspace?.id` is set and workspace has finished loading (no race with empty workspace).
2. **Request:** Frontend calls `GET /api/v1/graph/workspace/intelligence` with header `X-Workspace-Id: activeWorkspace.id`.
3. **Decision:**
   - If response has `has_intelligence === true` **and** `nodes.length > 0` → use **intelligence graph** (nodes + links from this API).
   - Otherwise → call `GET /api/v1/graph/workspace` with same header → use **simple graph** (nodes + links from this API, then frontend adds dense connections).

If the intelligence request fails (e.g. 401), the frontend falls back to the simple graph API. Stale responses are ignored when the user has switched workspace before the request completes.

### 3.2 Backend workspace and auth

- **Auth:** Both graph endpoints use `get_current_user_id` (JWT). Missing or invalid token → 401.
- **Workspace:** `get_current_workspace_id`:
  - If header `X-Workspace-Id` is present and the workspace exists and the user has access → use that ID.
  - Else → use the user’s **active workspace** from the DB (first with `is_active`, or first by creation date; if none, create default).

All graph queries (papers, intelligence, FAISS, claim_verifications) use this **same** `workspace_id`.

---

## 4. Simple graph (paper-only, citation + similarity)

Used when there is no intelligence data or the frontend falls back.

### 4.1 Data source

- **Nodes:** From MongoDB `papers`: `find({ workspace_id }).sort(upload_date, -1).limit(500)`. Each doc → one **paper node** (id = `paper_id`, label = title, type = `"paper"`, year from publication_date).
- **Links:** Built in code; nothing else is stored as “graph edges”.

### 4.2 Citation edges

- **DOI-based:** For each paper, read `metadata.references` / `metadata.cited_dois` / `metadata.dois_referenced` (list or string). For each cited DOI, if another paper in the workspace has that DOI, add a **citation** link (source = citing paper, target = cited paper).
- **Title-based (FAISS):** For each paper, collect chunk **text** from the **last few pages** (where references usually are) from FAISS metadata (same `workspace_id`). If paper A’s reference text **contains** paper B’s title (substring, B’s title ≥ 10 chars), add a **citation** link A → B.

### 4.3 Similarity edges

- **Centroids:** FAISS metadata is scanned for vectors with matching `workspace_id`; for each `paper_id`, vectors are averaged to get one **centroid** per paper. Papers with no vectors in that workspace get no centroid.
- **Pairs:** For every two papers that have centroids, **cosine similarity** is computed. If similarity ≥ **threshold** (configurable; can be set to 0 for testing), add a **similarity** link with `weight = round(sim, 4)`.
- **Fallback:** If there are ≥ 2 paper nodes but **no** links at all (e.g. no centroids), the backend adds a **similarity** link between every pair of papers (weight 0.7) so the graph is never empty.

### 4.4 Frontend “dense” connections (simple graph only)

- **Input:** Backend nodes + links (citation + similarity, plus any fallback).
- **buildDenseConnections:**
  - Keeps all backend links; assigns `distance` for force layout (e.g. similarity → 80 + (1−weight)*120).
  - **Same-year:** Papers with the same `year` get extra links of type **year_cluster** (weight 0.5, distance 120), up to a cap per node.
  - **Min connections:** Any node with &lt; 2 connections gets more **year_cluster** links (prefer same year, then any other node) until it has at least 2, again respecting cap.
- **Clustering:** Louvain community detection on the dense links → each node gets a `clusterId` (used for “Show Clusters” halo).
- **Filtering:** User can filter by edge type (All / Citation / Similarity / Year cluster) and by similarity threshold (≥ 0.65 or ≥ 0.75). Only links passing the filter are drawn.

Result: **Nodes** = papers; **links** = citation + similarity (from backend) + year_cluster (and min-connection) from frontend. **Display:** link color by type (citation blue, similarity purple, year_cluster green); link opacity/width by weight and highlight.

---

## 5. Intelligence graph (papers + methods + datasets + concepts)

Used when the intelligence API returns `has_intelligence === true` and at least one node.

### 5.1 When the backend returns “has intelligence”

- Load **papers** for the workspace (same as simple graph).
- Load **paper_intelligence** for those `paper_id`s. If **no** intelligence documents exist for any of those papers → return `nodes=[], links=[], has_intelligence=false` (frontend then uses simple graph).
- If at least one paper has a `paper_intelligence` document → we build the full intelligence graph and return `has_intelligence=true`.

### 5.2 Node types

- **Paper:** One node per paper; id = `paper_id`, label = title (truncated), type = `"paper"`, year; plus fields for the side panel: `main_problem`, `methods_used`, `key_findings`, `datasets_used`, `keywords`, `domain`, `claims`.
- **Method:** Deduplicated by normalized label (lowercase, collapsed spaces). id = `"method:{normalized}"`, label = original method name (up to 80 chars), type = `"method"`.
- **Dataset:** Same idea; id = `"dataset:{normalized}"`, type = `"dataset"`.
- **Concept:** From **keywords**; id = `"concept:{normalized}"`, type = `"concept"`, and a **paper_count** (how many papers use this concept). If **paper_count === 1** → that concept is marked **research gap** (`is_research_gap = true`) — “unique concept” of one paper.

### 5.3 Links (edges)

- **Paper → method:** `uses_method` — from `methods_used` (up to 15 per paper). Deduplicated globally by normalized method name.
- **Paper → dataset:** `uses_dataset` — from `datasets_used` (up to 10 per paper).
- **Paper → concept:** `has_concept` — from `keywords` (up to 15 per paper). When a link is added, the concept node’s `paper_count` is incremented. After all such links, any concept with `paper_count === 1` gets `is_research_gap = True`.
- **Paper–paper similarity:** From `paper_intelligence.embedding_vector`. Cosine similarity between every pair of papers that have a non-empty embedding. Threshold is configurable (e.g. 0.5 down to 0.25 in steps). Link type **similarity**, weight = round(sim, 4).
- **Paper–paper keyword overlap:** Keywords = LLM `keywords` **plus** title-derived words (length ≥ 4). For each pair of papers, overlap = size of intersection of normalized keyword sets. If overlap ≥ 1 (configurable) → **keyword_overlap** link, weight = min(1, overlap/10).
- **Paper–paper citation:** Same logic as simple graph (DOI in metadata + title-in-reference-text from FAISS). Link type **citation**.
- **Paper–paper contradiction:** From MongoDB **claim_verifications**. For each document in the workspace with `result.contradict_count > 0`, scan `result.scored_evidence`. Each item has `paper_id` and classification (SUPPORT / CONTRADICT / NEUTRAL). We collect `support_ids` and `contradict_ids` among papers in the workspace. For each pair (support_paper, contradict_paper) we add a **contradiction** link (weight 1.0). Deduplicated by unordered pair.
- **Guarantee:** If there are ≥ 2 papers and some paper has **no** paper–paper link (similarity, keyword_overlap, citation, or contradiction), we add one **keyword_overlap** link (weight 0.4) from that paper to the “best” other (by embedding similarity if available, else first other paper).
- **Dense guarantee (method/concept):** Each paper is ensured at least one **uses_method** edge (if it has any methods) and at least two **has_concept** edges (if it has keywords), by adding missing links to methods/concepts already in the graph.

### 5.4 Research gap (unique concept) — red display

- **Definition:** A **concept** node (from keywords) with **paper_count === 1** (only one paper in the workspace uses that keyword/concept).
- **Backend:** When building concept nodes and `has_concept` links, we increment each concept’s `paper_count`. After all links, we set `is_research_gap = True` for every concept where `paper_count == 1`.
- **Frontend:**
  - **Node drawing:** If the node has `is_research_gap === true` and is not hover/selected, we draw a **red halo** (circle at r+12, fill rgba(220,80,80,0.15), stroke rgba(220,80,80,0.4)). Then the normal node circle. If it’s a research-gap concept, we also draw a small **“1”** in red (top-right of node) to indicate “used by 1 paper.”
  - **Side panel:** When the selected node is a **concept** and `is_research_gap` is true, we show a red box: **“Unique concept — potential research gap”** and “Connected papers: 1”.

So “unique concept” = concept node with exactly one paper connected; it is **displayed in red** (halo + “1” badge + side-panel message).

---

## 6. Contradiction mode

- **Only in intelligence graph:** The “Contradiction mode” button is shown only when `useIntelligence` is true.
- **When OFF:** All link types are shown (similarity, citation, keyword_overlap, contradiction, uses_method, uses_dataset, has_concept). Contradiction links are still drawn in red and slightly thicker.
- **When ON:** **Only contradiction links** are shown. So the graph shows only paper–paper pairs that have a contradiction edge (one paper’s evidence supported the claim, another’s contradicted it, from claim verification runs).
- **Data source:** Same `claim_verifications` + `scored_evidence` as in Section 5.3; no extra API. The frontend just filters `intelligenceData.links` to `link.type === "contradiction"` when the toggle is on.

---

## 7. Frontend display details

### 7.1 Node appearance

- **Simple graph:** All nodes are papers. Radius grows with degree; high citation count adds extra radius. Color: default blue–grey; hover/selected brighter; others faded when something is highlighted. Cluster halo (when “Show Clusters” is on) uses a fixed palette by `clusterId`.
- **Intelligence graph:** Paper nodes larger (base 5 + degree/3); method 3.5, dataset 3, concept 2.5. **Concept** nodes with `is_research_gap` get the red halo and “1” badge as above. Same hover/selected and cluster halo behavior where applicable.

### 7.2 Link appearance

- **Colors (intelligence):** Contradiction = red (rgba(220,80,80,0.9)); similarity = purple; citation = blue; keyword_overlap = grey; others blue-grey.
- **Colors (simple):** Citation = blue; similarity = purple; year_cluster = green.
- **Opacity:** Default low; when either endpoint is in the **highlight set** (selected or hovered node + neighbors), links between two highlighted nodes get high opacity (and highlight color for non-contradiction).
- **Width:** Contradiction links thicker (3); others by weight (e.g. ≥0.75 → 2.5, ≥0.5 → 1.8, else 1.2). Highlighted links a bit thicker.

### 7.3 Side panel

- **Paper node (intelligence):** Year, main problem, methods, datasets, key findings (first 3), link to PDF view. If we have full paper from API, abstract snippet.
- **Paper node (simple):** Year, citation count, similarity count, link to PDF, “Zoom to cluster” if clusters are used.
- **Concept node:** If **research gap** → red box “Unique concept — potential research gap” and “Connected papers: 1”. List of connected **paper** nodes (names and links to PDF).

### 7.4 Fallback when intelligence has no links

If the intelligence API returns **nodes but 0 links** (e.g. no similarity/keyword/citation/contradiction and guarantee didn’t run or failed), the frontend builds **fallback** links so the graph is not disconnected:

- Consider only **paper** nodes (type === `"paper"`).
- Add **keyword_overlap** (weight 0.35) between papers in the same **year** (pairs within each year).
- Then ensure every paper has at least one link (connect to another paper if needed).

These are used only when the backend returned 0 links; they are drawn like normal links (grey for keyword_overlap).

---

## 8. End-to-end flow summary

| Stage | What happens |
|-------|------------------|
| **Upload** | PDF → ingestion (chunks, embeddings, FAISS + metadata with workspace_id, paper_id) → paper saved → background intelligence extraction (abstract+conclusion embedding + LLM → paper_intelligence). |
| **Claim Verify** | User runs claim verification → result (support/contradict counts, scored_evidence with paper_id + classification) stored in claim_verifications. |
| **Graph API choice** | Frontend requests intelligence API with X-Workspace-Id. If has_intelligence && nodes.length > 0 → intelligence graph; else simple graph API. |
| **Simple graph** | Papers by workspace_id → nodes. Citation (metadata DOI + title in FAISS text) + similarity (FAISS centroids by workspace_id, cosine ≥ threshold). Fallback: if 0 links and ≥2 nodes, add all pairs as similarity. Frontend: buildDenseConnections (year_cluster + min 2 links), cluster detection, edge filter. |
| **Intelligence graph** | Papers + paper_intelligence by paper_id → paper/method/dataset/concept nodes; paper_count on concepts; is_research_gap = (paper_count === 1). Links: uses_method, uses_dataset, has_concept, similarity (embedding_vector), keyword_overlap (keywords + title words), citation, contradiction (from claim_verifications scored_evidence). Guarantee: every paper has ≥1 paper–paper link. Dense: every paper gets ≥1 method and ≥2 concept links if data exists. |
| **Contradiction mode** | Intelligence only. Toggle filters links to type === "contradiction" (source: claim_verifications). |
| **Unique concept (red)** | Concept node with paper_count === 1 → is_research_gap. Frontend: red halo, “1” badge, side panel “Unique concept — potential research gap”. |
| **Display** | Force-directed layout; node/link colors and opacity by type and highlight; side panel by node type (paper vs concept); Show Clusters = cluster halo by clusterId (simple) or same (intelligence if clusters were computed). |

This is the full workflow from uploading a paper to how connections are determined and how the graph and contradiction mode and unique concepts in red are displayed.
