"""
Workspace & Invitation API Endpoints
"""
from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks

from app.api.dependencies import get_current_user_id
from app.models.schemas import (
    WorkspaceCreateRequest,
    WorkspaceUpdateRequest,
    WorkspaceResponse,
    WorkspaceListResponse,
    InvitationCreateRequest,
    InvitationResponse,
    InvitationListResponse,
    InvitationAcceptResponse,
    InvitationEmailStatusResponse,
)
from app.services.workspace_service import (
    get_workspaces,
    get_active_workspace,
    create_workspace,
    rename_workspace,
    switch_workspace,
    get_workspace_members_with_details,
    remove_collaborator as remove_collaborator_service,
)
from app.services.invitation_service import (
    create_invitation,
    accept_invitation,
    get_pending_invitations,
    get_my_pending_invitations,
    revoke_invitation,
    get_invitation_email_status,
    send_invitation_email_background,
)

router = APIRouter()


# ── Workspace CRUD ───────────────────────────────────────────────────

@router.get("/", response_model=WorkspaceListResponse)
async def list_workspaces(user_id: str = Depends(get_current_user_id)):
    ws_list = get_workspaces(user_id)
    return WorkspaceListResponse(workspaces=ws_list, total=len(ws_list))


@router.get("/active", response_model=WorkspaceResponse)
async def get_active(user_id: str = Depends(get_current_user_id)):
    return get_active_workspace(user_id)


@router.post("/", response_model=WorkspaceResponse)
async def create_new_workspace(
    payload: WorkspaceCreateRequest,
    user_id: str = Depends(get_current_user_id),
):
    try:
        return create_workspace(user_id, payload.name)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/{workspace_id}/switch", response_model=WorkspaceResponse)
async def switch_active_workspace(
    workspace_id: str,
    user_id: str = Depends(get_current_user_id),
):
    try:
        return switch_workspace(user_id, workspace_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.put("/{workspace_id}", response_model=WorkspaceResponse)
async def rename_workspace_endpoint(
    workspace_id: str,
    payload: WorkspaceUpdateRequest,
    user_id: str = Depends(get_current_user_id),
):
    try:
        return rename_workspace(user_id, workspace_id, payload.name)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


# ── Members (collaborators list & remove) ─────────────────────────────

@router.get("/{workspace_id}/members")
async def list_workspace_members(
    workspace_id: str,
    user_id: str = Depends(get_current_user_id),
):
    """List workspace members with name, email, picture, role (owner/collaborator)."""
    try:
        return {"members": get_workspace_members_with_details(workspace_id, user_id)}
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.delete("/{workspace_id}/members/{member_user_id}")
async def remove_collaborator_endpoint(
    workspace_id: str,
    member_user_id: str,
    user_id: str = Depends(get_current_user_id),
):
    """Remove a collaborator from the workspace. Only the owner can remove."""
    try:
        remove_collaborator_service(workspace_id, member_user_id, user_id)
        return {"message": "Collaborator removed"}
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


# ── Invitations ──────────────────────────────────────────────────────

@router.post("/{workspace_id}/invite", response_model=InvitationResponse)
async def invite_collaborator(
    workspace_id: str,
    payload: InvitationCreateRequest,
    background_tasks: BackgroundTasks,
    user_id: str = Depends(get_current_user_id),
):
    try:
        invitation, email_args = create_invitation(workspace_id, user_id, payload.email)

        delivery_method = (payload.delivery_method or "email").strip().lower()
        if delivery_method != "link" and email_args:
            background_tasks.add_task(
                send_invitation_email_background,
                email_args["invitation_id"],
                email_args["to_email"],
                email_args["inviter_name"],
                email_args["workspace_name"],
                email_args["invite_link"],
            )

        return invitation
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/invitations/mine")
async def my_pending_invitations(user_id: str = Depends(get_current_user_id)):
    """Return pending invitations addressed to the current user's email."""
    from app.db.mongo import get_users_collection
    users = get_users_collection()
    user_doc = users.find_one({"user_id": user_id})
    user_email = (user_doc or {}).get("email", "")
    if not user_email:
        return {"invitations": []}
    return {"invitations": get_my_pending_invitations(user_email)}


@router.post("/invitations/{token}/accept", response_model=InvitationAcceptResponse)
async def accept_invite(
    token: str,
    user_id: str = Depends(get_current_user_id),
):
    from app.db.mongo import get_users_collection
    users = get_users_collection()
    user_doc = users.find_one({"user_id": user_id})
    user_email = (user_doc or {}).get("email", "")

    try:
        workspace = accept_invitation(token, user_id, user_email)
        return InvitationAcceptResponse(workspace=workspace)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get("/{workspace_id}/invitations", response_model=InvitationListResponse)
async def list_invitations(
    workspace_id: str,
    user_id: str = Depends(get_current_user_id),
):
    try:
        inv_list = get_pending_invitations(workspace_id, user_id)
        return InvitationListResponse(invitations=inv_list, total=len(inv_list))
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.delete("/invitations/{invitation_id}")
async def revoke_invite(
    invitation_id: str,
    user_id: str = Depends(get_current_user_id),
):
    success = revoke_invitation(invitation_id, user_id)
    if not success:
        raise HTTPException(status_code=404, detail="Invitation not found or already processed")
    return {"message": "Invitation revoked"}


@router.get("/invitations/{invitation_id}/email-status", response_model=InvitationEmailStatusResponse)
async def invitation_email_status(
    invitation_id: str,
    user_id: str = Depends(get_current_user_id),
):
    try:
        return get_invitation_email_status(invitation_id, user_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
