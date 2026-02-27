"""
Workspace Service - Manage user workspaces with collaboration support.
"""
from datetime import datetime, timezone
from typing import List, Optional
import uuid

from app.db.mongo import get_workspaces_collection, get_papers_collection
from app.models.schemas import WorkspaceResponse

MAX_WORKSPACES = 5


def _doc_to_response(doc: dict, active_workspace_id: Optional[str] = None) -> WorkspaceResponse:
    owner_id = doc.get("owner_id", doc.get("user_id", ""))
    collaborators = doc.get("collaborators", [])
    return WorkspaceResponse(
        id=doc["workspace_id"],
        name=doc["name"],
        user_id=owner_id,
        owner_id=owner_id,
        collaborators=collaborators,
        is_shared=len(collaborators) > 0,
        is_active=doc["workspace_id"] == active_workspace_id if active_workspace_id else doc.get("is_default", False),
        created_at=doc["created_at"],
        updated_at=doc["updated_at"],
    )


def _user_can_access(doc: dict, user_id: str) -> bool:
    """Check if a user is the owner or a collaborator of a workspace."""
    owner_id = doc.get("owner_id", doc.get("user_id", ""))
    collaborators = doc.get("collaborators", [])
    return user_id == owner_id or user_id in collaborators


def get_workspaces(user_id: str) -> List[WorkspaceResponse]:
    """Get all workspaces a user owns or collaborates on."""
    workspaces = get_workspaces_collection()
    docs = list(
        workspaces.find({
            "$or": [
                {"owner_id": user_id},
                {"user_id": user_id},
                {"collaborators": user_id},
            ]
        }).sort("created_at", 1)
    )

    # Deduplicate (owner_id vs legacy user_id may overlap)
    seen = set()
    unique_docs = []
    for d in docs:
        wid = d["workspace_id"]
        if wid not in seen:
            seen.add(wid)
            unique_docs.append(d)
    docs = unique_docs

    if not docs:
        default = _create_default_workspace(user_id)
        return [default]

    active_id = _get_active_workspace_id(user_id)
    return [_doc_to_response(doc, active_id) for doc in docs]


def get_workspace_by_id(workspace_id: str, user_id: str) -> Optional[WorkspaceResponse]:
    workspaces = get_workspaces_collection()
    doc = workspaces.find_one({"workspace_id": workspace_id})
    if not doc or not _user_can_access(doc, user_id):
        return None
    active_id = _get_active_workspace_id(user_id)
    return _doc_to_response(doc, active_id)


def create_workspace(user_id: str, name: str) -> WorkspaceResponse:
    """Create a new workspace. Enforces the max limit per owned workspaces."""
    workspaces = get_workspaces_collection()
    normalized_name = name.strip()
    if not normalized_name:
        raise ValueError("Workspace name is required")

    owned_count = workspaces.count_documents({
        "$or": [{"owner_id": user_id}, {"user_id": user_id}]
    })

    if owned_count == 0:
        default = _create_default_workspace(user_id)
        if normalized_name.lower() == default.name.strip().lower():
            return default
        owned_count = 1

    if owned_count >= MAX_WORKSPACES:
        raise ValueError(f"Maximum of {MAX_WORKSPACES} workspaces allowed")
    _ensure_unique_workspace_name(user_id, normalized_name)

    now = datetime.now(timezone.utc)
    workspace_id = str(uuid.uuid4())
    doc = {
        "workspace_id": workspace_id,
        "owner_id": user_id,
        "user_id": user_id,
        "collaborators": [],
        "name": normalized_name,
        "is_default": False,
        "created_at": now,
        "updated_at": now,
    }
    workspaces.insert_one(doc)

    active_id = _get_active_workspace_id(user_id)
    return _doc_to_response(doc, active_id)


def switch_workspace(user_id: str, workspace_id: str) -> WorkspaceResponse:
    """Switch the active workspace for a user."""
    workspaces = get_workspaces_collection()
    doc = workspaces.find_one({"workspace_id": workspace_id})
    if not doc or not _user_can_access(doc, user_id):
        raise ValueError("Workspace not found")

    # Deactivate all workspaces the user owns
    workspaces.update_many(
        {"$or": [{"owner_id": user_id}, {"user_id": user_id}]},
        {"$set": {"is_active": False}},
    )
    workspaces.update_one(
        {"workspace_id": workspace_id},
        {"$set": {"is_active": True, "updated_at": datetime.now(timezone.utc)}},
    )
    return _doc_to_response(doc, workspace_id)


def rename_workspace(user_id: str, workspace_id: str, name: str) -> WorkspaceResponse:
    """Rename a workspace (any collaborator can rename)."""
    workspaces = get_workspaces_collection()
    normalized_name = name.strip()
    if not normalized_name:
        raise ValueError("Workspace name is required")

    doc = workspaces.find_one({"workspace_id": workspace_id})
    if not doc or not _user_can_access(doc, user_id):
        raise LookupError("Workspace not found")

    owner_id = doc.get("owner_id", doc.get("user_id", ""))
    _ensure_unique_workspace_name(owner_id, normalized_name, exclude_workspace_id=workspace_id)
    workspaces.update_one(
        {"workspace_id": workspace_id},
        {"$set": {"name": normalized_name, "updated_at": datetime.now(timezone.utc)}},
    )
    updated = workspaces.find_one({"workspace_id": workspace_id})
    active_id = _get_active_workspace_id(user_id)
    return _doc_to_response(updated, active_id)


def get_active_workspace(user_id: str) -> WorkspaceResponse:
    """Get the currently active workspace for a user."""
    workspaces = get_workspaces_collection()
    docs = list(
        workspaces.find({
            "$or": [
                {"owner_id": user_id},
                {"user_id": user_id},
                {"collaborators": user_id},
            ]
        }).sort("created_at", 1)
    )

    seen = set()
    unique_docs = []
    for d in docs:
        wid = d["workspace_id"]
        if wid not in seen:
            seen.add(wid)
            unique_docs.append(d)
    docs = unique_docs

    if not docs:
        return _create_default_workspace(user_id)

    active_doc = next((d for d in docs if d.get("is_active")), None)
    if not active_doc:
        active_doc = docs[0]
        workspaces.update_one(
            {"workspace_id": active_doc["workspace_id"]},
            {"$set": {"is_active": True}},
        )

    return _doc_to_response(active_doc, active_doc["workspace_id"])


def add_collaborator(workspace_id: str, user_id: str) -> None:
    """Add a user as a collaborator to a workspace."""
    workspaces = get_workspaces_collection()
    workspaces.update_one(
        {"workspace_id": workspace_id},
        {
            "$addToSet": {"collaborators": user_id},
            "$set": {"updated_at": datetime.now(timezone.utc)},
        },
    )


def is_workspace_shared(workspace_id: str) -> bool:
    workspaces = get_workspaces_collection()
    doc = workspaces.find_one({"workspace_id": workspace_id})
    if not doc:
        return False
    return len(doc.get("collaborators", [])) > 0


def get_workspace_members(workspace_id: str) -> List[str]:
    """Return all user_ids who have access to this workspace (owner + collaborators)."""
    workspaces = get_workspaces_collection()
    doc = workspaces.find_one({"workspace_id": workspace_id})
    if not doc:
        return []
    owner_id = doc.get("owner_id", doc.get("user_id", ""))
    collaborators = doc.get("collaborators", [])
    members = [owner_id] + [c for c in collaborators if c != owner_id]
    return members


def get_workspace_members_with_details(workspace_id: str, requester_user_id: str) -> List[dict]:
    """Return workspace members with name, email, picture, role. Requester must have access."""
    from app.db.mongo import get_users_collection
    workspaces = get_workspaces_collection()
    doc = workspaces.find_one({"workspace_id": workspace_id})
    if not doc or not _user_can_access(doc, requester_user_id):
        raise LookupError("Workspace not found")
    owner_id = doc.get("owner_id", doc.get("user_id", ""))
    collaborators = doc.get("collaborators", [])
    user_ids = [owner_id] + [c for c in collaborators if c != owner_id]
    users = get_users_collection()
    result = []
    for uid in user_ids:
        u = users.find_one({"user_id": uid})
        role = "owner" if uid == owner_id else "collaborator"
        result.append({
            "user_id": uid,
            "name": (u or {}).get("name", "Unknown"),
            "email": (u or {}).get("email", ""),
            "picture": (u or {}).get("picture", ""),
            "role": role,
        })
    return result


def remove_collaborator(workspace_id: str, collaborator_user_id: str, requester_user_id: str) -> None:
    """Remove a collaborator from the workspace. Only the owner can remove."""
    workspaces = get_workspaces_collection()
    doc = workspaces.find_one({"workspace_id": workspace_id})
    if not doc or not _user_can_access(doc, requester_user_id):
        raise LookupError("Workspace not found")
    owner_id = doc.get("owner_id", doc.get("user_id", ""))
    if requester_user_id != owner_id:
        raise PermissionError("Only the workspace owner can remove collaborators")
    if collaborator_user_id == owner_id:
        raise ValueError("Cannot remove the workspace owner")
    collaborators = doc.get("collaborators", [])
    if collaborator_user_id not in collaborators:
        raise ValueError("User is not a collaborator of this workspace")
    workspaces.update_one(
        {"workspace_id": workspace_id},
        {
            "$pull": {"collaborators": collaborator_user_id},
            "$set": {"updated_at": datetime.now(timezone.utc)},
        },
    )


def _get_active_workspace_id(user_id: str) -> Optional[str]:
    workspaces = get_workspaces_collection()
    active_doc = workspaces.find_one({
        "$or": [{"owner_id": user_id}, {"user_id": user_id}, {"collaborators": user_id}],
        "is_active": True,
    })
    if active_doc:
        return active_doc["workspace_id"]
    first = workspaces.find_one(
        {"$or": [{"owner_id": user_id}, {"user_id": user_id}, {"collaborators": user_id}]},
        sort=[("created_at", 1)],
    )
    return first["workspace_id"] if first else None


def _create_default_workspace(user_id: str) -> WorkspaceResponse:
    """Create the default workspace and migrate any existing papers."""
    workspaces = get_workspaces_collection()
    now = datetime.now(timezone.utc)
    workspace_id = str(uuid.uuid4())
    doc = {
        "workspace_id": workspace_id,
        "owner_id": user_id,
        "user_id": user_id,
        "collaborators": [],
        "name": "My Workspace",
        "is_default": True,
        "is_active": True,
        "created_at": now,
        "updated_at": now,
    }
    workspaces.insert_one(doc)

    papers = get_papers_collection()
    papers.update_many(
        {"user_id": user_id, "workspace_id": {"$ne": workspace_id}},
        {"$set": {"workspace_id": workspace_id}},
    )

    return _doc_to_response(doc, workspace_id)


def _ensure_unique_workspace_name(
    user_id: str,
    name: str,
    exclude_workspace_id: Optional[str] = None,
) -> None:
    """Prevent duplicate workspace names per owner (case-insensitive)."""
    workspaces = get_workspaces_collection()
    import re as _re
    escaped = _re.escape(name)
    query: dict = {
        "$or": [{"owner_id": user_id}, {"user_id": user_id}],
        "name": {"$regex": f"^{escaped}$", "$options": "i"},
    }
    if exclude_workspace_id:
        query["workspace_id"] = {"$ne": exclude_workspace_id}
    if workspaces.find_one(query):
        raise ValueError("Workspace name already exists")
