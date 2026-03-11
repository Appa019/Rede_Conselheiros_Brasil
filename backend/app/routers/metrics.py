"""Network metrics and concentration endpoints."""

import asyncio
import logging

import networkx as nx
from fastapi import APIRouter, Depends
from app.dependencies import get_neo4j
from app.graph.neo4j_client import Neo4jClient
from app.graph import queries
from app.graph.metrics import (
    compute_advanced_metrics,
    compute_centrality_correlations,
    compute_degree_distribution,
    compute_resilience,
    compute_sector_interlocking,
    get_cached_centrality_metrics,
    get_cached_graph,
)
from app.schemas.metrics import (
    AdvancedMetrics,
    CentralityCorrelation,
    ConcentrationMetrics,
    DegreeDistribution,
    MetricsOverview,
    ResilienceAnalysis,
    SectorInterlocking,
)

logger = logging.getLogger(__name__)

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
    """Return Gini, HHI, interlocking index (Mizruchi 1996), and network density."""

    # Gini and HHI from raw board counts (seats per person) — same basis for both
    board_records = await client.execute_read(
        "MATCH (p:Person)-[:MEMBER_OF]->(c:Company) "
        "WITH p, count(DISTINCT c) AS boards "
        "RETURN collect(boards) AS board_counts"
    )
    board_counts: list[int] = (
        board_records[0]["board_counts"]
        if board_records and board_records[0].get("board_counts")
        else []
    )
    board_counts_sorted = sorted(board_counts)
    n = len(board_counts_sorted)
    total_boards = sum(board_counts_sorted)

    if n > 0 and total_boards > 0:
        numerator = 2 * sum(i * d for i, d in enumerate(board_counts_sorted, 1))
        gini = numerator / (n * total_boards) - (n + 1) / n
        shares = [b / total_boards for b in board_counts_sorted]
        hhi = sum(s**2 for s in shares)
    else:
        gini = 0.0
        hhi = 0.0

    # Network density from the person-person CO_MEMBER graph
    G = await get_cached_graph(client)
    density = nx.density(G) if G.number_of_nodes() > 1 else 0.0

    # Real interlocking index (Mizruchi 1996): fraction of company pairs sharing ≥1 member
    # = interlocked_pairs / (N*(N-1)/2)  where N = number of companies
    interlocking_index = 0.0
    try:
        il_records = await client.execute_read("""
            MATCH (c:Company)
            WITH count(c) AS n_companies
            MATCH (c1:Company)<-[:MEMBER_OF]-(p:Person)-[:MEMBER_OF]->(c2:Company)
            WHERE id(c1) < id(c2)
            WITH n_companies, count(DISTINCT [c1.cd_cvm, c2.cd_cvm]) AS interlocked_pairs
            RETURN interlocked_pairs, n_companies,
                   CASE WHEN n_companies > 1
                        THEN toFloat(interlocked_pairs) / (toFloat(n_companies) * (n_companies - 1) / 2)
                        ELSE 0.0 END AS interlocking_index
        """)
        if il_records:
            interlocking_index = float(il_records[0].get("interlocking_index") or 0.0)
    except Exception:
        logger.warning("Interlocking index query failed, defaulting to 0.0", exc_info=True)

    return ConcentrationMetrics(
        gini_centrality=round(gini, 4),
        hhi_seats=round(hhi, 6),
        hhi_memberships=round(hhi, 6),  # same as hhi_seats (both from raw board counts)
        interlocking_index=round(interlocking_index, 4),
        network_density=round(density, 4),
    )


@router.get("/advanced", response_model=AdvancedMetrics)
async def get_advanced_metrics(
    client: Neo4jClient = Depends(get_neo4j),
) -> AdvancedMetrics:
    """Return advanced structural metrics: assortativity, transitivity, small-world, etc."""
    G = await get_cached_graph(client)
    # Offload to thread — avg_shortest_path + small_world_sigma (50 random graphs)
    # are CPU-bound and would block the event loop for 30-120s otherwise
    data = await asyncio.to_thread(compute_advanced_metrics, G)
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
    # Use cached metrics — avoids re-running NetworKit C++ (5-15s) per request
    metrics = await asyncio.to_thread(get_cached_centrality_metrics, G)
    data = compute_centrality_correlations(G, metrics)
    return [CentralityCorrelation(**row) for row in data]


@router.get("/resilience", response_model=ResilienceAnalysis)
async def get_resilience(
    client: Neo4jClient = Depends(get_neo4j),
) -> ResilienceAnalysis:
    """Return network resilience analysis under targeted node removal."""
    G = await get_cached_graph(client)
    # Offload to thread — PageRank + repeated LCC computation blocks event loop
    data = await asyncio.to_thread(compute_resilience, G)
    return ResilienceAnalysis(**data)
