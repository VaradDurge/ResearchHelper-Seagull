/**
 * # Tools Types
 * 
 * ## What it does:
 * TypeScript types for all ResearchHelper tools: claim verification, blueprint,
 * method reproduction, literature cleanup, graphs, cross evaluation.
 * 
 * ## How it works:
 * - Exports TypeScript interfaces and types for each tool
 * - Matches backend tool response structures
 * - Used by tool components
 * 
 * ## What to include:
 * - ClaimVerification types: VerificationResult, Verdict (Support/Refute/Uncertain), Evidence
 * - Blueprint types: Blueprint, BlueprintSection (Problem, Hypothesis, Architecture, etc.)
 * - MethodReproduction types: MethodDetails, Algorithm, Architecture, Hyperparameters, Experiments
 * - LiteratureCleanup types: GroupedPapers, PaperGroup, DeduplicatedReferences, Trends
 * - Graph types: GraphData, Node, Edge, NodeType, EdgeType
 * - CrossEvaluation types: EvaluationResult, LLMResponse, EvaluationMetrics, Ranking
 */

