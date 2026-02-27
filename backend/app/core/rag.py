"""
RAG (Retrieval-Augmented Generation) Module
Minimal retrieval + generation pipeline for grounded answers.
"""
from dataclasses import dataclass
from typing import List, Dict, Any, Optional, Tuple
import re

from app.config import settings
from app.core.embeddings import generate_embedding
from app.core.vector_db import get_vector_db
from app.core.llm import generate_completion

PROMPT_TEMPLATE = (
    "You are a helpful assistant. Use ONLY the context inside <context> tags. "
    "If the context is empty or says \"No context.\", respond with: "
    "\"Not found in the documents.\" Otherwise, answer using the context. "
    "If the exact answer is unclear, say so and summarize the most relevant "
    "information from the context.\n\n"
    "<context>\n{context}\n</context>\n\n"
    "Question:\n{question}\n"
)


@dataclass
class RAGResponse:
    answer: str
    citations: List[Dict[str, Any]]
    retrieved_chunks: List[Dict[str, Any]]


def retrieve(
    query: str,
    paper_ids: Optional[List[str]] = None,
    top_k: int = 5,
    workspace_id: Optional[str] = None,
    user_id: Optional[str] = None
) -> List[Dict[str, Any]]:
    """Retrieve relevant chunks from the vector database, scoped by workspace and/or paper_ids."""
    vector_db = get_vector_db(
        index_path=settings.vector_db_path,
        dimension=settings.embedding_dimension,
    )
    query_vector = generate_embedding(query)
    return vector_db.search(
        query_vector,
        top_k=top_k,
        paper_ids=paper_ids,
        workspace_id=workspace_id,
        user_id=user_id,
    )


def build_prompt(query: str, chunks: List[Dict[str, Any]]) -> str:
    """Build a single prompt that includes all retrieved context."""
    context_blocks: List[str] = []
    for idx, chunk in enumerate(chunks, start=1):
        metadata = chunk.get("metadata", {})
        text = metadata.get("text", "")
        paper_id = metadata.get("paper_id", "unknown")
        page_number = metadata.get("page_number", "N/A")
        chunk_index = metadata.get("chunk_index", "N/A")
        context_blocks.append(
            f"[{idx}] paper_id={paper_id} page={page_number} chunk={chunk_index}\n{text}"
        )

    context = "\n\n".join(context_blocks).strip()
    if not context:
        context = "No context."
    return PROMPT_TEMPLATE.format(context=context, question=query)


def _build_citations(chunks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    citations: List[Dict[str, Any]] = []
    for chunk in chunks:
        metadata = chunk.get("metadata", {})
        citations.append(
            {
                "paper_id": metadata.get("paper_id", "unknown"),
                "paper_title": metadata.get("paper_title", "Unknown"),
                "page_number": int(metadata.get("page_number", 0) or 0),
                "chunk_index": int(metadata.get("chunk_index", 0) or 0),
                "text": metadata.get("text", ""),
            }
        )
    return citations


def generate_answer(
    query: str,
    chunks: List[Dict[str, Any]],
    chat_history: Optional[List[Dict[str, str]]] = None,
) -> RAGResponse:
    """Generate an answer grounded in retrieved chunks, with conversation memory."""
    if not chunks:
        return RAGResponse(
            answer="Not found in the documents.",
            citations=[],
            retrieved_chunks=[],
        )

    prompt = build_prompt(query, chunks)
    answer = generate_completion(prompt, chat_history=chat_history)
    if not answer:
        answer = "Not found in the documents."

    return RAGResponse(
        answer=answer,
        citations=_build_citations(chunks),
        retrieved_chunks=chunks,
    )


_QUESTION_LIST_HINTS = (
    "what are the questions",
    "list the questions",
    "list questions",
    "show questions",
    "questions in the document",
    "questions in the pdf",
    "all questions",
    "question list",
)


def is_question_list_request(query: str) -> bool:
    normalized = " ".join(query.lower().strip().split())
    if not normalized:
        return False
    if normalized in _QUESTION_LIST_HINTS:
        return True
    if "question" not in normalized:
        return False
    return any(
        hint in normalized
        for hint in ("what are", "list", "show", "all", "questions")
    )


def _extract_questions_from_text(text: str) -> List[str]:
    if not text:
        return []
    if "?" not in text:
        return []
    normalized = " ".join(text.split())
    if "?" not in normalized:
        return []
    segments = re.split(r"(?<=[?])\s+", normalized)
    questions: List[str] = []
    for segment in segments:
        if "?" not in segment:
            continue
        question = segment.strip()
        if not question:
            continue
        if not question.endswith("?"):
            question = question[: question.rfind("?") + 1]
        if len(question) < 5:
            continue
        questions.append(question)
    return questions


def _normalize_question(question: str) -> str:
    return re.sub(r"\s+", " ", question.strip()).lower()


def list_questions(
    paper_ids: Optional[List[str]] = None,
    workspace_id: Optional[str] = None,
    user_id: Optional[str] = None,
    max_questions: int = 200,
    max_chunks: int = 2000,
    offset: int = 0,
    limit: int = 100,
) -> Tuple[List[str], List[Dict[str, Any]], bool]:
    """Scan indexed chunks and return extracted questions, scoped by workspace and/or paper_ids."""
    vector_db = get_vector_db(
        index_path=settings.vector_db_path,
        dimension=settings.embedding_dimension,
    )
    questions: List[str] = []
    citations: List[Dict[str, Any]] = []
    seen = set()
    truncated = False

    scanned_chunks = 0
    stop_early = False
    target_count = max(offset + limit, 0)

    paper_ids_set = set(paper_ids) if paper_ids else None
    for metadata in vector_db.metadata.values():
        if paper_ids_set and metadata.get("paper_id") not in paper_ids_set:
            continue
        meta_ws = metadata.get("workspace_id")
        if workspace_id and meta_ws is not None and meta_ws != workspace_id:
            continue
        if user_id:
            metadata_user_id = metadata.get("user_id")
            if metadata_user_id and metadata_user_id != user_id:
                continue
        scanned_chunks += 1
        if scanned_chunks > max_chunks:
            truncated = True
            break
        text = metadata.get("text", "")
        for question in _extract_questions_from_text(text):
            key = _normalize_question(question)
            if key in seen:
                continue
            seen.add(key)
            questions.append(question)
            if len(citations) < 20:
                citations.append(
                    {
                        "paper_id": metadata.get("paper_id", "unknown"),
                        "paper_title": metadata.get("paper_title", "Unknown"),
                        "page_number": int(metadata.get("page_number", 0) or 0),
                        "chunk_index": int(metadata.get("chunk_index", 0) or 0),
                        "text": text,
                    }
                )
            if len(questions) >= max_questions:
                truncated = True
                stop_early = True
                break
            if target_count and len(questions) >= target_count:
                truncated = True
                stop_early = True
                break
        if truncated:
            break

    if stop_early:
        return questions[offset:offset + limit], citations, True

    return questions[offset:offset + limit], citations, truncated

