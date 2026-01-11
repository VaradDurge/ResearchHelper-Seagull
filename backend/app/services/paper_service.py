"""
# Paper Service

## What it does:
Service layer for paper-related business logic. Handles paper CRUD operations,
chunk management, and paper metadata operations.

## How it works:
- Provides high-level functions for paper operations
- Uses database models for persistence
- Uses vector_db for chunk storage
- Coordinates between database and vector DB

## What to include:
- create_paper(metadata: PaperMetadata, pdf_path: str, workspace_id: str) -> Paper
  - Creates paper record in database
  - Stores PDF file path
  - Returns paper object
  
- get_paper(paper_id: str) -> Paper
  - Retrieves paper from database
  - Returns paper with metadata
  
- get_papers(workspace_id: str, limit: int, offset: int) -> List[Paper]
  - Lists papers in workspace
  - Supports pagination
  
- delete_paper(paper_id: str) -> None
  - Deletes paper from database
  - Deletes associated chunks from vector DB
  - Deletes PDF file
  
- get_chunks(paper_id: str) -> List[Chunk]
  - Retrieves chunks for paper from vector DB
  - Returns chunks with metadata
  
- update_paper_metadata(paper_id: str, metadata: PaperMetadata) -> Paper
  - Updates paper metadata
"""

