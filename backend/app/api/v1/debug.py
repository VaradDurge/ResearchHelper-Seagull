"""
Debug API — rebuild intelligence, status. Protected by auth.
"""
import logging
import os
from fastapi import APIRouter, Depends

from app.api.dependencies import get_current_user_id, get_current_workspace_id
from app.db.mongo import get_papers_collection, get_paper_intelligence_collection
from app.services.intelligence_extraction import run_intelligence_extraction

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/rebuild-intelligence")
async def rebuild_intelligence(
    user_id: str = Depends(get_current_user_id),
    workspace_id: str = Depends(get_current_workspace_id),
):
    """
    Re-run intelligence extraction for all papers in the current workspace.
    Deletes existing paper_intelligence per paper then runs run_intelligence_extraction.
    Returns summary: papers_processed, success_count, failure_count.
    """
    papers_coll = get_papers_collection()
    intel_coll = get_paper_intelligence_collection()
    docs = list(papers_coll.find({"workspace_id": workspace_id}))
    papers_processed = 0
    success_count = 0
    failure_count = 0
    for doc in docs:
        paper_id = doc.get("paper_id")
        pdf_path = doc.get("pdf_path")
        title = doc.get("title") or "Untitled"
        abstract = doc.get("abstract")
        if not paper_id:
            continue
        papers_processed += 1
        try:
            intel_coll.delete_many({"paper_id": paper_id})
        except Exception as e:
            logger.warning("Delete existing intel for %s: %s", paper_id, e)
        if not pdf_path:
            logger.warning("Paper %s has no pdf_path; skipping.", paper_id)
            failure_count += 1
            continue
        try:
            if not os.path.exists(pdf_path):
                logger.warning("PDF file missing for paper %s: %s", paper_id, pdf_path)
                failure_count += 1
                continue
            run_intelligence_extraction(
                paper_id=paper_id,
                pdf_path=pdf_path,
                workspace_id=workspace_id,
                title=title,
                abstract=abstract,
            )
            success_count += 1
        except Exception as e:
            logger.exception("Rebuild intelligence failed for paper_id=%s: %s", paper_id, e)
            failure_count += 1
    return {
        "papers_processed": papers_processed,
        "success_count": success_count,
        "failure_count": failure_count,
    }


@router.get("/intelligence-status")
async def intelligence_status(
    user_id: str = Depends(get_current_user_id),
    workspace_id: str = Depends(get_current_workspace_id),
):
    """
    Return counts for system health: total_papers, intelligence_docs,
    papers_with_embedding, papers_with_keywords, papers_with_methods.
    Scoped to current workspace for papers; intelligence_docs count for workspace.
    """
    papers_coll = get_papers_collection()
    intel_coll = get_paper_intelligence_collection()
    total_papers = papers_coll.count_documents({"workspace_id": workspace_id})
    intel_docs = list(intel_coll.find({"workspace_id": workspace_id}))
    intelligence_docs = len(intel_docs)
    papers_with_embedding = sum(1 for d in intel_docs if d.get("embedding_vector") and len(d.get("embedding_vector") or []) > 0)
    papers_with_keywords = sum(1 for d in intel_docs if d.get("keywords") and len(d.get("keywords") or []) > 0)
    papers_with_methods = sum(1 for d in intel_docs if d.get("methods_used") and len(d.get("methods_used") or []) > 0)
    return {
        "total_papers": total_papers,
        "intelligence_docs": intelligence_docs,
        "papers_with_embedding": papers_with_embedding,
        "papers_with_keywords": papers_with_keywords,
        "papers_with_methods": papers_with_methods,
    }
