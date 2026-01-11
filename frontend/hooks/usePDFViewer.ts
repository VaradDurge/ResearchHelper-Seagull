/**
 * # usePDFViewer Hook
 * 
 * ## What it does:
 * Custom React hook for managing PDF viewer state: current page, zoom level, PDF data,
 * and navigation.
 * 
 * ## How it works:
 * - Manages PDF viewer state (page, zoom, PDF URL)
 * - Handles page navigation (next, previous, jump to page)
 * - Syncs with URL parameters
 * - Integrates with PDF viewer component
 * 
 * ## What to include:
 * - State: currentPage, zoom, pdfUrl, totalPages, isLoading
 * - Functions: goToPage, nextPage, previousPage, setZoom, loadPDF
 * - URL synchronization (read/write page from URL params)
 * - PDF loading logic
 * - TypeScript return type
 */

