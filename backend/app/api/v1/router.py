"""
# Main API Router

## What it does:
Main FastAPI router that includes all v1 API endpoints. Aggregates all route modules
and provides the base router for the application.

## How it works:
- Creates APIRouter instance
- Includes routers from papers, chat, tools, workspace modules
- Sets common prefix ("/api/v1")
- Applies common dependencies (authentication, etc.)

## What to include:
- APIRouter instance
- Include papers router
- Include chat router
- Include tools routers (claim_verify, blueprint, method_reprod, literature, graphs, cross_eval)
- Include workspace router
- Common dependencies (authentication, database session)
- Tags for API documentation
"""

