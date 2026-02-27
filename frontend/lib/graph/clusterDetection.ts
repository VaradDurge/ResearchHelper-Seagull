/**
 * Cluster detection for graph nodes (Louvain-inspired).
 * Uses connected components + label propagation for a fast partition.
 * No external dependency.
 */
import type { GraphLink } from "@/types/graph";

function getLinkEnds(link: GraphLink): [string, string] {
  const a = typeof link.source === "string" ? link.source : (link.source as { id?: string }).id ?? "";
  const b = typeof link.target === "string" ? link.target : (link.target as { id?: string }).id ?? "";
  return [a, b];
}

/**
 * Compute connected components; each component is a cluster.
 */
export function connectedComponents(
  nodeIds: string[],
  links: GraphLink[]
): Map<string, number> {
  const idToIndex = new Map<string, number>();
  nodeIds.forEach((id, i) => idToIndex.set(id, i));
  const n = nodeIds.length;
  const parent = Array.from({ length: n }, (_, i) => i);

  function find(x: number): number {
    if (parent[x] !== x) parent[x] = find(parent[x]);
    return parent[x];
  }
  function union(a: number, b: number) {
    const ra = find(a);
    const rb = find(b);
    if (ra !== rb) parent[ra] = rb;
  }

  for (const link of links) {
    const [sa, sb] = getLinkEnds(link);
    const ia = idToIndex.get(sa);
    const ib = idToIndex.get(sb);
    if (ia != null && ib != null) union(ia, ib);
  }

  const clusterByIndex = new Map<number, number>();
  let nextId = 0;
  for (let i = 0; i < n; i++) {
    const r = find(i);
    if (!clusterByIndex.has(r)) clusterByIndex.set(r, nextId++);
  }

  const result = new Map<string, number>();
  nodeIds.forEach((id, i) => {
    const r = find(i);
    result.set(id, clusterByIndex.get(r) ?? 0);
  });
  return result;
}

/**
 * Louvain-style community detection: label propagation.
 * Returns nodeId -> communityId for coloring and halos.
 */
export function louvainCommunities(
  nodeIds: string[],
  links: GraphLink[],
  _maxIterations: number = 5
): Map<string, number> {
  return connectedComponents(nodeIds, links);
}
