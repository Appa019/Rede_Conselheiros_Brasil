"""End-to-end ETL orchestrator for the CVM board-member network."""

import logging
from pathlib import Path
from typing import Any

import pandas as pd

from app.config import settings
from app.graph.neo4j_client import Neo4jClient

from app.etl.downloader import download_cadastro, download_dfp_data, download_fre_data
from app.etl.extractor import (
    parse_administradores,
    parse_cadastro,
    parse_comites,
    parse_conselho_fiscal,
    parse_dfp,
    parse_posicao_acionaria,
    parse_transacoes_partes_relacionadas,
)
from app.etl.cleaner import clean_administradores, clean_cadastro, clean_dfp
from app.etl.loader import (
    create_constraints,
    load_companies,
    load_financial_data,
    load_members,
    load_memberships,
    load_related_party_transactions,
    load_shareholdings,
)

logger = logging.getLogger(__name__)

DEFAULT_YEARS = list(range(2021, 2027))  # 2021-2026


async def run_etl(
    years: list[int] | None = None,
    force_download: bool = False,
    on_progress: Any = None,
) -> dict[str, Any]:
    """Execute the full ETL pipeline and return a summary of what was loaded.

    Steps
    -----
    1. Download raw data from CVM.
    2. Extract & parse CSV files.
    3. Clean & normalise.
    4. Load into Neo4j.
    """
    def progress(pct: float, msg: str) -> None:
        if on_progress:
            on_progress(pct, msg)

    years = years or DEFAULT_YEARS
    data_dir = Path(settings.data_dir).resolve()
    extract_dir = data_dir / "extracted"
    data_dir.mkdir(parents=True, exist_ok=True)

    summary: dict[str, Any] = {
        "years": years,
        "companies": 0,
        "persons": 0,
        "memberships": 0,
        "shareholdings": 0,
        "related_party_txns": 0,
        "financial_updates": 0,
        "errors": [],
    }

    # ── 1. Download ─────────────────────────────────────────────────────────
    logger.info("Step 1/4 – Downloading data for years %s", years)
    progress(5, "Baixando dados FRE da CVM...")
    try:
        fre_zips = await download_fre_data(years, data_dir, force=force_download)
        logger.info("Downloaded %d FRE ZIP files", len(fre_zips))
    except Exception as exc:
        logger.exception("Failed to download FRE data")
        summary["errors"].append(f"FRE download: {exc}")
        fre_zips = []

    progress(15, "Baixando cadastro de empresas...")
    try:
        cadastro_path = await download_cadastro(data_dir, force=force_download)
    except Exception as exc:
        logger.exception("Failed to download cadastro")
        summary["errors"].append(f"Cadastro download: {exc}")
        cadastro_path = None

    progress(20, "Baixando dados DFP...")
    try:
        dfp_zips = await download_dfp_data(years, data_dir, force=force_download)
        logger.info("Downloaded %d DFP ZIP files", len(dfp_zips))
    except Exception as exc:
        logger.exception("Failed to download DFP data")
        summary["errors"].append(f"DFP download: {exc}")
        dfp_zips = []

    # ── 2. Extract & parse ──────────────────────────────────────────────────
    progress(30, "Extraindo e parseando CSVs...")
    logger.info("Step 2/4 – Extracting and parsing")

    admin_df = parse_administradores(fre_zips, extract_dir) if fre_zips else pd.DataFrame()
    comite_df = parse_comites(fre_zips, extract_dir) if fre_zips else pd.DataFrame()
    fiscal_df = parse_conselho_fiscal(fre_zips, extract_dir) if fre_zips else pd.DataFrame()
    acionaria_df = parse_posicao_acionaria(fre_zips, extract_dir) if fre_zips else pd.DataFrame()
    transacoes_df = parse_transacoes_partes_relacionadas(fre_zips, extract_dir) if fre_zips else pd.DataFrame()

    cadastro_df = parse_cadastro(cadastro_path) if cadastro_path else pd.DataFrame()
    dfp_df = parse_dfp(dfp_zips, extract_dir) if dfp_zips else pd.DataFrame()

    # Merge committee and fiscal-council members into administradores

    if not comite_df.empty:
        admin_df = pd.concat([admin_df, comite_df], ignore_index=True)
    if not fiscal_df.empty:
        admin_df = pd.concat([admin_df, fiscal_df], ignore_index=True)

    # ── 3. Clean & normalise ────────────────────────────────────────────────
    progress(45, "Limpando e normalizando dados...")
    logger.info("Step 3/4 – Cleaning and normalising")

    cadastro_clean = clean_cadastro(cadastro_df)
    admin_clean = clean_administradores(admin_df, cadastro_df=cadastro_clean)
    dfp_clean = clean_dfp(dfp_df)

    # ── 4. Load into Neo4j ──────────────────────────────────────────────────
    progress(55, "Criando constraints no Neo4j...")
    logger.info("Step 4/4 – Loading into Neo4j")

    async with Neo4jClient() as client:
        await create_constraints(client)

        progress(58, "Carregando empresas...")
        try:
            summary["companies"] = await load_companies(client, cadastro_clean)
        except Exception as exc:
            logger.exception("Failed to load companies")
            summary["errors"].append(f"Load companies: {exc}")

        progress(65, "Carregando membros...")
        try:
            summary["persons"] = await load_members(client, admin_clean)
        except Exception as exc:
            logger.exception("Failed to load members")
            summary["errors"].append(f"Load members: {exc}")

        progress(72, "Carregando vinculos...")
        try:
            summary["memberships"] = await load_memberships(client, admin_clean)
        except Exception as exc:
            logger.exception("Failed to load memberships")
            summary["errors"].append(f"Load memberships: {exc}")

        progress(78, "Carregando posicoes acionarias...")
        try:
            summary["shareholdings"] = await load_shareholdings(client, acionaria_df)
        except Exception as exc:
            logger.exception("Failed to load shareholdings")
            summary["errors"].append(f"Load shareholdings: {exc}")

        progress(84, "Carregando transacoes partes relacionadas...")
        try:
            summary["related_party_txns"] = await load_related_party_transactions(client, transacoes_df)
        except Exception as exc:
            logger.exception("Failed to load related-party transactions")
            summary["errors"].append(f"Load RPT: {exc}")

        progress(90, "Carregando dados financeiros...")
        try:
            summary["financial_updates"] = await load_financial_data(client, dfp_clean)
        except Exception as exc:
            logger.exception("Failed to load financial data")
            summary["errors"].append(f"Load financials: {exc}")

    progress(96, "Finalizando ETL...")
    logger.info("ETL complete – summary: %s", summary)
    return summary
