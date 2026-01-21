"""
Pydantic Schemas for API requests and responses
"""
from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from enum import Enum


class PaperStatus(str, Enum):
    PROCESSING = "processing"
    READY = "ready"
    ERROR = "error"


class PaperBase(BaseModel):
    title: str
    authors: List[str] = Field(default_factory=list)
    abstract: Optional[str] = None
    doi: Optional[str] = None
    publication_date: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class PaperResponse(PaperBase):
    id: str
    pdf_path: Optional[str] = None
    pdf_url: Optional[str] = None
    upload_date: datetime
    workspace_id: str
    user_id: str
    status: PaperStatus
    
    class Config:
        from_attributes = True


class PaperListResponse(BaseModel):
    papers: List[PaperResponse]
    total: int


class ErrorResponse(BaseModel):
    detail: str


class ChatMessageRequest(BaseModel):
    message: str
    paper_ids: Optional[List[str]] = None
    conversation_id: Optional[str] = None


class Citation(BaseModel):
    paper_id: str
    paper_title: str
    page_number: int
    chunk_index: int
    text: str


class ChatResponse(BaseModel):
    answer: str
    citations: List[Citation]
    retrieved_chunks: List[Dict[str, Any]]


class CrossEvalRequest(BaseModel):
    message: str
    paper_ids: Optional[List[str]] = None
    top_k: Optional[int] = 5


class CrossEvalResult(BaseModel):
    paper_id: str
    paper_title: str
    answer: str


class CrossEvalResponse(BaseModel):
    answer: str
    citations: List[Citation]
    per_paper: List[CrossEvalResult]


class DoiLookupRequest(BaseModel):
    dois: List[str]


class DoiLookupResult(BaseModel):
    doi: str
    title: Optional[str] = None
    authors: List[str] = Field(default_factory=list)
    url: Optional[str] = None
    source: Optional[str] = None
    error: Optional[str] = None


class DoiLookupResponse(BaseModel):
    results: List[DoiLookupResult]
