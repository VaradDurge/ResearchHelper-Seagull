/**
 * # PDFThumbnail Component
 * 
 * ## What it does:
 * Individual paper card/thumbnail. Shows paper title, metadata, and preview.
 * Clickable to open PDF viewer. Includes actions (delete, download).
 * 
 * ## How it works:
 * - Displays paper metadata (title, authors, date)
 * - Shows first page thumbnail or icon
 * - Clickable to open PDF viewer (navigates to /pdf/[id])
 * - Includes action menu (delete, download, etc.)
 * - Uses Card component from shadcn/ui
 * 
 * ## What to include:
 * - Paper title (truncated if too long)
 * - Authors list (truncated if many)
 * - Publication date or upload date
 * - Thumbnail image (first page) or PDF icon
 * - Click handler to open viewer (Next.js Link)
 * - Action menu (dropdown with delete, download, rename)
 * - Hover effects (shadow, scale)
 * - Loading state for thumbnail
 * - Paper status indicator (processing, ready, error)
 */

