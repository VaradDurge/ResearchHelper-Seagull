"""
# Claim Verification API Endpoint

## What it does:
FastAPI route handler for claim verification tool. Verifies claims against uploaded papers.

## How it works:
- Defines POST endpoint for claim verification
- Uses dependency injection for database session and authentication
- Calls claim_verifier tool for business logic
- Returns verification result with evidence

## What to include:
- POST /tools/claim-verify
  - Request body: claim (string), paper_ids (List[str])
  - Response: VerificationResult with verdict (Support/Refute/Uncertain), confidence, evidence
  - Calls: tools.claim_verifier.verify_claim()
  - Evidence includes: chunks, citations, page numbers
"""

