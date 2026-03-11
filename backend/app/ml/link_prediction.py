"""Link prediction using graph features and machine learning."""

import logging
from typing import Any

import networkx as nx

import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split, StratifiedKFold, cross_val_score
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


def _batch_link_features(
    G: nx.Graph, pairs: list[tuple[str, str]], on_progress: Any = None,
) -> np.ndarray:
    """Compute link features for all pairs in batch using NetworkX generators.

    Calls each predictor once with the full pair list instead of once per pair,
    which avoids repeated graph lookups and is significantly faster.
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

    # Common neighbors — must iterate (no batch API)
    features = np.empty((total, 5), dtype=np.float64)
    for i, (u, v) in enumerate(pairs):
        features[i, 0] = jaccard.get((u, v), 0.0)
        features[i, 1] = adamic.get((u, v), 0.0)
        features[i, 2] = pref.get((u, v), 0.0)
        features[i, 3] = resource.get((u, v), 0.0)
        features[i, 4] = len(list(nx.common_neighbors(G, u, v)))

    if on_progress:
        on_progress(100, f"Features: {total} pares completos")

    return features


def generate_training_data(
    G: nx.Graph,
    negative_ratio: float = 1.0,
    seed: int = 42,
    on_progress: Any = None,
) -> tuple[np.ndarray, np.ndarray]:
    """Generate positive and negative edge samples for training."""
    rng = np.random.default_rng(seed)
    nodes = list(G.nodes())

    # Positive samples (existing edges)
    positive_pairs = list(G.edges())

    # Negative samples (non-existing edges)
    num_negative = int(len(positive_pairs) * negative_ratio)
    negative_pairs = []
    attempts = 0
    max_attempts = num_negative * 10

    while len(negative_pairs) < num_negative and attempts < max_attempts:
        u = rng.choice(nodes)
        v = rng.choice(nodes)
        if u != v and not G.has_edge(u, v):
            negative_pairs.append((u, v))
        attempts += 1

    logger.info(
        f"Generated {len(positive_pairs)} positive and "
        f"{len(negative_pairs)} negative samples"
    )

    all_pairs = positive_pairs + negative_pairs
    labels = np.array([1] * len(positive_pairs) + [0] * len(negative_pairs))

    features = _batch_link_features(G, all_pairs, on_progress=on_progress)

    return features, labels


def train_link_predictor(
    G: nx.Graph,
    model_path: Path | None = None,
    on_progress: Any = None,
) -> dict[str, Any]:
    """Train a Random Forest link prediction model."""
    def progress(pct: float, msg: str) -> None:
        if on_progress:
            on_progress(pct, msg)

    def feature_progress(pct: float, msg: str) -> None:
        # Feature computation maps to 0-40% of link predictor
        progress(pct * 0.4, msg)

    progress(0, "Gerando dados de treino (amostras + features)...")
    logger.info("Generating training data...")
    X, y = generate_training_data(G, on_progress=feature_progress)

    if len(X) == 0:
        logger.warning("No training data generated")
        return {"status": "no_data"}

    progress(40, "Dividindo train/test...")
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )

    progress(50, f"Treinando Random Forest ({len(X_train)} amostras)...")
    logger.info("Training Random Forest classifier...")
    clf = RandomForestClassifier(
        n_estimators=100,
        max_depth=10,
        random_state=42,
        n_jobs=-1,
    )
    clf.fit(X_train, y_train)

    progress(80, "Avaliando modelo (metricas completas)...")
    # Evaluate
    y_pred_proba = clf.predict_proba(X_test)[:, 1]
    y_pred = clf.predict(X_test)
    auc_roc = roc_auc_score(y_test, y_pred_proba)
    precision = precision_score(y_test, y_pred)
    recall = recall_score(y_test, y_pred)
    f1 = f1_score(y_test, y_pred)
    avg_precision = average_precision_score(y_test, y_pred_proba)
    logger.info(
        f"Link prediction — AUC-ROC: {auc_roc:.4f}, "
        f"Precision: {precision:.4f}, Recall: {recall:.4f}, F1: {f1:.4f}, "
        f"AUPRC: {avg_precision:.4f}"
    )

    # 5-fold stratified cross-validation
    progress(90, "Cross-validation (5-fold)...")
    cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
    cv_scores = cross_val_score(clf, X, y, cv=cv, scoring="roc_auc", n_jobs=-1)
    cv_auc_mean = float(np.mean(cv_scores))
    cv_auc_std = float(np.std(cv_scores))
    logger.info(f"CV AUC-ROC: {cv_auc_mean:.4f} +/- {cv_auc_std:.4f}")

    # Save model
    if model_path:
        model_path.parent.mkdir(parents=True, exist_ok=True)
        joblib.dump(clf, model_path)
        logger.info(f"Saved model to {model_path}")

    feature_names = [
        "jaccard", "adamic_adar", "preferential_attachment",
        "resource_allocation", "common_neighbors"
    ]

    progress(100, f"AUC-ROC: {auc_roc:.4f} | CV: {cv_auc_mean:.4f}±{cv_auc_std:.4f}")
    return {
        "auc_roc": round(auc_roc, 4),
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "f1": round(f1, 4),
        "average_precision": round(avg_precision, 4),
        "cv_auc_mean": round(cv_auc_mean, 4),
        "cv_auc_std": round(cv_auc_std, 4),
        "feature_importances": dict(zip(feature_names, clf.feature_importances_.tolist())),
        "train_samples": len(X_train),
        "test_samples": len(X_test),
    }


def predict_new_links(
    G: nx.Graph,
    model_path: Path,
    top_k: int = 50,
) -> list[dict[str, Any]]:
    """Predict most likely new connections."""
    clf = joblib.load(model_path)
    nodes = list(G.nodes())

    # Sample non-existing edges for prediction
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

    features = _batch_link_features(G, candidates)
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
