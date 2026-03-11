"""Member and company-related Pydantic schemas."""

from typing import Any

from pydantic import BaseModel, Field


class CompanyInfo(BaseModel):
    """Basic company information."""

    cd_cvm: int | None = None
    nome: str | None = None
    cargo: str | None = None


class CompanyDetail(BaseModel):
    """Full company details."""

    cd_cvm: int | None = None
    cnpj: str | None = None
    nome: str | None = None
    setor: str | None = None
    segmento_listagem: str | None = None
    situacao: str | None = None


class CompanyMembership(BaseModel):
    """Company membership with temporal data."""

    cd_cvm: int | None = None
    nome: str | None = None
    cargo: str | None = None
    ano_referencia: int | None = None
    data_eleicao: str | None = None


class MemberSummary(BaseModel):
    """Summary of a member with key metrics."""

    id: str | None = None
    nome: str | None = None
    nome_normalizado: str | None = None
    formacao: str | None = None
    page_rank: float | None = None
    betweenness: float | None = None
    degree_centrality: float | None = None
    eigenvector: float | None = None
    closeness: float | None = None
    clustering_coeff: float | None = None
    community_id: int | None = None
    k_core: int | None = None


class MemberWithCompanies(BaseModel):
    """Member summary paired with their companies."""

    member: MemberSummary
    companies: list[CompanyInfo] = Field(default_factory=list)


class ConnectionSummary(BaseModel):
    """Summarized neighbor/connection info."""

    id: str | None = None
    nome: str | None = None
    page_rank: float | None = None


class MemberDetail(BaseModel):
    """Full member profile with metrics, companies, and connections."""

    member: MemberSummary
    companies: list[CompanyMembership] = Field(default_factory=list)
    connections: list[ConnectionSummary] = Field(default_factory=list)


class BoardMember(BaseModel):
    """A member on a company's board."""

    id: str | None = None
    nome: str | None = None
    cargo: str | None = None
    ano_referencia: int | None = None
    page_rank: float | None = None


class BoardResponse(BaseModel):
    """Company board composition."""

    company: CompanyDetail
    board_members: list[BoardMember] = Field(default_factory=list)


class InterlockingCompany(BaseModel):
    """Company connected via shared board members."""

    company: dict[str, Any] = Field(default_factory=dict)
    shared_members: list[str] = Field(default_factory=list)
    shared_count: int = 0


class TopMemberResponse(BaseModel):
    """Member entry in a top-N ranking."""

    id: str | None = None
    nome: str | None = None
    page_rank: float | None = None
    betweenness: float | None = None
    degree_centrality: float | None = None
    eigenvector: float | None = None
    closeness: float | None = None
    community_id: int | None = None
