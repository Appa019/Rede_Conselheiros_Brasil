from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI

from app.graph.neo4j_client import Neo4jClient


# Shared Neo4j client instance
_neo4j_client = Neo4jClient()


async def get_neo4j() -> AsyncGenerator[Neo4jClient, None]:
    """FastAPI dependency that yields the Neo4j client."""
    yield _neo4j_client


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, Any]:
    """Application lifespan: connect Neo4j on startup, disconnect on shutdown."""
    await _neo4j_client.connect()
    yield
    await _neo4j_client.close()
