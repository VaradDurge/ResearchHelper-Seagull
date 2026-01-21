"""
Cross-evaluation API Endpoints
Generate per-paper answers and return a comparison table.
"""
from fastapi import APIRouter, HTTPException, Depends

from app.api.dependencies import get_current_user_id
from app.models.schemas import CrossEvalRequest, CrossEvalResponse
from app.services.cross_eval_service import cross_evaluate

router = APIRouter()


@router.post("/", response_model=CrossEvalResponse)
async def cross_eval(
    payload: CrossEvalRequest,
    user_id: str = Depends(get_current_user_id),
):
    if not payload.message or not payload.message.strip():
        raise HTTPException(status_code=400, detail="Message is required")

    return cross_evaluate(
        message=payload.message,
        paper_ids=payload.paper_ids,
        top_k=payload.top_k or 5,
    )
