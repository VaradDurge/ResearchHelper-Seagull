"""
Invitation Service - Create, accept, list and revoke workspace invitations.
"""
from datetime import datetime, timezone, timedelta
from typing import List, Optional
import secrets
import uuid


def _utcnow() -> datetime:
    """Return a naive UTC datetime (matches what MongoDB stores back)."""
    return datetime.utcnow()

from app.db.mongo import get_invitations_collection, get_workspaces_collection, get_users_collection
from app.models.schemas import InvitationResponse, InvitationStatus, InvitationEmailStatusResponse
from app.services.email_service import send_invitation_email, get_email_delivery_status
from app.services.workspace_service import add_collaborator, _user_can_access, _doc_to_response
from app.config import settings

INVITATION_EXPIRY_DAYS = 7


def create_invitation(
    workspace_id: str,
    inviter_id: str,
    invitee_email: str,
) -> tuple[InvitationResponse, dict | None]:
    """Create a pending invitation. Returns (response, email_args_or_None)."""
    workspaces = get_workspaces_collection()
    ws_doc = workspaces.find_one({"workspace_id": workspace_id})
    if not ws_doc:
        raise LookupError("Workspace not found")
    if not _user_can_access(ws_doc, inviter_id):
        raise PermissionError("You do not have access to this workspace")

    users = get_users_collection()
    invitee_user = users.find_one({"email": invitee_email.lower().strip()})
    if invitee_user:
        invitee_uid = invitee_user.get("user_id", str(invitee_user["_id"]))
        if _user_can_access(ws_doc, invitee_uid):
            raise ValueError("This user is already a member of the workspace")

    normalized_email = invitee_email.lower().strip()

    invitations = get_invitations_collection()
    invitations.update_many(
        {
            "workspace_id": workspace_id,
            "invitee_email": normalized_email,
            "status": InvitationStatus.PENDING.value,
        },
        {"$set": {"status": InvitationStatus.REVOKED.value, "replaced_by_resend": True}},
    )

    now = _utcnow()
    invitation_id = str(uuid.uuid4())
    token = secrets.token_urlsafe(48)
    doc = {
        "invitation_id": invitation_id,
        "token": token,
        "workspace_id": workspace_id,
        "inviter_id": inviter_id,
        "invitee_email": normalized_email,
        "status": InvitationStatus.PENDING.value,
        "created_at": now,
        "expires_at": now + timedelta(days=INVITATION_EXPIRY_DAYS),
    }
    invitations.insert_one(doc)

    inviter_user = users.find_one({"user_id": inviter_id})
    inviter_name = (inviter_user or {}).get("name", "A Seagull user")
    workspace_name = ws_doc.get("name", "Workspace")
    invite_link = f"{settings.frontend_url}/invite/{token}"

    email_args = {
        "invitation_id": invitation_id,
        "to_email": normalized_email,
        "inviter_name": inviter_name,
        "workspace_name": workspace_name,
        "invite_link": invite_link,
    }

    return _doc_to_invitation_response(doc), email_args


def send_invitation_email_background(invitation_id: str, to_email: str, inviter_name: str, workspace_name: str, invite_link: str):
    """Called as a FastAPI BackgroundTask — sends the email and updates the DB."""
    import logging
    _logger = logging.getLogger(__name__)
    invitations = get_invitations_collection()
    try:
        provider_email_id = send_invitation_email(to_email, inviter_name, workspace_name, invite_link)
        invitations.update_one(
            {"invitation_id": invitation_id},
            {"$set": {
                "provider_email_id": provider_email_id,
                "provider_status": "submitted",
                "provider_last_event": "send_submitted",
            }},
        )
        _logger.info("Background email sent for invitation %s", invitation_id)
    except Exception as exc:
        _logger.error("Background email failed for invitation %s: %s", invitation_id, exc)
        invitations.update_one(
            {"invitation_id": invitation_id},
            {"$set": {"provider_status": "send_failed", "provider_last_event": str(exc)}},
        )


def accept_invitation(token: str, user_id: str, user_email: str):
    """Accept an invitation. Returns the workspace response."""
    invitations = get_invitations_collection()
    doc = invitations.find_one({"token": token})

    if not doc:
        raise LookupError("Invitation not found")
    if doc["status"] != InvitationStatus.PENDING.value:
        raise ValueError(f"Invitation has already been {doc['status']}")
    if _utcnow() > doc["expires_at"]:
        invitations.update_one({"token": token}, {"$set": {"status": InvitationStatus.EXPIRED.value}})
        raise ValueError("Invitation has expired")

    # Verify the accepting user's email matches (case-insensitive)
    if doc["invitee_email"].lower() != user_email.lower():
        raise PermissionError("This invitation was sent to a different email address")

    # Add user to workspace
    workspace_id = doc["workspace_id"]
    add_collaborator(workspace_id, user_id)

    # Mark invitation as accepted
    invitations.update_one(
        {"token": token},
        {"$set": {"status": InvitationStatus.ACCEPTED.value, "accepted_by": user_id}},
    )

    workspaces = get_workspaces_collection()
    ws_doc = workspaces.find_one({"workspace_id": workspace_id})
    return _doc_to_response(ws_doc, workspace_id)


def get_pending_invitations(workspace_id: str, user_id: str) -> List[InvitationResponse]:
    """List pending invitations for a workspace."""
    workspaces = get_workspaces_collection()
    ws_doc = workspaces.find_one({"workspace_id": workspace_id})
    if not ws_doc or not _user_can_access(ws_doc, user_id):
        raise LookupError("Workspace not found")

    invitations = get_invitations_collection()
    now = _utcnow()

    # Expire old invitations first
    invitations.update_many(
        {"workspace_id": workspace_id, "status": InvitationStatus.PENDING.value, "expires_at": {"$lt": now}},
        {"$set": {"status": InvitationStatus.EXPIRED.value}},
    )

    docs = list(
        invitations.find({"workspace_id": workspace_id, "status": InvitationStatus.PENDING.value})
        .sort("created_at", -1)
    )
    return [_doc_to_invitation_response(d) for d in docs]


def get_my_pending_invitations(user_email: str) -> List[dict]:
    """Return pending invitations addressed to this email, with workspace/inviter info."""
    invitations = get_invitations_collection()
    workspaces = get_workspaces_collection()
    users = get_users_collection()
    now = _utcnow()

    invitations.update_many(
        {"invitee_email": user_email.lower(), "status": InvitationStatus.PENDING.value, "expires_at": {"$lt": now}},
        {"$set": {"status": InvitationStatus.EXPIRED.value}},
    )

    docs = list(
        invitations.find({"invitee_email": user_email.lower(), "status": InvitationStatus.PENDING.value})
        .sort("created_at", -1)
    )

    results = []
    for d in docs:
        ws_doc = workspaces.find_one({"workspace_id": d["workspace_id"]})
        inviter_doc = users.find_one({"user_id": d["inviter_id"]})
        results.append({
            "invitation_id": d["invitation_id"],
            "token": d["token"],
            "workspace_id": d["workspace_id"],
            "workspace_name": (ws_doc or {}).get("name", "Workspace"),
            "inviter_name": (inviter_doc or {}).get("name", "Someone"),
            "inviter_picture": (inviter_doc or {}).get("picture", ""),
            "created_at": d["created_at"].isoformat(),
        })
    return results


def revoke_invitation(invitation_id: str, user_id: str) -> bool:
    """Revoke a pending invitation. Only workspace members can revoke."""
    invitations = get_invitations_collection()
    doc = invitations.find_one({"invitation_id": invitation_id})
    if not doc:
        return False

    workspaces = get_workspaces_collection()
    ws_doc = workspaces.find_one({"workspace_id": doc["workspace_id"]})
    if not ws_doc or not _user_can_access(ws_doc, user_id):
        return False

    if doc["status"] != InvitationStatus.PENDING.value:
        return False

    invitations.update_one(
        {"invitation_id": invitation_id},
        {"$set": {"status": InvitationStatus.REVOKED.value}},
    )
    return True


def get_invitation_email_status(invitation_id: str, user_id: str) -> InvitationEmailStatusResponse:
    """Fetch provider delivery status for an invitation email."""
    invitations = get_invitations_collection()
    doc = invitations.find_one({"invitation_id": invitation_id})
    if not doc:
        raise LookupError("Invitation not found")

    workspaces = get_workspaces_collection()
    ws_doc = workspaces.find_one({"workspace_id": doc["workspace_id"]})
    if not ws_doc or not _user_can_access(ws_doc, user_id):
        raise PermissionError("You do not have access to this invitation")

    provider_email_id = doc.get("provider_email_id")
    checked_at = _utcnow()

    if not provider_email_id:
        return InvitationEmailStatusResponse(
            invitation_id=invitation_id,
            provider_email_id=None,
            provider_status=doc.get("provider_status", "unknown"),
            last_event=doc.get("provider_last_event"),
            checked_at=checked_at,
            raw=None,
        )

    provider_raw = get_email_delivery_status(provider_email_id)
    provider_status = (
        provider_raw.get("status")
        or provider_raw.get("state")
        or doc.get("provider_status")
        or "unknown"
    )
    last_event = provider_raw.get("last_event") or provider_raw.get("event") or doc.get("provider_last_event")

    invitations.update_one(
        {"invitation_id": invitation_id},
        {
            "$set": {
                "provider_status": provider_status,
                "provider_last_event": last_event,
                "provider_checked_at": checked_at,
            }
        },
    )

    return InvitationEmailStatusResponse(
        invitation_id=invitation_id,
        provider_email_id=provider_email_id,
        provider_status=provider_status,
        last_event=last_event,
        checked_at=checked_at,
        raw=provider_raw,
    )


def _doc_to_invitation_response(doc: dict) -> InvitationResponse:
    invite_link = None
    token = doc.get("token")
    if token:
        invite_link = f"{settings.frontend_url}/invite/{token}"
    return InvitationResponse(
        id=doc["invitation_id"],
        workspace_id=doc["workspace_id"],
        inviter_id=doc["inviter_id"],
        invitee_email=doc["invitee_email"],
        invite_link=invite_link,
        status=InvitationStatus(doc["status"]),
        created_at=doc["created_at"],
        expires_at=doc["expires_at"],
    )
