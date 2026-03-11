"""Extract and parse CSV data from CVM ZIP archives."""

import logging
import zipfile
from pathlib import Path

import pandas as pd

logger = logging.getLogger(__name__)

DEFAULT_ENCODING_CHAIN = ["utf-8-sig", "cp1252", "latin-1"]


def extract_zip(zip_path: Path, extract_dir: Path) -> list[Path]:
    """Extract all files from a ZIP archive and return the list of paths."""
    extract_dir.mkdir(parents=True, exist_ok=True)
    extracted: list[Path] = []

    with zipfile.ZipFile(zip_path, "r") as zf:
        for member in zf.namelist():
            dest = extract_dir / member
            # Skip directories
            if member.endswith("/"):
                dest.mkdir(parents=True, exist_ok=True)
                continue
            dest.parent.mkdir(parents=True, exist_ok=True)
            with zf.open(member) as src, open(dest, "wb") as dst:
                dst.write(src.read())
            extracted.append(dest)

    logger.info("Extracted %d files from %s", len(extracted), zip_path.name)
    return extracted


def read_csv_safe(
    file_path: Path,
    encoding_chain: list[str] | None = None,
) -> pd.DataFrame:
    """Read a semicolon-separated CVM CSV trying multiple encodings."""
    chain = encoding_chain or DEFAULT_ENCODING_CHAIN

    for encoding in chain:
        try:
            df = pd.read_csv(
                file_path,
                sep=";",
                encoding=encoding,
                low_memory=False,
                dtype=str,
            )
            logger.debug(
                "Read %s with encoding %s (%d rows)",
                file_path.name,
                encoding,
                len(df),
            )
            return df
        except (UnicodeDecodeError, UnicodeError):
            logger.debug("Encoding %s failed for %s", encoding, file_path.name)
            continue

    raise ValueError(
        f"Could not read {file_path} with any of the encodings: {chain}"
    )


def _collect_csvs_from_zips(
    zip_paths: list[Path],
    extract_dir: Path,
    pattern: str,
) -> list[Path]:
    """Extract ZIPs and collect CSVs matching *pattern* in their name."""
    csv_files: list[Path] = []
    for zp in zip_paths:
        extracted = extract_zip(zp, extract_dir / zp.stem)
        for fp in extracted:
            if pattern in fp.name.lower():
                csv_files.append(fp)
    return csv_files


def _concat_csvs(csv_files: list[Path], label: str) -> pd.DataFrame:
    """Read and concatenate a list of CSVs into a single DataFrame."""
    if not csv_files:
        logger.warning("No CSV files found for %s", label)
        return pd.DataFrame()

    frames: list[pd.DataFrame] = []
    for fp in csv_files:
        try:
            df = read_csv_safe(fp)
            frames.append(df)
        except Exception:
            logger.exception("Failed to read %s", fp)

    if not frames:
        return pd.DataFrame()

    combined = pd.concat(frames, ignore_index=True)
    logger.info("Parsed %s: %d rows from %d files", label, len(combined), len(frames))
    return combined


# ── FRE parsers ─────────────────────────────────────────────────────────────


def parse_administradores(
    zip_paths: list[Path],
    extract_dir: Path,
) -> pd.DataFrame:
    """Parse board member / director data from FRE ZIPs."""
    csvs = _collect_csvs_from_zips(zip_paths, extract_dir, "administrador")
    return _concat_csvs(csvs, "administradores")


def parse_comites(
    zip_paths: list[Path],
    extract_dir: Path,
) -> pd.DataFrame:
    """Parse committee member data from FRE ZIPs."""
    csvs = _collect_csvs_from_zips(zip_paths, extract_dir, "membro_comite")
    return _concat_csvs(csvs, "comites")


def parse_conselho_fiscal(
    zip_paths: list[Path],
    extract_dir: Path,
) -> pd.DataFrame:
    """Parse fiscal council member data from FRE ZIPs."""
    csvs = _collect_csvs_from_zips(zip_paths, extract_dir, "membro_conselho_fiscal")
    return _concat_csvs(csvs, "conselho_fiscal")


def parse_posicao_acionaria(
    zip_paths: list[Path],
    extract_dir: Path,
) -> pd.DataFrame:
    """Parse shareholding position data from FRE ZIPs."""
    csvs = _collect_csvs_from_zips(zip_paths, extract_dir, "posicao_acionaria")
    return _concat_csvs(csvs, "posicao_acionaria")


def parse_transacoes_partes_relacionadas(
    zip_paths: list[Path],
    extract_dir: Path,
) -> pd.DataFrame:
    """Parse related-party transaction data from FRE ZIPs."""
    csvs = _collect_csvs_from_zips(zip_paths, extract_dir, "transacao_parte_relacionada")
    return _concat_csvs(csvs, "transacoes_partes_relacionadas")


# ── Cadastro ────────────────────────────────────────────────────────────────


def parse_cadastro(csv_path: Path) -> pd.DataFrame:
    """Parse the company registry CSV."""
    df = read_csv_safe(csv_path)
    logger.info("Parsed cadastro: %d rows", len(df))
    return df


# ── DFP ─────────────────────────────────────────────────────────────────────


def parse_dfp(
    zip_paths: list[Path],
    extract_dir: Path,
) -> pd.DataFrame:
    """Parse DFP financial statement data from DFP ZIPs.

    We focus on the consolidated balance-sheet / income-statement CSVs.
    """
    # DFP ZIPs typically contain files like dfp_cia_aberta_BPA_con_YYYY.csv,
    # dfp_cia_aberta_DRE_con_YYYY.csv, etc. We collect all of them.
    csvs = _collect_csvs_from_zips(zip_paths, extract_dir, "dfp_cia_aberta")
    return _concat_csvs(csvs, "dfp")
