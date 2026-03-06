"""
Graph API - Global knowledge graph of papers (Obsidian-style) and Research Intelligence Graph.
"""
import logging

from fastapi import APIRouter, Depends

from app.api.dependencies import get_current_user_id, get_current_workspace_id
from app.models.schemas import GraphResponse, IntelligenceGraphResponse
from app.services.graph_service import build_graph
from app.services.intelligence_graph_service import build_workspace_graph

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/workspace", response_model=GraphResponse)
async def get_graph_workspace(
    user_id: str = Depends(get_current_user_id),
    workspace_id: str = Depends(get_current_workspace_id),
):
    """
    GET /api/v1/graph/workspace
    Returns graph nodes (papers) and links (citation + similarity) for the active workspace.
    Used by the simple graph view (fallback when intelligence data is not available).
    """
    nodes, links = build_graph(user_id=user_id, workspace_id=workspace_id)
    if not nodes:
        logger.info("Graph workspace empty: workspace_id=%s (user_id=%s)", workspace_id, user_id)
    return GraphResponse(nodes=nodes, links=links)


@router.get("/workspace/intelligence", response_model=IntelligenceGraphResponse)
async def get_graph_workspace_intelligence(
    user_id: str = Depends(get_current_user_id),
    workspace_id: str = Depends(get_current_workspace_id),
):
    """
    GET /api/v1/graph/workspace/intelligence
    Returns Research Intelligence Graph: paper/method/dataset/concept nodes and edges.
    If no paper_intelligence data exists, returns has_intelligence=false so frontend can fall back to simple graph.
    """
    # STEP 9 — Workspace consistency: same workspace_id used for graph build
    logger.info("[CONTRADICTION DEBUG] API workspace_id=%s (user_id=%s)", workspace_id, user_id)

    nodes, links, has_intelligence = build_workspace_graph(
        workspace_id=workspace_id, user_id=user_id
    )
    if has_intelligence and not nodes:
        logger.info(
            "Graph intelligence empty despite has_intelligence: workspace_id=%s (user_id=%s)",
            workspace_id,
            user_id,
        )

    # STEP 3 — Verify API response before return
    total_links = len(links)
    contradiction_links = [l for l in links if l.type == "contradiction"]
    contradiction_count = len(contradiction_links)
    logger.info(
        "[CONTRADICTION DEBUG] API response: total_nodes=%s total_links=%s contradiction_links=%s",
        len(nodes),
        total_links,
        contradiction_count,
    )
    if contradiction_count == 0 and total_links > 0:
        logger.info("[CONTRADICTION DEBUG] No contradiction links in response. Frontend cannot show red lines.")

    return IntelligenceGraphResponse(
        nodes=nodes,
        links=links,
        has_intelligence=has_intelligence,
    )
