"""
File serving endpoints.
Handles PDF file serving with token-based auth (for iframes).
"""
import os
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
import jwt

from app.core.security import decode_access_token
from app.services.papers_service import get_paper_by_id

router = APIRouter()


@router.get("/papers/{paper_id}")
async def get_paper_file(paper_id: str, token: str = None):
    """
    Get the PDF file for a paper.
    Accepts token as query param since iframes can't set headers.
    """
    if not token:
        raise HTTPException(status_code=401, detail="Token required")

    try:
        payload = decode_access_token(token)
        user_id = payload.get("sub")
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid token")

    paper = get_paper_by_id(paper_id, user_id)
    if not paper:
        raise HTTPException(status_code=404, detail="Paper not found")

    if not paper.pdf_path or not os.path.exists(paper.pdf_path):
        raise HTTPException(status_code=404, detail="PDF file not found")

    return FileResponse(
        paper.pdf_path,
        media_type="application/pdf",
        filename=f"{paper.title}.pdf",
    )
