"""
# Workspace Database Model

## What it does:
SQLAlchemy model for Workspace table. Defines database schema for workspaces.

## How it works:
- Defines Workspace table with columns
- Relationships to other tables (papers, users)
- Provides ORM interface for workspace operations

## What to include:
- Workspace model with columns:
  - id: UUID (primary key)
  - name: String
  - description: Text (optional)
  - created_at: DateTime
  - updated_at: DateTime
  - owner_id: UUID (foreign key to User)
  - is_active: Boolean (user's active workspace)
- Relationships:
  - owner: Many-to-one with User
  - papers: One-to-many with Paper
  - members: Many-to-many with User (workspace members)
- Indexes on: owner_id, created_at
"""

