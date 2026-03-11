"""ML training orchestrator."""

import logging
from pathlib import Path
from typing import Any

from app.graph.neo4j_client import Neo4jClient
from app.graph.metrics import build_networkx_graph
from app.ml.embeddings import generate_embeddings, save_embeddings
from app.ml.pinecone_client import PineconeClient
from app.ml.link_prediction import train_link_predictor

logger = logging.getLogger(__name__)

MODEL_DIR = Path("data/models")
EMBEDDINGS_PATH = MODEL_DIR / "embeddings.npz"
LINK_MODEL_PATH = MODEL_DIR / "link_predictor.joblib"


async def run_training_pipeline(
    client: Neo4jClient,
    skip_pinecone: bool = False,
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

    # 1. Build graph (0-10%)
    progress(2, "Construindo grafo a partir do Neo4j...")
    logger.info("Building NetworkX graph from Neo4j...")
    G = await build_networkx_graph(client)

    if G.number_of_nodes() == 0:
        logger.warning("Empty graph, skipping ML pipeline")
        return {"status": "empty_graph"}

    progress(10, f"Grafo construido: {G.number_of_nodes()} nodes, {G.number_of_edges()} edges")

    # 2. Generate embeddings (10-55%) — CPU-bound
    logger.info("Generating Node2Vec embeddings...")
    embeddings = await asyncio.to_thread(
        generate_embeddings, G, on_progress=make_sub_progress(10, 55)
    )
    save_embeddings(embeddings, EMBEDDINGS_PATH)
    results["embeddings"] = {"count": len(embeddings), "path": str(EMBEDDINGS_PATH)}

    # 3. Upload to Pinecone (55-60%)
    if not skip_pinecone:
        progress(55, "Enviando embeddings para Pinecone...")
        logger.info("Uploading embeddings to Pinecone...")
        pc = PineconeClient()
        pc.connect()

        # Build metadata from Neo4j
        meta_query = """
        MATCH (p:Person)
        OPTIONAL MATCH (p)-[:MEMBER_OF]->(c:Company)
        WITH p, collect(c.nome)[..5] AS companies
        RETURN p.id AS id, p.nome AS nome, p.community_id AS community_id,
               p.page_rank AS page_rank, companies
        """
        records = await client.execute_read(meta_query)
        metadata = {}
        for r in records:
            metadata[r["id"]] = {
                "nome": r["nome"] or "",
                "community_id": r["community_id"] or 0,
                "page_rank": r["page_rank"] or 0,
                "companies": ", ".join(r["companies"][:3]) if r["companies"] else "",
            }

        upserted = pc.upsert_embeddings(embeddings, metadata)
        pc.close()
        results["pinecone"] = {"upserted": upserted}

    # 4. Train link predictor (55-95%) — CPU-bound
    logger.info("Training link prediction model...")
    link_results = await asyncio.to_thread(
        train_link_predictor, G, LINK_MODEL_PATH,
        on_progress=make_sub_progress(55, 95),
    )
    results["link_prediction"] = link_results

    progress(95, "Finalizando pipeline...")
    logger.info("ML training pipeline complete")
    return results
