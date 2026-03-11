"""Link prediction using graph features and machine learning."""

import logging
from typing import Any

import networkx as nx

import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import StratifiedKFold, cross_val_score
from sklearn.metrics import (
    roc_auc_score,
    precision_score,
    recall_score,
    f1_score,
    average_precision_score,
)
import joblib
from pathlib import Path

logger = logging.getLogger(__name__)


def _hadamard_features(
    embeddings: dict[str, np.ndarray],
    pairs: list[tuple[str, str]],
) -> np.ndarray:
    """Compute Hadamard product (element-wise) of embedding pairs.

    For each (u, v), returns e_u ⊙ e_v as a 128-d feature vector.
    Pairs without embeddings get zero vectors (Grover & Leskovec 2016).
    """
    emb_dim = next(iter(embeddings.values())).shape[0]
    result = np.zeros((len(pairs), emb_dim), dtype=np.float64)
    for i, (u, v) in enumerate(pairs):
        eu = embeddings.get(str(u))
        ev = embeddings.get(str(v))
        if eu is not None and ev is not None:
            result[i] = eu * ev
    return result


def _batch_link_features(
    G: nx.Graph,
    pairs: list[tuple[str, str]],
    embeddings: dict[str, np.ndarray] | None = None,
    on_progress: Any = None,
) -> np.ndarray:
    """Compute link features for all pairs in batch.

    Returns an [n_pairs × n_features] array.
    If embeddings are provided, features = [5 topological | 128 Hadamard].
    Otherwise, returns only the 5 topological features.

    Calls each NetworkX predictor once with the full pair list to avoid
    repeated graph lookups — significantly faster than per-pair iteration.
    """
    total = len(pairs)

    # Batch-compute all 4 NetworkX link predictors at once
    jaccard = {(u, v): p for u, v, p in nx.jaccard_coefficient(G, pairs)}
    if on_progress:
        on_progress(20, f"Features: jaccard done ({total} pares)")

    adamic = {(u, v): p for u, v, p in nx.adamic_adar_index(G, pairs)}
    if on_progress:
        on_progress(40, f"Features: adamic-adar done ({total} pares)")

    pref = {(u, v): p for u, v, p in nx.preferential_attachment(G, pairs)}
    if on_progress:
        on_progress(60, f"Features: pref. attachment done ({total} pares)")

    resource = {(u, v): p for u, v, p in nx.resource_allocation_index(G, pairs)}
    if on_progress:
        on_progress(80, f"Features: resource alloc done ({total} pares)")

    topo = np.empty((total, 5), dtype=np.float64)
    for i, (u, v) in enumerate(pairs):
        topo[i, 0] = jaccard.get((u, v), 0.0)
        topo[i, 1] = adamic.get((u, v), 0.0)
        topo[i, 2] = pref.get((u, v), 0.0)
        topo[i, 3] = resource.get((u, v), 0.0)
        topo[i, 4] = len(list(nx.common_neighbors(G, u, v)))

    if on_progress:
        on_progress(100, f"Features: {total} pares completos")

    if embeddings:
        hadamard = _hadamard_features(embeddings, pairs)
        return np.hstack([topo, hadamard])

    return topo


def generate_training_data(
    G: nx.Graph,
    negative_ratio: float = 1.0,
    seed: int = 42,
    embeddings: dict[str, np.ndarray] | None = None,
    on_progress: Any = None,
) -> tuple[np.ndarray, np.ndarray]:
    """Generate positive and negative edge samples for training."""
    rng = np.random.default_rng(seed)
    nodes = list(G.nodes())

    positive_pairs = list(G.edges())
    num_negative = int(len(positive_pairs) * negative_ratio)
    negative_pairs: list[tuple[str, str]] = []
    attempts = 0
    max_attempts = num_negative * 10

    while len(negative_pairs) < num_negative and attempts < max_attempts:
        u = rng.choice(nodes)
        v = rng.choice(nodes)
        if u != v and not G.has_edge(u, v):
            negative_pairs.append((u, v))
        attempts += 1

    logger.info(
        "Generated %d positive and %d negative samples",
        len(positive_pairs), len(negative_pairs),
    )

    all_pairs = positive_pairs + negative_pairs
    labels = np.array([1] * len(positive_pairs) + [0] * len(negative_pairs))
    features = _batch_link_features(G, all_pairs, embeddings=embeddings, on_progress=on_progress)
    return features, labels


def _compute_heuristic_baselines(
    X_test: np.ndarray, y_test: np.ndarray
) -> dict[str, float | None]:
    """Compute AUC-ROC for each topological heuristic individually.

    Provides a baseline to verify that the RF model adds value over
    individual features (Lü & Zhou 2011). Uses only the first 5 columns
    (topological features), which are always present regardless of embeddings.
    """
    names = [
        "jaccard", "adamic_adar", "preferential_attachment",
        "resource_allocation", "common_neighbors",
    ]
    baselines: dict[str, float | None] = {}
    for idx, name in enumerate(names):
        if idx >= X_test.shape[1]:
            break
        col = X_test[:, idx]
        if len(np.unique(col)) > 1:
            try:
                baselines[name] = round(float(roc_auc_score(y_test, col)), 4)
            except Exception:
                baselines[name] = None
        else:
            baselines[name] = None
    return baselines


def train_link_predictor(
    G: nx.Graph,
    model_path: Path | None = None,
    G_train: nx.Graph | None = None,
    embeddings: dict[str, np.ndarray] | None = None,
    on_progress: Any = None,
) -> dict[str, Any]:
    """Train a Random Forest link prediction model.

    Args:
        G: Full graph (all years). Used for final cross-validation and
           generating test-set negatives when doing temporal split.
        model_path: Where to save the trained model.
        G_train: Optional training graph (e.g. years ≤ 2023). When provided,
                 uses temporal train/test split instead of random split,
                 eliminating data leakage from future edges. Features for the
                 test set are computed on G_train to prevent leakage.
        embeddings: Optional Node2Vec embeddings. When provided, Hadamard
                    products are concatenated with topological features,
                    producing a hybrid [5 + 128] feature vector.
        on_progress: Optional callback(pct, msg) for progress reporting.
    """
    def progress(pct: float, msg: str) -> None:
        if on_progress:
            on_progress(pct, msg)

    def feature_progress(pct: float, msg: str) -> None:
        progress(pct * 0.4, msg)

    feature_graph = G_train if G_train is not None else G
    using_temporal_split = G_train is not None

    progress(0, "Gerando dados de treino...")
    logger.info("Generating training data (graph: %s)...", "temporal" if using_temporal_split else "full")
    X_train, y_train = generate_training_data(
        feature_graph, embeddings=embeddings, on_progress=feature_progress
    )

    if len(X_train) == 0:
        logger.warning("No training data generated")
        return {"status": "no_data"}

    # Build test set
    if using_temporal_split:
        progress(40, "Construindo test set temporal (arestas novas em G_full)...")
        test_positives = [
            (u, v) for u, v in G.edges()
            if not feature_graph.has_edge(u, v)
        ]

        if not test_positives:
            logger.warning(
                "No new edges found between G_train and G_full; falling back to random split"
            )
            using_temporal_split = False

    if not using_temporal_split:
        # Fallback: random 20% split from full graph (data leakage risk)
        logger.warning("Using random train/test split — temporal data leakage possible")
        X_all, y_all = generate_training_data(G, embeddings=embeddings)
        n_test = int(len(X_all) * 0.2)
        rng = np.random.default_rng(42)
        idx = rng.permutation(len(X_all))
        X_train, X_test = X_all[idx[n_test:]], X_all[idx[:n_test]]
        y_train, y_test = y_all[idx[n_test:]], y_all[idx[:n_test]]
        split_type = "random"
    else:
        # Temporal split: test negatives sampled from full graph node space
        rng = np.random.default_rng(42)
        nodes = list(G.nodes())
        test_negatives: list[tuple[str, str]] = []
        attempts = 0
        while len(test_negatives) < len(test_positives) and attempts < len(test_positives) * 20:
            u = str(rng.choice(nodes))
            v = str(rng.choice(nodes))
            if u != v and not G.has_edge(u, v):
                test_negatives.append((u, v))
            attempts += 1

        test_pairs = test_positives + test_negatives
        y_test = np.array([1] * len(test_positives) + [0] * len(test_negatives))
        # Features computed on G_train to avoid data leakage from future edges
        X_test = _batch_link_features(feature_graph, test_pairs, embeddings=embeddings)
        split_type = "temporal"
        logger.info(
            "Temporal split: %d train edges, %d test positives (new in 2024), %d test negatives",
            feature_graph.number_of_edges(), len(test_positives), len(test_negatives),
        )

    progress(50, f"Treinando Random Forest ({len(X_train)} amostras, split={split_type})...")
    logger.info("Training Random Forest classifier (%s split)...", split_type)

    n_features = X_train.shape[1]

    clf = RandomForestClassifier(
        n_estimators=100,
        max_depth=10,
        random_state=42,
        n_jobs=-1,
    )
    clf.fit(X_train, y_train)

    progress(80, "Avaliando modelo (metricas completas)...")
    y_pred_proba = clf.predict_proba(X_test)[:, 1]
    y_pred = clf.predict(X_test)
    auc_roc = roc_auc_score(y_test, y_pred_proba)
    precision = precision_score(y_test, y_pred)
    recall = recall_score(y_test, y_pred)
    f1 = f1_score(y_test, y_pred)
    avg_precision = average_precision_score(y_test, y_pred_proba)
    logger.info(
        "Link prediction [%s] — AUC-ROC: %.4f, Precision: %.4f, Recall: %.4f, "
        "F1: %.4f, AUPRC: %.4f",
        split_type, auc_roc, precision, recall, f1, avg_precision,
    )

    # Individual heuristic baselines for comparison (Lü & Zhou 2011)
    heuristic_baselines = _compute_heuristic_baselines(X_test, y_test)
    logger.info("Individual heuristic AUC-ROC baselines: %s", heuristic_baselines)

    # 5-fold stratified cross-validation on the training data
    progress(90, "Cross-validation (5-fold)...")
    cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
    cv_scores = cross_val_score(clf, X_train, y_train, cv=cv, scoring="roc_auc", n_jobs=-1)
    cv_auc_mean = float(np.mean(cv_scores))
    cv_auc_std = float(np.std(cv_scores))
    logger.info("CV AUC-ROC: %.4f +/- %.4f", cv_auc_mean, cv_auc_std)

    if model_path:
        model_path.parent.mkdir(parents=True, exist_ok=True)
        joblib.dump(clf, model_path)
        logger.info("Saved model to %s", model_path)

    # Compute feature importances only for the first 5 topological features
    topo_importances = clf.feature_importances_[:5].tolist()
    topo_names = ["jaccard", "adamic_adar", "preferential_attachment", "resource_allocation", "common_neighbors"]

    progress(100, f"[{split_type}] AUC-ROC: {auc_roc:.4f} | CV: {cv_auc_mean:.4f}±{cv_auc_std:.4f}")
    return {
        "split_type": split_type,
        "auc_roc": round(auc_roc, 4),
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "f1": round(f1, 4),
        "average_precision": round(avg_precision, 4),
        "cv_auc_mean": round(cv_auc_mean, 4),
        "cv_auc_std": round(cv_auc_std, 4),
        "feature_importances": dict(zip(topo_names, topo_importances)),
        "heuristic_baselines": heuristic_baselines,
        "train_samples": len(X_train),
        "test_samples": len(X_test),
        "n_features": n_features,
        "using_embeddings": embeddings is not None,
    }


def predict_new_links(
    G: nx.Graph,
    model_path: Path,
    top_k: int = 50,
    embeddings: dict[str, np.ndarray] | None = None,
) -> list[dict[str, Any]]:
    """Predict most likely new connections using the trained model."""
    clf = joblib.load(model_path)
    nodes = list(G.nodes())

    rng = np.random.default_rng(42)
    candidates_set: set[tuple[str, str]] = set()
    candidates: list[tuple[str, str]] = []

    for _ in range(min(len(nodes) * 5, 10000)):
        u = rng.choice(nodes)
        v = rng.choice(nodes)
        pair = (min(u, v), max(u, v))
        if u != v and not G.has_edge(u, v) and pair not in candidates_set:
            candidates_set.add(pair)
            candidates.append((u, v))

    if not candidates:
        return []

    features = _batch_link_features(G, candidates, embeddings=embeddings)

    # Handle feature dimension mismatch (model trained with/without embeddings)
    expected_features = clf.n_features_in_
    if features.shape[1] != expected_features:
        if features.shape[1] > expected_features:
            features = features[:, :expected_features]
        else:
            pad = np.zeros((features.shape[0], expected_features - features.shape[1]))
            features = np.hstack([features, pad])

    probas = clf.predict_proba(features)[:, 1]

    predictions = []
    for (u, v), prob in zip(candidates, probas):
        predictions.append({
            "source": u,
            "target": v,
            "probability": round(float(prob), 4),
        })

    predictions.sort(key=lambda x: x["probability"], reverse=True)
    return predictions[:top_k]
