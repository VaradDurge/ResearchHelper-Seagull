"""
Main API Router
"""
from fastapi import APIRouter
from app.api.v1 import papers, chat, cross_eval, doi

api_router = APIRouter()

api_router.include_router(papers.router, prefix="/papers", tags=["papers"])
api_router.include_router(chat.router, prefix="/chat", tags=["chat"])
api_router.include_router(cross_eval.router, prefix="/cross-eval", tags=["cross-eval"])
api_router.include_router(doi.router, prefix="/doi", tags=["doi"])
