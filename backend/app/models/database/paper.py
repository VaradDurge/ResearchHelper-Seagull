"""
# Paper Database Model

## What it does:
SQLAlchemy model for Paper table. Defines database schema for papers.

## How it works:
- Defines Paper table with columns
- Relationships to other tables (workspace, chunks, user)
- Provides ORM interface for paper operations

## What to include:
- Paper model with columns:
  - id: UUID (primary key)
  - title: String
  - authors: JSON (list of authors)
  - abstract: Text (optional)
  - pdf_path: String (file path)
  - pdf_url: String (URL to PDF, optional)
  - doi: String (optional)
  - publication_date: Date (optional)
  - upload_date: DateTime
  - workspace_id: UUID (foreign key)
  - user_id: UUID (foreign key, uploader)
  - status: Enum (processing, ready, error)
  - metadata: JSON (additional metadata)
- Relationships:
  - workspace: Many-to-one with Workspace
  - user: Many-to-one with User
- Indexes on: workspace_id, user_id, upload_date
"""

