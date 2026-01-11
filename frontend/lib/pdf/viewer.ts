/**
 * # PDF Viewer Utilities
 * 
 * ## What it does:
 * Utility functions for PDF viewer operations: page navigation, zoom, URL building,
 * and PDF-related helpers.
 * 
 * ## How it works:
 * - Exports utility functions for PDF operations
 * - Handles page number parsing and validation
 * - Builds URLs for PDF viewer with page parameters
 * 
 * ## What to include:
 * - buildPDFUrl(paperId: string, page?: number): string - Build PDF viewer URL with page
 * - parsePageFromUrl(searchParams: URLSearchParams): number | null - Extract page from URL
 * - validatePageNumber(page: number, totalPages: number): boolean - Validate page number
 * - formatPageNumber(page: number): string - Format page number for display
 * - Helper functions for PDF navigation
 */

