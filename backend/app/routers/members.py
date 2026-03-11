"""Member listing, detail, and ranking endpoints."""

import math

from fastapi import APIRouter, Depends, Query

from app.dependencies import get_neo4j
from app.graph.neo4j_client import Neo4jClient
from app.graph import queries
from app.schemas.common import (
    CompanyInfo,
    CompanyMembership,
    ConnectionSummary,
    MemberDetail,
    MemberSummary,
    MemberWithCompanies,
    PaginatedResponse,
    TopMemberResponse,
)

router = APIRouter(prefix="/api/members", tags=["members"])


@router.get("/top", response_model=list[TopMemberResponse])
async def get_top_members(
    metric: str = Query("page_rank", description="Metric to rank by"),
    limit: int = Query(20, ge=1, le=100, description="Number of results"),
    client: Neo4jClient = Depends(get_neo4j),
) -> list[TopMemberResponse]:
    """Return top-N members ranked by a given metric."""
    # Validate metric name to prevent injection
    allowed_metrics = {
        "page_rank", "betweenness", "degree_centrality",
        "eigenvector", "closeness",
    }
    if metric not in allowed_metrics:
        metric = "page_rank"

    records = await client.execute_read(
        queries.GET_TOP_MEMBERS, {"metric": metric, "limit": limit}
    )
    return [TopMemberResponse(**(r.get("member") or {})) for r in records]


@router.get("", response_model=PaginatedResponse)
async def get_members(
    search: str | None = Query(None, description="Search by name"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    client: Neo4jClient = Depends(get_neo4j),
) -> PaginatedResponse:
    """Return paginated list of members with optional name search."""
    skip = (page - 1) * page_size
    params = {"search": search, "skip": skip, "limit": page_size}

    # Count total
    count_result = await client.execute_read(queries.COUNT_MEMBERS, {"search": search})
    total = count_result[0]["total"] if count_result else 0

    # Fetch page
    records = await client.execute_read(queries.GET_MEMBERS, params)

    items = [
        MemberWithCompanies(
            member=MemberSummary(**(r.get("member") or {})),
            companies=[CompanyInfo(**c) for c in (r.get("companies") or [])],
        )
        for r in records
    ]

    return PaginatedResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=math.ceil(total / page_size) if total > 0 else 0,
    )


@router.get("/{member_id}", response_model=MemberDetail)
async def get_member_by_id(
    member_id: str,
    client: Neo4jClient = Depends(get_neo4j),
) -> MemberDetail:
    """Return full member profile with metrics, companies, and connections."""
    records = await client.execute_read(
        queries.GET_MEMBER_BY_ID, {"id": member_id}
    )

    if not records:
        return MemberDetail(member=MemberSummary())

    r = records[0]
    return MemberDetail(
        member=MemberSummary(**(r.get("member") or {})),
        companies=[CompanyMembership(**c) for c in (r.get("companies") or [])],
        connections=[ConnectionSummary(**c) for c in (r.get("connections") or [])],
    )
