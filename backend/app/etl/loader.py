"""Load cleaned CVM data into Neo4j using batched MERGE operations."""

import logging
import math
from typing import Any

import pandas as pd

from app.graph.neo4j_client import Neo4jClient

logger = logging.getLogger(__name__)

BATCH_SIZE = 500


def _to_batches(df: pd.DataFrame, size: int = BATCH_SIZE) -> list[list[dict[str, Any]]]:
    """Split a DataFrame into a list of record-dict batches."""
    records = df.where(df.notna(), None).to_dict(orient="records")
    return [records[i : i + size] for i in range(0, len(records), size)]


def _safe_value(val: Any) -> Any:
    """Convert pandas / numpy special values to Python-native equivalents."""
    if val is None:
        return None
    if isinstance(val, float) and math.isnan(val):
        return None
    # Convert numpy int/float to python int/float
    try:
        if hasattr(val, "item"):
            return val.item()
    except Exception:
        logger.debug("Could not convert value via .item(), returning as-is: %r", val, exc_info=True)
    # Timestamps → ISO string
    if isinstance(val, pd.Timestamp):
        return val.isoformat()
    return val


def _sanitise_batch(batch: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Ensure all values in *batch* are safe for the Neo4j driver."""
    return [{k: _safe_value(v) for k, v in row.items()} for row in batch]


# ── Constraints & indexes ───────────────────────────────────────────────────

async def create_constraints(client: Neo4jClient) -> None:
    """Create uniqueness constraints and indexes in Neo4j."""
    constraints = [
        "CREATE CONSTRAINT IF NOT EXISTS FOR (p:Person) REQUIRE p.id IS UNIQUE",
        "CREATE CONSTRAINT IF NOT EXISTS FOR (c:Company) REQUIRE c.cd_cvm IS UNIQUE",
        "CREATE CONSTRAINT IF NOT EXISTS FOR (s:Sector) REQUIRE s.nome IS UNIQUE",
        "CREATE INDEX IF NOT EXISTS FOR (p:Person) ON (p.nome_normalizado)",
        "CREATE INDEX IF NOT EXISTS FOR (c:Company) ON (c.nome)",
    ]
    for cypher in constraints:
        await client.execute_write(cypher)
    logger.info("Neo4j constraints and indexes created")


# ── Loaders ─────────────────────────────────────────────────────────────────

async def load_companies(client: Neo4jClient, df: pd.DataFrame) -> int:
    """MERGE Company nodes and BELONGS_TO Sector relationships."""
    if df.empty:
        return 0

    required = {"cd_cvm", "nome"}
    if not required.issubset(df.columns):
        logger.error("load_companies: missing columns %s", required - set(df.columns))
        return 0

    # Keep unique companies
    cols = [c for c in ("cd_cvm", "nome", "cnpj", "segmento_listagem", "situacao", "setor") if c in df.columns]
    companies = df[cols].drop_duplicates(subset=["cd_cvm"])

    query = """
    UNWIND $batch AS row
    MERGE (c:Company {cd_cvm: row.cd_cvm})
    SET c.nome = row.nome,
        c.cnpj = row.cnpj,
        c.segmento_listagem = row.segmento_listagem,
        c.situacao = row.situacao
    WITH c, row
    WHERE row.setor IS NOT NULL
    MERGE (s:Sector {nome: row.setor})
    MERGE (c)-[:BELONGS_TO]->(s)
    """

    total = 0
    for batch in _to_batches(companies):
        batch = _sanitise_batch(batch)
        await client.execute_write(query, {"batch": batch})
        total += len(batch)

    logger.info("Loaded %d companies", total)
    return total


async def load_members(client: Neo4jClient, df: pd.DataFrame) -> int:
    """MERGE Person nodes from the administradores dataset."""
    if df.empty:
        return 0

    required = {"id", "nome", "nome_normalizado"}
    if not required.issubset(df.columns):
        logger.error("load_members: missing columns %s", required - set(df.columns))
        return 0

    cols = [c for c in ("id", "nome", "nome_normalizado", "data_nascimento", "formacao") if c in df.columns]
    persons = df[cols].drop_duplicates(subset=["id"])

    query = """
    UNWIND $batch AS row
    MERGE (p:Person {id: row.id})
    SET p.nome = row.nome,
        p.nome_normalizado = row.nome_normalizado,
        p.data_nascimento = row.data_nascimento,
        p.formacao = row.formacao
    """

    total = 0
    for batch in _to_batches(persons):
        batch = _sanitise_batch(batch)
        await client.execute_write(query, {"batch": batch})
        total += len(batch)

    logger.info("Loaded %d persons", total)
    return total


async def load_memberships(client: Neo4jClient, df: pd.DataFrame) -> int:
    """MERGE MEMBER_OF relationships between Person and Company."""
    if df.empty:
        return 0

    required = {"id", "cd_cvm", "cargo"}
    if not required.issubset(df.columns):
        logger.error("load_memberships: missing columns %s", required - set(df.columns))
        return 0

    cols = [
        c for c in ("id", "cd_cvm", "cargo", "tipo_orgao", "data_eleicao", "mandato_fim", "ano_referencia")
        if c in df.columns
    ]
    rels = df[cols].rename(columns={"id": "person_id"})

    # Ensure ano_referencia is never null (required for MERGE key)
    if "ano_referencia" in rels.columns:
        rels["ano_referencia"] = rels["ano_referencia"].fillna(0).astype(int)
    else:
        rels["ano_referencia"] = 0

    query = """
    UNWIND $batch AS row
    MATCH (p:Person {id: row.person_id})
    MATCH (c:Company {cd_cvm: row.cd_cvm})
    MERGE (p)-[r:MEMBER_OF {cargo: row.cargo, ano_referencia: row.ano_referencia}]->(c)
    SET r.tipo_orgao = row.tipo_orgao,
        r.data_eleicao = row.data_eleicao,
        r.mandato_fim = row.mandato_fim
    """

    total = 0
    for batch in _to_batches(rels):
        batch = _sanitise_batch(batch)
        await client.execute_write(query, {"batch": batch})
        total += len(batch)

    logger.info("Loaded %d memberships", total)
    return total


async def load_shareholdings(client: Neo4jClient, df: pd.DataFrame) -> int:
    """MERGE SHAREHOLDER_OF relationships from posicao_acionaria data."""
    if df.empty:
        return 0

    # Shareholding CSVs typically have: CD_CVM, NOME_ACIONISTA, QTD_ACOES, PERC_PART
    col_map = {
        "CD_CVM": "cd_cvm",
        "NOME_ACIONISTA": "nome_acionista",
        "NM_ACIONISTA": "nome_acionista",
        "QTD_ACOES": "qtd_acoes",
        "PERC_PART": "perc_part",
        "PERC_PARTICIPACAO": "perc_part",
        "DT_REFER": "dt_referencia",
    }
    rename = {k: v for k, v in col_map.items() if k in df.columns}
    df = df.rename(columns=rename)

    if "cd_cvm" not in df.columns or "nome_acionista" not in df.columns:
        logger.warning("load_shareholdings: required columns missing – skipping")
        return 0

    df["cd_cvm"] = pd.to_numeric(df["cd_cvm"], errors="coerce")
    df = df.dropna(subset=["cd_cvm", "nome_acionista"])
    df["cd_cvm"] = df["cd_cvm"].astype(int)

    if "perc_part" in df.columns:
        df["perc_part"] = pd.to_numeric(
            df["perc_part"].astype(str).str.replace(",", "."), errors="coerce"
        )

    query = """
    UNWIND $batch AS row
    MERGE (sh:Shareholder {nome: row.nome_acionista})
    WITH sh, row
    MATCH (c:Company {cd_cvm: row.cd_cvm})
    MERGE (sh)-[r:SHAREHOLDER_OF]->(c)
    SET r.perc_part = row.perc_part,
        r.qtd_acoes = row.qtd_acoes
    """

    total = 0
    for batch in _to_batches(df):
        batch = _sanitise_batch(batch)
        await client.execute_write(query, {"batch": batch})
        total += len(batch)

    logger.info("Loaded %d shareholdings", total)
    return total


async def load_related_party_transactions(client: Neo4jClient, df: pd.DataFrame) -> int:
    """MERGE TRANSACTED_WITH relationships from related-party transaction data."""
    if df.empty:
        return 0

    col_map = {
        "CD_CVM": "cd_cvm",
        "NM_PARTE_RELACIONADA": "nome_parte",
        "NOME_PARTE_RELACIONADA": "nome_parte",
        "NATUREZA_OPERACAO": "natureza",
        "DS_NATUREZA": "natureza",
        "VL_OPERACAO": "valor",
        "DT_REFER": "dt_referencia",
    }
    rename = {k: v for k, v in col_map.items() if k in df.columns}
    df = df.rename(columns=rename)

    if "cd_cvm" not in df.columns or "nome_parte" not in df.columns:
        logger.warning("load_related_party_transactions: required columns missing – skipping")
        return 0

    df["cd_cvm"] = pd.to_numeric(df["cd_cvm"], errors="coerce")
    df = df.dropna(subset=["cd_cvm", "nome_parte"])
    df["cd_cvm"] = df["cd_cvm"].astype(int)

    if "valor" in df.columns:
        df["valor"] = pd.to_numeric(
            df["valor"].astype(str).str.replace(",", "."), errors="coerce"
        )

    query = """
    UNWIND $batch AS row
    MATCH (c:Company {cd_cvm: row.cd_cvm})
    MERGE (rp:RelatedParty {nome: row.nome_parte})
    MERGE (c)-[r:TRANSACTED_WITH]->(rp)
    SET r.natureza = row.natureza,
        r.valor = row.valor
    """

    total = 0
    for batch in _to_batches(df):
        batch = _sanitise_batch(batch)
        await client.execute_write(query, {"batch": batch})
        total += len(batch)

    logger.info("Loaded %d related-party transactions", total)
    return total


async def load_financial_data(client: Neo4jClient, df: pd.DataFrame) -> int:
    """Update Company nodes with key financial metrics from DFP data.

    Extracts Patrimonio Liquido (equity) and Receita Liquida (net revenue)
    and stores them as properties on the Company node.
    """
    if df.empty:
        return 0

    required = {"cd_cvm", "ds_conta", "vl_conta"}
    if not required.issubset(df.columns):
        logger.warning("load_financial_data: required columns missing – skipping")
        return 0

    # Filter for key metrics
    equity_mask = df["ds_conta"].str.contains("Patrimônio Líquido", case=False, na=False)
    revenue_mask = df["ds_conta"].str.contains("Receita de Venda|Receita Líquida", case=False, na=False)

    metrics: list[dict[str, Any]] = []

    for cd_cvm, group in df[equity_mask | revenue_mask].groupby("cd_cvm"):
        row: dict[str, Any] = {"cd_cvm": int(cd_cvm)}
        eq = group[group["ds_conta"].str.contains("Patrimônio Líquido", case=False, na=False)]
        if not eq.empty:
            row["patrimonio_liquido"] = float(eq["vl_conta"].iloc[0]) if pd.notna(eq["vl_conta"].iloc[0]) else None
        rev = group[group["ds_conta"].str.contains("Receita de Venda|Receita Líquida", case=False, na=False)]
        if not rev.empty:
            row["receita_liquida"] = float(rev["vl_conta"].iloc[0]) if pd.notna(rev["vl_conta"].iloc[0]) else None
        metrics.append(row)

    if not metrics:
        logger.info("No financial metrics to load")
        return 0

    query = """
    UNWIND $batch AS row
    MATCH (c:Company {cd_cvm: row.cd_cvm})
    SET c.patrimonio_liquido = row.patrimonio_liquido,
        c.receita_liquida = row.receita_liquida
    """

    total = 0
    for i in range(0, len(metrics), BATCH_SIZE):
        batch = _sanitise_batch(metrics[i : i + BATCH_SIZE])
        await client.execute_write(query, {"batch": batch})
        total += len(batch)

    logger.info("Updated financial data for %d companies", total)
    return total
