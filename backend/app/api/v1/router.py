"""
Main API Router
"""
from fastapi import APIRouter, Depends
from app.api.dependencies import get_current_user_id
from app.api.v1 import papers, chat, cross_eval, doi, auth, conversations, files, workspace, ws, verification, graph, debug

api_router = APIRouter()

# Auth routes (no auth required)
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])

# File serving (handles own auth via query param for iframe support)
api_router.include_router(files.router, prefix="/files", tags=["files"])

# Protected routes (require JWT)
api_router.include_router(
    workspace.router, prefix="/workspaces", tags=["workspaces"], dependencies=[Depends(get_current_user_id)]
)
api_router.include_router(
    papers.router, prefix="/papers", tags=["papers"], dependencies=[Depends(get_current_user_id)]
)
api_router.include_router(
    chat.router, prefix="/chat", tags=["chat"], dependencies=[Depends(get_current_user_id)]
)
api_router.include_router(
    cross_eval.router, prefix="/cross-eval", tags=["cross-eval"], dependencies=[Depends(get_current_user_id)]
)
api_router.include_router(
    doi.router, prefix="/doi", tags=["doi"], dependencies=[Depends(get_current_user_id)]
)
api_router.include_router(
    conversations.router, prefix="/conversations", tags=["conversations"], dependencies=[Depends(get_current_user_id)]
)
api_router.include_router(
    verification.router, prefix="/verify", tags=["verification"], dependencies=[Depends(get_current_user_id)]
)
api_router.include_router(
    graph.router, prefix="/graph", tags=["graph"], dependencies=[Depends(get_current_user_id)]
)
api_router.include_router(
    debug.router, prefix="/debug", tags=["debug"], dependencies=[Depends(get_current_user_id)]
)

# WebSocket (auth handled inside via query param token)
api_router.include_router(ws.router, tags=["websocket"])
