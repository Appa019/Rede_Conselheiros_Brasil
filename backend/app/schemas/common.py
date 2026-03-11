"""Pydantic schemas for the Rede de Conselheiros CVM API."""

from datetime import datetime
from typing import Any, Generic, TypeVar

from pydantic import BaseModel, Field


T = TypeVar("T")


# --- Health ---

class HealthResponse(BaseModel):
    """Response schema for the health check endpoint."""

    status: str
    neo4j_connected: bool


# --- Pagination ---

class PaginatedResponse(BaseModel, Generic[T]):
    """Generic paginated response wrapper."""

    items: list[Any]
    total: int
    page: int
    page_size: int
    total_pages: int


# --- Company ---

class CompanyInfo(BaseModel):
    """Basic company information."""

    cd_cvm: int | None = None
    nome: str | None = None
    cargo: str | None = None


class CompanyDetail(BaseModel):
    """Full company details."""

    cd_cvm: int | None = None
    cnpj: str | None = None
    nome: str | None = None
    setor: str | None = None
    segmento_listagem: str | None = None
    situacao: str | None = None


class CompanyMembership(BaseModel):
    """Company membership with temporal data."""

    cd_cvm: int | None = None
    nome: str | None = None
    cargo: str | None = None
    ano_referencia: int | None = None
    data_eleicao: str | None = None


# --- Member ---

class MemberSummary(BaseModel):
    """Summary of a member with key metrics."""

    id: str | None = None
    nome: str | None = None
    nome_normalizado: str | None = None
    formacao: str | None = None
    page_rank: float | None = None
    betweenness: float | None = None
    degree_centrality: float | None = None
    eigenvector: float | None = None
    closeness: float | None = None
    clustering_coeff: float | None = None
    community_id: int | None = None
    k_core: int | None = None


class MemberWithCompanies(BaseModel):
    """Member summary paired with their companies."""

    member: MemberSummary
    companies: list[CompanyInfo] = Field(default_factory=list)


class ConnectionSummary(BaseModel):
    """Summarized neighbor/connection info."""

    id: str | None = None
    nome: str | None = None
    page_rank: float | None = None


class MemberDetail(BaseModel):
    """Full member profile with metrics, companies, and connections."""

    member: MemberSummary
    companies: list[CompanyMembership] = Field(default_factory=list)
    connections: list[ConnectionSummary] = Field(default_factory=list)


# --- Board ---

class BoardMember(BaseModel):
    """A member on a company's board."""

    id: str | None = None
    nome: str | None = None
    cargo: str | None = None
    ano_referencia: int | None = None
    page_rank: float | None = None


class BoardResponse(BaseModel):
    """Company board composition."""

    company: CompanyDetail
    board_members: list[BoardMember] = Field(default_factory=list)


class InterlockingCompany(BaseModel):
    """Company connected via shared board members."""

    company: dict[str, Any] = Field(default_factory=dict)
    shared_members: list[str] = Field(default_factory=list)
    shared_count: int = 0


# --- Graph ---

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


# --- Communities ---

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


# --- Metrics ---

class MetricsOverview(BaseModel):
    """Dashboard-level network summary."""

    total_members: int = 0
    total_companies: int = 0
    total_connections: int = 0
    num_communities: int = 0
    avg_degree: float | None = None
    modularity: float | None = None


class ConcentrationMetrics(BaseModel):
    """Network concentration/inequality metrics."""

    gini_centrality: float = 0.0
    hhi_seats: float = 0.0
    hhi_memberships: float | None = None
    interlocking_index: float = 0.0
    network_density: float = 0.0


# --- Top Members ---

class TopMemberResponse(BaseModel):
    """Member entry in a top-N ranking."""

    id: str | None = None
    nome: str | None = None
    page_rank: float | None = None
    betweenness: float | None = None
    degree_centrality: float | None = None
    eigenvector: float | None = None
    closeness: float | None = None
    community_id: int | None = None


# --- Temporal ---

class TemporalDataPoint(BaseModel):
    """Single year data point for temporal evolution."""

    year: int | None = None
    members: int = 0
    companies: int = 0
    memberships: int = 0


# --- Advanced Metrics ---

class AdvancedMetrics(BaseModel):
    """Advanced structural metrics for the network."""

    assortativity: float = 0.0
    transitivity: float = 0.0
    avg_shortest_path: float | None = None
    diameter: int | None = None
    small_world_sigma: float | None = None
    small_world_sigma_ci_low: float | None = None
    small_world_sigma_ci_high: float | None = None
    is_small_world: bool = False
    rich_club_top: dict[int, float] = Field(default_factory=dict)
    rich_club_normalized: dict[int, float] = Field(default_factory=dict)


class DegreeDistribution(BaseModel):
    """Degree distribution statistics."""

    mean: float = 0.0
    median: float = 0.0
    std: float = 0.0
    skewness: float = 0.0
    power_law_alpha: float | None = None
    power_law_alpha_ci_low: float | None = None
    power_law_alpha_ci_high: float | None = None
    power_law_xmin: int | None = None
    power_law_p_value: float | None = None
    is_power_law: bool = False
    logn_vs_pl_ratio: float | None = None
    logn_vs_pl_p_value: float | None = None


class SectorInterlocking(BaseModel):
    """Cross-sector interlocking through shared board members."""

    sector_a: str
    sector_b: str
    shared_members: int


class CentralityCorrelation(BaseModel):
    """Spearman correlation between two centrality metrics."""

    metric_a: str
    metric_b: str
    spearman_rho: float
    p_value: float
    p_value_corrected: float | None = None
    is_significant: bool = True


class ResiliencePoint(BaseModel):
    """A single point in the resilience analysis."""

    removal_percentage: float
    remaining_largest_component: float
    nodes_removed: int


class ResilienceAnalysis(BaseModel):
    """Network resilience to targeted node removal."""

    points: list[ResiliencePoint] = Field(default_factory=list)
    random_points: list[ResiliencePoint] = Field(default_factory=list)
    vulnerability_ratio: float | None = None
    is_fragile: bool = False


# --- Admin / Jobs ---

class JobStatus(BaseModel):
    """Background job status."""

    job_id: str
    type: str
    status: str = "pending"
    progress: float = 0.0
    message: str = ""
    started_at: datetime | None = None
    completed_at: datetime | None = None
    result: dict[str, Any] | None = None
