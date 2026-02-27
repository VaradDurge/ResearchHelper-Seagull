/**
 * # API Endpoints Constants
 * 
 * ## What it does:
 * Centralized constants for all API endpoint URLs. Makes it easy to update
 * endpoints and ensures consistency across the app.
 * 
 * ## How it works:
 * - Exports constants for each endpoint
 * - Uses template strings for dynamic endpoints (e.g., paper ID)
 * - Groups endpoints by feature (papers, chat, tools, workspace)
 * 
 * ## What to include:
 * - Paper endpoints: GET /api/v1/papers, POST /api/v1/papers, GET /api/v1/papers/:id, etc.
 * - Chat endpoints: POST /api/v1/chat, GET /api/v1/chat/history
 * - Tool endpoints: POST /api/v1/tools/claim-verify, POST /api/v1/tools/blueprint, etc.
 * - Workspace endpoints: GET /api/v1/workspace, POST /api/v1/workspace, etc.
 * - DOI endpoint: POST /api/v1/papers/import-doi
 * - Helper functions for building URLs with params
 */

export const VERIFY_CLAIM = "/api/v1/verify/claim";
export const VERIFY_RECENT = "/api/v1/verify/recent";
