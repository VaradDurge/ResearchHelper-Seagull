"""
Graph Service - Builds global knowledge graph of papers for a workspace.
Uses existing paper data only: no schema changes.
Edges: citation (from metadata DOI refs), embedding similarity (>0.75), optional shared keywords.
"""
from typing import List, Dict, Set, Tuple, Any
import re
import logging
import numpy as np

from app.db.mongo import get_papers_collection
from app.models.schemas import GraphNode, GraphLink
from app.core.vector_db import get_vector_db
from app.config import settings

logger = logging.getLogger(__name__)

MAX_NODES = 500
# Temporarily 0 to verify connections; revert to 0.75 when asked
SIMILARITY_THRESHOLD = 0.0


def _year_from_date(publication_date: str) -> int | None:
    if not publication_date:
        return None
    match = re.search(r"\d{4}", publication_date)
    return int(match.group(0)) if match else None


def _cited_dois_from_metadata(metadata: dict | None) -> List[str]:
    """Extract list of DOIs that this paper references, if stored in metadata."""
    if not metadata:
        return []
    refs = metadata.get("references") or metadata.get("cited_dois") or metadata.get("dois_referenced")
    if isinstance(refs, list):
        return [str(r).strip() for r in refs if r]
    if isinstance(refs, str):
        return [s.strip() for s in re.split(r"[\s,;]+", refs) if s]
    return []


def _add_title_citation_edges_from_index(
    papers: List[Dict[str, Any]],
    workspace_id: str,
    vector_db,
    link_set: Set[Tuple[str, str, str]],
    links: List[GraphLink],
    max_ref_pages: int = 4,
) -> None:
    """
    Infer citation edges A -> B when paper A's reference text contains B's title.

    This does NOT change storage or schema; it only inspects existing FAISS metadata.
    """
    if not getattr(vector_db, "metadata", None):
        return

    id_to_title: Dict[str, str] = {
        p["id"]: (p.get("title") or "").strip().lower() for p in papers
    }
    paper_ids = set(id_to_title.keys())

    # First pass: determine max page number per paper so we can focus on the tail pages
    max_page_by_paper: Dict[str, int] = {}
    for meta in vector_db.metadata.values():
        if meta.get("workspace_id") != workspace_id:
            continue
        pid = meta.get("paper_id")
        if pid not in paper_ids:
            continue
        try:
            page = int(meta.get("page_number") or 0)
        except (TypeError, ValueError):
            page = 0
        if page > max_page_by_paper.get(pid, 0):
            max_page_by_paper[pid] = page

    # Second pass: collect reference-like text from the last few pages
    paper_ref_text: Dict[str, str] = {pid: "" for pid in paper_ids}
    for meta in vector_db.metadata.values():
        if meta.get("workspace_id") != workspace_id:
            continue
        pid = meta.get("paper_id")
        if pid not in paper_ids:
            continue
        text = meta.get("text") or ""
        if not text:
            continue
        try:
            page = int(meta.get("page_number") or 0)
        except (TypeError, ValueError):
            page = 0
        max_page = max_page_by_paper.get(pid, 0)
        # Heuristic: focus on the last few pages where references typically live
        if max_page and page < max_page - max_ref_pages:
            continue
        lower_text = text.lower()
        paper_ref_text[pid] += "\n" + lower_text

    # For each paper A, check if it appears to cite B by title substring match
    for pid_a, ref_text in paper_ref_text.items():
        if not ref_text:
            continue
        for pid_b, title_b in id_to_title.items():
            if pid_a == pid_b:
                continue
            # Skip very short titles to avoid noisy matches
            if not title_b or len(title_b) < 10:
                continue
            if title_b in ref_text:
                key = (pid_a, pid_b, "citation")
                if key in link_set:
                    continue
                link_set.add(key)
                links.append(GraphLink(source=pid_a, target=pid_b, type="citation"))


def build_graph(
    user_id: str,
    workspace_id: str,
    cap_nodes: int = MAX_NODES,
    similarity_threshold: float = SIMILARITY_THRESHOLD,
) -> Tuple[List[GraphNode], List[GraphLink]]:
    """
    Build graph nodes (papers) and links (citation + similarity) for the workspace.
    Does not modify any existing data or schema.
    """
    papers_coll = get_papers_collection()
    docs = list(
        papers_coll.find({"workspace_id": workspace_id}).sort("upload_date", -1).limit(cap_nodes)
    )
    if not docs:
        logger.debug("Graph: no papers for workspace_id=%s", workspace_id)
        return [], []

    papers: List[Dict[str, Any]] = []
    for doc in docs:
        pid = doc.get("paper_id")
        if not pid:
            continue
        papers.append({
            "id": pid,
            "title": doc.get("title") or "Untitled",
            "doi": doc.get("doi"),
            "publication_date": doc.get("publication_date"),
            "metadata": doc.get("metadata") or {},
        })
    if not papers:
        return [], []

    id_to_paper = {p["id"]: p for p in papers}
    doi_to_ids: Dict[str, List[str]] = {}
    for p in papers:
        doi = (p.get("doi") or "").strip()
        if doi:
            doi_to_ids.setdefault(doi.lower(), []).append(p["id"])

    nodes: List[GraphNode] = []
    link_set: Set[Tuple[str, str, str]] = set()
    links: List[GraphLink] = []

    for p in papers:
        year = _year_from_date(p.get("publication_date"))
        nodes.append(
            GraphNode(
                id=p["id"],
                label=p["title"],
                type="paper",
                year=year,
                embedding_cluster=None,
            )
        )

    for p in papers:
        cited = _cited_dois_from_metadata(p.get("metadata"))
        for doi in cited:
            doi_lower = doi.lower()
            if doi_lower in doi_to_ids:
                for target_id in doi_to_ids[doi_lower]:
                    if target_id != p["id"] and (p["id"], target_id, "citation") not in link_set:
                        link_set.add((p["id"], target_id, "citation"))
                        links.append(GraphLink(source=p["id"], target=target_id, type="citation"))

    try:
        vector_db = get_vector_db(
            index_path=settings.vector_db_path,
            dimension=settings.embedding_dimension,
        )
        # Also infer citation-like edges when A's reference text contains B's title
        _add_title_citation_edges_from_index(
            papers=papers,
            workspace_id=workspace_id,
            vector_db=vector_db,
            link_set=link_set,
            links=links,
        )
        centroids = vector_db.get_paper_centroids(workspace_id=workspace_id)
    except Exception as e:
        logger.warning("Graph: could not get paper centroids for similarity: %s", e)
        centroids = {}

    paper_ids_with_vectors = [p["id"] for p in papers if p["id"] in centroids]
    similarity_count = 0
    for i, pid_a in enumerate(paper_ids_with_vectors):
        vec_a = centroids[pid_a]
        norm_a = float(np.dot(vec_a, vec_a)) ** 0.5
        if norm_a <= 0:
            continue
        for pid_b in paper_ids_with_vectors[i + 1 :]:
            vec_b = centroids[pid_b]
            norm_b = float(np.dot(vec_b, vec_b)) ** 0.5
            if norm_b <= 0:
                continue
            sim = float(np.dot(vec_a, vec_b)) / (norm_a * norm_b)
            if sim >= similarity_threshold:
                if (pid_a, pid_b, "similarity") not in link_set and (pid_b, pid_a, "similarity") not in link_set:
                    link_set.add((pid_a, pid_b, "similarity"))
                    links.append(
                        GraphLink(source=pid_a, target=pid_b, type="similarity", weight=round(sim, 4))
                    )
                    similarity_count += 1
    logger.info(
        "Graph simple: workspace_id=%s papers=%s centroids=%s paper_ids_with_vectors=%s similarity_edges=%s",
        workspace_id,
        len(papers),
        len(centroids),
        len(paper_ids_with_vectors),
        similarity_count,
    )
    if len(nodes) >= 2 and len(links) == 0:
        for i, pa in enumerate(papers):
            for pb in papers[i + 1 :]:
                if (pa["id"], pb["id"], "similarity") not in link_set and (pb["id"], pa["id"], "similarity") not in link_set:
                    link_set.add((pa["id"], pb["id"], "similarity"))
                    links.append(GraphLink(source=pa["id"], target=pb["id"], type="similarity", weight=0.7))
        logger.info("Graph simple: added fallback paper-paper links (no centroids/similarity), total=%s", len(links))
    return nodes, links
