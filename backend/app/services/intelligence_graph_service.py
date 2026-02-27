"""
Research Intelligence Graph — buildWorkspaceGraph().
Reads from papers + paper_intelligence; builds paper/method/dataset/concept nodes and edges.
Server-side only; frontend only renders. Similarity uses stored embeddings (cosine).
"""
from typing import List, Dict, Set, Tuple, Any, Optional
import re
import logging
import math

from app.db.mongo import (
    get_papers_collection,
    get_paper_intelligence_collection,
    get_claim_verifications_collection,
)
from app.models.schemas import (
    IntelligenceGraphNode,
    IntelligenceGraphLink,
)
from app.services.graph_service import _cited_dois_from_metadata
from app.config import settings

logger = logging.getLogger(__name__)

MAX_NODES = 500
# Temporarily 0 to verify connections; revert to 0.5 / 0.25 when asked
SIMILARITY_THRESHOLD_INITIAL = 0.0
SIMILARITY_THRESHOLD_MIN = 0.0
KEYWORD_OVERLAP_MIN = 1
MIN_METHOD_EDGES = 1
MIN_CONCEPT_EDGES = 2
MIN_PAPER_PAPER_EDGES = 1
MIN_TITLE_WORD_LEN = 4


def _year_from_paper(doc: dict) -> Optional[int]:
    pub = doc.get("publication_date")
    if not pub:
        return None
    match = re.search(r"\d{4}", str(pub))
    return int(match.group(0)) if match else None


def _cosine_similarity(a: List[float], b: List[float]) -> float:
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(x * x for x in b))
    if na <= 0 or nb <= 0:
        return 0.0
    return dot / (na * nb)


def _normalize_label(s: str) -> str:
    return " ".join(s.strip().lower().split())


def _title_to_keywords(title: str) -> Set[str]:
    """Extract significant words from paper title for thematic overlap (e.g. 'neural network')."""
    if not title or not title.strip():
        return set()
    words = re.findall(r"[a-zA-Z0-9]+", title.lower())
    return {w for w in words if len(w) >= MIN_TITLE_WORD_LEN}


def _get_contradiction_edges(workspace_id: str, paper_ids: Set[str]) -> List[Tuple[str, str]]:
    """From claim_verifications, find paper pairs (support, contradict) for contradiction edges."""
    coll = get_claim_verifications_collection()
    cursor = coll.find({"workspace_id": workspace_id}).sort("created_at", -1).limit(200)
    pairs: List[Tuple[str, str]] = []
    seen = set()
    for doc in cursor:
        result = doc.get("result") or {}
        if result.get("contradict_count", 0) == 0:
            continue
        evidence = result.get("scored_evidence") or []
        support_ids = set()
        contradict_ids = set()
        for item in evidence:
            if not isinstance(item, dict):
                continue
            pid = item.get("paper_id")
            if not pid or pid not in paper_ids:
                continue
            raw = item.get("label") or item.get("classification")
            if isinstance(raw, dict):
                raw = raw.get("classification") or raw.get("label")
            label = (raw or "").upper()
            if "SUPPORT" in label:
                support_ids.add(pid)
            elif "CONTRADICT" in label:
                contradict_ids.add(pid)
        for pa in support_ids:
            for pb in contradict_ids:
                if pa == pb:
                    continue
                key = (pa, pb) if pa < pb else (pb, pa)
                if key not in seen:
                    seen.add(key)
                    pairs.append((pa, pb))
    return pairs


def build_workspace_graph(
    workspace_id: str,
    user_id: Optional[str] = None,
    cap_nodes: int = MAX_NODES,
) -> Tuple[List[IntelligenceGraphNode], List[IntelligenceGraphLink], bool]:
    """
    Build full intelligence graph for workspace.
    Returns (nodes, links, has_intelligence).
    has_intelligence False when no paper_intelligence data exists (frontend can fall back to simple graph).
    """
    papers_coll = get_papers_collection()
    docs = list(
        papers_coll.find({"workspace_id": workspace_id}).sort("upload_date", -1).limit(cap_nodes)
    )
    if not docs:
        logger.debug("Intelligence graph: no papers for workspace_id=%s", workspace_id)
        return [], [], False

    papers = []
    for d in docs:
        pid = d.get("paper_id")
        if not pid:
            continue
        papers.append({
            "id": pid,
            "title": d.get("title") or "Untitled",
            "publication_date": d.get("publication_date"),
            "metadata": d.get("metadata") or {},
            "doi": d.get("doi"),
        })
    if not papers:
        return [], [], False
    paper_ids = {p["id"] for p in papers}

    intel_coll = get_paper_intelligence_collection()
    intel_by_paper: Dict[str, dict] = {}
    for d in intel_coll.find({"workspace_id": workspace_id, "paper_id": {"$in": list(paper_ids)}}):
        # Only treat as valid if it has at least embedding or meaningful structured data
        has_embedding = d.get("embedding_vector") and len(d.get("embedding_vector") or []) > 0
        has_keywords = d.get("keywords") and len(d.get("keywords") or []) > 0
        has_main = bool((d.get("main_problem") or "").strip())
        if has_embedding or has_keywords or has_main:
            intel_by_paper[d["paper_id"]] = d

    # If no intelligence data at all, signal fallback
    if not intel_by_paper:
        return [], [], False

    nodes: List[IntelligenceGraphNode] = []
    links: List[IntelligenceGraphLink] = []
    link_set: Set[Tuple[str, str, str]] = set()

    # Global deduplicated entity ids
    method_ids: Dict[str, str] = {}
    dataset_ids: Dict[str, str] = {}
    concept_ids: Dict[str, str] = {}

    def add_method(name: str) -> str:
        key = _normalize_label(name)
        if not key or len(key) < 2:
            return ""
        if key not in method_ids:
            mid = f"method:{key}"
            method_ids[key] = mid
            nodes.append(
                IntelligenceGraphNode(id=mid, label=name.strip()[:80], type="method", paper_count=None)
            )
        return method_ids[key]

    def add_dataset(name: str) -> str:
        key = _normalize_label(name)
        if not key or len(key) < 2:
            return ""
        if key not in dataset_ids:
            did = f"dataset:{key}"
            dataset_ids[key] = did
            nodes.append(
                IntelligenceGraphNode(id=did, label=name.strip()[:80], type="dataset", paper_count=None)
            )
        return dataset_ids[key]

    def add_concept(name: str) -> str:
        key = _normalize_label(name)
        if not key or len(key) < 2:
            return ""
        if key not in concept_ids:
            cid = f"concept:{key}"
            concept_ids[key] = cid
            nodes.append(
                IntelligenceGraphNode(id=cid, label=name.strip()[:80], type="concept", paper_count=0)
            )
        return concept_ids[key]

    # Paper nodes (with optional intelligence payload for side panel)
    for p in papers:
        year = _year_from_paper(p)
        intel = intel_by_paper.get(p["id"]) or {}
        nodes.append(
            IntelligenceGraphNode(
                id=p["id"],
                label=p["title"][:120],
                type="paper",
                year=year,
                main_problem=intel.get("main_problem"),
                methods_used=intel.get("methods_used") or [],
                key_findings=intel.get("key_findings") or [],
                datasets_used=intel.get("datasets_used") or [],
                keywords=intel.get("keywords") or [],
                domain=intel.get("domain"),
                claims=intel.get("claims") or [],
            )
        )

    # Paper -> method, dataset, concept edges; count concept usage
    for p in papers:
        pid = p["id"]
        intel = intel_by_paper.get(pid) or {}
        methods = intel.get("methods_used") or []
        datasets = intel.get("datasets_used") or []
        keywords = intel.get("keywords") or []
        for m in methods[:15]:
            mid = add_method(m)
            if mid and (pid, mid, "uses_method") not in link_set:
                link_set.add((pid, mid, "uses_method"))
                links.append(IntelligenceGraphLink(source=pid, target=mid, type="uses_method"))
        for d in datasets[:10]:
            did = add_dataset(d)
            if did and (pid, did, "uses_dataset") not in link_set:
                link_set.add((pid, did, "uses_dataset"))
                links.append(IntelligenceGraphLink(source=pid, target=did, type="uses_dataset"))
        for k in keywords[:15]:
            cid = add_concept(k)
            if cid:
                if (pid, cid, "has_concept") not in link_set:
                    link_set.add((pid, cid, "has_concept"))
                    links.append(IntelligenceGraphLink(source=pid, target=cid, type="has_concept"))
                # bump paper_count on concept node
                for n in nodes:
                    if n.id == cid and n.type == "concept":
                        n.paper_count = (n.paper_count or 0) + 1
                        break

    # Concept research gap: mark nodes with paper_count == 1
    for n in nodes:
        if n.type == "concept" and (n.paper_count or 0) == 1:
            n.is_research_gap = True

    # Paper–paper similarity (stored embeddings)
    vecs: Dict[str, List[float]] = {}
    for pid, intel in intel_by_paper.items():
        ev = intel.get("embedding_vector")
        if ev and isinstance(ev, list) and len(ev) > 0:
            vecs[pid] = ev
    pid_list = [p for p in papers if p["id"] in vecs]
    threshold = SIMILARITY_THRESHOLD_INITIAL
    similarity_added = 0
    for _ in range(5):
        added = 0
        for i, pa in enumerate(pid_list):
            for pb in pid_list[i + 1 :]:
                if pa["id"] == pb["id"]:
                    continue
                sim = _cosine_similarity(vecs[pa["id"]], vecs[pb["id"]])
                if sim >= threshold:
                    key = (pa["id"], pb["id"], "similarity")
                    if key not in link_set:
                        link_set.add(key)
                        links.append(
                            IntelligenceGraphLink(
                                source=pa["id"], target=pb["id"], type="similarity", weight=round(sim, 4)
                            )
                        )
                        added += 1
                        similarity_added += 1
        if added >= 1:
            break
        threshold -= 0.05
        if threshold < SIMILARITY_THRESHOLD_MIN:
            break
    logger.info(
        "Graph intelligence: workspace_id=%s papers=%s with_embedding=%s similarity_edges=%s",
        workspace_id,
        len(papers),
        len(vecs),
        similarity_added,
    )

    # Paper–paper keyword overlap (>= KEYWORD_OVERLAP_MIN); include title-derived keywords
    kw_by_paper: Dict[str, Set[str]] = {}
    for p in papers:
        pid = p["id"]
        intel = intel_by_paper.get(pid) or {}
        kws = {_normalize_label(k) for k in (intel.get("keywords") or []) if _normalize_label(k)}
        kws |= _title_to_keywords(p.get("title") or "")
        kw_by_paper[pid] = kws
    for i, pa in enumerate(papers):
        for pb in papers[i + 1 :]:
            if pa["id"] == pb["id"]:
                continue
            overlap = len(kw_by_paper.get(pa["id"], set()) & kw_by_paper.get(pb["id"], set()))
            if overlap >= KEYWORD_OVERLAP_MIN:
                key = (pa["id"], pb["id"], "keyword_overlap")
                if key not in link_set:
                    link_set.add(key)
                    links.append(
                        IntelligenceGraphLink(
                            source=pa["id"],
                            target=pb["id"],
                            type="keyword_overlap",
                            weight=min(1.0, overlap / 10.0),
                        )
                    )

    # Citation edges (reuse existing logic via FAISS title match + DOI from metadata)
    doi_to_ids: Dict[str, List[str]] = {}
    for p in papers:
        doi = (p.get("doi") or "").strip()
        if doi:
            doi_to_ids.setdefault(doi.lower(), []).append(p["id"])
    for p in papers:
        cited = _cited_dois_from_metadata(p.get("metadata"))
        for doi in cited:
            for target_id in doi_to_ids.get(doi.lower(), []):
                if target_id != p["id"] and (p["id"], target_id, "citation") not in link_set:
                    link_set.add((p["id"], target_id, "citation"))
                    links.append(IntelligenceGraphLink(source=p["id"], target=target_id, type="citation"))

    # Contradiction edges
    for pa, pb in _get_contradiction_edges(workspace_id, paper_ids):
        if (pa, pb, "contradiction") not in link_set and (pb, pa, "contradiction") not in link_set:
            link_set.add((pa, pb, "contradiction"))
            links.append(IntelligenceGraphLink(source=pa, target=pb, type="contradiction", weight=1.0))

    # Guarantee: every paper has at least one paper–paper link when we have 2+ papers
    paper_paper_link_types = {"similarity", "keyword_overlap", "citation", "contradiction"}
    paper_to_neighbors: Dict[str, Set[str]] = {p["id"]: set() for p in papers}
    for link in links:
        if link.type in paper_paper_link_types:
            a, b = link.source, link.target
            if a in paper_to_neighbors and b in paper_to_neighbors:
                paper_to_neighbors[a].add(b)
                paper_to_neighbors[b].add(a)
    if len(papers) >= 2:
        for p in papers:
            pid = p["id"]
            if paper_to_neighbors[pid]:
                continue
            # Link to best candidate: highest similarity in vecs, or first other paper
            best_id: Optional[str] = None
            best_sim = -1.0
            for other in papers:
                if other["id"] == pid:
                    continue
                oid = other["id"]
                if pid in vecs and oid in vecs:
                    s = _cosine_similarity(vecs[pid], vecs[oid])
                    if s > best_sim:
                        best_sim = s
                        best_id = oid
                elif best_id is None:
                    best_id = oid
            if best_id and (pid, best_id, "keyword_overlap") not in link_set and (best_id, pid, "keyword_overlap") not in link_set:
                link_set.add((pid, best_id, "keyword_overlap"))
                links.append(
                    IntelligenceGraphLink(
                        source=pid,
                        target=best_id,
                        type="keyword_overlap",
                        weight=0.4,
                    )
                )
    logger.info("Graph intelligence: after guarantee total_links=%s", len(links))

    # Dense guarantee: ensure each paper has at least MIN_METHOD_EDGES, MIN_CONCEPT_EDGES, MIN_PAPER_PAPER_EDGES
    paper_degree: Dict[str, Set[str]] = {p["id"]: set() for p in papers}
    for link in links:
        paper_degree.get(link.source, set()).add(link.target)
        paper_degree.get(link.target, set()).add(link.source)
    for p in papers:
        pid = p["id"]
        intel = intel_by_paper.get(pid) or {}
        methods = intel.get("methods_used") or []
        keywords = intel.get("keywords") or []
        # Ensure at least one method edge
        has_method = any(l.source == pid and l.type == "uses_method" for l in links)
        if methods and not has_method:
            mid = add_method(methods[0])
            if mid and (pid, mid, "uses_method") not in link_set:
                link_set.add((pid, mid, "uses_method"))
                links.append(IntelligenceGraphLink(source=pid, target=mid, type="uses_method"))
        # Ensure at least 2 concept edges
        concept_count = sum(1 for l in links if l.source == pid and l.type == "has_concept")
        for k in keywords:
            if concept_count >= MIN_CONCEPT_EDGES:
                break
            cid = add_concept(k)
            if cid and (pid, cid, "has_concept") not in link_set:
                link_set.add((pid, cid, "has_concept"))
                links.append(IntelligenceGraphLink(source=pid, target=cid, type="has_concept"))
                concept_count += 1
                for n in nodes:
                    if n.id == cid:
                        n.paper_count = (n.paper_count or 0) + 1
                        break

    return nodes, links, True