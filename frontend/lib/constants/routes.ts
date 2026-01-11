/**
 * # Route Constants
 * 
 * ## What it does:
 * Centralized constants for all application routes. Makes it easy to update routes
 * and ensures consistency across the app.
 * 
 * ## How it works:
 * - Exports constants for each route
 * - Uses template strings for dynamic routes (e.g., paper ID)
 * - Groups routes by feature
 * 
 * ## What to include:
 * - Dashboard routes: /chat, /pdf, /claim-verify, /blueprint, /method-reprod, /literature, /graphs, /cross-eval
 * - PDF viewer route: /pdf/[id] with helper function to build URL
 * - Helper functions: buildPDFViewerUrl(id: string, page?: number): string
 * - Route groups and base paths
 */

