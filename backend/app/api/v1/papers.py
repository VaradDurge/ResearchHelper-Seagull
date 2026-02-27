"""
Papers API Endpoints with real-time broadcast.
"""
from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
from pathlib import Path
import os
import uuid
import logging

from app.models.schemas import PaperResponse, PaperListResponse, PaperStatus
from app.api.dependencies import get_current_user_id, get_current_workspace_id
from app.config import settings
from app.services.ingestion_service import ingest_pdf
from app.services.papers_service import (
    save_paper,
    get_papers_by_user,
    get_paper_by_id,
    delete_paper as delete_paper_service,
)
from app.core.ws_manager import manager

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/", response_model=PaperResponse)
async def upload_paper(
    file: UploadFile = File(...),
    user_id: str = Depends(get_current_user_id),
    workspace_id: str = Depends(get_current_workspace_id),
):
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are allowed")

    file_content = await file.read()
    file_size = len(file_content)

    if file_size > settings.max_upload_size:
        raise HTTPException(
            status_code=413,
            detail=f"File size exceeds maximum allowed size of {settings.max_upload_size / (1024*1024):.1f}MB",
        )

    if file_size == 0:
        raise HTTPException(status_code=400, detail="Uploaded file is empty")

    file_path = None
    try:
        paper_id = str(uuid.uuid4())
        file_extension = Path(file.filename).suffix
        saved_filename = f"{paper_id}{file_extension}"
        file_path = os.path.join(settings.upload_dir, saved_filename)

        os.makedirs(settings.upload_dir, exist_ok=True)
        with open(file_path, "wb") as buffer:
            buffer.write(file_content)

        logger.info(f"Starting PDF ingestion for paper {paper_id}")
        paper_response = ingest_pdf(
            pdf_path=file_path,
            paper_id=paper_id,
            workspace_id=workspace_id,
            user_id=user_id,
            original_filename=file.filename,
        )

        save_paper(paper_response)
        logger.info(f"Successfully processed PDF for paper {paper_id}")

        # Trigger intelligence extraction in background (embedding + LLM extraction)
        try:
            import threading
            from app.services.intelligence_extraction import run_intelligence_extraction
            threading.Thread(
                target=run_intelligence_extraction,
                kwargs={
                    "paper_id": paper_response.id,
                    "pdf_path": file_path,
                    "workspace_id": workspace_id,
                    "title": paper_response.title,
                    "abstract": paper_response.abstract,
                },
                daemon=True,
            ).start()
        except Exception as e:
            logger.warning("Failed to start intelligence extraction: %s", e)

        await manager.broadcast(
            workspace_id,
            {
                "type": "paper_added",
                "payload": {
                    "paper_id": paper_response.id,
                    "title": paper_response.title,
                    "user_id": user_id,
                },
            },
            exclude_user=user_id,
        )

        return paper_response

    except Exception as e:
        if file_path and os.path.exists(file_path):
            try:
                os.remove(file_path)
            except Exception:
                pass
        raise HTTPException(status_code=500, detail=f"Error uploading file: {str(e)}")


@router.get("/", response_model=PaperListResponse)
async def list_papers(
    user_id: str = Depends(get_current_user_id),
    workspace_id: str = Depends(get_current_workspace_id),
):
    papers = get_papers_by_user(user_id, workspace_id=workspace_id)
    return PaperListResponse(papers=papers, total=len(papers))


@router.get("/{paper_id}", response_model=PaperResponse)
async def get_paper(paper_id: str, user_id: str = Depends(get_current_user_id)):
    paper = get_paper_by_id(paper_id, user_id)
    if not paper:
        raise HTTPException(status_code=404, detail="Paper not found")
    return paper


@router.delete("/{paper_id}")
async def delete_paper(
    paper_id: str,
    user_id: str = Depends(get_current_user_id),
    workspace_id: str = Depends(get_current_workspace_id),
):
    success = delete_paper_service(paper_id, user_id)
    if not success:
        raise HTTPException(status_code=404, detail="Paper not found")

    await manager.broadcast(
        workspace_id,
        {
            "type": "paper_deleted",
            "payload": {"paper_id": paper_id, "user_id": user_id},
        },
        exclude_user=user_id,
    )

    return {"message": "Paper deleted successfully"}
