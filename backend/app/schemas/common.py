"""Pydantic schemas for the Rede de Conselheiros CVM API.

Domain-specific schemas live in their own modules; this file provides
backward-compatible re-exports and the two generic schemas used everywhere.
"""

from typing import Any, Generic, TypeVar

from pydantic import BaseModel

from app.schemas.admin import *  # noqa: F401,F403
from app.schemas.graph import *  # noqa: F401,F403
from app.schemas.members import *  # noqa: F401,F403
from app.schemas.metrics import *  # noqa: F401,F403
from app.schemas.predictions import *  # noqa: F401,F403

T = TypeVar("T")


class HealthResponse(BaseModel):
    """Response schema for the health check endpoint."""

    status: str
    neo4j_connected: bool


class PaginatedResponse(BaseModel, Generic[T]):
    """Generic paginated response wrapper."""

    items: list[Any]
    total: int
    page: int
    page_size: int
    total_pages: int
