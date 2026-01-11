"""
# Literature Cleanup API Endpoint

## What it does:
FastAPI route handler for literature cleanup tool. Groups papers by similarity and deduplicates references.

## How it works:
- Defines POST endpoint for literature cleanup
- Uses dependency injection for database session and authentication
- Calls literature_cleaner tool for business logic
- Returns grouped papers and trends

## What to include:
- POST /tools/literature-cleanup
  - Request body: paper_ids (List[str]), options (similarity_threshold, enable_deduplication)
  - Response: GroupedPapers with: groups, deduplicated_references, trends, summaries
  - Calls: tools.literature_cleaner.cleanup_literature()
  - Uses embeddings to calculate similarity between papers
"""

