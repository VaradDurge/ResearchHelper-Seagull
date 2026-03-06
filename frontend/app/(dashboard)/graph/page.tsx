"use client";

import { useCallback, useMemo, useRef, useState, useEffect, useLayoutEffect } from "react";
import dynamic from "next/dynamic";
import { getGraphWorkspace, getGraphWorkspaceIntelligence } from "@/lib/api/graph";
import { getPaper } from "@/lib/api/papers";
import type { GraphNode, GraphLink, GraphData, IntelligenceGraphNode, IntelligenceGraphLink, IntelligenceGraphResponse, ContradictionEntry } from "@/types/graph";
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
// Paper/title nodes: beige #DFD0B8, fully opaque
const NODE_DEFAULT = "rgba(223, 208, 184, 1)"; // #DFD0B8
const NODE_HOVER = "rgba(240, 228, 205, 1)";
const NODE_SELECTED = "rgba(255, 245, 220, 1)";
const NODE_FADED = "rgba(223, 208, 184, 0.15)";
const EDGE_OPACITY_DEFAULT = 0.14;
const EDGE_OPACITY_HIGHLIGHT = 0.95;
// Edge colors – all links rendered as #7E7474
const LINK_CITATION = "#7E7474";
const LINK_SIMILARITY = "#7E7474";
const LINK_YEAR = "#7E7474";
const LINK_HIGHLIGHT = "#7E7474";
const CLUSTER_COLORS = [
  "rgba(100, 160, 255, 0.5)",
  "rgba(160, 100, 255, 0.5)",
  "rgba(255, 140, 100, 0.5)",
  "rgba(100, 220, 180, 0.5)",
  "rgba(220, 180, 100, 0.5)",
  "rgba(180, 100, 220, 0.5)",
];

// Debug flag so we only log once from the custom link renderer
let _loggedCustomLinkRenderer = false;

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
  // STEP 3 — Runtime proof: open DevTools Console and refresh. Must see this log.
  useEffect(() => {
    // eslint-disable-next-line no-console
    console.log("GRAPH COMPONENT MOUNTED");
  }, []);

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
  /** When user clicks a contradiction edge, show payload in right panel. */
  const [selectedContradiction, setSelectedContradiction] = useState<IntelligenceGraphLink | null>(null);
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

  // STEP 8 — Debug: log when selectedContradiction changes (panel should open)
  useEffect(() => {
    // eslint-disable-next-line no-console
    console.log("[CONTRADICTION DEBUG] selectedContradiction state=", selectedContradiction);
  }, [selectedContradiction]);

  // Debug: which graph mode is active
  useEffect(() => {
    if (useIntelligence) {
      // eslint-disable-next-line no-console
      console.log("INTELLIGENCE GRAPH ACTIVE");
    } else {
      // eslint-disable-next-line no-console
      console.log("SIMPLE GRAPH ACTIVE");
    }
  }, [useIntelligence]);

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
    // STEP 5 — Exact string "contradiction" (not "Contradiction" or "CONTRADICT")
    if (contradictionMode) return intelligenceData.links.filter((l) => l.type === "contradiction");
    return intelligenceData.links;
  }, [intelligenceData?.links, contradictionMode]);

  // STEP 5 — Debug: when contradiction mode ON, log visible link count
  useEffect(() => {
    if (useIntelligence && contradictionMode) {
      // eslint-disable-next-line no-console
      console.log("[CONTRADICTION DEBUG] Contradiction mode ON: visible links=", filteredIntelligenceLinks.length, filteredIntelligenceLinks);
    }
  }, [useIntelligence, contradictionMode, filteredIntelligenceLinks]);

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

      // STEP 4 — Verify frontend receives contradiction links from API
      const links = intel?.links ?? [];
      const contradictionLinks = links.filter((l: { type?: string }) => l.type === "contradiction");
      // eslint-disable-next-line no-console
      console.log("[CONTRADICTION DEBUG] After fetch: total links=", links.length, "contradiction links=", contradictionLinks.length, contradictionLinks);
      if (links.length > 0 && contradictionLinks.length === 0) {
        // eslint-disable-next-line no-console
        console.warn("[CONTRADICTION DEBUG] API returned links but none with type 'contradiction'. Check backend.");
      }

      // STEP 9 — Frontend active workspace
      // eslint-disable-next-line no-console
      console.log("[CONTRADICTION DEBUG] Frontend request workspace_id=", requestWorkspaceId);

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

  // Force simulation tuning: compact, centered layout (no extreme scattering)
  const CHARGE_STRENGTH = -45;
  const LINK_DISTANCE_DEFAULT = 45;
  const CENTER_STRENGTH = 0.6;

  useEffect(() => {
    if (!fgRef.current || !graphData.nodes.length) return;
    try {
      const charge = fgRef.current.d3Force("charge");
      if (charge && typeof charge.strength === "function") {
        (charge as { strength: (v: number) => void }).strength(CHARGE_STRENGTH);
      }
      const link = fgRef.current.d3Force("link");
      if (link) {
        if (typeof link.strength === "function") (link as { strength: (v: number) => void }).strength(0.75);
        if (typeof link.distance === "function") {
          link.distance((l: EnrichedLink) => (l.distance != null ? l.distance : LINK_DISTANCE_DEFAULT));
        }
      }
      const center = fgRef.current.d3Force("center");
      if (center && typeof center.strength === "function") {
        (center as { strength: (v: number) => void }).strength(CENTER_STRENGTH);
      }
      // Diagnostic: log force config
      const nodeIds = new Set(graphData.nodes.map((n) => n.id));
      const adj: Record<string, Set<string>> = {};
      nodeIds.forEach((id) => (adj[id] = new Set()));
      for (const l of graphData.links) {
        const a = typeof l.source === "string" ? l.source : (l.source as { id?: string })?.id;
        const b = typeof l.target === "string" ? l.target : (l.target as { id?: string })?.id;
        if (a && b && nodeIds.has(a) && nodeIds.has(b)) {
          adj[a].add(b);
          adj[b].add(a);
        }
      }
      let components = 0;
      const seen = new Set<string>();
      for (const id of nodeIds) {
        if (seen.has(id)) continue;
        components += 1;
        const stack = [id];
        while (stack.length) {
          const u = stack.pop()!;
          if (seen.has(u)) continue;
          seen.add(u);
          for (const v of adj[u]) stack.push(v);
        }
      }
      // eslint-disable-next-line no-console
      console.log("[GRAPH FORCE] charge strength:", CHARGE_STRENGTH, "| link distance:", LINK_DISTANCE_DEFAULT, "| center strength:", CENTER_STRENGTH, "| disconnected components:", components);
    } catch {
      // ignore
    }
  }, [graphData.nodes.length, graphData.links, graphData.nodes]);

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
    setSelectedContradiction(null);
  }, []);

  const handleBackgroundDblClick = useCallback(() => {
    if (fgRef.current) {
      fgRef.current.zoomToFit(400, 100);
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
      setSelectedContradiction(null);
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

  const NODE_RADIUS_DEFAULT = 3;
  const NODE_RADIUS_PAPER = 6;

  /** Visual radius by type: paper nodes slightly larger; method/dataset/concept use default. */
  const getNodeRadius = useCallback((node: any) => {
    return node?.type === "paper" ? NODE_RADIUS_PAPER : NODE_RADIUS_DEFAULT;
  }, []);

  // Pointer hit-testing radius (matches drawNode circle).
  const nodeRadius = useCallback((node: any) => getNodeRadius(node), [getNodeRadius]);

  const lastScaleLogRef = useRef<number | null>(null);

  // Custom node renderer: circle + Obsidian-style label below (all node types).
  // Label uses library globalScale (3rd param) for zoom-stable visual size.
  const drawNode = useCallback(
    (node: any, ctx: CanvasRenderingContext2D, globalScale?: number) => {
      const x = node?.x;
      const y = node?.y;
      if (x == null || y == null) return;

      const size = getNodeRadius(node);
      const scale = Math.max(0.001, globalScale ?? 1);
      // Temporary debug: confirm globalScale changes when zooming (log once per distinct value).
      if (lastScaleLogRef.current !== scale) {
        lastScaleLogRef.current = scale;
        // eslint-disable-next-line no-console
        console.log("Zoom scale (globalScale):", scale);
      }
      const labelText =
        node.label ?? node.name ?? node.title ?? node.id ?? "";

      ctx.save();

      // 1) Draw node circle (no zoom scaling)
      ctx.beginPath();
      ctx.arc(x, y, size, 0, 2 * Math.PI);
      ctx.fillStyle = "#7077A1";
      ctx.fill();

      // 2) Label below node: inverse scale so text stays visually stable
      if (labelText) {
        const baseFontSize = 6;
        let fontSize = baseFontSize / scale;
        fontSize = Math.max(3, Math.min(fontSize, 10));

        ctx.font = `${fontSize}px Inter, sans-serif`;
        ctx.textAlign = "center";
        ctx.textBaseline = "top";
        ctx.fillStyle = "rgba(223, 208, 184, 0.85)";

        const maxLength = 30;
        const displayLabel =
          String(labelText).length > maxLength
            ? String(labelText).substring(0, maxLength) + "..."
            : String(labelText);
        ctx.fillText(displayLabel, x, y + size + 4);
      }

      ctx.restore();
    },
    [getNodeRadius]
  );

  const linkOpacity = useCallback(
    (_link: EnrichedLink | IntelligenceGraphLink) => {
      // For debugging link color, keep links fully opaque (pure white).
      return EDGE_OPACITY_DEFAULT;
    },
    []
  );

  const linkWidthByWeight = useCallback((link: EnrichedLink | IntelligenceGraphLink) => {
    // Thin, Obsidian-style lines with slightly thicker contradiction edges.
    if (useIntelligence && link.type === "contradiction") return 2.2;
    return 1.6;
  }, [useIntelligence]);

  const drawLink = useCallback(
    (link: unknown, ctx: CanvasRenderingContext2D) => {
      const L = link as { source?: { x?: number; y?: number }; target?: { x?: number; y?: number }; type?: string };
      if (!_loggedCustomLinkRenderer) {
        // eslint-disable-next-line no-console
        console.log("Custom link renderer active");
        _loggedCustomLinkRenderer = true;
      }
      const x1 = L.source?.x ?? 0;
      const y1 = L.source?.y ?? 0;
      const x2 = L.target?.x ?? 0;
      const y2 = L.target?.y ?? 0;
      if (x1 === 0 && y1 === 0 && x2 === 0 && y2 === 0) return;

      // STEP 6 — Contradiction links: forced thick red for debugging; log each draw
      const isContradiction = useIntelligence && L.type === "contradiction";
      if (isContradiction) {
        // eslint-disable-next-line no-console
        console.log("[CONTRADICTION DEBUG] Drawing contradiction link", L.source, "->", L.target);
        ctx.strokeStyle = "rgba(255, 0, 0, 0.95)";
        ctx.lineWidth = 8;
      } else {
        ctx.strokeStyle = "rgba(126, 116, 124, 0.2)";
        ctx.lineWidth = 1;
      }
      ctx.beginPath();
      ctx.moveTo(x1, y1);
      ctx.lineTo(x2, y2);
      ctx.stroke();
    },
    [useIntelligence]
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
      <div className="flex h-[calc(100vh-8rem)] flex-col items-center justify-center gap-2" style={{ background: BG }}>
        <p className="text-lg font-semibold text-foreground">HELLO VARAAD</p>
        <p className="text-muted-foreground">Loading graph...</p>
      </div>
    );
  }

  return (
    <div className="flex h-[calc(100vh-8rem)] w-full overflow-hidden" style={{ background: BG }}>
      {/* STEP 2 — Visual breakpoint: if you see this, this file is the one rendering /graph */}
      <div className="absolute top-0 left-0 right-0 z-[100] bg-red-600 text-white py-3 text-center text-xl font-bold shadow-lg">
        GRAPH FILE ACTIVE
      </div>
      <div ref={containerRef} className="relative flex-1 flex flex-col" style={{ background: BG }}>
        <div className="absolute top-2 right-4 z-20 text-xs font-semibold text-foreground/80">
          HELLO VARAAD
        </div>
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
            {/* When contradiction mode is ON but no contradiction edges exist */}
            {useIntelligence && contradictionMode && graphData.links.length === 0 && (
              <div className="absolute inset-0 flex items-center justify-center pointer-events-none z-10">
                <p className="text-muted-foreground">No contradiction data.</p>
              </div>
            )}
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
              linkSource="source"
              linkTarget="target"
              // Explicitly set white link color; nodeCanvasObject handles nodes.
              linkColor={() => "#FFFFFF"}
              backgroundColor="transparent"
              nodeCanvasObject={drawNode}
              nodeCanvasObjectMode={() => "replace"}
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
              linkCanvasObjectMode={() => "replace"}
              onNodeClick={(node, ev) => {
                ev.preventDefault();
                handleNodeClick(node as NodeWithMeta, ev as unknown as React.MouseEvent);
              }}
              onNodeHover={(node) => setHoverNode(node as NodeWithMeta)}
              onLinkClick={(link) => {
                const l = link as IntelligenceGraphLink;
                // STEP 7 — Verify link click handler receives contradiction links
                if (l?.type === "contradiction") {
                  // eslint-disable-next-line no-console
                  console.log("[CONTRADICTION DEBUG] Clicked contradiction edge", l);
                  setSelectedContradiction(l);
                  setSelectedNode(null);
                }
              }}
              onBackgroundClick={handleBackgroundClick}
              d3AlphaDecay={0.02}
              d3VelocityDecay={0.25}
              cooldownTicks={300}
              onEngineStop={() => {
                // Auto-fit only after simulation stabilizes (no fit before engine ends)
                setTimeout(() => {
                  if (fgRef.current) {
                    fgRef.current.zoomToFit(400, 100);
                    // eslint-disable-next-line no-console
                    console.log("[GRAPH FORCE] fitView triggered after stabilization (padding=100, duration=400ms)");
                  }
                }, 80);
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

      {(selectedContradiction || selectedNode) && (
        <aside className="w-[360px] shrink-0 border-l border-border bg-card p-4 overflow-y-auto shadow-xl animate-in slide-in-from-right duration-200">
          <div className="space-y-3">
            {selectedContradiction ? (
              <>
                <h2 className="text-sm font-semibold text-foreground uppercase tracking-wide">Contradictions detected</h2>
                <p className="text-sm text-foreground">
                  <strong>
                    {graphData.nodes.find((n) => n.id === selectedContradiction.source)?.label ?? selectedContradiction.source}
                  </strong>
                  {" vs "}
                  <strong>
                    {graphData.nodes.find((n) => n.id === selectedContradiction.target)?.label ?? selectedContradiction.target}
                  </strong>
                </p>
                {selectedContradiction.contradictions && selectedContradiction.contradictions.length > 0 ? (
                  <div className="space-y-4">
                    {selectedContradiction.contradictions.map((item: ContradictionEntry, index: number) => (
                      <div key={index} className="rounded border border-border bg-muted/30 p-3 text-sm">
                        <h4 className="font-medium text-foreground mb-1.5">Contradiction {index + 1}</h4>
                        <p className="text-muted-foreground mb-1"><strong>Claim:</strong> {item.claim}</p>
                        {item.paperA_statement != null && item.paperA_statement !== "" && (
                          <p className="text-foreground mb-1"><strong>Paper A (support):</strong> {item.paperA_statement}</p>
                        )}
                        {item.paperB_statement != null && item.paperB_statement !== "" && (
                          <p className="text-foreground"><strong>Paper B (contradict):</strong> {item.paperB_statement}</p>
                        )}
                      </div>
                    ))}
                  </div>
                ) : (
                  <p className="text-sm text-muted-foreground">
                    These papers do not have structured contradiction evidence yet. Run claim verification.
                  </p>
                )}
              </>
            ) : selectedNode ? (
              <>
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
              </>
            ) : null}
          </div>
        </aside>
      )}
    </div>
  );
}
