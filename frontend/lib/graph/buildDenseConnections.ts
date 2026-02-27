/**
 * Dense connection builder: ensures every paper has visible connections
 * using existing data only (no backend changes).
 * - Same-year clustering
 * - Cap max edges per node
 * - Min 2–3 connections per node where possible
 */
import type { GraphNode, GraphLink } from "@/types/graph";

const MAX_EDGES_PER_NODE = 15;
const MIN_CONNECTIONS_TARGET = 2;

export interface EnrichedLink extends GraphLink {
  distance?: number;
}

/**
 * Build dense connections from API nodes + links.
 * Adds same-year edges, caps edges per node, assigns link distance for physics.
 */
export function buildDenseConnections(
  nodes: GraphNode[],
  links: GraphLink[]
): EnrichedLink[] {
  const nodeIds = new Set(nodes.map((n) => n.id));
  const idToNode = new Map(nodes.map((n) => [n.id, n]));

  const edgeCount = new Map<string, number>();
  nodes.forEach((n) => edgeCount.set(n.id, 0));

  const linkSet = new Set<string>();
  function linkKey(a: string, b: string) {
    return a < b ? `${a}|${b}` : `${b}|${a}`;
  }
  function addLink(source: string, target: string, type: GraphLink["type"], weight?: number, cap: boolean = true): boolean {
    if (source === target) return false;
    if (!nodeIds.has(source) || !nodeIds.has(target)) return false;
    const k = linkKey(source, target);
    if (linkSet.has(k)) return false;
    const sc = edgeCount.get(source)!;
    const tc = edgeCount.get(target)!;
    if (cap && (sc >= MAX_EDGES_PER_NODE || tc >= MAX_EDGES_PER_NODE)) return false;
    linkSet.add(k);
    edgeCount.set(source, sc + 1);
    edgeCount.set(target, tc + 1);
    return true;
  }

  const result: EnrichedLink[] = [];

  for (const link of links) {
    const src = typeof link.source === "string" ? link.source : (link.source as { id?: string }).id;
    const tgt = typeof link.target === "string" ? link.target : (link.target as { id?: string }).id;
    if (!src || !tgt) continue;
    if (!addLink(src, tgt, link.type, link.weight, false)) continue;
    const w = link.weight ?? 0.5;
    result.push({
      ...link,
      source: src,
      target: tgt,
      distance: link.type === "similarity" ? 80 + (1 - w) * 120 : 100,
    });
  }

  const byYear = new Map<number, string[]>();
  for (const n of nodes) {
    if (n.year != null) {
      const list = byYear.get(n.year) ?? [];
      list.push(n.id);
      byYear.set(n.year, list);
    }
  }

  for (const [, ids] of byYear) {
    if (ids.length < 2) continue;
    for (let i = 0; i < ids.length; i++) {
      for (let j = i + 1; j < ids.length; j++) {
        if (addLink(ids[i], ids[j], "year_cluster", 0.5, true)) {
          result.push({
            source: ids[i],
            target: ids[j],
            type: "year_cluster",
            weight: 0.5,
            distance: 120,
          });
        }
      }
    }
  }

  for (const n of nodes) {
    const count = edgeCount.get(n.id) ?? 0;
    if (count >= MIN_CONNECTIONS_TARGET) continue;
    const others = nodes.filter((o) => o.id !== n.id && (edgeCount.get(o.id) ?? 0) < MAX_EDGES_PER_NODE);
    const sameYear = n.year != null ? others.filter((o) => o.year === n.year) : [];
    const pool = sameYear.length >= MIN_CONNECTIONS_TARGET - count ? sameYear : others;
    let added = 0;
    for (const o of pool) {
      if (added >= MIN_CONNECTIONS_TARGET - count) break;
      if (addLink(n.id, o.id, "year_cluster", 0.4, true)) {
        result.push({
          source: n.id,
          target: o.id,
          type: "year_cluster",
          weight: 0.4,
          distance: 150,
        });
        added++;
      }
    }
  }

  return result;
}
