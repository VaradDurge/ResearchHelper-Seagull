"""
# Method Reproduction API Endpoint

## What it does:
FastAPI route handler for method reproduction tool. Extracts method details from a paper.

## How it works:
- Defines POST endpoint for method extraction
- Uses dependency injection for database session and authentication
- Calls method_extractor tool for business logic
- Returns extracted method details

## What to include:
- POST /tools/method-reprod
  - Request body: paper_id (string)
  - Response: MethodDetails with: Algorithm, Architecture, Training schedule, Hyperparameters, Experiments
  - Calls: tools.method_extractor.extract_method()
  - Uses LLM to extract structured information from paper
"""

