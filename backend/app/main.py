"""
# FastAPI Application Entry Point

## What it does:
Main FastAPI application entry point. Initializes the FastAPI app, configures middleware,
registers routers, and sets up the application lifecycle.

## How it works:
- Creates FastAPI app instance
- Configures CORS for frontend
- Registers API routers (v1)
- Sets up middleware (logging, error handling)
- Configures startup/shutdown events
- Runs the application

## What to include:
- FastAPI app instance creation
- CORS configuration (allow frontend origin)
- API router registration (from app.api.v1.router)
- Middleware setup (logging, request ID, error handling)
- Startup event: database initialization, vector DB connection
- Shutdown event: cleanup connections
- Root endpoint ("/")
- Health check endpoint ("/health")
- uvicorn run configuration (if running directly)
"""

