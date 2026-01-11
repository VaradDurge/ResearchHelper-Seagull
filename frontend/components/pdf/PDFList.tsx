/**
 * # PDFList Component
 * 
 * ## What it does:
 * Displays list of all uploaded papers in current workspace. Shows paper metadata
 * and thumbnails. Supports filtering and sorting.
 * 
 * ## How it works:
 * - Fetches papers from API using TanStack Query (usePapers hook)
 * - Maps papers to PDFThumbnail components
 * - Handles empty state (no papers uploaded)
 * - Supports filtering and sorting
 * - Updates when papers are added/deleted
 * 
 * ## What to include:
 * - Grid or list layout of papers
 * - PDFThumbnail components for each paper
 * - Empty state component (EmptyState with "Upload PDF" CTA)
 * - Search/filter functionality (by title, author, date)
 * - Sort options (date uploaded, name, author)
 * - Loading skeleton states
 * - Delete paper action (with confirmation)
 * - Refresh button
 * - Pagination (if many papers)
 */

