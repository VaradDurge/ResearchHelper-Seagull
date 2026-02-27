"""
Papers Service - MongoDB storage for paper metadata.
Supports shared workspace access: queries filter by workspace_id so all
collaborators see the same papers.
"""
from datetime import datetime, timezone
from typing import List, Optional
import os

from app.db.mongo import get_papers_collection
from app.models.schemas import PaperResponse, PaperStatus
from app.config import settings
from app.core.vector_db import get_vector_db


def save_paper(paper: PaperResponse) -> PaperResponse:
    """Save paper metadata to MongoDB."""
    papers = get_papers_collection()
    doc = {
        "paper_id": paper.id,
        "title": paper.title,
        "authors": paper.authors,
        "abstract": paper.abstract,
        "doi": paper.doi,
        "publication_date": paper.publication_date,
        "pdf_path": paper.pdf_path,
        "pdf_url": paper.pdf_url,
        "upload_date": paper.upload_date,
        "workspace_id": paper.workspace_id,
        "user_id": paper.user_id,
        "status": paper.status.value,
        "metadata": paper.metadata,
    }
    papers.update_one(
        {"paper_id": paper.id, "workspace_id": paper.workspace_id},
        {"$set": doc},
        upsert=True,
    )
    return paper


def get_papers_by_user(user_id: str, workspace_id: Optional[str] = None) -> List[PaperResponse]:
    """Get papers for a workspace (shared) or fallback to user_id."""
    papers = get_papers_collection()
    if workspace_id:
        query: dict = {"workspace_id": workspace_id}
    else:
        query = {"user_id": user_id}
    docs = papers.find(query).sort("upload_date", -1)
    result = []
    for doc in docs:
        result.append(
            PaperResponse(
                id=doc["paper_id"],
                title=doc["title"],
                authors=doc.get("authors", []),
                abstract=doc.get("abstract"),
                doi=doc.get("doi"),
                publication_date=doc.get("publication_date"),
                pdf_path=doc.get("pdf_path"),
                pdf_url=doc.get("pdf_url"),
                upload_date=doc["upload_date"],
                workspace_id=doc["workspace_id"],
                user_id=doc["user_id"],
                status=PaperStatus(doc["status"]),
                metadata=doc.get("metadata"),
            )
        )
    return result


def get_paper_ids_for_workspace(user_id: str, workspace_id: str) -> List[str]:
    """Return all paper IDs belonging to a workspace (shared access)."""
    papers = get_papers_collection()
    docs = papers.find(
        {"workspace_id": workspace_id},
        {"paper_id": 1},
    )
    return [doc["paper_id"] for doc in docs]


def get_paper_by_id(paper_id: str, user_id: str) -> Optional[PaperResponse]:
    """Get a single paper by ID. Checks workspace membership for shared access."""
    papers = get_papers_collection()
    doc = papers.find_one({"paper_id": paper_id})
    if not doc:
        return None

    # Allow access if the user is the uploader or a workspace member
    from app.services.workspace_service import get_workspace_members
    ws_id = doc.get("workspace_id", "")
    members = get_workspace_members(ws_id) if ws_id else []
    if doc["user_id"] != user_id and user_id not in members:
        return None

    return PaperResponse(
        id=doc["paper_id"],
        title=doc["title"],
        authors=doc.get("authors", []),
        abstract=doc.get("abstract"),
        doi=doc.get("doi"),
        publication_date=doc.get("publication_date"),
        pdf_path=doc.get("pdf_path"),
        pdf_url=doc.get("pdf_url"),
        upload_date=doc["upload_date"],
        workspace_id=doc["workspace_id"],
        user_id=doc["user_id"],
        status=PaperStatus(doc["status"]),
        metadata=doc.get("metadata"),
    )


def delete_paper(paper_id: str, user_id: str) -> bool:
    """Delete a paper and its vectors. Any workspace member can delete."""
    papers = get_papers_collection()
    doc = papers.find_one({"paper_id": paper_id})
    if not doc:
        return False

    from app.services.workspace_service import get_workspace_members
    ws_id = doc.get("workspace_id", "")
    members = get_workspace_members(ws_id) if ws_id else []
    if doc["user_id"] != user_id and user_id not in members:
        return False

    papers.delete_one({"paper_id": paper_id})

    pdf_path = doc.get("pdf_path")
    if pdf_path and os.path.exists(pdf_path):
        try:
            os.remove(pdf_path)
        except Exception:
            pass

    try:
        vector_db = get_vector_db(
            index_path=settings.vector_db_path,
            dimension=settings.embedding_dimension,
        )
        vector_db.delete_by_paper_id(paper_id)
        vector_db.save_index()
    except Exception:
        pass

    try:
        from app.db.mongo import get_paper_intelligence_collection
        get_paper_intelligence_collection().delete_many({"paper_id": paper_id})
    except Exception:
        pass

    return True
