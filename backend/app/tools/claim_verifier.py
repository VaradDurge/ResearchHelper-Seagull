"""
# Claim Verifier Tool

## What it does:
Implements claim verification logic. Verifies claims against uploaded papers by
searching for supporting or refuting evidence.

## How it works:
- Searches vector DB for relevant chunks related to claim
- Uses LLM to analyze evidence and determine verdict
- Returns verdict (Support/Refute/Uncertain) with confidence and evidence

## What to include:
- verify_claim(claim: str, paper_ids: List[str]) -> VerificationResult
  - Searches vector DB for chunks related to claim
  - Retrieves top-k relevant chunks
  - Uses LLM to analyze evidence and determine verdict
  - Returns: verdict (Support/Refute/Uncertain), confidence (float), evidence (List[Evidence])
  
- Evidence includes: chunk text, paper name, page number, relevance score
- Uses RAG-like retrieval but with verification-specific prompt
- LLM prompt asks: "Does the evidence support, refute, or is uncertain about this claim?"
"""

