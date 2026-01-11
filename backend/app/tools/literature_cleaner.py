"""
# Literature Cleaner Tool

## What it does:
Groups papers by similarity, deduplicates references, and identifies trends.
Uses embeddings to calculate similarity between papers.

## How it works:
- Calculates pairwise similarity between papers using embeddings
- Groups papers by similarity threshold
- Deduplicates references across papers
- Identifies trends and patterns
- Generates summaries for each group

## What to include:
- cleanup_literature(paper_ids: List[str], options: CleanupOptions) -> GroupedPapers
  - Gets embeddings/representations for each paper
  - Calculates pairwise similarity matrix
  - Groups papers by similarity threshold
  - Deduplicates references (extract references, find duplicates)
  - Identifies trends (common themes, methods, findings)
  - Generates summaries for each group using LLM
  - Returns: groups (List[PaperGroup]), deduplicated_references, trends, summaries
  
- PaperGroup: paper_ids, similarity_scores, summary
- Uses paper embeddings (average of chunk embeddings) for similarity
- Clustering algorithm (optional, e.g., DBSCAN)
"""

