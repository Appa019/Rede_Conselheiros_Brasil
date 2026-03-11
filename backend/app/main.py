from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.dependencies import get_neo4j, lifespan
from app.routers import admin, companies, graph, members, metrics, predictions, temporal
from app.schemas.common import HealthResponse

app = FastAPI(
    title="Rede de Conselheiros CVM",
    description="API for board member network analysis from CVM data",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Router registration
app.include_router(graph.router)
app.include_router(members.router)
app.include_router(companies.router)
app.include_router(metrics.router)
app.include_router(temporal.router)
app.include_router(predictions.router)
app.include_router(admin.router)


@app.get("/api/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """Check API and Neo4j connectivity."""
    neo4j_client = None
    async for client in get_neo4j():
        neo4j_client = client

    neo4j_ok = False
    if neo4j_client is not None:
        neo4j_ok = await neo4j_client.health_check()

    return HealthResponse(
        status="ok" if neo4j_ok else "degraded",
        neo4j_connected=neo4j_ok,
    )
