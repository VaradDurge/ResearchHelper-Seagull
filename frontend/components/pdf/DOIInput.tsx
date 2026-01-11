/**
 * # DOIInput Component
 * 
 * ## What it does:
 * Input field for entering DOI (Digital Object Identifier). Fetches paper metadata
 * and PDF from DOI. Validates DOI format and handles import process.
 * 
 * ## How it works:
 * - User enters DOI (e.g., "10.48550/arXiv.2010.11929")
 * - Validates DOI format client-side
 * - Calls backend API to fetch paper from DOI
 * - Backend handles DOI resolution and PDF download
 * - Updates paper list after successful import
 * - Shows loading state during fetch
 * 
 * ## What to include:
 * - Text input for DOI entry
 * - Submit button ("Import" or "Fetch")
 * - DOI format validation (regex pattern)
 * - Loading state during fetch (spinner, disabled input)
 * - Error handling (invalid DOI, network errors, paper not found)
 * - Success notification
 * - Optional: Preview of fetched paper metadata before import
 * - Integration with DOI import API endpoint
 */

