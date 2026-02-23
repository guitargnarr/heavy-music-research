"""Network graph endpoints for the Metalcore Index API."""
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from database import get_db
from models import Artist, Relationship, Score
from schemas import NetworkGraph, NetworkNode, NetworkLink

router = APIRouter(prefix="/api/network", tags=["network"])


@router.get("/graph", response_model=NetworkGraph)
def get_network_graph(
    center: Optional[str] = Query(None, description="Center node ID (spotify_id or name)"),
    depth: int = Query(1, ge=1, le=3, description="Traversal depth from center"),
    db: Session = Depends(get_db),
):
    """Build network graph from relationships table."""
    relationships = db.query(Relationship).all()

    nodes_map: dict[str, NetworkNode] = {}
    links: list[NetworkLink] = []

    # Build all nodes from relationships
    for rel in relationships:
        src_key = f"{rel.source_type}:{rel.source_id}"
        tgt_key = f"{rel.target_type}:{rel.target_id}"

        if src_key not in nodes_map:
            nodes_map[src_key] = NetworkNode(
                id=src_key,
                label=rel.source_id,
                type=rel.source_type,
            )
        if tgt_key not in nodes_map:
            nodes_map[tgt_key] = NetworkNode(
                id=tgt_key,
                label=rel.target_id,
                type=rel.target_type,
            )

        links.append(
            NetworkLink(
                source=src_key,
                target=tgt_key,
                relationship=rel.relationship_type,
            )
        )

    # Enrich artist nodes with composite scores
    artists = db.query(Artist).all()
    for artist in artists:
        key = f"artist:{artist.name}"
        if key in nodes_map:
            latest_score = (
                db.query(Score)
                .filter(Score.artist_id == artist.spotify_id)
                .order_by(Score.score_date.desc())
                .first()
            )
            if latest_score:
                nodes_map[key].score = latest_score.composite

    # Filter by center node if specified
    if center:
        connected = _get_connected_nodes(center, links, nodes_map, depth)
        nodes_map = {k: v for k, v in nodes_map.items() if k in connected}
        links = [
            link
            for link in links
            if link.source in connected and link.target in connected
        ]

    return NetworkGraph(nodes=list(nodes_map.values()), links=links)


def _get_connected_nodes(
    center: str,
    links: list[NetworkLink],
    nodes_map: dict[str, NetworkNode],
    depth: int,
) -> set[str]:
    """BFS to find nodes within N hops of center."""
    # Try to match center to a node
    center_key = None
    for key, node in nodes_map.items():
        if center.lower() in node.label.lower() or center.lower() in key.lower():
            center_key = key
            break

    if not center_key:
        return set(nodes_map.keys())  # No match, return all

    visited: set[str] = {center_key}
    frontier: set[str] = {center_key}

    for _ in range(depth):
        next_frontier: set[str] = set()
        for link in links:
            if link.source in frontier:
                next_frontier.add(link.target)
            if link.target in frontier:
                next_frontier.add(link.source)
        next_frontier -= visited
        visited |= next_frontier
        frontier = next_frontier

    return visited
