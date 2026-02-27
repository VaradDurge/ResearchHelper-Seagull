# Graph Page – Integration

## Overview

The **Graph** page is a global knowledge graph of uploaded papers in the active workspace, with an Obsidian-style dark graph view. It does not depend on claim verification and does not modify any existing backend schema or features.

## Route

- **Frontend:** `/graph`
- **Backend:** `GET /api/v1/graph/workspace` (requires JWT + `X-Workspace-Id` header)

## Backend

- **Router:** `backend/app/api/v1/graph.py` – registered under prefix `/graph`.
- **Service:** `backend/app/services/graph_service.py` – builds nodes (papers) and links (citation + similarity).
- **Vector DB:** `get_paper_centroids()` in `backend/app/core/vector_db.py` – used only for similarity edges; no schema change.
- **Schemas:** `GraphNode`, `GraphLink`, `GraphResponse` in `backend/app/models/schemas.py`.

## Frontend

- **Page:** `frontend/app/(dashboard)/graph/page.tsx`
- **API:** `frontend/lib/api/graph.ts` – `getGraphWorkspace()`
- **Types:** `frontend/types/graph.ts`
- **Nav:** New item **Graph** (icon: Workflow) in `frontend/lib/constants/nav-items.ts` pointing to `/graph`.

## Data

- **Nodes:** One per paper (id, label, type `"paper"`, optional year, optional `embedding_cluster`).
- **Links:**
  - **Citation:** From `metadata.references` / `metadata.cited_dois` / `metadata.dois_referenced` (if present) to papers with matching DOI.
  - **Similarity:** Embedding centroid similarity between papers in the workspace; threshold `> 0.75`; `weight` = similarity score.
- **Cap:** 500 nodes per workspace.

## Behaviour

- **Physics:** Strong repulsion, medium link strength, slow cooling, high damping (Obsidian-like).
- **Interactions:** Zoom (wheel), pan (drag background), drag nodes, hover (highlight neighbours, fade others), click (select + right panel), “Fit view” resets zoom.
- **Side panel:** Title, year, citation/similar counts, abstract preview, “Open Paper” → `/pdf?id=<paper_id>`.

## Dependencies

- **Frontend:** `react-force-graph-2d` (already in `package.json`).
- **Backend:** No new packages; uses existing FAISS, MongoDB, and workspace auth.

## Optional Enhancements (not implemented)

- Color nodes by folder/workspace or by cluster (e.g. Louvain) via a toggle; default remains the current Obsidian-style view.
