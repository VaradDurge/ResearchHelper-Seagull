"""
Papers Service - MongoDB storage for paper metadata.
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
        {"paper_id": paper.id, "user_id": paper.user_id},
        {"$set": doc},
        upsert=True,
    )
    return paper


def get_papers_by_user(user_id: str) -> List[PaperResponse]:
    """Get all papers for a user."""
    papers = get_papers_collection()
    docs = papers.find({"user_id": user_id}).sort("upload_date", -1)
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


def get_paper_by_id(paper_id: str, user_id: str) -> Optional[PaperResponse]:
    """Get a single paper by ID."""
    papers = get_papers_collection()
    doc = papers.find_one({"paper_id": paper_id, "user_id": user_id})
    if not doc:
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
    """Delete a paper and its vectors."""
    papers = get_papers_collection()
    doc = papers.find_one({"paper_id": paper_id, "user_id": user_id})
    if not doc:
        return False

    # Delete from MongoDB
    papers.delete_one({"paper_id": paper_id, "user_id": user_id})

    # Delete PDF file
    pdf_path = doc.get("pdf_path")
    if pdf_path and os.path.exists(pdf_path):
        try:
            os.remove(pdf_path)
        except Exception:
            pass

    # Delete vectors from FAISS
    try:
        vector_db = get_vector_db(
            index_path=settings.vector_db_path,
            dimension=settings.embedding_dimension,
        )
        vector_db.delete_by_paper_id(paper_id)
        vector_db.save_index()
    except Exception:
        pass

    return True
