# Research Intelligence Graph — Architecture

## Overview

The Research Intelligence Graph is a semantic research topology built on an **intelligence extraction layer**. The graph does not recompute embeddings or run LLM at request time; it reads from stored data only.

---

## Phase 1 — Intelligence Extraction (Mandatory)

### 1. Embedding storage

- **When:** Triggered asynchronously after each paper upload (background thread).
- **Input:** Abstract + conclusion text (last 3 pages) from the PDF.
- **Provider:** Configurable `paper_embedding_provider`: `"local"` (sentence-transformers) or `"openai"` (text-embedding-3-small).
- **Storage:** MongoDB collection `paper_intelligence`, field `embedding_vector` (array of floats).
- **Important:** Embedding is computed once at upload; never recomputed for graph requests.

### 2. Structured semantic extraction

- **When:** Same background run as embedding, after parsing the PDF.
- **LLM:** Uses existing `openai_model` (e.g. gpt-4o-mini) with a strict JSON extraction prompt.
- **Output:** `main_problem`, `methods_used[]`, `key_findings[]`, `datasets_used[]`, `keywords[]`, `domain`, `claims[]`.
- **Storage:** Same `paper_intelligence` document; no extra collections.

### 3. Background job handling

- No separate queue: from the Papers API, after `save_paper()`, a **daemon thread** is started that calls `run_intelligence_extraction(paper_id, pdf_path, workspace_id, title, abstract)`.
- Upload response is returned immediately; extraction runs in the background.
- On paper delete, the corresponding `paper_intelligence` document is removed.

---

## Phase 2 — Graph data builder

### buildWorkspaceGraph(workspace_id)

- **Location:** `backend/app/services/intelligence_graph_service.py`.
- **Input:** Workspace ID (and optional user_id).
- **Output:** `(nodes, links, has_intelligence)`.

**Steps:**

1. Load papers for workspace (cap 500).
2. Load `paper_intelligence` for those paper IDs. If none exist, return `has_intelligence=False` (frontend falls back to simple graph).
3. **Paper nodes:** One per paper; optional payload for side panel (`main_problem`, `methods_used`, etc.).
4. **Method / dataset / concept nodes:** Deduplicated globally (e.g. one node per method name).
5. **Edges:**
   - Paper → Method, Paper → Dataset, Paper → Concept (from extracted arrays).
   - Paper ↔ Paper: **similarity** (cosine on stored embeddings, threshold ≥ 0.7, relaxed if needed), **citation** (DOI + title from existing logic), **keyword_overlap** (≥ 2 shared keywords).
   - **Contradiction:** From `claim_verifications` collection; when a run has both supporting and contradicting evidence, add a red contradiction edge between those papers.
6. **Research gap:** Concepts with `paper_count == 1` are marked `is_research_gap`.
7. **Dense guarantee:** Each paper gets at least 1 method edge, 2 concept edges, and at least 1 similarity/citation/keyword edge when possible (threshold relaxed for similarity).

---

## API

- **GET /api/v1/graph/workspace**  
  Existing simple graph (papers + citation + similarity + year_cluster). Used when intelligence is not available.

- **GET /api/v1/graph/workspace/intelligence**  
  Returns `IntelligenceGraphResponse`: `nodes`, `links`, `has_intelligence`.  
  If `has_intelligence` is false or no nodes, frontend uses the simple graph.

---

## Frontend behaviour

- **Route:** Same `/graph` page.
- **Load:** Call `getGraphWorkspaceIntelligence()` first. If `has_intelligence && nodes.length > 0`, use the intelligence graph; otherwise call `getGraphWorkspace()` and use the existing simple graph (unchanged behaviour).
- **Intelligence mode:**
  - **Node types:** paper (larger), method, dataset, concept (smaller). Concept with `is_research_gap` has red halo and badge.
  - **Edge types:** similarity (purple), citation (blue), keyword_overlap (gray), contradiction (red, thick).
  - **Toggles:** “Contradiction mode” (only contradiction edges), “Show Clusters” (cluster coloring).
  - **Side panel:** For a **paper**, show main problem, methods, datasets, key findings, Open Paper. For a **concept**, show connected papers and “Unique concept — potential research gap” when applicable.
- **Physics:** charge -250, linkStrength 0.6, velocityDecay 0.25, cooldownTicks 150; canvas rendering, memoized data, resize debounced via single state.

---

## Mongo schema (paper_intelligence)

- `paper_id` (str)
- `embedding_vector` (array of float, optional)
- `main_problem` (str, optional)
- `methods_used`, `key_findings`, `datasets_used`, `keywords`, `claims` (arrays of str)
- `domain` (str, optional)
- `extracted_at` (datetime, optional)

No change to existing `papers` or other collections.

---

## Testing strategy

1. **Extraction:** Upload a PDF, wait a few seconds, then check `paper_intelligence` for that `paper_id` (embedding + extracted fields).
2. **Graph API:** With at least one paper that has intelligence data, call `GET /api/v1/graph/workspace/intelligence` and assert `has_intelligence` true, non-empty nodes/links, and paper nodes with `main_problem` / `methods_used` when present.
3. **Fallback:** Use a workspace with no `paper_intelligence` documents; assert `has_intelligence` false and that the frontend shows the simple graph.
4. **Contradiction:** Run claim verification so one paper supports and another contradicts a claim; reload intelligence graph and assert a contradiction edge between those papers.
5. **Research gap:** With one concept used by only one paper, assert that concept node has `is_research_gap` and that the UI shows the research-gap indicator and side panel text.

---

## Config

- `paper_embedding_provider`: `"local"` | `"openai"`.
- `openai_embedding_model`: e.g. `"text-embedding-3-small"` (used when provider is openai).
- Existing `openai_api_key`, `openai_model` for LLM extraction.
