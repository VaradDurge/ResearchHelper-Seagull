"""
FastAPI Application Entry Point - Seagull Research Platform
"""
from contextlib import asynccontextmanager
import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.api.v1.router import api_router
import os

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
logging.getLogger("uvicorn.access").setLevel(logging.INFO)

os.makedirs(settings.upload_dir, exist_ok=True)


def _verify_and_rebuild_faiss():
    """Check FAISS index consistency and rebuild from MongoDB if corrupted."""
    from app.core.vector_db import get_vector_db

    vector_db = get_vector_db(
        index_path=settings.vector_db_path,
        dimension=settings.embedding_dimension,
    )

    ntotal = vector_db.index.ntotal if vector_db.index else 0
    meta_count = len(vector_db.metadata)

    valid_ids = {int(k) for k in vector_db.metadata}
    max_meta_id = max(valid_ids) if valid_ids else -1
    has_gap = meta_count > 0 and (max_meta_id >= ntotal)
    has_desync = ntotal > 0 and meta_count > 0 and meta_count != ntotal

    if ntotal == 0 and meta_count == 0:
        print("[FAISS] Index is empty — nothing to verify.")
        return
    if not has_gap and not has_desync:
        print(f"[FAISS] Index looks healthy (vectors={ntotal}, metadata={meta_count}).")
        return

    print(
        f"[FAISS] Index is INCONSISTENT (vectors={ntotal}, metadata={meta_count}, "
        f"max_id={max_meta_id}). Rebuilding..."
    )
    _rebuild_faiss_index(vector_db)


def _rebuild_faiss_index(vector_db):
    """Rebuild the entire FAISS index by re-ingesting every paper in MongoDB."""
    from app.db.mongo import get_papers_collection
    from app.utils.pdf_parser import parse_pdf
    from app.core.chunking import chunk_text
    from app.core.embeddings import generate_embeddings_batch, get_embedding_dimensions

    vector_db._initialize_index()
    vector_db.metadata = {}

    papers = list(get_papers_collection().find())
    if not papers:
        logger.info("No papers in MongoDB — saving empty FAISS index.")
        vector_db.save_index()
        return

    total_chunks = 0
    for doc in papers:
        paper_id = doc["paper_id"]
        pdf_path = doc.get("pdf_path", "")
        user_id = doc.get("user_id", "")
        title = doc.get("title", "Untitled")

        if not pdf_path or not os.path.exists(pdf_path):
            logger.warning("PDF missing for paper %s (%s) — skipping.", paper_id, pdf_path)
            continue

        try:
            pdf_data = parse_pdf(pdf_path)
            all_chunks = []
            for page in pdf_data.pages:
                if page.text.strip():
                    all_chunks.extend(
                        chunk_text(
                            text=page.text,
                            page_number=page.page_number,
                            paper_id=paper_id,
                            chunk_size=settings.chunk_size,
                            overlap=settings.chunk_overlap,
                        )
                    )
            if not all_chunks:
                continue

            embeddings = generate_embeddings_batch([c.text for c in all_chunks])
            vector_ids = [
                f"{paper_id}_chunk_{c.chunk_index}_page_{c.page_number}"
                for c in all_chunks
            ]
            metadata_list = [
                {
                    "paper_id": paper_id,
                    "paper_title": title,
                    "user_id": user_id,
                    "chunk_index": c.chunk_index,
                    "page_number": c.page_number,
                    "text": c.text,
                    "start_char": c.start_char,
                    "end_char": c.end_char,
                }
                for c in all_chunks
            ]
            vector_db.upsert_vectors(embeddings, vector_ids, metadata_list)
            total_chunks += len(all_chunks)
            logger.info("Re-indexed paper %s (%d chunks).", paper_id, len(all_chunks))
        except Exception:
            logger.exception("Failed to re-index paper %s — skipping.", paper_id)

    vector_db.save_index()
    print(f"[FAISS] Rebuild complete: {len(papers)} papers, {total_chunks} chunks.")


def _validate_openai_api_key():
    """Raise at startup if OPENAI_API_KEY is not set (required for LLM extraction and optional embeddings)."""
    key = os.getenv("OPENAI_API_KEY")
    if not key or not str(key).strip():
        raise RuntimeError(
            "OPENAI_API_KEY is not set. Set it in the environment or in a .env file in the project root. "
            "Example: OPENAI_API_KEY=sk-your-key-here"
        )
    logger.info("OPENAI_API_KEY is set (length=%s).", len(str(key).strip()))


@asynccontextmanager
async def lifespan(app: FastAPI):
    _validate_openai_api_key()
    _verify_and_rebuild_faiss()
    yield


app = FastAPI(
    title="ResearchHelper API",
    version="1.0.0",
    description="API for ResearchHelper - PDF paper management and RAG chat",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix="/api/v1")

@app.get("/")
def root():
    return {"message": "ResearchHelper API", "version": "1.0.0"}

@app.get("/health")
def health():
    return {"status": "healthy"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
