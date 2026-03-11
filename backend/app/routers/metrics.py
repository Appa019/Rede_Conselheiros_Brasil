"""Network metrics and concentration endpoints."""

import networkx as nx
from fastapi import APIRouter, Depends

from app.dependencies import get_neo4j
from app.graph.neo4j_client import Neo4jClient
from app.graph import queries
from app.graph.metrics import (
    compute_advanced_metrics,
    compute_centrality_correlations,
    compute_centrality_metrics,
    compute_degree_distribution,
    compute_resilience,
    compute_sector_interlocking,
    get_cached_graph,
)
from app.schemas.common import (
    AdvancedMetrics,
    CentralityCorrelation,
    ConcentrationMetrics,
    DegreeDistribution,
    MetricsOverview,
    ResilienceAnalysis,
    SectorInterlocking,
)

router = APIRouter(prefix="/api/metrics", tags=["metrics"])


@router.get("/overview", response_model=MetricsOverview)
async def get_metrics_overview(
    client: Neo4jClient = Depends(get_neo4j),
) -> MetricsOverview:
    """Return dashboard-level network summary."""
    records = await client.execute_read(queries.GET_METRICS_OVERVIEW)

    if not records:
        return MetricsOverview()

    r = records[0]
    return MetricsOverview(
        total_members=r.get("total_members", 0),
        total_companies=r.get("total_companies", 0),
        total_connections=r.get("total_connections", 0),
        num_communities=r.get("num_communities", 0),
        avg_degree=r.get("avg_degree"),
        modularity=r.get("modularity"),
    )


@router.get("/concentration", response_model=ConcentrationMetrics)
async def get_concentration_metrics(
    client: Neo4jClient = Depends(get_neo4j),
) -> ConcentrationMetrics:
    """Return Gini, HHI, interlocking index, and network density."""
    records = await client.execute_read(queries.GET_CONCENTRATION_METRICS)

    if not records or not records[0].get("centralities"):
        return ConcentrationMetrics()

    centralities = sorted(records[0]["centralities"])
    n = len(centralities)

    # Gini coefficient
    if n > 0 and sum(centralities) > 0:
        numerator = 2 * sum(i * d for i, d in enumerate(centralities, 1))
        denominator = n * sum(centralities)
        gini = (numerator / denominator - (n + 1) / n)
    else:
        gini = 0.0

    # HHI approximation from degree centrality distribution
    total = sum(centralities)
    if total > 0:
        shares = [c / total for c in centralities]
        hhi = sum(s**2 for s in shares)
    else:
        hhi = 0.0

    # Real density and interlocking from the actual graph
    G = await get_cached_graph(client)
    density = nx.density(G) if G.number_of_nodes() > 1 else 0.0

    # HHI of memberships: count boards per person from Neo4j
    hhi_memberships = None
    try:
        membership_records = await client.execute_read(
            "MATCH (p:Person)-[:MEMBER_OF]->(c:Company) "
            "WITH p, count(DISTINCT c) AS boards "
            "RETURN collect(boards) AS board_counts"
        )
        if membership_records and membership_records[0].get("board_counts"):
            board_counts = membership_records[0]["board_counts"]
            total_boards = sum(board_counts)
            if total_boards > 0:
                shares_m = [b / total_boards for b in board_counts]
                hhi_memberships = round(sum(s**2 for s in shares_m), 6)
    except Exception:
        pass

    return ConcentrationMetrics(
        gini_centrality=round(gini, 4),
        hhi_seats=round(hhi, 6),
        hhi_memberships=hhi_memberships,
        interlocking_index=round(density, 4),
        network_density=round(density, 4),
    )


@router.get("/advanced", response_model=AdvancedMetrics)
async def get_advanced_metrics(
    client: Neo4jClient = Depends(get_neo4j),
) -> AdvancedMetrics:
    """Return advanced structural metrics: assortativity, transitivity, small-world, etc."""
    G = await get_cached_graph(client)
    data = compute_advanced_metrics(G)
    return AdvancedMetrics(**data)


@router.get("/distribution", response_model=DegreeDistribution)
async def get_degree_distribution(
    client: Neo4jClient = Depends(get_neo4j),
) -> DegreeDistribution:
    """Return degree distribution statistics and power-law fit."""
    G = await get_cached_graph(client)
    data = compute_degree_distribution(G)
    return DegreeDistribution(**data)


@router.get("/sector-interlocking", response_model=list[SectorInterlocking])
async def get_sector_interlocking(
    client: Neo4jClient = Depends(get_neo4j),
) -> list[SectorInterlocking]:
    """Return cross-sector interlocking matrix."""
    data = await compute_sector_interlocking(client)
    return [SectorInterlocking(**row) for row in data]


@router.get("/centrality-correlation", response_model=list[CentralityCorrelation])
async def get_centrality_correlation(
    client: Neo4jClient = Depends(get_neo4j),
) -> list[CentralityCorrelation]:
    """Return Spearman correlations between centrality metrics."""
    G = await get_cached_graph(client)
    metrics = compute_centrality_metrics(G)
    data = compute_centrality_correlations(G, metrics)
    return [CentralityCorrelation(**row) for row in data]


@router.get("/resilience", response_model=ResilienceAnalysis)
async def get_resilience(
    client: Neo4jClient = Depends(get_neo4j),
) -> ResilienceAnalysis:
    """Return network resilience analysis under targeted node removal."""
    G = await get_cached_graph(client)
    data = compute_resilience(G)
    return ResilienceAnalysis(**data)
