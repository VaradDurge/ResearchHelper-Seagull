"""
# Graphs API Endpoint

## What it does:
FastAPI route handler for method relationship graphs tool. Generates graph data for visualization.

## How it works:
- Defines POST endpoint for graph generation
- Uses dependency injection for database session and authentication
- Calls graph_builder tool for business logic
- Returns graph data (nodes and edges)

## What to include:
- POST /tools/graphs
  - Request body: paper_ids (List[str]), options (node_types, edge_types, layout)
  - Response: GraphData with: nodes (List[Node]), edges (List[Edge])
  - Calls: tools.graph_builder.build_graph()
  - Nodes represent techniques/methods, edges represent relationships
  - Uses co-occurrence and influence analysis
"""

