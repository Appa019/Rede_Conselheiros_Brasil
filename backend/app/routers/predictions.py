"""Prediction endpoints (stubs for future ML features)."""

from fastapi import APIRouter, Query

router = APIRouter(prefix="/api/predictions", tags=["predictions"])


@router.get("/links")
async def predict_links(
    top_k: int = Query(10, ge=1, le=100, description="Number of predictions"),
) -> list[dict]:
    """Placeholder: predict likely future board connections."""
    # TODO: return actual predictions when ML pipeline is implemented
    _ = top_k
    return []


@router.get("/similar/{member_id}")
async def get_similar_members(
    member_id: str,
    top_k: int = Query(10, ge=1, le=50, description="Number of similar members"),
) -> list[dict]:
    """Placeholder: find structurally similar members via embeddings."""
    # TODO: return actual similar members when embeddings are implemented
    _ = member_id, top_k
    return []
