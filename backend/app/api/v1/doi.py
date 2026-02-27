"""
DOI lookup API Endpoints with real-time broadcast.
"""
from fastapi import APIRouter, HTTPException, Depends

from app.api.dependencies import get_current_user_id, get_current_workspace_id
from app.models.schemas import DoiLookupRequest, DoiLookupResponse, DoiImportRequest, DoiImportResponse
from app.services.doi_service import lookup_dois, import_doi
from app.services.papers_service import save_paper
from app.core.ws_manager import manager

router = APIRouter()


@router.post("/lookup", response_model=DoiLookupResponse)
async def lookup_doi(payload: DoiLookupRequest):
    if not payload.dois:
        raise HTTPException(status_code=400, detail="At least one DOI is required")
    if len(payload.dois) > 5:
        raise HTTPException(status_code=400, detail="Maximum of 5 DOIs allowed")

    results = lookup_dois(payload.dois, max_items=5)
    return DoiLookupResponse(results=results)


@router.post("/import", response_model=DoiImportResponse)
async def import_doi_endpoint(
    payload: DoiImportRequest,
    user_id: str = Depends(get_current_user_id),
    workspace_id: str = Depends(get_current_workspace_id),
):
    if not payload.doi or not payload.doi.strip():
        raise HTTPException(status_code=400, detail="DOI is required")
    try:
        paper = import_doi(payload.doi, workspace_id=workspace_id, user_id=user_id)
        save_paper(paper)

        await manager.broadcast(
            workspace_id,
            {
                "type": "paper_added",
                "payload": {
                    "paper_id": paper.id,
                    "title": paper.title,
                    "user_id": user_id,
                },
            },
            exclude_user=user_id,
        )

        return DoiImportResponse(paper=paper)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
