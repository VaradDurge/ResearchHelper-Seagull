/**
 * # Individual PDF Viewer Page
 * 
 * ## What it does:
 * Displays a single PDF document in the viewer. Handles page navigation and can
 * jump to specific pages (e.g., from citation clicks).
 * 
 * ## How it works:
 * - Receives paper ID from URL params ([id])
 * - Fetches PDF data from API
 * - Renders PDFViewer component
 * - Handles page navigation via URL query params (?page=12)
 * - Supports deep linking to specific pages
 * 
 * ## What to include:
 * - PDFViewer component
 * - Page parameter extraction from URL
 * - PDF data fetching (TanStack Query)
 * - Loading state
 * - Error handling (PDF not found, loading error)
 * - Back button to PDF list
 * - Paper metadata display (title, authors)
 */

