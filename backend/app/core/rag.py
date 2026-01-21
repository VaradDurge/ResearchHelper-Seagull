"""
RAG (Retrieval-Augmented Generation) Module
Minimal retrieval + generation pipeline for grounded answers.
"""
from dataclasses import dataclass
from typing import List, Dict, Any, Optional

from app.config import settings
from app.core.embeddings import generate_embedding
from app.core.vector_db import get_vector_db
from app.core.llm import generate_completion

PROMPT_TEMPLATE = (
    "You are a helpful assistant. Use ONLY the context inside <context> tags. "
    "If the answer is not present in the context, respond with: "
    "\"Not found in the documents.\"\n\n"
    "<context>\n{context}\n</context>\n\n"
    "Question:\n{question}\n"
)


@dataclass
class RAGResponse:
    answer: str
    citations: List[Dict[str, Any]]
    retrieved_chunks: List[Dict[str, Any]]


def retrieve(query: str, paper_ids: Optional[List[str]] = None, top_k: int = 5) -> List[Dict[str, Any]]:
    """Retrieve relevant chunks from the vector database."""
    vector_db = get_vector_db(
        index_path=settings.vector_db_path,
        dimension=settings.embedding_dimension,
    )
    query_vector = generate_embedding(query)
    return vector_db.search(query_vector, top_k=top_k, paper_ids=paper_ids)


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


def generate_answer(query: str, chunks: List[Dict[str, Any]]) -> RAGResponse:
    """Generate an answer grounded in retrieved chunks."""
    if not chunks:
        return RAGResponse(
            answer="Not found in the documents.",
            citations=[],
            retrieved_chunks=[],
        )

    prompt = build_prompt(query, chunks)
    answer = generate_completion(prompt)
    if not answer:
        answer = "Not found in the documents."

    return RAGResponse(
        answer=answer,
        citations=_build_citations(chunks),
        retrieved_chunks=chunks,
    )

