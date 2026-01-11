/**
 * # useTool Hook (Generic Tool Hook Pattern)
 * 
 * ## What it does:
 * Generic React hook pattern for tool operations. Can be used as a base for tool-specific
 * hooks or used directly for simple tools. Handles tool execution, loading states, and results.
 * 
 * ## How it works:
 * - Generic hook that accepts tool function and parameters
 * - Manages loading, error, and result states
 * - Handles tool execution
 * - Can be extended for specific tools
 * 
 * ## What to include:
 * - State: result, isLoading, error
 * - Function: executeTool
 * - Generic type parameters for tool input/output
 * - Error handling
 * - TypeScript return type with generics
 */

