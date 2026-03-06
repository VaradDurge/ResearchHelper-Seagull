/**
 * Types for global paper graph (Obsidian-style).
 */
export interface GraphNode {
  id: string;
  label: string;
  type: "paper";
  year?: number;
  embedding_cluster?: number;
}

export type GraphLinkType = "citation" | "similarity" | "year_cluster";

export interface GraphLink {
  source: string;
  target: string;
  type: GraphLinkType;
  weight?: number;
  /** For force simulation: high weight = shorter distance */
  distance?: number;
}

export interface GraphResponse {
  nodes: GraphNode[];
  links: GraphLink[];
}

export interface GraphData {
  nodes: GraphNode[];
  links: GraphLink[];
}

// --- Research Intelligence Graph ---

export type IntelligenceNodeType = "paper" | "method" | "dataset" | "concept";

export interface IntelligenceGraphNode {
  id: string;
  label: string;
  type: IntelligenceNodeType;
  year?: number;
  cluster_id?: number;
  is_research_gap?: boolean;
  paper_count?: number;
  /** Paper nodes only: for side panel */
  main_problem?: string;
  methods_used?: string[];
  key_findings?: string[];
  datasets_used?: string[];
  keywords?: string[];
  domain?: string;
  claims?: string[];
}

export type IntelligenceLinkType =
  | "similarity"
  | "citation"
  | "keyword_overlap"
  | "contradiction"
  | "uses_method"
  | "uses_dataset"
  | "has_concept";

export interface ContradictionEntry {
  claim: string;
  paperA_statement?: string;
  paperB_statement?: string;
  paperA_page?: number;
  paperB_page?: number;
}

export interface IntelligenceGraphLink {
  source: string;
  target: string;
  type: IntelligenceLinkType;
  weight?: number;
  contradictions?: ContradictionEntry[];
}

export interface IntelligenceGraphResponse {
  nodes: IntelligenceGraphNode[];
  links: IntelligenceGraphLink[];
  has_intelligence: boolean;
}
