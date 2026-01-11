"""
# Database Initialization

## What it does:
Initializes database: creates tables, runs migrations, seeds initial data (optional).

## How it works:
- Creates all database tables from models
- Runs Alembic migrations (if using)
- Seeds initial data (optional)

## What to include:
- init_db() - Initialize database
  - Creates all tables
  - Runs migrations
  
- create_tables() - Create tables from models
  - Uses Base.metadata.create_all()
  
- seed_data() - Seed initial data (optional)
  - Creates default workspace
  - Creates admin user (optional)
  
- Run on application startup
- Handles database already exists errors
"""

