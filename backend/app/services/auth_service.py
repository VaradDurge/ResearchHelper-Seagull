"""
Authentication service.
"""
from datetime import datetime, timezone
import uuid

from google.oauth2 import id_token
from google.auth.transport import requests as google_requests

from app.config import settings
from app.core.security import create_access_token
from app.db.mongo import get_users_collection


def authenticate_google_token(token: str):
    if not settings.google_client_id:
        raise ValueError("Google client ID is not configured")

    try:
        id_info = id_token.verify_oauth2_token(
            token, google_requests.Request(), settings.google_client_id
        )
    except Exception as exc:
        raise ValueError(f"Invalid Google ID token: {str(exc)}") from exc

    google_sub = id_info.get("sub")
    if not google_sub:
        raise ValueError("Invalid Google ID token - no sub")

    email = id_info.get("email")
    name = id_info.get("name")
    picture = id_info.get("picture")

    users = get_users_collection()
    user = users.find_one({"google_sub": google_sub})

    now = datetime.now(timezone.utc)
    if user is None:
        user = {
            "user_id": str(uuid.uuid4()),
            "google_sub": google_sub,
            "email": email,
            "name": name,
            "picture": picture,
            "created_at": now,
            "updated_at": now,
        }
        users.insert_one(user)
    else:
        users.update_one(
            {"_id": user["_id"]},
            {"$set": {"email": email, "name": name, "picture": picture, "updated_at": now}},
        )
        user = users.find_one({"_id": user["_id"]})

    access_token = create_access_token(user["user_id"])
    return user, access_token


def get_user_by_id(user_id: str):
    users = get_users_collection()
    return users.find_one({"user_id": user_id})
