"""Download public datasets from CVM (Comissão de Valores Mobiliários)."""

import asyncio
import logging
from pathlib import Path

import httpx

logger = logging.getLogger(__name__)

CVM_FRE_URL = "https://dados.cvm.gov.br/dados/CIA_ABERTA/DOC/FRE/DADOS/fre_cia_aberta_{year}.zip"
CVM_CADASTRO_URL = "https://dados.cvm.gov.br/dados/CIA_ABERTA/CAD/DADOS/cad_cia_aberta.csv"
CVM_DFP_URL = "https://dados.cvm.gov.br/dados/CIA_ABERTA/DOC/DFP/DADOS/dfp_cia_aberta_{year}.zip"

MAX_RETRIES = 3
BACKOFF_BASE = 2.0
DOWNLOAD_TIMEOUT = 300.0


async def download_file(
    url: str,
    dest_path: Path,
    force: bool = False,
) -> Path:
    """Download a file from *url* to *dest_path* with retry and progress tracking.

    If the file already exists and *force* is False the download is skipped.
    Returns the destination path on success.
    """
    dest_path.parent.mkdir(parents=True, exist_ok=True)

    if dest_path.exists() and not force:
        logger.info("Cached – skipping download: %s", dest_path.name)
        return dest_path

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            logger.info(
                "Downloading %s (attempt %d/%d)", url, attempt, MAX_RETRIES
            )
            async with httpx.AsyncClient(
                timeout=httpx.Timeout(DOWNLOAD_TIMEOUT),
                follow_redirects=True,
            ) as client:
                async with client.stream("GET", url) as response:
                    response.raise_for_status()
                    total = int(response.headers.get("content-length", 0))
                    downloaded = 0

                    with open(dest_path, "wb") as fh:
                        async for chunk in response.aiter_bytes(chunk_size=65_536):
                            fh.write(chunk)
                            downloaded += len(chunk)
                            if total:
                                pct = downloaded / total * 100
                                logger.debug(
                                    "  %s – %.1f%% (%d / %d bytes)",
                                    dest_path.name,
                                    pct,
                                    downloaded,
                                    total,
                                )

            logger.info("Downloaded %s (%d bytes)", dest_path.name, downloaded)
            return dest_path

        except (httpx.HTTPStatusError, httpx.TransportError) as exc:
            logger.warning("Attempt %d failed for %s: %s", attempt, url, exc)
            if attempt < MAX_RETRIES:
                wait = BACKOFF_BASE ** attempt
                logger.info("Retrying in %.1f s …", wait)
                await asyncio.sleep(wait)
            else:
                logger.error("All %d attempts exhausted for %s", MAX_RETRIES, url)
                raise

    # Should never be reached, but keeps mypy happy.
    raise RuntimeError(f"Failed to download {url}")


async def download_fre_data(
    years: list[int],
    data_dir: Path,
    force: bool = False,
) -> list[Path]:
    """Download FRE ZIP files for the given *years*."""
    paths: list[Path] = []
    for year in years:
        url = CVM_FRE_URL.format(year=year)
        dest = data_dir / f"fre_cia_aberta_{year}.zip"
        try:
            path = await download_file(url, dest, force=force)
            paths.append(path)
        except httpx.HTTPStatusError as exc:
            # 404 is expected for future years – warn and skip.
            if exc.response.status_code == 404:
                logger.warning("FRE data not available for %d – skipping", year)
            else:
                raise
    return paths


async def download_cadastro(
    data_dir: Path,
    force: bool = False,
) -> Path:
    """Download the company registry CSV."""
    dest = data_dir / "cad_cia_aberta.csv"
    return await download_file(CVM_CADASTRO_URL, dest, force=force)


async def download_dfp_data(
    years: list[int],
    data_dir: Path,
    force: bool = False,
) -> list[Path]:
    """Download DFP (financial statements) ZIP files for the given *years*."""
    paths: list[Path] = []
    for year in years:
        url = CVM_DFP_URL.format(year=year)
        dest = data_dir / f"dfp_cia_aberta_{year}.zip"
        try:
            path = await download_file(url, dest, force=force)
            paths.append(path)
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code == 404:
                logger.warning("DFP data not available for %d – skipping", year)
            else:
                raise
    return paths
