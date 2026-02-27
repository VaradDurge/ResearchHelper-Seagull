# How the Graph Works — Example Walkthrough

This doc explains **when you see dots (nodes) and when you see lines (edges)** between them, using a simple example.

---

## Example: You have 3 uploaded papers

| Paper | Title           | Year | In metadata                    |
|-------|-----------------|------|---------------------------------|
| A     | "Deep Learning" | 2023 | (nothing special)               |
| B     | "Neural Nets"   | 2023 | (nothing special)               |
| C     | "AI Survey"      | 2022 | (nothing special)               |

---

## Step 1: What the **backend** returns

The API `GET /api/v1/graph/workspace` only creates edges from:

1. **Citations**  
   "Paper X cites Paper Y" → only if Paper X has a list of DOIs it references **and** one of those DOIs is Paper Y’s DOI.  
   In our example, none of the papers have that list in metadata → **0 citation edges**.

2. **Similarity**  
   "Paper X is very similar to Paper Y" → only if the **embedding similarity** between the two papers is **≥ 0.75**.  
   In our example, assume A–B are a bit similar (0.7) and C is different → **0 similarity edges** (none above 0.75).

So the API returns:

- **Nodes:** A, B, C (3 dots)
- **Links:** [] (empty)

You would see **3 dots and no lines** if we stopped here.

---

## Step 2: What the **frontend** adds (dense connections)

The frontend runs `buildDenseConnections` so that the graph is not empty:

1. **Same year**  
   Papers with the same **year** get a link of type `year_cluster`.  
   - A and B are both 2023 → add edge **A–B** (year_cluster).  
   - C is 2022 → no other 2022 paper → no extra edge from “same year” for C.

2. **Minimum 2 connections per node**  
   Any node with fewer than 2 connections gets more links until it has at least 2.  
   - A: has 1 link (A–B) → add one more → e.g. **A–C**.  
   - B: has 1 link (A–B) → add one more → e.g. **B–C**.  
   - C: now has 2 links (A–C, B–C) → no need to add more.

After this step the graph has:

- **Nodes:** A, B, C
- **Links:** A–B (year_cluster), A–C (year_cluster), B–C (year_cluster)

So you **should** see **3 dots and 3 lines** (a triangle), as long as the UI is not filtering edges out.

---

## Step 3: What **you** see on the screen

- The **dots** = papers (nodes).
- The **lines** = connections (edges). Each line is one of:
  - **Citation** (blue) — “this paper cites that paper” (from backend).
  - **Similarity** (purple) — “these papers are very similar” (from backend).
  - **Year cluster** (green) — “same publication year” or “we added this so the graph isn’t empty” (from frontend).

If you see **no lines** even though you have 2+ papers:

1. **Check the “Edge type” dropdown** (top-left).  
   If it is **“Citation”** or **“Similarity”**, only those types are shown.  
   In our example we only have **year_cluster** edges → set it to **“All edges”** or **“Year cluster”** to see the triangle.

2. **Papers with no year**  
   If all 3 papers had no `publication_date` (so no year), the “same year” step adds nothing, but the “min 2 connections” step still adds links between all of them. So you should still get lines (e.g. A–B, A–C, B–C).

---

## Quick reference

| You see…              | Meaning |
|-----------------------|--------|
| 1 dot                 | 1 paper in the workspace. No lines possible. |
| 3 dots, no lines      | Filter might be “Citation” or “Similarity” only; switch to “All edges” or “Year cluster”. Or a bug in drawing (e.g. edges at 0,0). |
| 3 dots, 3 lines       | Normal: each paper has at least 2 connections (e.g. triangle). |
| Many dots, many lines | Many papers; citation/similarity/year and “min 2 connections” create a dense graph. |

---

## One-sentence summary

**Dots = papers; lines = "cites", "very similar", or "same year / we added so everyone has at least 2 connections".** If you see dots but no lines, set the edge filter to **"All edges"** or **"Year cluster"** first; if it's still empty, the next thing to fix is how edges are drawn (so they use the correct node positions).

---

## Graph workflow and dependencies

### Request flow

1. **Frontend** (Graph page) waits until `activeWorkspace` is set and workspace loading is done, then calls:
   - `GET /api/v1/graph/workspace/intelligence` with header `X-Workspace-Id: <activeWorkspace.id>`
   - If response has `has_intelligence: true` and at least one node → use **intelligence graph** (paper/method/dataset/concept nodes and edges).
   - Otherwise → `GET /api/v1/graph/workspace` with same header → **simple graph** (papers + citation/similarity/year_cluster).

2. **Backend** resolves workspace via `get_current_workspace_id`: uses `X-Workspace-Id` if present and valid for the user, else the user’s active workspace in the DB. Both graph endpoints require auth (`get_current_user_id`).

### Backend dependencies

| Piece | Depends on |
|-------|------------|
| **Simple graph** (`graph_service.build_graph`) | `papers` collection (query by `workspace_id`), optional: FAISS vector DB (centroids for similarity), optional: vector DB metadata (title-based citation from chunk text). |
| **Intelligence graph** (`intelligence_graph_service.build_workspace_graph`) | `papers` (by `workspace_id`), `paper_intelligence` (by `paper_id`), optional: `claim_verifications` (contradiction edges). |

- If there are **no papers** for that `workspace_id`, both APIs return empty nodes (and intelligence returns `has_intelligence: false`).
- Simple graph still returns **nodes** when papers exist even if vector DB is missing or has no centroids (only similarity/title-citation edges are skipped).

### Frontend dependencies

- **Workspace**: Graph runs only when `activeWorkspace?.id` is set and `workspaceLoading` is false. Graph API calls pass this `id` explicitly so the requested workspace always matches the UI.
- **Stale responses**: Each load captures the current workspace id; if the user switches workspace before the request finishes, the response is ignored so the graph doesn’t show data for the wrong workspace.
- **Empty intelligence links**: Intelligence graph can have nodes but no links (e.g. one paper). The UI still shows those nodes with degree 0.
- **Malformed API responses**: `nodes`/`links` are normalized to arrays so missing or null values don’t crash the UI.
