"""ML training orchestrator."""

import logging
from pathlib import Path
from typing import Any

from app.graph.neo4j_client import Neo4jClient
from app.graph.metrics import build_networkx_graph, build_networkx_graph_for_years
from app.ml.embeddings import generate_embeddings, save_embeddings
from app.ml.local_vector_store import LocalVectorStore
from app.ml.link_prediction import train_link_predictor

logger = logging.getLogger(__name__)

MODEL_DIR = Path("data/models")
EMBEDDINGS_PATH = MODEL_DIR / "embeddings.npz"
LINK_MODEL_PATH = MODEL_DIR / "link_predictor.joblib"


async def run_training_pipeline(
    client: Neo4jClient,
    on_progress: Any = None,
) -> dict[str, Any]:
    """Run the complete ML training pipeline."""

    def progress(pct: float, msg: str) -> None:
        if on_progress:
            on_progress(pct, msg)

    import asyncio

    def make_sub_progress(start: float, end: float):
        """Create a sub-progress callback mapped to a range of the overall progress."""
        def sub(pct: float, msg: str) -> None:
            overall = start + (pct / 100) * (end - start)
            progress(overall, msg)
        return sub

    results = {}

    # 1. Build graphs (0-10%): full graph + temporal training graph (≤2023)
    progress(2, "Construindo grafo completo a partir do Neo4j...")
    logger.info("Building full NetworkX graph from Neo4j...")
    G = await build_networkx_graph(client)

    if G.number_of_nodes() == 0:
        logger.warning("Empty graph, skipping ML pipeline")
        return {"status": "empty_graph"}

    progress(6, f"Grafo completo: {G.number_of_nodes()} nodes, {G.number_of_edges()} edges")

    # Temporal training graph: edges present up to 2023 (avoids data leakage)
    progress(7, "Construindo grafo de treino temporal (≤2023)...")
    logger.info("Building temporal training graph (MEMBER_OF ≤ 2023)...")
    G_train = await build_networkx_graph_for_years(client, max_year=2023)
    progress(10, f"Grafo de treino: {G_train.number_of_nodes()} nodes, {G_train.number_of_edges()} edges")

    # 2. Generate embeddings (10-55%) — CPU-bound
    logger.info("Generating Node2Vec embeddings...")
    embeddings = await asyncio.to_thread(
        generate_embeddings, G, on_progress=make_sub_progress(10, 55)
    )
    save_embeddings(embeddings, EMBEDDINGS_PATH)
    results["embeddings"] = {"count": len(embeddings), "path": str(EMBEDDINGS_PATH)}

    # 3. Save embeddings to local vector store with metadata (55-60%)
    progress(55, "Salvando embeddings no store local...")
    logger.info("Building metadata and saving to local vector store...")

    meta_query = """
    MATCH (p:Person)
    OPTIONAL MATCH (p)-[:MEMBER_OF]->(c:Company)
    WITH p, collect(c.nome)[..5] AS companies
    RETURN p.id AS id, p.nome AS nome, p.community_id AS community_id,
           p.page_rank AS page_rank, companies
    """
    records = await client.execute_read(meta_query)
    metadata: dict[str, dict[str, Any]] = {}
    for r in records:
        metadata[r["id"]] = {
            "nome": r["nome"] or "",
            "community_id": r["community_id"] or 0,
            "page_rank": r["page_rank"] or 0,
            "companies": ", ".join(r["companies"][:3]) if r["companies"] else "",
        }

    store = LocalVectorStore(embeddings_path=EMBEDDINGS_PATH)
    saved = store.save(embeddings, metadata)
    results["local_store"] = {"saved": saved}
    progress(60, f"Store local atualizado: {saved} embeddings")

    # 4. Train link predictor (60-95%) — CPU-bound
    # Passes G_train for temporal split and embeddings for Hadamard features
    logger.info("Training link prediction model (temporal split + Node2Vec embeddings)...")
    link_results = await asyncio.to_thread(
        train_link_predictor,
        G,
        LINK_MODEL_PATH,
        G_train=G_train,
        embeddings=embeddings,
        on_progress=make_sub_progress(60, 95),
    )
    results["link_prediction"] = link_results

    progress(95, "Finalizando pipeline...")
    logger.info("ML training pipeline complete")
    return results
