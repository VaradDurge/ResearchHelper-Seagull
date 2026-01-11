/**
 * # Tools API Functions
 * 
 * ## What it does:
 * API functions for all ResearchHelper tools: claim verification, blueprint generation,
 * method reproduction, literature cleanup, graphs, cross evaluation.
 * 
 * ## How it works:
 * - Exports functions for each tool
 * - Uses API client from client.ts
 * - Uses endpoint constants from endpoints.ts
 * - Returns typed responses for each tool
 * 
 * ## What to include:
 * - verifyClaim(claim: string, paperIds: string[]): Promise<VerificationResult>
 * - generateBlueprint(query: string, paperIds?: string[]): Promise<Blueprint>
 * - extractMethod(paperId: string): Promise<MethodDetails>
 * - cleanupLiterature(paperIds: string[], options: CleanupOptions): Promise<GroupedPapers>
 * - generateGraph(paperIds: string[], options: GraphOptions): Promise<GraphData>
 * - crossEvaluate(query: string, llmProviders: string[], paperIds: string[]): Promise<EvaluationResult>
 * - TypeScript types for each tool's request/response
 */

