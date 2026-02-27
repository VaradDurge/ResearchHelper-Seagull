"""
Ingestion Service
Service layer for paper ingestion. Handles PDF parsing, chunking, embedding generation, and storage.
"""
from typing import List, Optional
import os
import uuid
import logging
from pathlib import Path

from app.utils.pdf_parser import parse_pdf
from app.core.chunking import chunk_text, Chunk
from app.core.embeddings import generate_embeddings_batch, get_embedding_dimensions
from app.core.vector_db import get_vector_db
from app.config import settings
from app.models.schemas import PaperResponse, PaperStatus
from app.verification.metadata_enrichment import enrich_metadata_at_ingestion
from datetime import datetime

logger = logging.getLogger(__name__)


def ingest_pdf(
    pdf_path: str,
    paper_id: str,
    workspace_id: str,
    user_id: str,
    original_filename: str = None,
    paper_metadata: Optional[dict] = None,
) -> PaperResponse:
    """
    Main PDF ingestion function.
    
    Steps:
    1. Parse PDF to extract text (page-wise)
    2. Extract metadata (title, authors, etc.)
    3. Chunk text using chunking module
    4. Generate embeddings for chunks
    5. Store chunks in vector DB
    6. Return paper object
    
    Args:
        pdf_path: Path where PDF is saved
        paper_id: Unique ID for the paper
        workspace_id: Workspace ID
        user_id: User ID
        original_filename: Original filename of the uploaded file
        
    Returns:
        PaperResponse object with paper metadata
    """
    try:
        # Step 1: Parse PDF to extract text
        logger.info(f"Parsing PDF: {pdf_path}")
        pdf_data = parse_pdf(pdf_path)
        
        # Step 2: Extract metadata
        metadata = pdf_data.metadata
        title = metadata.title or (Path(original_filename).stem if original_filename else "Untitled")
        authors = metadata.authors or []
        abstract = metadata.abstract
        
        # Step 3: Chunk text from all pages
        logger.info(f"Chunking text from {len(pdf_data.pages)} pages")
        all_chunks: List[Chunk] = []
        
        for page in pdf_data.pages:
            if page.text.strip():  # Only chunk non-empty pages
                page_chunks = chunk_text(
                    text=page.text,
                    page_number=page.page_number,
                    paper_id=paper_id,
                    chunk_size=settings.chunk_size,
                    overlap=settings.chunk_overlap
                )
                all_chunks.extend(page_chunks)
        
        logger.info(f"Created {len(all_chunks)} chunks")
        
        if not all_chunks:
            raise Exception("No text could be extracted from PDF")
        
        # Step 4: Generate embeddings for all chunks
        logger.info("Generating embeddings...")
        chunk_texts = [chunk.text for chunk in all_chunks]
        embeddings = generate_embeddings_batch(chunk_texts)
        
        if len(embeddings) != len(all_chunks):
            raise Exception(f"Embedding generation failed: expected {len(all_chunks)} embeddings, got {len(embeddings)}")
        
        # Step 5: Store chunks in vector DB
        logger.info("Storing chunks in vector database...")
        vector_db = get_vector_db(
            index_path=settings.vector_db_path,
            dimension=get_embedding_dimensions()
        )
        
        # Prepare vectors and metadata for FAISS
        vector_ids = []
        metadata_list = []
        
        for i, chunk in enumerate(all_chunks):
            vector_id = f"{paper_id}_chunk_{chunk.chunk_index}_page_{chunk.page_number}"
            vector_ids.append(vector_id)
            
            chunk_meta = {
                "paper_id": paper_id,
                "paper_title": title,
                "user_id": user_id,
                "workspace_id": workspace_id,
                "chunk_index": chunk.chunk_index,
                "page_number": chunk.page_number,
                "text": chunk.text,
                "start_char": chunk.start_char,
                "end_char": chunk.end_char,
            }
            metadata_list.append(enrich_metadata_at_ingestion(chunk_meta, paper_metadata))
        
        # Upsert vectors to FAISS
        vector_db.upsert_vectors(
            vectors=embeddings,
            vector_ids=vector_ids,
            metadata_list=metadata_list
        )
        
        # Save index to disk
        vector_db.save_index()
        
        logger.info(f"Successfully ingested PDF with {len(all_chunks)} chunks")
        
        # Step 6: Create and return paper response
        paper_response = PaperResponse(
            id=paper_id,
            title=title,
            authors=authors,
            abstract=abstract,
            pdf_path=pdf_path,
            pdf_url=None,  # TODO: Generate URL if serving files
            upload_date=datetime.utcnow(),
            workspace_id=workspace_id,
            user_id=user_id,
            status=PaperStatus.READY,
            metadata={
                "original_filename": original_filename or "unknown.pdf",
                "file_size": os.path.getsize(pdf_path),
                "num_pages": len(pdf_data.pages),
                "num_chunks": len(all_chunks),
            }
        )
        
        return paper_response
        
    except Exception as e:
        logger.error(f"Error ingesting PDF: {str(e)}", exc_info=True)
        raise Exception(f"Failed to ingest PDF: {str(e)}")
