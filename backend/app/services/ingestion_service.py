"""
# Ingestion Service

## What it does:
Service layer for paper ingestion. Handles PDF parsing, DOI fetching, chunking,
embedding generation, and storage. Main entry point for adding papers to the system.

## How it works:
- Orchestrates the ingestion pipeline
- Parses PDFs to extract text
- Chunks text using chunking module
- Generates embeddings using embeddings module
- Stores chunks in vector DB
- Stores paper metadata in database

## What to include:
- ingest_pdf(pdf_file: UploadFile, workspace_id: str, user_id: str) -> Paper
  - Main PDF ingestion function
  - Steps:
    1. Save PDF file
    2. Parse PDF to extract text (page-wise)
    3. Extract metadata (title, authors, etc.)
    4. Chunk text using chunking module
    5. Generate embeddings for chunks
    6. Store chunks in vector DB
    7. Store paper in database
    8. Return paper object
  
- import_from_doi(doi: str, workspace_id: str, user_id: str) -> Paper
  - Fetches paper from DOI
  - Downloads PDF
  - Calls ingest_pdf() with downloaded PDF
  - Returns paper object
  
- Uses pdf_parser for PDF parsing
- Uses chunking module for text chunking
- Uses embeddings module for embedding generation
- Uses vector_db for chunk storage
- Uses paper_service for database operations
"""

