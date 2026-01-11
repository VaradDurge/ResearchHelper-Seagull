"""
# Pytest Configuration and Fixtures

## What it does:
Pytest configuration and shared fixtures for all tests. Provides test database,
test clients, and common test utilities.

## How it works:
- Defines pytest fixtures
- Sets up test database
- Provides test FastAPI client
- Provides test data factories

## What to include:
- test_db - Test database session fixture
  - Creates test database
  - Yields test session
  - Cleans up after test
  
- client - FastAPI test client fixture
  - Creates test client
  - Provides authenticated client (optional)
  
- test_user - Test user fixture
  - Creates test user
  - Returns user object
  
- test_workspace - Test workspace fixture
  - Creates test workspace
  - Returns workspace object
  
- test_paper - Test paper fixture
  - Creates test paper
  - Returns paper object
  
- Pytest configuration
- Test database setup/teardown
"""

