"""
# Cross Evaluation API Endpoint

## What it does:
FastAPI route handler for cross evaluation tool. Compares responses from multiple LLMs.

## How it works:
- Defines POST endpoint for cross evaluation
- Uses dependency injection for database session and authentication
- Calls cross_evaluator tool for business logic
- Returns evaluation results with rankings

## What to include:
- POST /tools/cross-eval
  - Request body: query (string), llm_providers (List[str]), paper_ids (List[str])
  - Response: EvaluationResult with: responses (List[LLMResponse]), rankings, metrics, justifications
  - Calls: tools.cross_evaluator.evaluate()
  - Gets responses from multiple LLMs, then uses evaluator LLM to rank them
"""

