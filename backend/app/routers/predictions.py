"""Prediction endpoints — link prediction and member similarity."""

import asyncio
import logging
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query

from app.dependencies import get_neo4j
from app.graph.metrics import get_cached_graph
from app.graph.neo4j_client import Neo4jClient
from app.ml.link_prediction import predict_new_links
from app.ml.local_vector_store import LocalVectorStore
from app.schemas.predictions import PredictedLink

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/predictions", tags=["predictions"])

# Path where the trained link predictor is saved by train_model.py
LINK_MODEL_PATH = Path("data/models/link_predictor.joblib")

# Shared store instance (lazy-loads embeddings on first request)
_store = LocalVectorStore()


@router.get("/links", response_model=list[PredictedLink])
async def predict_links(
    top_k: int = Query(10, ge=1, le=100, description="Number of predictions"),
    client: Neo4jClient = Depends(get_neo4j),
) -> list[PredictedLink]:
    """Predict likely future board connections using the trained Random Forest model."""
    if not LINK_MODEL_PATH.exists():
        raise HTTPException(
            status_code=503,
            detail="Model not available. Run the ML training pipeline first.",
        )

    G = await get_cached_graph(client)
    results = await asyncio.to_thread(predict_new_links, G, LINK_MODEL_PATH, top_k)
    return [PredictedLink(**r) for r in results]


@router.get("/similar/{member_id}")
async def get_similar_members(
    member_id: str,
    top_k: int = Query(10, ge=1, le=50, description="Number of similar members"),
) -> list[dict]:
    """Find structurally similar members via Node2Vec embedding cosine similarity."""
    if not _store.is_ready():
        raise HTTPException(
            status_code=503,
            detail="Embeddings not available. Run the ML training pipeline first.",
        )

    results = _store.find_similar(member_id, top_k=top_k)

    if not results and _store.is_ready():
        # Store loaded but member not found
        raise HTTPException(status_code=404, detail=f"Member '{member_id}' not found in embeddings.")

    return results
