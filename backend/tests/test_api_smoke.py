"""Smoke tests for API endpoints."""

import pytest

from app.schemas.common import (
    AdvancedMetrics,
    ConcentrationMetrics,
    DegreeDistribution,
    HealthResponse,
    MetricsOverview,
    NetworkResponse,
    ResilienceAnalysis,
)


pytestmark = pytest.mark.smoke


# --- Health ---


async def test_health(api_client):
    resp = await api_client.get("/api/health")
    assert resp.status_code == 200
    data = resp.json()
    HealthResponse(**data)


# --- Metrics ---


async def test_metrics_overview(api_client):
    resp = await api_client.get("/api/metrics/overview")
    assert resp.status_code == 200
    data = resp.json()
    m = MetricsOverview(**data)
    assert m.total_members > 0
    assert m.total_companies > 0
    assert m.num_communities > 0
    assert m.avg_degree is not None


async def test_metrics_concentration(api_client):
    resp = await api_client.get("/api/metrics/concentration")
    assert resp.status_code == 200
    ConcentrationMetrics(**resp.json())


async def test_metrics_advanced(api_client):
    resp = await api_client.get("/api/metrics/advanced")
    assert resp.status_code == 200
    AdvancedMetrics(**resp.json())


async def test_metrics_distribution(api_client):
    resp = await api_client.get("/api/metrics/distribution")
    assert resp.status_code == 200
    DegreeDistribution(**resp.json())


async def test_metrics_resilience(api_client):
    resp = await api_client.get("/api/metrics/resilience")
    assert resp.status_code == 200
    ResilienceAnalysis(**resp.json())


# --- Graph ---


async def test_graph_network(api_client):
    resp = await api_client.get("/api/graph/network?limit=10")
    assert resp.status_code == 200
    data = resp.json()
    net = NetworkResponse(**data)
    assert len(net.nodes) > 0


async def test_graph_communities(api_client):
    resp = await api_client.get("/api/graph/communities")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)


# --- Members ---


async def test_members_list(api_client):
    resp = await api_client.get("/api/members?page=1&page_size=5")
    assert resp.status_code == 200
    data = resp.json()
    assert "items" in data
    assert "total" in data
    assert "page" in data
    assert "page_size" in data
    assert "total_pages" in data


async def test_members_top(api_client):
    resp = await api_client.get("/api/members/top?metric=page_rank&limit=5")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert len(data) > 0


# --- Temporal ---


async def test_temporal_evolution(api_client):
    resp = await api_client.get("/api/temporal/evolution")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    if len(data) > 0:
        item = data[0]
        assert "year" in item
        assert "members" in item
        assert "companies" in item


# --- Admin ---


async def test_admin_jobs_list(api_client):
    resp = await api_client.get("/api/admin/jobs")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
