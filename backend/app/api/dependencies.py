"""
# API Dependencies

## What it does:
FastAPI dependency functions for common dependencies used across API routes:
authentication, database session, current user, current workspace.

## How it works:
- Defines dependency functions using FastAPI Depends
- Provides reusable dependencies for routes
- Handles authentication and authorization
- Provides database session management

## What to include:
- get_db() - Database session dependency
  - Yields database session
  - Handles session cleanup
  
- get_current_user() - Current user dependency
  - Validates authentication token
  - Returns current user from database
  - Raises 401 if not authenticated
  
- get_current_workspace() - Current workspace dependency
  - Gets workspace from user's active workspace or request
  - Returns workspace object
  - Raises 404 if workspace not found
  
- Optional: Role-based access control dependencies
"""

