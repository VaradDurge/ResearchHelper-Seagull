/**
 * # API Proxy Route
 * 
 * ## What it does:
 * Next.js API route that proxies requests to the FastAPI backend. Useful for
 * handling CORS, authentication, or request transformation. Optional - can also
 * call backend directly from frontend.
 * 
 * ## How it works:
 * - Receives requests from frontend
 * - Forwards requests to FastAPI backend
 * - Handles CORS if needed
 * - Transforms requests/responses if necessary
 * - Returns backend response to frontend
 * 
 * ## What to include:
 * - Request forwarding logic
 * - Backend URL from environment variable
 * - CORS headers (if needed)
 * - Error handling
 * - Request/response transformation (optional)
 * - Authentication token forwarding (if using)
 * - Rate limiting (optional)
 */

