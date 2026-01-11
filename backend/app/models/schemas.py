"""
# Pydantic Schemas

## What it does:
Pydantic models for request/response validation and serialization. Defines the
shape of data exchanged between frontend and backend.

## How it works:
- Defines Pydantic models for all API requests and responses
- Provides validation and serialization
- Used by FastAPI for automatic validation and OpenAPI docs

## What to include:
- Request schemas:
  - PaperUploadRequest, DOIImportRequest
  - ChatMessageRequest, ClaimVerifyRequest, BlueprintRequest, etc.
  
- Response schemas:
  - PaperResponse, PaperListResponse
  - ChatResponse, MessageResponse
  - VerificationResult, Blueprint, MethodDetails, etc.
  
- Common schemas:
  - Citation, Chunk, Embedding
  - PaginationParams, ErrorResponse
  
- All schemas should match TypeScript types in frontend
- Use Field() for validation rules
- Use Optional for nullable fields
"""

