"""Shared fixtures for smoke tests."""

import pytest
import httpx

from app.dependencies import _neo4j_client
from app.graph.neo4j_client import Neo4jClient
from app.graph.metrics import build_networkx_graph
from app.main import app


@pytest.fixture(scope="session")
async def neo4j_client():
    """Session-scoped Neo4j client."""
    client = Neo4jClient()
    await client.connect()
    yield client
    await client.close()


@pytest.fixture(scope="session")
async def api_client():
    """Session-scoped async HTTP client using ASGI transport.

    Connects the shared Neo4j singleton so endpoints that depend on
    ``get_neo4j`` work without the full lifespan startup.
    """
    await _neo4j_client.connect()
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(
        transport=transport,
        base_url="http://test",
    ) as client:
        yield client
    await _neo4j_client.close()


@pytest.fixture(scope="session")
async def networkx_graph(neo4j_client):
    """Session-scoped NetworkX graph built once from Neo4j (full graph)."""
    G = await build_networkx_graph(neo4j_client)
    return G
