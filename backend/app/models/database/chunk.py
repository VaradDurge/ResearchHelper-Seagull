"""
# Chunk Database Model

## What it does:
SQLAlchemy model for Chunk table. Stores chunk metadata (chunks themselves are in vector DB).

## How it works:
- Defines Chunk table with columns
- Relationships to Paper table
- Provides ORM interface for chunk operations

## What to include:
- Chunk model with columns:
  - id: UUID (primary key)
  - paper_id: UUID (foreign key to Paper)
  - chunk_index: Integer (order in paper)
  - page_number: Integer
  - text: Text (chunk text)
  - start_char: Integer (character position in page)
  - end_char: Integer
  - vector_id: String (ID in vector DB)
  - metadata: JSON (additional metadata)
- Relationships:
  - paper: Many-to-one with Paper
- Indexes on: paper_id, page_number
- Note: Embeddings stored in vector DB, not in this table
"""

