# Intelligence Extraction — Testing Instructions

After implementing the intelligence extraction pipeline fixes:

## 1. Upload two related research papers

- Use the app’s PDF upload in the current workspace.
- Ensure both papers finish ingestion (chunks in FAISS and paper record in MongoDB).

## 2. Call the rebuild-intelligence endpoint

From a terminal (with auth token and workspace header):

```bash
# Replace YOUR_JWT and YOUR_WORKSPACE_ID
curl -X POST "http://localhost:8000/api/v1/debug/rebuild-intelligence" \
  -H "Authorization: Bearer YOUR_JWT" \
  -H "X-Workspace-Id: YOUR_WORKSPACE_ID" \
  -H "Content-Type: application/json"
```

Expected response:

```json
{
  "papers_processed": 2,
  "success_count": 2,
  "failure_count": 0
}
```

If `failure_count` > 0, check backend logs for the failing paper (e.g. missing PDF path or extraction error).

## 3. Check MongoDB

```bash
# If using MongoDB shell
mongosh
use Seagull
db.paper_intelligence.find().pretty()
```

Confirm for each document:

- `embedding_vector`: array of numbers, length > 0 (e.g. 384 for local, 1536 for OpenAI small).
- `keywords`: array with at least a few items.
- `methods_used`: array (can be empty but often has items).
- `workspace_id`: present and matches the workspace used for upload/rebuild.

## 4. Call the intelligence-status endpoint

```bash
curl -X GET "http://localhost:8000/api/v1/debug/intelligence-status" \
  -H "Authorization: Bearer YOUR_JWT" \
  -H "X-Workspace-Id: YOUR_WORKSPACE_ID"
```

Expected (for 2 papers, both with intel):

```json
{
  "total_papers": 2,
  "intelligence_docs": 2,
  "papers_with_embedding": 2,
  "papers_with_keywords": 2,
  "papers_with_methods": 2
}
```

Use this to verify system health: if `papers_with_embedding` or `papers_with_keywords` is lower than `total_papers`, some papers failed extraction or were not rebuilt.

## 5. Verify the graph

- Open the Graph page in the app (same workspace).
- You should see paper nodes and edges (similarity, keyword_overlap, or fallback links).
- If the graph still shows only nodes and no edges, check backend logs for “Graph intelligence” and “similarity_edges” / “total_links” to confirm the graph builder is receiving embeddings and links.

## Docker: OPENAI_API_KEY in container

- **docker-compose:** Ensure the backend service has `env_file: - .env` and `environment: - OPENAI_API_KEY=${OPENAI_API_KEY}`. Create `.env` in the project root with `OPENAI_API_KEY=sk-...`.
- **docker run:**  
  `docker run -e OPENAI_API_KEY=sk-your-key ... your_image`
- **Verify key inside container:**  
  `docker exec -it <backend_container_name> printenv | grep OPENAI`
- **Rebuild container after changing env:**  
  `docker-compose build backend && docker-compose up -d backend`  
  or  
  `docker build -t seagull-backend ./backend && docker run ...`

## Backend startup validation

If `OPENAI_API_KEY` is not set, the backend raises at startup:

```
RuntimeError: OPENAI_API_KEY is not set. Set it in the environment or in a .env file in the project root.
```

Fix by adding `OPENAI_API_KEY` to `.env` in the project root (or exporting it in the shell before starting the server).
