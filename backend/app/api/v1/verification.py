"""
Claim verification API — Evidence Confidence Scoring Engine.
POST /verify/claim: verify one atomic claim; returns structured JSON only.
Collaborative: saves run to DB and broadcasts to workspace so others see it.
"""
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, Request

from app.api.dependencies import get_current_user_id, get_current_workspace_id
from app.db.mongo import get_claim_verifications_collection, get_users_collection
from app.models.schemas import (
    ClaimVerifyRequest,
    ClaimVerifyResponse,
    ClaimVerifyRecentResponse,
    ClaimVerifyRunItem,
)
from app.services.papers_service import get_paper_ids_for_workspace
from app.verification import VerificationEngine
from app.core.ws_manager import manager

router = APIRouter()


def _user_display_name(user_id: str) -> str:
    users = get_users_collection()
    doc = users.find_one({"user_id": user_id}) or {}
    return doc.get("name") or doc.get("email") or user_id[:8]


@router.post("/claim", response_model=ClaimVerifyResponse)
async def verify_claim(
    body: ClaimVerifyRequest,
    request: Request,
    user_id: str = Depends(get_current_user_id),
    workspace_id: str = Depends(get_current_workspace_id),
):
    """
    Verify a single atomic claim against workspace papers.
    Returns structured JSON. Saves run to DB and broadcasts to workspace collaborators.
    """
    paper_ids = body.paper_ids or get_paper_ids_for_workspace(user_id, workspace_id)
    engine = VerificationEngine(top_k=10, workspace_id=workspace_id, user_id=user_id)
    result = engine.verify(claim=body.claim, paper_ids=paper_ids if paper_ids else None, include_scored_evidence=True)

    response = ClaimVerifyResponse(
        claim=result.claim,
        support_count=result.support_count,
        contradict_count=result.contradict_count,
        neutral_count=result.neutral_count,
        evidence_count=result.evidence_count,
        confidence_score=result.confidence_score,
        confidence_label=result.confidence_label.value,
        evidence_strength=result.evidence_strength,
        strongest_study_types=result.strongest_study_types,
        guardrail_triggered=result.guardrail_triggered,
        scored_evidence=result.scored_evidence,
    )

    # Persist for shared history
    coll = get_claim_verifications_collection()
    now = datetime.now(timezone.utc)
    doc = {
        "workspace_id": workspace_id,
        "user_id": user_id,
        "claim": body.claim,
        "result": response.model_dump(),
        "created_at": now,
    }
    insert_result = coll.insert_one(doc)
    run_id = str(insert_result.inserted_id)

    # Broadcast to other workspace members (exclude sender so they already have the result)
    await manager.broadcast(
        workspace_id,
        {
            "type": "claim_verify_result",
            "payload": {
                "user_id": user_id,
                "user_name": _user_display_name(user_id),
                "claim": body.claim,
                "result": response.model_dump(),
                "created_at": now.isoformat(),
            },
        },
        exclude_user=user_id,
    )

    return response


@router.get("/recent", response_model=ClaimVerifyRecentResponse)
def get_recent_verifications(
    limit: int = 30,
    user_id: str = Depends(get_current_user_id),
    workspace_id: str = Depends(get_current_workspace_id),
):
    """Return recent claim verification runs for the current workspace (shared with collaborators)."""
    coll = get_claim_verifications_collection()
    cursor = (
        coll.find({"workspace_id": workspace_id})
        .sort("created_at", -1)
        .limit(limit)
    )
    runs: list = []
    for doc in cursor:
        run_id = str(doc["_id"])
        uid = doc.get("user_id", "")
        runs.append(
            ClaimVerifyRunItem(
                run_id=run_id,
                user_id=uid,
                user_name=_user_display_name(uid),
                claim=doc.get("claim", ""),
                result=ClaimVerifyResponse(**doc.get("result", {})),
                created_at=doc["created_at"],
            )
        )
    return ClaimVerifyRecentResponse(runs=runs, total=len(runs))
