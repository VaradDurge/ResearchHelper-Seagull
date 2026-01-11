"""
# Workspace API Endpoints

## What it does:
FastAPI route handlers for workspace operations: get, create, update, delete, switch workspace.

## How it works:
- Defines API endpoints for workspace operations
- Uses dependency injection for database session and authentication
- Calls workspace service for business logic
- Returns workspace data

## What to include:
- GET /workspace - Get current workspace
  - Response: WorkspaceResponse
  - Calls: workspace_service.get_current_workspace()
  
- GET /workspace/list - List all workspaces for user
  - Response: List[WorkspaceResponse]
  - Calls: workspace_service.get_workspaces()
  
- POST /workspace - Create new workspace
  - Request body: name (string), description (optional)
  - Response: WorkspaceResponse
  - Calls: workspace_service.create_workspace()
  
- PUT /workspace/{workspace_id} - Update workspace
  - Path param: workspace_id
  - Request body: name, description (optional)
  - Response: WorkspaceResponse
  - Calls: workspace_service.update_workspace()
  
- DELETE /workspace/{workspace_id} - Delete workspace
  - Path param: workspace_id
  - Response: success message
  - Calls: workspace_service.delete_workspace()
  
- POST /workspace/{workspace_id}/switch - Switch active workspace
  - Path param: workspace_id
  - Response: success message
  - Calls: workspace_service.switch_workspace()
"""

