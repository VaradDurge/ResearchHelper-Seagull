/**
 * # CitationLink Component
 * 
 * ## What it does:
 * Reusable clickable citation component that displays paper name and page number.
 * When clicked, opens the PDF viewer at the specific page. Used throughout the app
 * wherever citations appear (chat messages, tool results, etc.).
 * 
 * ## How it works:
 * - Receives citation data: paperId, paperName, pageNumber
 * - Displays citation in format: "PaperName (p12)" or "[[PaperName|p12]]"
 * - On click, navigates to PDF viewer route with paper ID and page number
 * - Uses Next.js router.push() for navigation
 * - Can open in new tab or same window
 * 
 * ## What to include:
 * - Citation text display with styling
 * - Click handler for navigation
 * - Hover effects (underline, color change)
 * - Props: paperId, paperName, pageNumber, onClick (optional)
 * - Link component from Next.js
 * - Visual styling (blue/primary color, underline on hover)
 * - Optional tooltip showing full citation
 */

