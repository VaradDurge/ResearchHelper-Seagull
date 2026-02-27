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
    conversation_id: Optional[str] = None


# Conversation models
class MessageRole(str, Enum):
    USER = "user"
    ASSISTANT = "assistant"


class Message(BaseModel):
    id: str
    role: MessageRole
    content: str
    citations: List[Citation] = Field(default_factory=list)
    created_at: datetime


class ConversationResponse(BaseModel):
    id: str
    title: str
    user_id: str
    workspace_id: str = ""
    created_at: datetime
    updated_at: datetime
    message_count: int = 0


class ConversationListResponse(BaseModel):
    conversations: List[ConversationResponse]
    total: int


class ConversationDetailResponse(ConversationResponse):
    messages: List[Message] = Field(default_factory=list)


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
    pdf_url: Optional[str] = None
    source: Optional[str] = None
    error: Optional[str] = None


class DoiLookupResponse(BaseModel):
    results: List[DoiLookupResult]


class DoiImportRequest(BaseModel):
    doi: str


class DoiImportResponse(BaseModel):
    paper: PaperResponse


class UserResponse(BaseModel):
    user_id: str
    email: Optional[str] = None
    name: Optional[str] = None
    picture: Optional[str] = None


class GoogleAuthRequest(BaseModel):
    id_token: str


class AuthResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse


class WorkspaceCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)


class WorkspaceUpdateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)


class WorkspaceResponse(BaseModel):
    id: str
    name: str
    user_id: str
    owner_id: str = ""
    collaborators: List[str] = Field(default_factory=list)
    is_shared: bool = False
    is_active: bool = False
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class WorkspaceListResponse(BaseModel):
    workspaces: List[WorkspaceResponse]
    total: int


# --- Invitation schemas ---

class InvitationStatus(str, Enum):
    PENDING = "pending"
    ACCEPTED = "accepted"
    EXPIRED = "expired"
    REVOKED = "revoked"


class InvitationCreateRequest(BaseModel):
    email: str = Field(..., min_length=3, max_length=320)
    delivery_method: str = Field(default="email")


class InvitationResponse(BaseModel):
    id: str
    workspace_id: str
    inviter_id: str
    invitee_email: str
    invite_link: Optional[str] = None
    status: InvitationStatus
    created_at: datetime
    expires_at: datetime


class InvitationListResponse(BaseModel):
    invitations: List[InvitationResponse]
    total: int


class InvitationAcceptResponse(BaseModel):
    workspace: WorkspaceResponse
    message: str = "Invitation accepted"


class InvitationEmailStatusResponse(BaseModel):
    invitation_id: str
    provider_email_id: Optional[str] = None
    provider_status: str = "unknown"
    last_event: Optional[str] = None
    checked_at: datetime
    raw: Optional[Dict[str, Any]] = None


# --- Claim verification (Evidence Confidence Scoring Engine) ---


class ClaimVerifyRequest(BaseModel):
    claim: str
    paper_ids: Optional[List[str]] = None


class ClaimVerifyResponse(BaseModel):
    claim: str
    support_count: int
    contradict_count: int
    neutral_count: int
    evidence_count: int
    confidence_score: float
    confidence_label: str
    evidence_strength: str
    strongest_study_types: List[str] = Field(default_factory=list)
    guardrail_triggered: Optional[str] = None
    scored_evidence: List[Dict[str, Any]] = Field(default_factory=list)


class ClaimVerifyRunItem(BaseModel):
    """One run in the shared workspace history."""
    run_id: str
    user_id: str
    user_name: str
    claim: str
    result: ClaimVerifyResponse
    created_at: datetime


class ClaimVerifyRecentResponse(BaseModel):
    runs: List[ClaimVerifyRunItem]
    total: int


# --- Graph (knowledge graph of papers) ---


class GraphNode(BaseModel):
    id: str
    label: str
    type: str = "paper"
    year: Optional[int] = None
    embedding_cluster: Optional[int] = None


class GraphLink(BaseModel):
    source: str
    target: str
    type: str  # "citation" | "similarity"
    weight: Optional[float] = None


class GraphResponse(BaseModel):
    nodes: List[GraphNode]
    links: List[GraphLink]


# --- Research Intelligence Graph ---


class PaperIntelligence(BaseModel):
    """Stored per-paper extracted intelligence (MongoDB paper_intelligence)."""
    paper_id: str
    embedding_vector: Optional[List[float]] = None
    main_problem: Optional[str] = None
    methods_used: List[str] = Field(default_factory=list)
    key_findings: List[str] = Field(default_factory=list)
    datasets_used: List[str] = Field(default_factory=list)
    keywords: List[str] = Field(default_factory=list)
    domain: Optional[str] = None
    claims: List[str] = Field(default_factory=list)
    extracted_at: Optional[datetime] = None


class IntelligenceGraphNode(BaseModel):
    id: str
    label: str
    type: str  # "paper" | "method" | "dataset" | "concept"
    year: Optional[int] = None
    cluster_id: Optional[int] = None
    is_research_gap: bool = False
    paper_count: Optional[int] = None
    # For paper nodes only: payload for side panel (main_problem, methods_used, etc.)
    main_problem: Optional[str] = None
    methods_used: List[str] = Field(default_factory=list)
    key_findings: List[str] = Field(default_factory=list)
    datasets_used: List[str] = Field(default_factory=list)
    keywords: List[str] = Field(default_factory=list)
    domain: Optional[str] = None
    claims: List[str] = Field(default_factory=list)


class IntelligenceGraphLink(BaseModel):
    source: str
    target: str
    type: str  # "similarity" | "citation" | "keyword_overlap" | "contradiction" | "uses_method" | "uses_dataset" | "has_concept"
    weight: Optional[float] = None


class IntelligenceGraphResponse(BaseModel):
    nodes: List[IntelligenceGraphNode]
    links: List[IntelligenceGraphLink]
    has_intelligence: bool = True
