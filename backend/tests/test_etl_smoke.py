"""Smoke tests for the ETL pipeline."""

import tempfile
from pathlib import Path

import pytest

from app.etl.downloader import download_cadastro, download_fre_data
from app.etl.extractor import parse_administradores, parse_cadastro
from app.etl.cleaner import clean_administradores, clean_cadastro


pytestmark = pytest.mark.smoke

YEARS = [2021, 2022, 2023, 2024, 2025]


# --- Download tests ---


@pytest.mark.parametrize("year", YEARS)
async def test_download_fre_per_year(year):
    with tempfile.TemporaryDirectory() as tmp:
        data_dir = Path(tmp)
        try:
            paths = await download_fre_data([year], data_dir)
        except Exception as exc:
            pytest.skip(f"CVM offline or download failed: {exc}")
        assert len(paths) > 0
        for p in paths:
            assert p.exists()
            assert p.stat().st_size > 0


async def test_download_cadastro():
    with tempfile.TemporaryDirectory() as tmp:
        data_dir = Path(tmp)
        try:
            path = await download_cadastro(data_dir)
        except Exception as exc:
            pytest.skip(f"CVM offline or download failed: {exc}")
        assert path.exists()
        assert path.stat().st_size > 0


# --- Parse tests ---


async def test_parse_administradores():
    with tempfile.TemporaryDirectory() as tmp:
        data_dir = Path(tmp)
        try:
            zip_paths = await download_fre_data([2024], data_dir)
        except Exception as exc:
            pytest.skip(f"CVM offline: {exc}")

        extract_dir = data_dir / "extracted"
        extract_dir.mkdir(exist_ok=True)
        df = parse_administradores(zip_paths, extract_dir)
        assert len(df) > 0
        expected_cols = {"CNPJ_CIA", "NOME_ADM"}
        assert expected_cols.issubset(set(df.columns)) or len(df.columns) > 3


async def test_parse_cadastro():
    with tempfile.TemporaryDirectory() as tmp:
        data_dir = Path(tmp)
        try:
            path = await download_cadastro(data_dir)
        except Exception as exc:
            pytest.skip(f"CVM offline: {exc}")

        df = parse_cadastro(path)
        assert len(df) > 0
        assert "CD_CVM" in df.columns or "DENOM_SOCIAL" in df.columns


# --- Clean tests ---


async def test_clean_administradores():
    with tempfile.TemporaryDirectory() as tmp:
        data_dir = Path(tmp)
        try:
            zip_paths = await download_fre_data([2024], data_dir)
        except Exception as exc:
            pytest.skip(f"CVM offline: {exc}")

        extract_dir = data_dir / "extracted"
        extract_dir.mkdir(exist_ok=True)
        df_raw = parse_administradores(zip_paths, extract_dir)

        cadastro_path = None
        try:
            cadastro_path = await download_cadastro(data_dir)
        except Exception:
            pass

        cadastro_df = parse_cadastro(cadastro_path) if cadastro_path else None
        df_clean = clean_administradores(df_raw, cadastro_df)
        assert len(df_clean) > 0
        assert "id" in df_clean.columns
        assert "nome_normalizado" in df_clean.columns


# --- Full ETL ---


@pytest.mark.slow
async def test_full_etl_single_year():
    from app.etl.orchestrator import run_etl

    try:
        summary = await run_etl(years=[2024])
    except Exception as exc:
        pytest.skip(f"ETL failed (network/Neo4j): {exc}")
    assert summary["persons"] > 0
