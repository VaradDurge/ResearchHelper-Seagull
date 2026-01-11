/**
 * # PDFViewer Component
 * 
 * ## What it does:
 * Displays PDF document with page navigation. Supports zoom, page navigation, and search.
 * Can navigate to specific page from citation clicks.
 * 
 * ## How it works:
 * - Uses react-pdf or similar library (@react-pdf/renderer or react-pdf-viewer)
 * - Receives PDF URL or file from backend
 * - Renders PDF pages
 * - Handles page navigation (previous/next, jump to page)
 * - Supports zoom in/out
 * - Can navigate to specific page from citation click (via URL params or props)
 * 
 * ## What to include:
 * - PDF page rendering (using react-pdf library)
 * - Page navigation controls (previous, next, page number input)
 * - Zoom controls (zoom in, zoom out, fit to width, fit to page)
 * - Current page number display
 * - Total pages display
 * - Loading state while PDF loads
 * - Error handling (corrupted PDF, network issues)
 * - Full-screen mode option
 * - Text selection support
 * - Search functionality (optional)
 * - Print functionality (optional)
 * - Download button
 */

