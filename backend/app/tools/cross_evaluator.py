"""
# Cross Evaluator Tool

## What it does:
Compares responses from multiple LLMs and evaluates them. Gets responses from
different LLM providers, then uses an evaluator LLM to rank and judge responses.

## How it works:
- Sends query to multiple LLM providers
- Collects responses
- Uses evaluator LLM to judge responses
- Returns ranked list with justifications

## What to include:
- evaluate(query: str, llm_providers: List[str], paper_ids: List[str]) -> EvaluationResult
  - Uses RAG to get context from papers
  - Sends query + context to each LLM provider
  - Collects responses
  - Uses evaluator LLM to judge:
    - Correctness
    - Completeness
    - Citation quality
  - Ranks responses
  - Returns: responses (List[LLMResponse]), rankings, metrics, justifications
  
- LLMResponse: provider, response, citations
- EvaluationMetrics: correctness_score, completeness_score, citation_score, overall_score
- Ranking: ordered list with justifications
"""

