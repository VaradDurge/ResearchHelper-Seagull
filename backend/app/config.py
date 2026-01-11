"""
# Configuration Module

## What it does:
Centralized configuration management using Pydantic Settings. Loads environment variables
and provides typed configuration for the application.

## How it works:
- Uses pydantic-settings to load environment variables
- Defines Settings class with all configuration options
- Provides default values and validation
- Exports settings instance

## What to include:
- Database configuration: DATABASE_URL, DB_POOL_SIZE, etc.
- Vector DB configuration: VECTOR_DB_TYPE (Pinecone/Qdrant), API keys, index names
- LLM configuration: OPENAI_API_KEY, ANTHROPIC_API_KEY, GROQ_API_KEY, default provider
- Embedding configuration: EMBEDDING_MODEL, embedding dimensions
- Application settings: SECRET_KEY, DEBUG, ENVIRONMENT
- CORS settings: ALLOWED_ORIGINS
- File upload settings: MAX_UPLOAD_SIZE, UPLOAD_DIR
- DOI fetching settings: DOI_API_KEY (optional)
- Settings class with validation
- Settings instance export
"""

