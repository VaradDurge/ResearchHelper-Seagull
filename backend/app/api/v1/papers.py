"""
# Papers API Endpoints

## What it does:
FastAPI route handlers for paper-related operations: upload, list, get, delete, import from DOI.

## How it works:
- Defines API endpoints for paper operations
- Uses dependency injection for database session and authentication
- Calls paper_service for business logic
- Returns Pydantic response models
- Handles file uploads (multipart form data)

## What to include:
- POST /papers - Upload PDF file
  - Request: multipart form with file
  - Response: PaperResponse with paper ID, metadata
  - Calls: ingestion_service.ingest_pdf()
  
- GET /papers - List all papers in workspace
  - Query params: workspace_id (from auth), limit, offset
  - Response: List[PaperResponse]
  - Calls: paper_service.get_papers()
  
- GET /papers/{paper_id} - Get single paper
  - Path param: paper_id
  - Response: PaperResponse with full details
  - Calls: paper_service.get_paper()
  
- DELETE /papers/{paper_id} - Delete paper
  - Path param: paper_id
  - Response: success message
  - Calls: paper_service.delete_paper()
  
- POST /papers/import-doi - Import paper from DOI
  - Request body: DOI string
  - Response: PaperResponse
  - Calls: ingestion_service.import_from_doi()
  
- GET /papers/{paper_id}/chunks - Get paper chunks
  - Path param: paper_id
  - Response: List[ChunkResponse]
  - Calls: paper_service.get_chunks()
"""

