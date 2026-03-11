"""Local vector store for member similarity search using numpy cosine similarity."""

import json
import logging
from pathlib import Path
from typing import Any

import numpy as np

logger = logging.getLogger(__name__)

_DEFAULT_NPZ = Path("data/models/embeddings.npz")
_DEFAULT_META = Path("data/models/embeddings_metadata.json")


class LocalVectorStore:
    """Disk-backed vector store with in-memory cosine similarity via numpy."""

    def __init__(
        self,
        embeddings_path: Path = _DEFAULT_NPZ,
        metadata_path: Path = _DEFAULT_META,
    ) -> None:
        self._embeddings_path = embeddings_path
        self._metadata_path = metadata_path
        self._ids: list[str] = []
        self._id_to_idx: dict[str, int] = {}
        self._matrix: np.ndarray | None = None
        self._metadata: dict[str, dict[str, Any]] = {}
        self._loaded = False

    def save(
        self,
        embeddings: dict[str, np.ndarray],
        metadata: dict[str, dict[str, Any]] | None = None,
    ) -> int:
        """Persist embeddings and metadata to disk."""
        self._embeddings_path.parent.mkdir(parents=True, exist_ok=True)

        ids = list(embeddings.keys())
        matrix = np.array([embeddings[id_] for id_ in ids], dtype=np.float32)
        np.savez_compressed(self._embeddings_path, ids=ids, matrix=matrix)

        with open(self._metadata_path, "w", encoding="utf-8") as f:
            json.dump(metadata or {}, f, ensure_ascii=False)

        logger.info("Saved %d embeddings to %s", len(ids), self._embeddings_path)
        self._loaded = False  # Invalidate in-memory cache
        return len(ids)

    def _load(self) -> bool:
        """Load embeddings and metadata from disk into memory."""
        if not self._embeddings_path.exists():
            logger.warning("No embeddings file at %s", self._embeddings_path)
            return False

        data = np.load(self._embeddings_path, allow_pickle=True)
        self._ids = data["ids"].tolist()
        self._id_to_idx = {id_: i for i, id_ in enumerate(self._ids)}
        self._matrix = data["matrix"].astype(np.float32)

        if self._metadata_path.exists():
            with open(self._metadata_path, encoding="utf-8") as f:
                self._metadata = json.load(f)

        self._loaded = True
        logger.info("Loaded %d embeddings from %s", len(self._ids), self._embeddings_path)
        return True

    def find_similar(self, node_id: str, top_k: int = 10) -> list[dict[str, Any]]:
        """Return top_k most similar members by cosine similarity."""
        if not self._loaded and not self._load():
            return []

        if node_id not in self._id_to_idx:
            logger.warning("Node %s not found in local vector store", node_id)
            return []

        matrix = self._matrix  # (N, D)
        idx = self._id_to_idx[node_id]
        query = matrix[idx]  # (D,)

        norms = np.linalg.norm(matrix, axis=1)  # (N,)
        query_norm = float(np.linalg.norm(query))
        if query_norm == 0.0:
            return []

        with np.errstate(divide="ignore", invalid="ignore"):
            sims = (matrix @ query) / (norms * query_norm)
            sims = np.nan_to_num(sims)

        order = np.argsort(sims)[::-1]
        results: list[dict[str, Any]] = []
        for i in order:
            candidate_id = self._ids[i]
            if candidate_id == node_id:
                continue
            results.append({
                "id": candidate_id,
                "score": round(float(sims[i]), 4),
                "metadata": self._metadata.get(candidate_id, {}),
            })
            if len(results) >= top_k:
                break

        return results

    def is_ready(self) -> bool:
        """Check whether embeddings exist on disk."""
        return self._embeddings_path.exists()
