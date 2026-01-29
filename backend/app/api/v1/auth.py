"""
Auth API Endpoints
"""
from fastapi import APIRouter, HTTPException, Depends

from app.api.dependencies import get_current_user_id
from app.models.schemas import GoogleAuthRequest, AuthResponse, UserResponse
from app.services.auth_service import authenticate_google_token, get_user_by_id

router = APIRouter()


@router.post("/google", response_model=AuthResponse)
async def google_auth(payload: GoogleAuthRequest):
    if not payload.id_token or not payload.id_token.strip():
        raise HTTPException(status_code=400, detail="id_token is required")
    try:
        user, access_token = authenticate_google_token(payload.id_token)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return AuthResponse(
        access_token=access_token,
        user=UserResponse(
            user_id=user["user_id"],
            email=user.get("email"),
            name=user.get("name"),
            picture=user.get("picture"),
        ),
    )


@router.get("/me", response_model=UserResponse)
async def get_me(user_id: str = Depends(get_current_user_id)):
    user = get_user_by_id(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return UserResponse(
        user_id=user["user_id"],
        email=user.get("email"),
        name=user.get("name"),
        picture=user.get("picture"),
    )
