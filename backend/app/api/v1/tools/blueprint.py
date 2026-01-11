"""
# Blueprint Generator API Endpoint

## What it does:
FastAPI route handler for blueprint generator tool. Generates structured research blueprints.

## How it works:
- Defines POST endpoint for blueprint generation
- Uses dependency injection for database session and authentication
- Calls blueprint_generator tool for business logic
- Returns structured blueprint

## What to include:
- POST /tools/blueprint
  - Request body: query (string), paper_ids (List[str], optional - defaults to all)
  - Response: Blueprint with sections: Problem, Hypothesis, Architecture, Experiments, Metrics, Risks
  - Calls: tools.blueprint_generator.generate_blueprint()
  - Uses RAG to retrieve relevant information from papers
"""

