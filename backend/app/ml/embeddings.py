"""Node2Vec embedding generation for the board member network."""

import logging
from pathlib import Path
from typing import Any

import numpy as np
import networkx as nx
from node2vec import Node2Vec

logger = logging.getLogger(__name__)

EMBEDDING_DIM = 128


def generate_embeddings(
    G: nx.Graph,
    dimensions: int = EMBEDDING_DIM,
    walk_length: int = 20,
    num_walks: int = 80,
    p: float = 1.0,
    q: float = 1.0,
    workers: int = 8,
    on_progress: Any = None,
) -> dict[str, np.ndarray]:
    """Generate Node2Vec embeddings for all nodes in the graph."""
    def progress(pct: float, msg: str) -> None:
        if on_progress:
            on_progress(pct, msg)

    if G.number_of_nodes() == 0:
        logger.warning("Empty graph, skipping embedding generation")
        return {}

    logger.info(
        f"Generating Node2Vec embeddings: {G.number_of_nodes()} nodes, "
        f"dim={dimensions}, walks={num_walks}, length={walk_length}"
    )

    progress(0, f"Preparando random walks ({G.number_of_nodes()} nodes)...")
    node2vec = Node2Vec(
        G,
        dimensions=dimensions,
        walk_length=walk_length,
        num_walks=num_walks,
        p=p,
        q=q,
        workers=workers,
        quiet=True,
    )

    progress(40, "Treinando Word2Vec nos random walks...")
    model = node2vec.fit(window=10, min_count=1, batch_words=4)

    progress(85, "Extraindo vetores de embedding...")
    embeddings = {}
    for node in G.nodes():
        try:
            embeddings[str(node)] = model.wv[str(node)]
        except KeyError:
            logger.warning(f"No embedding for node {node}")

    progress(100, f"{len(embeddings)} embeddings gerados")
    logger.info(f"Generated {len(embeddings)} embeddings")
    return embeddings


def save_embeddings(embeddings: dict[str, np.ndarray], output_path: Path) -> None:
    """Save embeddings to a numpy file."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    np.savez(str(output_path), **embeddings)
    logger.info(f"Saved embeddings to {output_path}")


def load_embeddings(input_path: Path) -> dict[str, np.ndarray]:
    """Load embeddings from a numpy file."""
    data = np.load(str(input_path))
    return {key: data[key] for key in data.files}
