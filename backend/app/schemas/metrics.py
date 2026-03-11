"""Metrics-related Pydantic schemas."""

from pydantic import BaseModel, Field


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
    # Real interlocking index (Mizruchi 1996): fraction of company pairs sharing ≥1 member
    interlocking_index: float | None = None
    network_density: float = 0.0


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


class TemporalDataPoint(BaseModel):
    """Single year data point for temporal evolution."""

    year: int | None = None
    members: int = 0
    companies: int = 0
    memberships: int = 0
