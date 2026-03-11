"""Pinecone vector store client for member similarity search."""

import logging
from typing import Any

from pinecone import Pinecone
import numpy as np

from app.config import settings

logger = logging.getLogger(__name__)


class PineconeClient:
    """Client for upserting and querying member embeddings in Pinecone."""

    def __init__(self) -> None:
        self._client: Pinecone | None = None
        self._index = None

    def connect(self) -> None:
        """Initialize Pinecone client and get index reference."""
        if not settings.pinecone_api_key:
            logger.warning("Pinecone API key not set, skipping connection")
            return

        self._client = Pinecone(api_key=settings.pinecone_api_key)
        self._index = self._client.Index(settings.pinecone_index_name)
        logger.info(f"Connected to Pinecone index: {settings.pinecone_index_name}")

    def close(self) -> None:
        """Close Pinecone client."""
        self._client = None
        self._index = None

    def upsert_embeddings(
        self,
        embeddings: dict[str, np.ndarray],
        metadata: dict[str, dict[str, Any]] | None = None,
        batch_size: int = 100,
    ) -> int:
        """Upsert embeddings into Pinecone index."""
        if self._index is None:
            logger.warning("Pinecone not connected, skipping upsert")
            return 0

        vectors = []
        for node_id, embedding in embeddings.items():
            meta = metadata.get(node_id, {}) if metadata else {}
            vectors.append({
                "id": node_id,
                "values": embedding.tolist(),
                "metadata": meta,
            })

        total_upserted = 0
        for i in range(0, len(vectors), batch_size):
            batch = vectors[i : i + batch_size]
            self._index.upsert(vectors=batch)
            total_upserted += len(batch)

        logger.info(f"Upserted {total_upserted} vectors to Pinecone")
        return total_upserted

    def find_similar(
        self,
        node_id: str,
        embedding: np.ndarray,
        top_k: int = 10,
        filter_dict: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        """Find similar members by embedding similarity."""
        if self._index is None:
            logger.warning("Pinecone not connected, returning empty results")
            return []

        results = self._index.query(
            vector=embedding.tolist(),
            top_k=top_k + 1,  # +1 to exclude self
            include_metadata=True,
            filter=filter_dict,
        )

        similar = []
        for match in results.matches:
            if match.id != node_id:
                similar.append({
                    "id": match.id,
                    "score": match.score,
                    "metadata": match.metadata or {},
                })

        return similar[:top_k]

    def query_by_vector(
        self,
        vector: list[float],
        top_k: int = 10,
        filter_dict: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        """Query Pinecone by raw vector."""
        if self._index is None:
            return []

        results = self._index.query(
            vector=vector,
            top_k=top_k,
            include_metadata=True,
            filter=filter_dict,
        )

        return [
            {"id": m.id, "score": m.score, "metadata": m.metadata or {}}
            for m in results.matches
        ]
