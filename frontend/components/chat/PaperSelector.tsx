/**
 * # PaperSelector Component
 * 
 * ## What it does:
 * Allows user to select which papers to include in chat context.
 * Multi-select interface for papers. Updates chat context with selected papers.
 * 
 * ## How it works:
 * - Fetches papers from workspace via API (usePapers hook)
 * - Displays checkboxes or multi-select dropdown
 * - Updates chatStore with selected papers
 * - Shows selected papers count
 * - Filters papers list (optional search)
 * 
 * ## What to include:
 * - List of available papers from workspace
 * - Multi-select checkboxes or Select component
 * - Search/filter functionality
 * - Selected papers count display
 * - "Select All" / "Deselect All" options
 * - Paper thumbnails/metadata display
 * - Loading state while fetching papers
 * - Empty state when no papers available
 * - Selected papers summary/badges
 */

