"""
DOI lookup API Endpoints with real-time broadcast.
"""
import asyncio
import logging
import threading

from fastapi import APIRouter, HTTPException, Depends

from app.api.dependencies import get_current_user_id, get_current_workspace_id
from app.core.ws_manager import manager
from app.models.schemas import DoiImportRequest, DoiImportResponse, DoiLookupRequest, DoiLookupResponse, PaperStatus
from app.services.doi_service import import_doi_fast, lookup_dois, run_doi_background_task
from app.services.papers_service import get_paper_by_id, save_paper

logger = logging.getLogger(__name__)

router = APIRouter()


def _run_doi_import_background(payload: dict, loop: asyncio.AbstractEventLoop) -> None:
    """Run download + ingest in background; on completion update paper and broadcast paper_ready."""
    result, exc = run_doi_background_task(payload)
    workspace_id = payload["workspace_id"]
    user_id = payload["user_id"]
    paper_id = payload["paper_id"]

    def broadcast_ready(status: str) -> None:
        fut = asyncio.run_coroutine_threadsafe(
            manager.broadcast(
                workspace_id,
                {"type": "paper_ready", "payload": {"paper_id": paper_id, "status": status}},
            )
        )
        try:
            fut.result(timeout=5)
        except Exception as e:
            logger.warning("Failed to broadcast paper_ready: %s", e)

    if result is not None:
        save_paper(result)
        broadcast_ready("ready")
    else:
        paper = get_paper_by_id(paper_id, user_id)
        if paper is not None:
            updated = paper.model_copy(update={"status": PaperStatus.ERROR})
            save_paper(updated)
        broadcast_ready("error")


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
        paper, background_payload = import_doi_fast(
            payload.doi, workspace_id=workspace_id, user_id=user_id
        )
        if background_payload is None:
            return DoiImportResponse(paper=paper)

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
        loop = asyncio.get_running_loop()
        threading.Thread(
            target=_run_doi_import_background,
            args=(background_payload, loop),
            daemon=True,
        ).start()
        return DoiImportResponse(paper=paper)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
