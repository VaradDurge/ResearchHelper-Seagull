/**
 * # Citation Component
 * 
 * ## What it does:
 * Clickable citation component showing paper name and page number.
 * Opens PDF viewer at specific page when clicked. Used inline in chat messages.
 * 
 * ## How it does:
 * - Displays citation in format: `[[PaperName|p12]]` or "PaperName (p12)"
 * - On click, navigates to PDF viewer with paper ID and page number
 * - Uses Next.js router for navigation
 * - Highlights citation in message text
 * 
 * ## What to include:
 * - Citation text display (paper name and page number)
 * - Click handler to open PDF viewer
 * - Hover effects (underline, color change)
 * - Props: paperId, paperName, pageNumber
 * - Link component or click handler
 * - Visual styling (blue/primary color, underline on hover)
 * - Optional tooltip showing full citation details
 * - Icon indicator (optional)
 */

