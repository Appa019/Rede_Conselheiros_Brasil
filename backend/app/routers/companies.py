"""Company board and interlocking endpoints."""

from fastapi import APIRouter, Depends

from app.dependencies import get_neo4j
from app.graph.neo4j_client import Neo4jClient
from app.graph import queries
from app.schemas.common import (
    BoardMember,
    BoardResponse,
    CompanyDetail,
    InterlockingCompany,
)

router = APIRouter(prefix="/api/companies", tags=["companies"])


@router.get("/{cd_cvm}/board", response_model=BoardResponse)
async def get_company_board(
    cd_cvm: int,
    client: Neo4jClient = Depends(get_neo4j),
) -> BoardResponse:
    """Return a company's board composition."""
    records = await client.execute_read(
        queries.GET_COMPANY_BOARD, {"cd_cvm": cd_cvm}
    )

    if not records:
        return BoardResponse(company=CompanyDetail(cd_cvm=cd_cvm))

    r = records[0]
    return BoardResponse(
        company=CompanyDetail(**(r.get("company") or {})),
        board_members=[BoardMember(**m) for m in (r.get("board_members") or [])],
    )


@router.get("/{cd_cvm}/network", response_model=list[InterlockingCompany])
async def get_company_interlocking(
    cd_cvm: int,
    client: Neo4jClient = Depends(get_neo4j),
) -> list[InterlockingCompany]:
    """Return companies connected via shared board members (interlocking directorates)."""
    records = await client.execute_read(
        queries.GET_COMPANY_INTERLOCKING, {"cd_cvm": cd_cvm}
    )

    return [
        InterlockingCompany(
            company=r.get("company") or {},
            shared_members=r.get("shared_members") or [],
            shared_count=r.get("shared_count") or 0,
        )
        for r in records
    ]
