"""
# Graph Builder Tool

## What it does:
Builds method relationship graphs. Identifies techniques/methods mentioned in papers
and creates graph of relationships (co-occurrence, influence, etc.).

## How it works:
- Extracts techniques/methods from papers using LLM
- Identifies relationships between techniques
- Builds graph structure (nodes and edges)
- Returns graph data for visualization

## What to include:
- build_graph(paper_ids: List[str], options: GraphOptions) -> GraphData
  - Extracts techniques/methods from papers using LLM/NER
  - Identifies relationships:
    - Co-occurrence: techniques mentioned together
    - Influence: one technique builds on another
    - Similarity: similar techniques
  - Builds graph: nodes (techniques), edges (relationships)
  - Returns: nodes (List[Node]), edges (List[Edge])
  
- Node: id, label, type (technique/method), paper_ids (where it appears)
- Edge: source_id, target_id, type (co-occurrence/influence), weight
- Uses graph algorithms for layout (optional)
- Filters by node/edge types based on options
"""

