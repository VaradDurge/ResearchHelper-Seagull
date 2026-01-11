"""
# User Database Model

## What it does:
SQLAlchemy model for User table. Defines database schema for users.

## How it works:
- Defines User table with columns
- Relationships to other tables (workspaces, papers)
- Provides ORM interface for user operations

## What to include:
- User model with columns:
  - id: UUID (primary key)
  - email: String (unique)
  - name: String
  - hashed_password: String (optional, if using password auth)
  - created_at: DateTime
  - updated_at: DateTime
  - active_workspace_id: UUID (foreign key to Workspace, optional)
- Relationships:
  - workspaces: One-to-many with Workspace (owned workspaces)
  - papers: One-to-many with Paper (uploaded papers)
  - workspace_memberships: Many-to-many with Workspace (member workspaces)
- Indexes on: email, active_workspace_id
"""

