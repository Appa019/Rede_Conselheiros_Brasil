"""Graph-related Pydantic schemas."""

from typing import Any

from pydantic import BaseModel, Field

from app.schemas.members import CompanyInfo


class GraphNode(BaseModel):
    """Node in the network visualization."""

    id: str
    nome: str | None = None
    page_rank: float | None = None
    community_id: int | None = None
    degree_centrality: float | None = None
    companies: list[CompanyInfo] = Field(default_factory=list)
    connections: int = 0


class GraphEdge(BaseModel):
    """Edge in the network visualization."""

    source: str
    target: str
    weight: float | None = None


class NetworkResponse(BaseModel):
    """Full network response for visualization."""

    nodes: list[GraphNode] = Field(default_factory=list)
    total: int = 0


class SubgraphResponse(BaseModel):
    """Ego-network subgraph response."""

    center: dict[str, Any] = Field(default_factory=dict)
    neighbors: list[dict[str, Any]] = Field(default_factory=list)
    edges: list[dict[str, Any]] = Field(default_factory=list)


class CommunityMember(BaseModel):
    """Member inside a community listing."""

    id: str | None = None
    nome: str | None = None
    page_rank: float | None = None


class CommunityInfo(BaseModel):
    """Detected community information."""

    community_id: int
    member_count: int
    top_members: list[CommunityMember] = Field(default_factory=list)
