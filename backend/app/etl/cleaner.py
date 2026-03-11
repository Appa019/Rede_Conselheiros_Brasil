"""Data cleaning and normalisation for CVM datasets."""

import hashlib
import logging
import re

import pandas as pd
from unidecode import unidecode

logger = logging.getLogger(__name__)

# ── Name / cargo helpers ────────────────────────────────────────────────────

CARGO_MAP: dict[str, str] = {
    "PRESIDENTE DO CONSELHO DE ADMINISTRACAO": "PRESIDENTE DO CONSELHO",
    "PRESIDENTE DO CONSELHO DE ADMINISTRAÇÃO": "PRESIDENTE DO CONSELHO",
    "VICE-PRESIDENTE DO CONSELHO DE ADMINISTRACAO": "VICE-PRESIDENTE DO CONSELHO",
    "VICE-PRESIDENTE DO CONSELHO DE ADMINISTRAÇÃO": "VICE-PRESIDENTE DO CONSELHO",
    "MEMBRO DO CONSELHO DE ADMINISTRACAO": "CONSELHEIRO",
    "MEMBRO DO CONSELHO DE ADMINISTRAÇÃO": "CONSELHEIRO",
    "CONSELHEIRO DE ADMINISTRACAO": "CONSELHEIRO",
    "CONSELHEIRO DE ADMINISTRAÇÃO": "CONSELHEIRO",
    "MEMBRO SUPLENTE DO CONSELHO DE ADMINISTRACAO": "CONSELHEIRO SUPLENTE",
    "MEMBRO SUPLENTE DO CONSELHO DE ADMINISTRAÇÃO": "CONSELHEIRO SUPLENTE",
    "DIRETOR PRESIDENTE": "CEO",
    "DIRETOR-PRESIDENTE": "CEO",
    "DIRETOR DE RELACOES COM INVESTIDORES": "DRI",
    "DIRETOR DE RELAÇÕES COM INVESTIDORES": "DRI",
    "MEMBRO DO CONSELHO FISCAL": "CONSELHEIRO FISCAL",
    "MEMBRO SUPLENTE DO CONSELHO FISCAL": "CONSELHEIRO FISCAL SUPLENTE",
    "PRESIDENTE DO CONSELHO FISCAL": "PRESIDENTE DO CONSELHO FISCAL",
}


def normalize_name(name: str) -> str:
    """Normalize a person/company name: unidecode → upper → strip → collapse whitespace."""
    if not isinstance(name, str):
        return ""
    normalized = unidecode(name).upper().strip()
    normalized = re.sub(r"\s+", " ", normalized)
    return normalized


def normalize_cargo(cargo: str) -> str:
    """Map raw position titles to a standardised set."""
    if not isinstance(cargo, str):
        return ""
    upper = cargo.strip().upper()
    return CARGO_MAP.get(upper, upper)


def generate_person_id(nome_normalizado: str, data_nascimento: str | None) -> str:
    """Create a deterministic 12-char hex ID for a person.

    Uses SHA-256 of nome_normalizado + data_nascimento (or name only when
    birth date is missing).
    """
    key = nome_normalizado
    if data_nascimento and str(data_nascimento).strip():
        key = f"{nome_normalizado}|{str(data_nascimento).strip()}"
    return hashlib.sha256(key.encode("utf-8")).hexdigest()[:12]


# ── Column mapping helpers ──────────────────────────────────────────────────

# CVM column names vary across years; map known variants to a unified schema.
ADMIN_COLUMN_MAP: dict[str, str] = {
    # Legacy format (pre-2023)
    "CD_CVM": "cd_cvm",
    "DENOM_SOCIAL": "denom_social",
    "DENOM_CIA": "denom_social",
    "CNPJ_CIA": "cnpj",
    "NOME_ADMINISTRADOR": "nome",
    "NM_ADMINISTRADOR": "nome",
    "DT_NASC": "data_nascimento",
    "DT_NASCIMENTO": "data_nascimento",
    "CARGO": "cargo",
    "DS_CARGO": "cargo",
    "TIPO_ORGAO": "tipo_orgao",
    "DS_ORGAO": "tipo_orgao",
    "DT_ELEICAO": "data_eleicao",
    "DT_POSSE": "data_eleicao",
    "DT_FIM_MANDATO": "mandato_fim",
    "ANO_REFER": "ano_referencia",
    "DT_REFER": "dt_referencia",
    "FORMACAO": "formacao",
    "DS_FORMACAO": "formacao",
    # Current format (2023+)
    "CNPJ_Companhia": "cnpj",
    "Nome_Companhia": "denom_social",
    "Nome": "nome",
    "CPF": "cpf",
    "Profissao": "formacao",
    "Cargo_Eletivo_Ocupado": "cargo",
    "Data_Eleicao": "data_eleicao",
    "Data_Posse": "data_posse",
    "Data_Nascimento": "data_nascimento",
    "Orgao_Administracao": "tipo_orgao",
    "Data_Referencia": "dt_referencia",
    "Prazo_Mandato": "mandato_fim",
    "Eleito_Controlador": "eleito_controlador",
    "Outro_Cargo_Funcao": "outro_cargo",
    "Complemento_Cargo_Eletivo_Ocupado": "complemento_cargo",
    "ID_Documento": "id_documento",
    "Versao": "versao",
}

CADASTRO_COLUMN_MAP: dict[str, str] = {
    "CD_CVM": "cd_cvm",
    "DENOM_SOCIAL": "nome",
    "DENOM_CIA": "nome",
    "CNPJ_CIA": "cnpj",
    "SIT": "situacao",
    "SETOR_ATIV": "setor",
    "TP_MERC": "tipo_mercado",
    "CATEG_REG": "categoria_registro",
    "SEG_MERC": "segmento_listagem",
}

DFP_COLUMN_MAP: dict[str, str] = {
    "CD_CVM": "cd_cvm",
    "DENOM_CIA": "denom_social",
    "CNPJ_CIA": "cnpj",
    "DT_REFER": "dt_referencia",
    "ANO_REFER": "ano_referencia",
    "CD_CONTA": "cd_conta",
    "DS_CONTA": "ds_conta",
    "VL_CONTA": "vl_conta",
    "ORDEM_EXERC": "ordem_exerc",
    "ESCALA_MOEDA": "escala_moeda",
}


def _rename_columns(df: pd.DataFrame, col_map: dict[str, str]) -> pd.DataFrame:
    """Rename columns using *col_map*, keeping only mapped ones that exist."""
    rename = {k: v for k, v in col_map.items() if k in df.columns}
    df = df.rename(columns=rename)
    return df


def _parse_date_col(series: pd.Series) -> pd.Series:
    """Best-effort date parsing that silently coerces bad values to NaT."""
    return pd.to_datetime(series, errors="coerce", dayfirst=True)


# ── Cleaning pipelines ──────────────────────────────────────────────────────


def deduplicate_members(df: pd.DataFrame) -> pd.DataFrame:
    """Deduplicate person records by nome_normalizado + data_nascimento.

    Keeps the first occurrence and logs any ambiguities.
    """
    if "nome_normalizado" not in df.columns:
        logger.warning("deduplicate_members: 'nome_normalizado' column missing")
        return df

    dedup_cols = ["nome_normalizado"]
    if "data_nascimento" in df.columns:
        dedup_cols.append("data_nascimento")

    before = len(df)
    df = df.drop_duplicates(subset=dedup_cols, keep="first")
    removed = before - len(df)
    if removed:
        logger.info("Deduplicated members: removed %d duplicates", removed)
    return df


def clean_administradores(
    df: pd.DataFrame,
    cadastro_df: pd.DataFrame | None = None,
) -> pd.DataFrame:
    """Full cleaning pipeline for the administradores dataset."""
    if df.empty:
        return df

    df = _rename_columns(df, ADMIN_COLUMN_MAP)

    # If cd_cvm is missing but cnpj is present, resolve via cadastro lookup
    if "cd_cvm" not in df.columns and "cnpj" in df.columns and cadastro_df is not None:
        cad = cadastro_df[["cd_cvm", "cnpj"]].drop_duplicates(subset=["cnpj"])
        # Normalize CNPJ format for matching
        df["cnpj"] = df["cnpj"].astype(str).str.strip()
        cad["cnpj"] = cad["cnpj"].astype(str).str.strip()
        df = df.merge(cad, on="cnpj", how="left")
        unmatched = df["cd_cvm"].isna().sum()
        if unmatched:
            logger.warning("%d admin rows could not be matched to cd_cvm via CNPJ", unmatched)

    # Ensure mandatory columns exist
    for col in ("nome",):
        if col not in df.columns:
            logger.error("Missing mandatory column '%s' in administradores", col)
            return pd.DataFrame()

    if "cd_cvm" not in df.columns:
        logger.error("Missing 'cd_cvm' column and could not resolve from CNPJ")
        return pd.DataFrame()

    # Drop rows without a name
    df = df.dropna(subset=["nome"])

    # Normalize
    df["nome_normalizado"] = df["nome"].apply(normalize_name)
    df = df[df["nome_normalizado"].str.len() > 0]

    if "cargo" in df.columns:
        df["cargo"] = df["cargo"].apply(normalize_cargo)

    # Parse dates
    for date_col in ("data_nascimento", "data_eleicao", "mandato_fim"):
        if date_col in df.columns:
            df[date_col] = _parse_date_col(df[date_col])

    # Extract ano_referencia from dt_referencia when missing
    if "ano_referencia" not in df.columns and "dt_referencia" in df.columns:
        dt = _parse_date_col(df["dt_referencia"])
        df["ano_referencia"] = dt.dt.year

    if "ano_referencia" in df.columns:
        df["ano_referencia"] = pd.to_numeric(df["ano_referencia"], errors="coerce")

    # Coerce cd_cvm to int
    df["cd_cvm"] = pd.to_numeric(df["cd_cvm"], errors="coerce")
    df = df.dropna(subset=["cd_cvm"])
    df["cd_cvm"] = df["cd_cvm"].astype(int)

    # Generate person ID
    df["data_nascimento_str"] = df.get("data_nascimento", pd.Series(dtype=str)).astype(str)
    df["id"] = df.apply(
        lambda r: generate_person_id(
            r["nome_normalizado"],
            r["data_nascimento_str"] if r["data_nascimento_str"] != "NaT" else None,
        ),
        axis=1,
    )
    df = df.drop(columns=["data_nascimento_str"])

    logger.info("Cleaned administradores: %d rows", len(df))
    return df


def clean_cadastro(df: pd.DataFrame) -> pd.DataFrame:
    """Clean the company registry dataset."""
    if df.empty:
        return df

    df = _rename_columns(df, CADASTRO_COLUMN_MAP)

    for col in ("nome", "cd_cvm"):
        if col not in df.columns:
            logger.error("Missing mandatory column '%s' in cadastro", col)
            return pd.DataFrame()

    df["cd_cvm"] = pd.to_numeric(df["cd_cvm"], errors="coerce")
    df = df.dropna(subset=["cd_cvm"])
    df["cd_cvm"] = df["cd_cvm"].astype(int)

    # Normalize company name
    df["nome"] = df["nome"].apply(lambda x: x.strip().upper() if isinstance(x, str) else x)

    # Strip whitespace from text columns
    for col in ("cnpj", "situacao", "setor", "segmento_listagem"):
        if col in df.columns:
            df[col] = df[col].apply(lambda x: x.strip() if isinstance(x, str) else x)

    logger.info("Cleaned cadastro: %d rows", len(df))
    return df


def clean_dfp(df: pd.DataFrame) -> pd.DataFrame:
    """Clean DFP financial data."""
    if df.empty:
        return df

    df = _rename_columns(df, DFP_COLUMN_MAP)

    if "cd_cvm" not in df.columns:
        logger.error("Missing mandatory column 'cd_cvm' in DFP data")
        return pd.DataFrame()

    df["cd_cvm"] = pd.to_numeric(df["cd_cvm"], errors="coerce")
    df = df.dropna(subset=["cd_cvm"])
    df["cd_cvm"] = df["cd_cvm"].astype(int)

    if "vl_conta" in df.columns:
        df["vl_conta"] = pd.to_numeric(
            df["vl_conta"].astype(str).str.replace(",", "."), errors="coerce"
        )

    if "ano_referencia" not in df.columns and "dt_referencia" in df.columns:
        dt = _parse_date_col(df["dt_referencia"])
        df["ano_referencia"] = dt.dt.year

    if "ano_referencia" in df.columns:
        df["ano_referencia"] = pd.to_numeric(df["ano_referencia"], errors="coerce")

    # Keep only the most recent fiscal year exercise when duplicates exist
    if "ordem_exerc" in df.columns:
        df = df[df["ordem_exerc"].astype(str).str.strip() == "ÚLTIMO"]

    logger.info("Cleaned DFP: %d rows", len(df))
    return df
