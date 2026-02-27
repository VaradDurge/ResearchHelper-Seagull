"""
API Dependencies
"""
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Generator
import jwt

from app.core.security import decode_access_token


def get_db() -> Generator:
    """Dummy database dependency - returns None for now"""
    yield None


auth_scheme = HTTPBearer(auto_error=False)


def get_current_user_id(
    credentials: HTTPAuthorizationCredentials = Depends(auth_scheme),
) -> str:
    """Get current user ID from JWT token."""
    if credentials is None or not credentials.credentials:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")

    token = credentials.credentials

    try:
        payload = decode_access_token(token)
        user_id = payload.get("sub")
    except jwt.PyJWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    
    return user_id


def get_current_workspace_id(
    request: Request,
    user_id: str = Depends(get_current_user_id),
) -> str:
    """
    Resolve the active workspace ID from the X-Workspace-Id header.
    Falls back to the user's active workspace stored in the database.
    Supports both owned and collaborated workspaces.
    """
    from app.services.workspace_service import get_active_workspace, get_workspace_by_id

    header_ws_id = request.headers.get("x-workspace-id")
    if header_ws_id:
        ws = get_workspace_by_id(header_ws_id, user_id)
        if ws:
            return ws.id

    active = get_active_workspace(user_id)
    return active.id
