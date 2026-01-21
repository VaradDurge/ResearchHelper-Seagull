"""
DOI lookup API Endpoints
"""
from fastapi import APIRouter, HTTPException

from app.models.schemas import DoiLookupRequest, DoiLookupResponse
from app.services.doi_service import lookup_dois

router = APIRouter()


@router.post("/lookup", response_model=DoiLookupResponse)
async def lookup_doi(payload: DoiLookupRequest):
    if not payload.dois:
        raise HTTPException(status_code=400, detail="At least one DOI is required")
    if len(payload.dois) > 5:
        raise HTTPException(status_code=400, detail="Maximum of 5 DOIs allowed")

    results = lookup_dois(payload.dois, max_items=5)
    return DoiLookupResponse(results=results)
