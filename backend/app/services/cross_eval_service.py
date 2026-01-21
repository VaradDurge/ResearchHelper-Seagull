"""
Cross-evaluation service.
Generates per-paper answers and formats them as a markdown table.
"""
from typing import List, Optional, Dict, Any

from app.config import settings
from app.core.rag import retrieve, generate_answer
from app.core.vector_db import get_vector_db
from app.models.schemas import CrossEvalResponse, CrossEvalResult


def _get_all_paper_ids(vector_db) -> List[str]:
    paper_ids = {
        metadata.get("paper_id")
        for metadata in vector_db.metadata.values()
        if metadata.get("paper_id")
    }
    return sorted(paper_ids)


def _get_paper_title(vector_db, paper_id: str) -> str:
    for metadata in vector_db.metadata.values():
        if metadata.get("paper_id") == paper_id and metadata.get("paper_title"):
            return metadata["paper_title"]
    return paper_id


def _escape_table_cell(text: str) -> str:
    if not text:
        return "Not found in the documents."
    return (
        text.replace("|", r"\|")
        .replace("\r\n", "\n")
        .replace("\r", "\n")
        .replace("\n", "<br />")
        .strip()
    )


def _build_markdown_table(rows: List[CrossEvalResult]) -> str:
    if not rows:
        return "No papers available. Upload papers to run cross-evaluation."

    headers = [row.paper_title or row.paper_id for row in rows]
    header_line = "| " + " | ".join(headers) + " |"
    separator_line = "| " + " | ".join(["---"] * len(headers)) + " |"
    answers_line = "| " + " | ".join(_escape_table_cell(row.answer) for row in rows) + " |"
    return "\n".join([header_line, separator_line, answers_line])


def cross_evaluate(
    message: str,
    paper_ids: Optional[List[str]] = None,
    top_k: int = 5,
) -> CrossEvalResponse:
    vector_db = get_vector_db(
        index_path=settings.vector_db_path,
        dimension=settings.embedding_dimension,
    )

    selected_paper_ids = paper_ids or _get_all_paper_ids(vector_db)
    if not selected_paper_ids:
        return CrossEvalResponse(answer=_build_markdown_table([]), citations=[], per_paper=[])

    results: List[CrossEvalResult] = []
    all_citations: List[Dict[str, Any]] = []

    for paper_id in selected_paper_ids:
        retrieved = retrieve(message, paper_ids=[paper_id], top_k=top_k)
        rag_response = generate_answer(message, retrieved)

        paper_title = _get_paper_title(vector_db, paper_id)

        results.append(
            CrossEvalResult(
                paper_id=paper_id,
                paper_title=paper_title,
                answer=rag_response.answer,
            )
        )
        all_citations.extend(rag_response.citations)

    table = _build_markdown_table(results)
    return CrossEvalResponse(answer=table, citations=all_citations, per_paper=results)
