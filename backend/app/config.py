"""
Configuration Module
"""
import os
from typing import List

from dotenv import load_dotenv
from pydantic_settings import BaseSettings, SettingsConfigDict

load_dotenv()


class Settings(BaseSettings):
    # Database
    database_url: str = "sqlite:///./researchhelper.db"
    mongodb_uri: str = ""
    mongo_db: str = "Seagull"
    
    # Application
    secret_key: str = "dev-secret-key-change-in-production"
    jwt_secret: str = ""
    jwt_algorithm: str = "HS256"
    jwt_exp_minutes: int = 60 * 24 * 7  # 7 days
    debug: bool = True
    environment: str = "development"
    
    # Auth
    google_client_id: str = ""
    
    # CORS
    allowed_origins: List[str] = ["http://localhost:3000", "http://127.0.0.1:3000"]
    
    # File Upload
    max_upload_size: int = 50 * 1024 * 1024  # 50MB
    upload_dir: str = "./uploads"
    
    # Vector Database
    vector_db_path: str = "./vector_db/faiss.index"
    embedding_dimension: int = 384  # Dimension for all-MiniLM-L6-v2

    # LLM
    openai_api_key: str = os.getenv("OPENAI_API_KEY", "")
    openai_model: str = "gpt-4o-mini"

    # Chunking
    chunk_size: int = 1000
    chunk_overlap: int = 200
    
    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=False,
        extra="ignore"
    )


settings = Settings()
