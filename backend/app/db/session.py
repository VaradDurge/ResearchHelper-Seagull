"""
# Database Session Management

## What it does:
Manages database connections and sessions. Provides SQLAlchemy session factory
and session management utilities.

## How it works:
- Creates SQLAlchemy engine from database URL
- Provides session factory
- Handles session lifecycle
- Provides dependency for FastAPI routes

## What to include:
- create_engine() - Create SQLAlchemy engine
  - Uses DATABASE_URL from config
  - Configures connection pool
  
- SessionLocal - Session factory
  - Creates database sessions
  - Used by dependency injection
  
- get_db() - Dependency function for FastAPI
  - Yields database session
  - Handles session cleanup
  
- Base - SQLAlchemy declarative base
  - Base class for all models
  
- Database initialization
- Connection pooling configuration
"""

