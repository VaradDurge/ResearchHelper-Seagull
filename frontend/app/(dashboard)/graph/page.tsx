"use client";

import { useCallback, useMemo, useRef, useState, useEffect, useLayoutEffect } from "react";
import dynamic from "next/dynamic";
import { getGraphWorkspace, getGraphWorkspaceIntelligence } from "@/lib/api/graph";
import { getPaper } from "@/lib/api/papers";
import type { GraphNode, GraphLink, GraphData, IntelligenceGraphNode, IntelligenceGraphLink, IntelligenceGraphResponse } from "@/types/graph";
import type { Paper } from "@/types/paper";
import { useWorkspace } from "@/store/workspaceStore";
import { Button } from "@/components/ui/button";
import { ExternalLink, Maximize2, Layers } from "lucide-react";
import { buildDenseConnections, type EnrichedLink } from "@/lib/graph/buildDenseConnections";
import { rebuildIntelligenceForWorkspace } from "@/lib/api/debug";
import { louvainCommunities } from "@/lib/graph/clusterDetection";

const ForceGraph2D = dynamic(() => import("react-force-graph-2d"), { ssr: false });

// Obsidian-like dark background and graph colors
const BG = "#1f2024";
// Paper/title nodes: beige #DFD0B8 with lighter hover/selected variants
const NODE_DEFAULT = "rgba(223, 208, 184, 0.95)"; // #DFD0B8
const NODE_HOVER = "rgba(240, 228, 205, 1)";
const NODE_SELECTED = "rgba(255, 245, 220, 1)";
const NODE_FADED = "rgba(223, 208, 184, 0.15)";
const EDGE_OPACITY_DEFAULT = 0.55;
const EDGE_OPACITY_HIGHLIGHT = 0.95;
// Soft grey edges similar to Obsidian’s graph view
const LINK_CITATION = "rgba(180, 180, 180, 1)";
const LINK_SIMILARITY = "rgba(180, 180, 180, 1)";
const LINK_YEAR = "rgba(180, 180, 180, 1)";
const LINK_HIGHLIGHT = "rgba(230, 230, 230, 1)";
const CLUSTER_COLORS = [
  "rgba(100, 160, 255, 0.5)",
  "rgba(160, 100, 255, 0.5)",
  "rgba(255, 140, 100, 0.5)",
  "rgba(100, 220, 180, 0.5)",
  "rgba(220, 180, 100, 0.5)",
  "rgba(180, 100, 220, 0.5)",
];

const BASE_NODE_R = 3;
const CITATION_THRESHOLD = 2;

type NodeWithMeta = GraphNode & {
  degree?: number;
  citationCount?: number;
  similarCount?: number;
  clusterId?: number;
  x?: number;
  y?: number;
};

function enrichGraphData(data: GraphData): { nodes: NodeWithMeta[]; links: GraphLink[] } {
  const nodes = data.nodes.map((n) => ({
    ...n,
    degree: 0,
    citationCount: 0,
    similarCount: 0,
  }));
  const nodeMap = new Map(nodes.map((n) => [n.id, n]));
  for (const link of data.links) {
    const src = typeof link.source === "string" ? link.source : (link.source as { id?: string }).id;
    const tgt = typeof link.target === "string" ? link.target : (link.target as { id?: string }).id;
    if (!src || !tgt) continue;
    const sourceNode = nodeMap.get(src);
    const targetNode = nodeMap.get(tgt);
    if (sourceNode) {
      sourceNode.degree = (sourceNode.degree ?? 0) + 1;
      if (link.type === "similarity") sourceNode.similarCount = (sourceNode.similarCount ?? 0) + 1;
    }
    if (targetNode) {
      targetNode.degree = (targetNode.degree ?? 0) + 1;
      if (link.type === "citation") targetNode.citationCount = (targetNode.citationCount ?? 0) + 1;
      if (link.type === "similarity") targetNode.similarCount = (targetNode.similarCount ?? 0) + 1;
    }
  }
  return { nodes, links: data.links };
}

function getConnectedNodeIds(nodeId: string, links: EnrichedLink[]): Set<string> {
  const set = new Set<string>([nodeId]);
  for (const l of links) {
    const a = typeof l.source === "string" ? l.source : (l.source as { id?: string }).id;
    const b = typeof l.target === "string" ? l.target : (l.target as { id?: string }).id;
    if (a === nodeId && b) set.add(b);
    if (b === nodeId && a) set.add(a);
  }
  return set;
}

function getClusterNodeIds(clusterId: number, nodes: NodeWithMeta[]): NodeWithMeta[] {
  return nodes.filter((n) => n.clusterId === clusterId);
}

type SelectedNode = NodeWithMeta | IntelligenceGraphNode | null;

export default function GraphPage() {
  const { activeWorkspace, loading: workspaceLoading } = useWorkspace();
  const [rawData, setRawData] = useState<GraphData | null>(null);
  const [intelligenceData, setIntelligenceData] = useState<IntelligenceGraphResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState(false);
  const [hoverNode, setHoverNode] = useState<SelectedNode>(null);
  const [selectedNode, setSelectedNode] = useState<SelectedNode>(null);
  const [panelPaper, setPanelPaper] = useState<Paper | null>(null);
  const workspaceIdRef = useRef<string | null>(null);
  workspaceIdRef.current = activeWorkspace?.id ?? null;
  const [showClusters, setShowClusters] = useState(false);
  const [contradictionMode, setContradictionMode] = useState(false);
  const [edgeTypeFilter, setEdgeTypeFilter] = useState<"all" | "citation" | "similarity" | "year_cluster">("all");
  const [similarityThreshold, setSimilarityThreshold] = useState<0.65 | 0.75>(0.65);
  const [rebuildingIntel, setRebuildingIntel] = useState(false);
  const fgRef = useRef<any>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  /** For paper mini-circle hit-test: graph → screen transform (updated each frame in nodeCanvasObject). */
  const canvasTransformRef = useRef<DOMMatrix | null>(null);
  /** Mini-circle positions in graph space per paper node id (method and dataset arcs). */
  const nodeMiniCircleRef = useRef<Map<string, { method: [number, number][]; dataset: [number, number][] }>>(new Map());
  /** Floating popup for methods/datasets (internal paper intelligence). */
  const [paperPopup, setPaperPopup] = useState<{
    type: "methods" | "datasets";
    node: IntelligenceGraphNode;
    x: number;
    y: number;
  } | null>(null);

  const useIntelligence = Boolean(
    intelligenceData?.has_intelligence && intelligenceData?.nodes?.length > 0
  );

  const { nodes: enrichedNodes, links: denseLinks } = useMemo(() => {
    if (!rawData || !rawData.nodes.length) return { nodes: [], links: [] };
    const { nodes } = enrichGraphData(rawData);
    const dense = buildDenseConnections(nodes, rawData.links);
    const nodeMap = new Map(nodes.map((n) => [n.id, n as NodeWithMeta]));
    for (const n of nodes) {
      const m = n as NodeWithMeta;
      m.degree = 0;
      m.citationCount = 0;
      m.similarCount = 0;
    }
    for (const link of dense) {
      const src = typeof link.source === "string" ? link.source : (link.source as { id?: string }).id;
      const tgt = typeof link.target === "string" ? link.target : (link.target as { id?: string }).id;
      if (src && nodeMap.has(src)) {
        const m = nodeMap.get(src)!;
        m.degree = (m.degree ?? 0) + 1;
        if (link.type === "similarity") m.similarCount = (m.similarCount ?? 0) + 1;
      }
      if (tgt && nodeMap.has(tgt)) {
        const m = nodeMap.get(tgt)!;
        m.degree = (m.degree ?? 0) + 1;
        if (link.type === "citation") m.citationCount = (m.citationCount ?? 0) + 1;
        if (link.type === "similarity") m.similarCount = (m.similarCount ?? 0) + 1;
      }
    }
    const nodeIds = nodes.map((n) => n.id);
    const clusterMap = louvainCommunities(nodeIds, dense);
    nodes.forEach((n) => {
      (n as NodeWithMeta).clusterId = clusterMap.get(n.id) ?? 0;
    });
    return { nodes: nodes as NodeWithMeta[], links: dense };
  }, [rawData]);

  const filteredLinks = useMemo(() => {
    return denseLinks.filter((link) => {
      if (edgeTypeFilter === "all") {
        if (link.type === "similarity" && typeof link.weight === "number" && link.weight < similarityThreshold)
          return false;
        return true;
      }
      if (edgeTypeFilter === "similarity") {
        return link.type === "similarity" && (typeof link.weight !== "number" || link.weight >= similarityThreshold);
      }
      return link.type === edgeTypeFilter;
    });
  }, [denseLinks, edgeTypeFilter, similarityThreshold]);

  const intelligenceNodesWithDegree = useMemo(() => {
    if (!intelligenceData?.nodes?.length) return [];
    const nodeMap = new Map(intelligenceData.nodes.map((n) => [n.id, { ...n, degree: 0 }]));
    const links = intelligenceData.links ?? [];
    for (const l of links) {
      const a = typeof l.source === "string" ? l.source : (l.source as { id?: string })?.id;
      const b = typeof l.target === "string" ? l.target : (l.target as { id?: string })?.id;
      if (a && nodeMap.has(a)) (nodeMap.get(a) as { degree: number }).degree++;
      if (b && nodeMap.has(b)) (nodeMap.get(b) as { degree: number }).degree++;
    }
    return Array.from(nodeMap.values());
  }, [intelligenceData]);

  const filteredIntelligenceLinks = useMemo(() => {
    if (!intelligenceData?.links) return [];
    if (contradictionMode) return intelligenceData.links.filter((l) => l.type === "contradiction");
    return intelligenceData.links;
  }, [intelligenceData?.links, contradictionMode]);

  const effectiveIntelligenceLinks = useMemo(() => {
    if (filteredIntelligenceLinks.length > 0) return filteredIntelligenceLinks;
    const nodes = intelligenceNodesWithDegree;
    if (nodes.length < 2) return [];
    const paperNodes = nodes.filter((n) => (n as IntelligenceGraphNode).type === "paper");
    if (paperNodes.length < 2) return [];
    const fallback: Array<{ source: string; target: string; type: "keyword_overlap"; weight: number }> = [];
    const byYear = new Map<number, typeof paperNodes>();
    for (const n of paperNodes) {
      const y = (n as IntelligenceGraphNode).year;
      const year = typeof y === "number" ? y : null;
      if (year != null) {
        const list = byYear.get(year) ?? [];
        list.push(n);
        byYear.set(year, list);
      }
    }
    const linkSet = new Set<string>();
    const add = (a: string, b: string) => {
      const key = a < b ? `${a}|${b}` : `${b}|${a}`;
      if (linkSet.has(key)) return;
      linkSet.add(key);
      fallback.push({ source: a, target: b, type: "keyword_overlap", weight: 0.35 });
    };
    for (const list of byYear.values()) {
      for (let i = 0; i < list.length; i++) for (let j = i + 1; j < list.length; j++) add(list[i].id, list[j].id);
    }
    const degree = new Map<string, number>();
    for (const n of paperNodes) degree.set(n.id, 0);
    for (const l of fallback) {
      degree.set(l.source, (degree.get(l.source) ?? 0) + 1);
      degree.set(l.target, (degree.get(l.target) ?? 0) + 1);
    }
    for (const n of paperNodes) {
      if ((degree.get(n.id) ?? 0) >= 1) continue;
      const other = paperNodes.find((o) => o.id !== n.id);
      if (other) add(n.id, other.id);
    }
    return fallback;
  }, [filteredIntelligenceLinks, intelligenceNodesWithDegree]);

  const graphData = useMemo(() => {
    if (useIntelligence) {
      return { nodes: intelligenceNodesWithDegree, links: effectiveIntelligenceLinks };
    }
    return { nodes: enrichedNodes, links: filteredLinks };
  }, [useIntelligence, intelligenceNodesWithDegree, effectiveIntelligenceLinks, enrichedNodes, filteredLinks]);

  /** Paper ids that are connected to a concept with paper_count === 1 (research gap). Used for inner glow + red dot. */
  const paperHasUniqueConcept = useMemo(() => {
    if (!useIntelligence || !graphData.links.length) return new Set<string>();
    const conceptIdToPaperCount = new Map<string, number>();
    for (const n of graphData.nodes) {
      if ((n as IntelligenceGraphNode).type === "concept" && (n as IntelligenceGraphNode).paper_count != null)
        conceptIdToPaperCount.set(n.id, (n as IntelligenceGraphNode).paper_count!);
    }
    const set = new Set<string>();
    for (const l of graphData.links) {
      if (l.type !== "has_concept") continue;
      const conceptId = typeof l.target === "string" ? l.target : (l.target as { id?: string })?.id;
      const paperId = typeof l.source === "string" ? l.source : (l.source as { id?: string })?.id;
      if (conceptId && paperId && conceptIdToPaperCount.get(conceptId) === 1) set.add(paperId);
    }
    return set;
  }, [useIntelligence, graphData.nodes, graphData.links]);

  const highlightSet = useMemo(() => {
    const id = selectedNode?.id ?? hoverNode?.id;
    if (!id) return null;
    const links = useIntelligence ? effectiveIntelligenceLinks : filteredLinks;
    const set = new Set<string>([id]);
    for (const l of links) {
      const a = typeof l.source === "string" ? l.source : (l.source as { id?: string })?.id;
      const b = typeof l.target === "string" ? l.target : (l.target as { id?: string })?.id;
      if (a === id && b) set.add(b);
      if (b === id && a) set.add(a);
    }
    return set;
  }, [selectedNode?.id, hoverNode?.id, filteredLinks, effectiveIntelligenceLinks, useIntelligence]);

  const loadGraph = useCallback(async () => {
    const requestWorkspaceId = workspaceIdRef.current;
    if (!requestWorkspaceId) return;
    setLoadError(false);
    try {
      setLoading(true);
      setIntelligenceData(null);
      setRawData(null);
      const intel = await getGraphWorkspaceIntelligence(requestWorkspaceId);
      if (workspaceIdRef.current !== requestWorkspaceId) return;
      const hasIntelNodes = Array.isArray(intel?.nodes) && intel.nodes.length > 0;
      if (intel?.has_intelligence && hasIntelNodes) {
        setIntelligenceData(intel);
      } else {
        const data = await getGraphWorkspace(requestWorkspaceId);
        if (workspaceIdRef.current !== requestWorkspaceId) return;
        setRawData({
          nodes: Array.isArray(data?.nodes) ? data.nodes : [],
          links: Array.isArray(data?.links) ? data.links : [],
        });
      }
    } catch {
      if (workspaceIdRef.current !== requestWorkspaceId) return;
      try {
        const data = await getGraphWorkspace(requestWorkspaceId);
        if (workspaceIdRef.current !== requestWorkspaceId) return;
        setRawData({
          nodes: Array.isArray(data?.nodes) ? data.nodes : [],
          links: Array.isArray(data?.links) ? data.links : [],
        });
      } catch {
        if (workspaceIdRef.current !== requestWorkspaceId) return;
        setLoadError(true);
        setRawData({ nodes: [], links: [] });
      }
    } finally {
      if (workspaceIdRef.current === requestWorkspaceId) setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (workspaceLoading) return;
    if (!activeWorkspace?.id) {
      setLoading(false);
      return;
    }
    loadGraph();
  }, [activeWorkspace?.id, workspaceLoading, loadGraph]);

  useEffect(() => {
    if (!fgRef.current || !graphData.nodes.length) return;
    try {
      const charge = fgRef.current.d3Force("charge");
      if (charge && typeof charge.strength === "function") {
        (charge as { strength: (v: number) => void }).strength(-300);
      }
      const link = fgRef.current.d3Force("link");
      if (link) {
        if (typeof link.strength === "function") (link as { strength: (v: number) => void }).strength(0.6);
        if (typeof link.distance === "function") {
          link.distance((l: EnrichedLink) => (l.distance != null ? l.distance : 100));
        }
      }
      const center = fgRef.current.d3Force("center");
      if (center && typeof center.strength === "function") {
        (center as { strength: (v: number) => void }).strength(0.1);
      }
    } catch {
      // ignore
    }
  }, [graphData.nodes.length]);

  useEffect(() => {
    if (!selectedNode) {
      setPanelPaper(null);
      return;
    }
    const isPaper = !("type" in selectedNode) || (selectedNode as IntelligenceGraphNode).type === "paper";
    if (!isPaper) {
      setPanelPaper(null);
      return;
    }
    let cancelled = false;
    getPaper(selectedNode.id)
      .then((p) => {
        if (!cancelled) setPanelPaper(p);
      })
      .catch(() => {
        if (!cancelled) setPanelPaper(null);
      });
    return () => {
      cancelled = true;
    };
  }, [selectedNode?.id, selectedNode]);

  const handleBackgroundClick = useCallback(() => {
    setSelectedNode(null);
  }, []);

  const handleBackgroundDblClick = useCallback(() => {
    if (fgRef.current) {
      fgRef.current.zoomToFit(400, 50);
    }
  }, []);

  const handleNodeClick = useCallback(
    (node: NodeWithMeta | IntelligenceGraphNode, ev: React.MouseEvent) => {
      if (useIntelligence && "type" in node && (node as IntelligenceGraphNode).type === "paper") {
        const paperNode = node as IntelligenceGraphNode;
        const circles = nodeMiniCircleRef.current.get(node.id);
        const transform = canvasTransformRef.current;
        if (circles && transform) {
          try {
            const inv = transform.inverse();
            const pt = inv.transformPoint({ x: ev.nativeEvent.offsetX, y: ev.nativeEvent.offsetY });
            const hitR2 = 36; // 6px hit radius (mini-circles are 3px)
            for (const [gx, gy] of circles.method) {
              if ((pt.x - gx) ** 2 + (pt.y - gy) ** 2 <= hitR2) {
                ev.preventDefault();
                ev.stopPropagation();
                setPaperPopup({
                  type: "methods",
                  node: paperNode,
                  x: ev.nativeEvent.clientX,
                  y: ev.nativeEvent.clientY,
                });
                return;
              }
            }
            for (const [gx, gy] of circles.dataset) {
              if ((pt.x - gx) ** 2 + (pt.y - gy) ** 2 <= hitR2) {
                ev.preventDefault();
                ev.stopPropagation();
                setPaperPopup({
                  type: "datasets",
                  node: paperNode,
                  x: ev.nativeEvent.clientX,
                  y: ev.nativeEvent.clientY,
                });
                return;
              }
            }
          } catch {
            // fallback to normal selection
          }
        }
      }
      setSelectedNode(node);
      if (fgRef.current && (node as NodeWithMeta).x != null && (node as NodeWithMeta).y != null) {
        fgRef.current.centerAt((node as NodeWithMeta).x!, (node as NodeWithMeta).y!, 300);
      }
    },
    [useIntelligence]
  );

  const zoomToCluster = useCallback(() => {
    if (!selectedNode || !fgRef.current) return;
    const cid = selectedNode.clusterId ?? 0;
    const clusterNodes = getClusterNodeIds(cid, enrichedNodes);
    if (clusterNodes.length === 0) return;
    const xs = clusterNodes.map((n) => (n as NodeWithMeta & { x?: number }).x).filter((v): v is number => v != null);
    const ys = clusterNodes.map((n) => (n as NodeWithMeta & { y?: number }).y).filter((v): v is number => v != null);
    if (xs.length === 0 || ys.length === 0) return;
    const cx = (Math.min(...xs) + Math.max(...xs)) / 2;
    const cy = (Math.min(...ys) + Math.max(...ys)) / 2;
    fgRef.current.centerAt(cx, cy, 300);
    fgRef.current.zoom(2, 300);
  }, [selectedNode, enrichedNodes]);

  const nodeOpacity = useCallback(
    (node: NodeWithMeta) => {
      if (!highlightSet) return 1;
      return highlightSet.has(node.id) ? 1 : 0.1;
    },
    [highlightSet]
  );

  const nodeColor = useCallback(
    (node: NodeWithMeta | IntelligenceGraphNode) => {
      const opacity = nodeOpacity(node as NodeWithMeta);
      if (selectedNode?.id === node.id) return NODE_SELECTED;
      if (hoverNode?.id === node.id) return NODE_HOVER;
      if (opacity < 0.5) return NODE_FADED;
      if (useIntelligence && "type" in node) {
        const t = (node as IntelligenceGraphNode).type;
        if (t === "method") return "rgba(220, 160, 100, 0.95)";
        if (t === "dataset") return "rgba(100, 200, 180, 0.95)";
        if (t === "concept") return "rgba(180, 140, 220, 0.9)";
      }
      if (showClusters && "clusterId" in node && node.clusterId != null) {
        return CLUSTER_COLORS[node.clusterId % CLUSTER_COLORS.length];
      }
      return NODE_DEFAULT;
    },
    [hoverNode?.id, selectedNode?.id, nodeOpacity, showClusters, useIntelligence]
  );

  const nodeRadius = useCallback((node: NodeWithMeta | (IntelligenceGraphNode & { degree?: number })) => {
    const d = node.degree ?? 0;
    if (useIntelligence && "type" in node) {
      const t = (node as IntelligenceGraphNode).type;
      if (t === "method") return 3.5;
      if (t === "dataset") return 3;
      if (t === "concept") return 2.5;
      return 5 + Math.floor(d / 3) * 1;
    }
    const steps = Math.floor(d / 3);
    let r = BASE_NODE_R + steps * 2;
    if ((node as NodeWithMeta).citationCount != null && (node as NodeWithMeta).citationCount! > CITATION_THRESHOLD) r += 3;
    return Math.min(r, 12);
  }, [useIntelligence]);

  const drawNode = useCallback(
    (node: NodeWithMeta | (IntelligenceGraphNode & { x?: number; y?: number; degree?: number }), ctx: CanvasRenderingContext2D) => {
      const x = (node as { x?: number }).x;
      const y = (node as { y?: number }).y;
      if (x == null || y == null) return;
      ctx.save();
      const r = nodeRadius(node);
      const color = nodeColor(node);
      const isHighlight = hoverNode?.id === node.id || selectedNode?.id === node.id;

      // In intelligence graph, treat as paper if type is "paper" or if node has paper-like fields (fallback for API quirks)
      const nodeType = (node as IntelligenceGraphNode).type;
      const isPaperIntelligence =
        useIntelligence &&
        (nodeType === "paper" ||
          (nodeType !== "method" &&
            nodeType !== "dataset" &&
            nodeType !== "concept" &&
            Boolean((node as IntelligenceGraphNode).label)));
      const paperNode = isPaperIntelligence ? (node as IntelligenceGraphNode) : null;
      const hasUniqueConcept = paperNode && paperHasUniqueConcept.has(paperNode.id);

      if (useIntelligence && "is_research_gap" in node && (node as IntelligenceGraphNode).is_research_gap && !isHighlight) {
        ctx.beginPath();
        ctx.arc(x, y, r + 12, 0, 2 * Math.PI);
        ctx.fillStyle = "rgba(220, 80, 80, 0.15)";
        ctx.fill();
        ctx.strokeStyle = "rgba(220, 80, 80, 0.4)";
        ctx.lineWidth = 1;
        ctx.stroke();
      }
      if (showClusters && "clusterId" in node && node.clusterId != null && !isHighlight) {
        const halo = CLUSTER_COLORS[node.clusterId % CLUSTER_COLORS.length];
        ctx.beginPath();
        ctx.arc(x, y, r + 14, 0, 2 * Math.PI);
        ctx.fillStyle = halo.replace("0.5)", "0.12)");
        ctx.fill();
      }

      if (isPaperIntelligence && paperNode) {
        // --- Paper intelligence capsule (visual only; no extra graph nodes) ---
        canvasTransformRef.current = ctx.getTransform();
        const methods = paperNode.methods_used ?? [];
        const datasets = paperNode.datasets_used ?? [];
        const arcR = r * 0.65;
        const miniR = 3;
        const maxDots = 5;
        const methodPositions: [number, number][] = [];
        const datasetPositions: [number, number][] = [];

        // Research gap: subtle inner red glow (do not change base paper color)
        if (hasUniqueConcept && !isHighlight) {
          const gradient = ctx.createRadialGradient(x, y, 0, x, y, r);
          gradient.addColorStop(0, "rgba(220, 80, 80, 0.25)");
          gradient.addColorStop(0.7, "rgba(220, 80, 80, 0.08)");
          gradient.addColorStop(1, "rgba(220, 80, 80, 0)");
          ctx.beginPath();
          ctx.arc(x, y, r, 0, 2 * Math.PI);
          ctx.fillStyle = gradient;
          ctx.fill();
        }

        ctx.shadowColor = "rgba(0,0,0,0.4)";
        ctx.shadowBlur = 4;
        ctx.beginPath();
        ctx.arc(x, y, r, 0, 2 * Math.PI);
        ctx.fillStyle = color;
        ctx.fill();
        ctx.shadowBlur = 0;

        if (isHighlight) {
          ctx.beginPath();
          ctx.arc(x, y, r + 4, 0, 2 * Math.PI);
          ctx.strokeStyle = "rgba(150, 200, 255, 0.8)";
          ctx.lineWidth = 2;
          ctx.stroke();
        }

        // Small red dot near title for research gap
        if (hasUniqueConcept) {
          ctx.beginPath();
          ctx.arc(x + r * 0.5, y - r * 0.35, 3, 0, 2 * Math.PI);
          ctx.fillStyle = "rgba(220, 80, 80, 0.95)";
          ctx.fill();
        }

        // Title: centered, 2 lines max, smaller font
        const title = (paperNode.label || "").trim();
        if (title) {
          ctx.save();
          ctx.font = "9px sans-serif";
          ctx.fillStyle = "rgba(255,255,255,0.95)";
          ctx.textAlign = "center";
          ctx.textBaseline = "middle";
          const maxWidth = Math.max(20, r * 1.6);
          const lineHeight = 10;
          const words = title.split(/\s+/);
          const lines: string[] = [];
          let current = "";
          for (const w of words) {
            const test = current ? `${current} ${w}` : w;
            const m = ctx.measureText(test);
            if (m.width <= maxWidth) current = test;
            else {
              if (current) lines.push(current);
              current = ctx.measureText(w).width <= maxWidth ? w : w.slice(0, Math.ceil(maxWidth / 5));
            }
          }
          if (current) lines.push(current);
          const drawn = lines.slice(0, 2);
          const startY = y - (drawn.length - 1) * (lineHeight / 2);
          drawn.forEach((line, i) => {
            ctx.fillText(line, x, startY + i * lineHeight);
          });
          ctx.restore();
        }

        // Bottom arc: teal method indicators (max 5, then "+X")
        const methodCount = Math.min(methods.length, maxDots);
        const methodStartAngle = Math.PI * 0.6;
        const methodEndAngle = Math.PI * 0.9;
        for (let i = 0; i < methodCount; i++) {
          const t = methodCount === 1 ? 0.5 : i / (methodCount - 1);
          const angle = methodStartAngle + t * (methodEndAngle - methodStartAngle);
          const px = x + arcR * Math.cos(angle);
          const py = y + arcR * Math.sin(angle);
          methodPositions.push([px, py]);
          ctx.beginPath();
          ctx.arc(px, py, miniR, 0, 2 * Math.PI);
          ctx.fillStyle = "#1abc9c";
          ctx.fill();
        }
        if (methods.length > maxDots) {
          const badgeAngle = methodEndAngle + 0.08;
          const px = x + arcR * Math.cos(badgeAngle);
          const py = y + arcR * Math.sin(badgeAngle);
          ctx.font = "8px sans-serif";
          ctx.fillStyle = "#1abc9c";
          ctx.textAlign = "center";
          ctx.textBaseline = "middle";
          ctx.fillText(`+${methods.length - maxDots}`, px, py);
        }

        // Right arc: yellow dataset indicators
        const datasetCount = Math.min(datasets.length, maxDots);
        const datasetStartAngle = -Math.PI * 0.25;
        const datasetEndAngle = Math.PI * 0.25;
        for (let i = 0; i < datasetCount; i++) {
          const t = datasetCount === 1 ? 0.5 : i / (datasetCount - 1);
          const angle = datasetStartAngle + t * (datasetEndAngle - datasetStartAngle);
          const px = x + arcR * Math.cos(angle);
          const py = y + arcR * Math.sin(angle);
          datasetPositions.push([px, py]);
          ctx.beginPath();
          ctx.arc(px, py, miniR, 0, 2 * Math.PI);
          ctx.fillStyle = "#f1c40f";
          ctx.fill();
        }
        if (datasets.length > maxDots) {
          const badgeAngle = datasetEndAngle + 0.08;
          const px = x + arcR * Math.cos(badgeAngle);
          const py = y + arcR * Math.sin(badgeAngle);
          ctx.font = "8px sans-serif";
          ctx.fillStyle = "#f1c40f";
          ctx.textAlign = "center";
          ctx.textBaseline = "middle";
          ctx.fillText(`+${datasets.length - maxDots}`, px, py);
        }

        nodeMiniCircleRef.current.set(node.id, { method: methodPositions, dataset: datasetPositions });
      } else {
        // Non-paper or simple graph: original circle drawing
        ctx.shadowColor = "rgba(0,0,0,0.4)";
        ctx.shadowBlur = 4;
        ctx.beginPath();
        ctx.arc(x, y, r, 0, 2 * Math.PI);
        ctx.fillStyle = color;
        ctx.fill();
        ctx.shadowBlur = 0;

        if (isHighlight) {
          ctx.beginPath();
          ctx.arc(x, y, r + 4, 0, 2 * Math.PI);
          ctx.strokeStyle = "rgba(150, 200, 255, 0.8)";
          ctx.lineWidth = 2;
          ctx.stroke();
        }
        if (useIntelligence && "is_research_gap" in node && (node as IntelligenceGraphNode).is_research_gap) {
          ctx.font = "10px sans-serif";
          ctx.fillStyle = "rgba(220, 80, 80, 0.9)";
          ctx.fillText("1", x + r - 4, y - r + 4);
        }
      }

      // Draw label just below each node (Obsidian-style) for quick reading.
      const rawLabel = ((node as unknown as { label?: string }).label || "").trim();
      if (rawLabel) {
        ctx.save();
        ctx.font = "10px sans-serif";
        ctx.fillStyle = "rgba(235, 235, 235, 0.9)";
        ctx.textAlign = "center";
        ctx.textBaseline = "top";
        const maxWidth = 160;
        let text = rawLabel;
        // Truncate with ellipsis if too wide
        while (ctx.measureText(text).width > maxWidth && text.length > 4) {
          text = text.slice(0, -4) + "…";
        }
        ctx.fillText(text, x, y + r + 6);
        ctx.restore();
      }

      ctx.restore();
    },
    [nodeColor, nodeRadius, hoverNode?.id, selectedNode?.id, showClusters, useIntelligence, paperHasUniqueConcept]
  );

  const linkOpacity = useCallback(
    (link: EnrichedLink | IntelligenceGraphLink) => {
      if (!highlightSet) return EDGE_OPACITY_DEFAULT;
      const a = typeof link.source === "string" ? link.source : (link.source as { id?: string })?.id;
      const b = typeof link.target === "string" ? link.target : (link.target as { id?: string })?.id;
      return a != null && b != null && highlightSet.has(a) && highlightSet.has(b)
        ? EDGE_OPACITY_HIGHLIGHT
        : useIntelligence && link.type === "contradiction"
          ? 0.8
          : EDGE_OPACITY_DEFAULT * 0.6;
    },
    [highlightSet, useIntelligence]
  );

  const linkWidthByWeight = useCallback((link: EnrichedLink | IntelligenceGraphLink) => {
    // Thin, Obsidian-style lines with slightly thicker contradiction edges.
    if (useIntelligence && link.type === "contradiction") return 2.2;
    return 1.6;
  }, [useIntelligence]);

  const linkWidth = useCallback(
    (link: EnrichedLink | IntelligenceGraphLink) => {
      const base = linkWidthByWeight(link);
      const opacity = linkOpacity(link);
      return opacity >= 0.8 ? base * 1.3 : base;
    },
    [linkOpacity, linkWidthByWeight]
  );

  const linkColor = useCallback(
    (link: EnrichedLink | IntelligenceGraphLink) => {
      if (useIntelligence && link.type === "contradiction") {
        // Keep contradictions clearly visible in red.
        return "rgba(230, 90, 90, 1)";
      }
      // All non-contradiction edges are soft grey; brightness handled via globalAlpha.
      return LINK_CITATION;
    },
    [useIntelligence]
  );

  const drawLink = useCallback(
    (link: EnrichedLink & { source?: { x?: number; y?: number }; target?: { x?: number; y?: number } }, ctx: CanvasRenderingContext2D) => {
      const src = link.source as { x?: number; y?: number } | undefined;
      const tgt = link.target as { x?: number; y?: number } | undefined;
      const x1 = src?.x ?? 0;
      const y1 = src?.y ?? 0;
      const x2 = tgt?.x ?? 0;
      const y2 = tgt?.y ?? 0;
      if (x1 === 0 && y1 === 0 && x2 === 0 && y2 === 0) return;
      const opacity = linkOpacity(link);
      const isHighlight = opacity >= 0.8;
      const w = linkWidth(link);
      ctx.beginPath();
      ctx.moveTo(x1, y1);
      ctx.lineTo(x2, y2);
      ctx.strokeStyle = linkColor(link);
      ctx.lineWidth = w;
      const prevAlpha = ctx.globalAlpha;
      ctx.globalAlpha = opacity;
      ctx.stroke();
      ctx.globalAlpha = prevAlpha;
      if (isHighlight) {
        ctx.shadowColor = "rgba(140, 200, 255, 0.5)";
        ctx.shadowBlur = 8;
        ctx.stroke();
        ctx.shadowBlur = 0;
      }
    },
    [linkOpacity, linkWidth, linkColor]
  );

  const [dimensions, setDimensions] = useState({ width: 800, height: 600 });
  const resizeObserver = useMemo(
    () =>
      typeof window !== "undefined"
        ? new ResizeObserver((entries) => {
            const entry = entries[0];
            if (entry) {
              const { width, height } = entry.contentRect;
              setDimensions((d) => (d.width === width && d.height === height ? d : { width: Math.max(100, width), height: Math.max(100, height) }));
            }
          })
        : null,
    []
  );
  useLayoutEffect(() => {
    const el = containerRef.current;
    if (!el || !resizeObserver) return;
    resizeObserver.observe(el);
    setDimensions({ width: el.clientWidth, height: el.clientHeight });
    return () => resizeObserver.disconnect();
  }, [resizeObserver]);

  if (loading) {
    return (
      <div className="flex h-[calc(100vh-8rem)] items-center justify-center" style={{ background: BG }}>
        <p className="text-muted-foreground">Loading graph...</p>
      </div>
    );
  }

  return (
    <div className="flex h-[calc(100vh-8rem)] w-full overflow-hidden" style={{ background: BG }}>
      <div ref={containerRef} className="relative flex-1 flex flex-col" style={{ background: BG }}>
        <div className="absolute top-2 left-2 z-10 flex flex-wrap items-center gap-2">
          {useIntelligence && (
            <Button
              variant={contradictionMode ? "default" : "secondary"}
              size="sm"
              onClick={() => setContradictionMode((v) => !v)}
            >
              Contradiction mode
            </Button>
          )}
          <Button
            variant={showClusters ? "default" : "secondary"}
            size="sm"
            onClick={() => setShowClusters((v) => !v)}
          >
            <Layers className="h-4 w-4 mr-1" />
            Show Clusters
          </Button>
          {!useIntelligence && (
            <>
              <select
                className="rounded-md border border-border bg-card px-2 py-1.5 text-sm text-foreground"
                value={edgeTypeFilter}
                onChange={(e) => setEdgeTypeFilter(e.target.value as typeof edgeTypeFilter)}
              >
                <option value="all">All edges</option>
                <option value="citation">Citation</option>
                <option value="similarity">Similarity</option>
                <option value="year_cluster">Year cluster</option>
              </select>
              <select
                className="rounded-md border border-border bg-card px-2 py-1.5 text-sm text-foreground"
                value={similarityThreshold}
                onChange={(e) => setSimilarityThreshold(Number(e.target.value) as 0.65 | 0.75)}
              >
                <option value={0.65}>Similarity ≥ 0.65</option>
                <option value={0.75}>Similarity ≥ 0.75</option>
              </select>
            </>
          )}
          <Button
            variant="secondary"
            size="sm"
            disabled={rebuildingIntel}
            onClick={async () => {
              try {
                setRebuildingIntel(true);
                await rebuildIntelligenceForWorkspace();
                await loadGraph();
              } finally {
                setRebuildingIntel(false);
              }
            }}
          >
            {rebuildingIntel ? "Rebuilding intelligence…" : "Re-run intelligence"}
          </Button>
          <Button variant="secondary" size="sm" onClick={handleBackgroundDblClick}>
            <Maximize2 className="h-4 w-4 mr-1" />
            Fit view
          </Button>
        </div>
        {graphData.nodes.length === 0 ? (
          <div className="absolute inset-0 flex flex-col items-center justify-center gap-3 text-muted-foreground">
            {loadError ? (
              <>
                <p>Couldn&apos;t load the graph. Check your connection and try again.</p>
                <Button variant="outline" size="sm" onClick={() => loadGraph()}>
                  Retry
                </Button>
              </>
            ) : (
              <p>No papers in this workspace. Upload papers to see the graph.</p>
            )}
          </div>
        ) : (
          <>
            {/* Subtle vignette instead of heavy noise, closer to Obsidian-style background */}
            <div
              className="absolute inset-0 pointer-events-none"
              style={{
                background: "radial-gradient(circle at center, rgba(255,255,255,0.02) 0, transparent 60%)",
              }}
            />
            <ForceGraph2D
              ref={fgRef}
              graphData={graphData}
              width={dimensions.width}
              height={dimensions.height}
              nodeId="id"
              nodeLabel={(n) => {
                const label = (n as { label?: string }).label ?? "";
                if (useIntelligence && "type" in n && (n as IntelligenceGraphNode).type === "paper" && paperHasUniqueConcept.has(n.id))
                  return `${label}\nContains unique concept (Research Gap)`;
                return label;
              }}
              linkSource="source"
              linkTarget="target"
              backgroundColor="transparent"
              nodeCanvasObject={drawNode}
              nodeCanvasObjectMode="replace"
              nodePointerAreaPaint={(node, color, ctx) => {
                const n = node as NodeWithMeta;
                const r = nodeRadius(n) + 6;
                if (n.x == null || n.y == null) return;
                ctx.fillStyle = color;
                ctx.beginPath();
                ctx.arc(n.x, n.y, r, 0, 2 * Math.PI);
                ctx.fill();
              }}
              linkCanvasObject={drawLink}
              linkCanvasObjectMode="replace"
              onNodeClick={(node, ev) => {
                ev.preventDefault();
                handleNodeClick(node as NodeWithMeta, ev as unknown as React.MouseEvent);
              }}
              onNodeHover={(node) => setHoverNode(node as NodeWithMeta)}
              onBackgroundClick={handleBackgroundClick}
              d3AlphaDecay={0.01}
              d3VelocityDecay={0.2}
              cooldownTicks={200}
              onEngineStop={() => {
                if (fgRef.current) fgRef.current.zoomToFit(400, 50);
              }}
            />
          </>
        )}
      </div>

      {/* Paper intelligence popup (methods/datasets from internal mini-circles) */}
      {paperPopup && (
        <>
          <div
            className="fixed inset-0 z-40"
            aria-hidden
            onClick={() => setPaperPopup(null)}
          />
          <div
            className="fixed z-50 min-w-[220px] max-w-[320px] rounded-lg border border-border bg-card/95 p-3 shadow-xl backdrop-blur-sm animate-in fade-in-0 zoom-in-95 duration-150"
            style={{ left: Math.min(paperPopup.x + 12, typeof window !== "undefined" ? window.innerWidth - 340 : paperPopup.x + 12), top: paperPopup.y + 12 }}
            role="dialog"
            aria-label={paperPopup.type === "methods" ? "Methods used" : "Datasets used"}
          >
            <p className="text-xs font-medium text-muted-foreground mb-1.5 line-clamp-2">{paperPopup.node.label}</p>
            {paperPopup.type === "methods" ? (
              <>
                <p className="text-xs font-semibold text-foreground uppercase tracking-wide mb-1">Methods used</p>
                <ul className="text-sm text-foreground list-disc pl-4 space-y-0.5">
                  {(paperPopup.node.methods_used ?? []).map((m, i) => (
                    <li key={i}>{m}</li>
                  ))}
                </ul>
              </>
            ) : (
              <>
                <p className="text-xs font-semibold text-foreground uppercase tracking-wide mb-1">Datasets used</p>
                <ul className="text-sm text-foreground list-disc pl-4 space-y-0.5">
                  {(paperPopup.node.datasets_used ?? []).map((d, i) => (
                    <li key={i}>{d}</li>
                  ))}
                </ul>
              </>
            )}
          </div>
        </>
      )}

      {selectedNode && (
        <aside className="w-[360px] shrink-0 border-l border-border bg-card p-4 overflow-y-auto shadow-xl animate-in slide-in-from-right duration-200">
          <div className="space-y-3">
            <h3 className="font-semibold text-foreground line-clamp-2">{selectedNode.label}</h3>
            {useIntelligence && "type" in selectedNode && (selectedNode as IntelligenceGraphNode).type === "concept" ? (
              <>
                {(selectedNode as IntelligenceGraphNode).is_research_gap && (
                  <div className="rounded-md bg-red-500/10 border border-red-500/30 px-2 py-1.5 text-sm text-red-400">
                    Unique concept — potential research gap
                  </div>
                )}
                <p className="text-sm text-muted-foreground">
                  Connected papers: {(selectedNode as IntelligenceGraphNode).paper_count ?? 0}
                </p>
                {graphData.links
                  .filter((l) => l.source === selectedNode.id || l.target === selectedNode.id)
                  .map((l) => {
                    const otherId = l.source === selectedNode.id ? l.target : l.source;
                    const other = graphData.nodes.find((n) => n.id === otherId);
                    return other && (other as IntelligenceGraphNode).type === "paper" ? (
                      <div key={otherId} className="text-sm">
                        <a href={`/pdf/${otherId}`} className="text-primary hover:underline line-clamp-2">
                          {(other as IntelligenceGraphNode).label}
                        </a>
                      </div>
                    ) : null;
                  })}
              </>
            ) : panelPaper || (useIntelligence && "main_problem" in selectedNode) ? (
              <>
                {(selectedNode.year ?? panelPaper?.publication_date) && (
                  <p className="text-sm text-muted-foreground">
                    Year: {selectedNode.year ?? (panelPaper?.publication_date ? new Date(panelPaper.publication_date).getFullYear() : "—")}
                  </p>
                )}
                {useIntelligence && "main_problem" in selectedNode && (selectedNode as IntelligenceGraphNode).main_problem && (
                  <div>
                    <p className="text-xs font-medium text-muted-foreground uppercase">Main problem</p>
                    <p className="text-sm text-foreground">{(selectedNode as IntelligenceGraphNode).main_problem}</p>
                  </div>
                )}
                {useIntelligence && "methods_used" in selectedNode && (selectedNode as IntelligenceGraphNode).methods_used?.length ? (
                  <div>
                    <p className="text-xs font-medium text-muted-foreground uppercase">Methods</p>
                    <p className="text-sm text-foreground">{(selectedNode as IntelligenceGraphNode).methods_used!.join(", ")}</p>
                  </div>
                ) : null}
                {useIntelligence && "datasets_used" in selectedNode && (selectedNode as IntelligenceGraphNode).datasets_used?.length ? (
                  <div>
                    <p className="text-xs font-medium text-muted-foreground uppercase">Datasets</p>
                    <p className="text-sm text-foreground">{(selectedNode as IntelligenceGraphNode).datasets_used!.join(", ")}</p>
                  </div>
                ) : null}
                {useIntelligence && "key_findings" in selectedNode && (selectedNode as IntelligenceGraphNode).key_findings?.length ? (
                  <div>
                    <p className="text-xs font-medium text-muted-foreground uppercase">Key findings</p>
                    <ul className="text-sm text-foreground list-disc pl-4">
                      {(selectedNode as IntelligenceGraphNode).key_findings!.slice(0, 3).map((f, i) => (
                        <li key={i} className="line-clamp-2">{f}</li>
                      ))}
                    </ul>
                  </div>
                ) : null}
                {!useIntelligence && (selectedNode as NodeWithMeta).citationCount != null && (
                  <p className="text-sm text-muted-foreground">
                    Citation links: {(selectedNode as NodeWithMeta).citationCount ?? 0} · Similar: {(selectedNode as NodeWithMeta).similarCount ?? 0}
                  </p>
                )}
                {panelPaper?.abstract && (
                  <p className="text-sm text-muted-foreground line-clamp-4">{panelPaper.abstract}</p>
                )}
                <div className="flex gap-2 flex-wrap">
                  {!useIntelligence && (
                    <Button variant="outline" size="sm" onClick={zoomToCluster}>
                      <Maximize2 className="mr-2 h-4 w-4" />
                      Zoom to cluster
                    </Button>
                  )}
                  {(!useIntelligence || (selectedNode as IntelligenceGraphNode).type === "paper") && (
                    <Button variant="default" size="sm" asChild>
                      <a href={`/pdf/${selectedNode.id}`} target="_blank" rel="noopener noreferrer">
                        <ExternalLink className="mr-2 h-4 w-4" />
                        Open Paper
                      </a>
                    </Button>
                  )}
                </div>
              </>
            ) : (
              <p className="text-sm text-muted-foreground">Loading paper details…</p>
            )}
          </div>
        </aside>
      )}
    </div>
  );
}
