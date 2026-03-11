"""Smoke tests for graph metrics computation."""

import pytest

from app.graph.metrics import (
    compute_advanced_metrics,
    compute_and_save_metrics,
    compute_centrality_metrics,
    compute_communities,
    compute_degree_distribution,
)


pytestmark = pytest.mark.smoke


async def test_build_graph(networkx_graph):
    assert networkx_graph.number_of_nodes() > 0


async def test_centrality_metrics(networkx_graph):
    metrics = compute_centrality_metrics(networkx_graph)
    assert "degree_centrality" in metrics
    assert "betweenness" in metrics
    assert "page_rank" in metrics
    assert len(metrics["degree_centrality"]) > 0


async def test_communities(networkx_graph):
    partition, modularity = compute_communities(networkx_graph)
    assert isinstance(partition, dict)
    assert len(partition) > 0
    assert isinstance(modularity, float)
    assert 0 <= modularity <= 1


async def test_advanced_metrics(networkx_graph):
    result = compute_advanced_metrics(networkx_graph)
    assert "assortativity" in result
    assert "transitivity" in result


async def test_degree_distribution(networkx_graph):
    result = compute_degree_distribution(networkx_graph)
    assert "mean" in result
    assert "median" in result
    assert "skewness" in result


@pytest.mark.slow
async def test_full_compute_and_save(neo4j_client):
    result = await compute_and_save_metrics(neo4j_client)
    assert result["nodes"] > 0
