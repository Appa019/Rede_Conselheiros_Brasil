"""Temporal evolution endpoints."""

from fastapi import APIRouter, Depends

from app.dependencies import get_neo4j
from app.graph.neo4j_client import Neo4jClient
from app.graph import queries
from app.schemas.metrics import TemporalDataPoint

router = APIRouter(prefix="/api/temporal", tags=["temporal"])


@router.get("/evolution", response_model=list[TemporalDataPoint])
async def get_temporal_evolution(
    client: Neo4jClient = Depends(get_neo4j),
) -> list[TemporalDataPoint]:
    """Return network metrics aggregated by year."""
    records = await client.execute_read(queries.GET_TEMPORAL_METRICS)

    return [
        TemporalDataPoint(
            year=r.get("year"),
            members=r.get("members", 0),
            companies=r.get("companies", 0),
            memberships=r.get("memberships", 0),
        )
        for r in records
    ]
