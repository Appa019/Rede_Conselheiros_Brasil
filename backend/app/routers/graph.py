"""Graph network endpoints."""

from fastapi import APIRouter, Depends, Query

from app.dependencies import get_neo4j
from app.graph.neo4j_client import Neo4jClient
from app.graph import queries
from app.schemas.common import (
    CommunityInfo,
    CommunityMember,
    CompanyInfo,
    GraphNode,
    NetworkResponse,
    SubgraphResponse,
)

router = APIRouter(prefix="/api/graph", tags=["graph"])


@router.get("/network", response_model=NetworkResponse)
async def get_network(
    year: int | None = Query(None, description="Filter by reference year"),
    sector: str | None = Query(None, description="Filter by sector name"),
    min_connections: int = Query(0, ge=0, description="Minimum number of connections"),
    limit: int = Query(200, ge=1, le=2000, description="Maximum nodes to return"),
    client: Neo4jClient = Depends(get_neo4j),
) -> NetworkResponse:
    """Return filtered network nodes for visualization."""
    params = {
        "year": year,
        "sector": sector,
        "min_connections": min_connections,
        "limit": limit,
    }
    records = await client.execute_read(queries.GET_NETWORK, params)

    nodes = [
        GraphNode(
            id=r["id"],
            nome=r["nome"],
            page_rank=r["page_rank"],
            community_id=r["community_id"],
            degree_centrality=r["degree_centrality"],
            companies=[CompanyInfo(**c) for c in (r.get("companies") or [])],
            connections=r["connections"],
        )
        for r in records
    ]
    return NetworkResponse(nodes=nodes, total=len(nodes))


@router.get("/subgraph/{person_id}", response_model=SubgraphResponse)
async def get_subgraph(
    person_id: str,
    client: Neo4jClient = Depends(get_neo4j),
) -> SubgraphResponse:
    """Return the ego-network subgraph centered on a person."""
    records = await client.execute_read(queries.GET_SUBGRAPH, {"person_id": person_id})

    if not records:
        return SubgraphResponse()

    # Extract unique nodes and edges from raw records
    center_data: dict = {}
    neighbors_map: dict = {}
    edges_list: list[dict] = []
    seen_edges: set = set()

    for r in records:
        # Center node
        center_node = r.get("center")
        if center_node and not center_data:
            center_data = dict(center_node) if hasattr(center_node, "__iter__") else {"id": person_id}

        # Neighbor
        neighbor = r.get("neighbor")
        if neighbor:
            n_dict = dict(neighbor) if hasattr(neighbor, "__iter__") else {}
            if n_dict.get("id"):
                neighbors_map[n_dict["id"]] = n_dict

        # Edges from co relationship
        co = r.get("co")
        if co and neighbor:
            n_id = n_dict.get("id") if neighbor else None
            if n_id:
                edge_key = tuple(sorted([person_id, n_id]))
                if edge_key not in seen_edges:
                    seen_edges.add(edge_key)
                    edges_list.append({
                        "source": person_id,
                        "target": n_id,
                        "weight": dict(co).get("weight") if hasattr(co, "__iter__") else None,
                    })

        # Secondary neighbor edges
        neighbor2 = r.get("neighbor2")
        co2 = r.get("co2")
        if neighbor2 and co2:
            n2_dict = dict(neighbor2) if hasattr(neighbor2, "__iter__") else {}
            n2_id = n2_dict.get("id")
            n_id = n_dict.get("id") if neighbor else None
            if n2_id and n_id:
                neighbors_map.setdefault(n2_id, n2_dict)
                edge_key = tuple(sorted([n_id, n2_id]))
                if edge_key not in seen_edges:
                    seen_edges.add(edge_key)
                    edges_list.append({
                        "source": n_id,
                        "target": n2_id,
                        "weight": dict(co2).get("weight") if hasattr(co2, "__iter__") else None,
                    })

    return SubgraphResponse(
        center=center_data,
        neighbors=list(neighbors_map.values()),
        edges=edges_list,
    )


@router.get("/communities", response_model=list[CommunityInfo])
async def get_communities(
    client: Neo4jClient = Depends(get_neo4j),
) -> list[CommunityInfo]:
    """Return detected communities with their top members."""
    records = await client.execute_read(queries.GET_COMMUNITIES)

    return [
        CommunityInfo(
            community_id=r["community_id"],
            member_count=r["member_count"],
            top_members=[CommunityMember(**m) for m in (r.get("top_members") or [])],
        )
        for r in records
    ]
