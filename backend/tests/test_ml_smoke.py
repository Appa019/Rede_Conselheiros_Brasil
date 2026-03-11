"""Smoke tests for ML training pipeline."""

import pytest

from app.ml.embeddings import generate_embeddings
from app.ml.link_prediction import train_link_predictor
from app.ml.train import run_training_pipeline


pytestmark = pytest.mark.smoke


async def test_generate_embeddings(networkx_graph):
    embeddings = generate_embeddings(networkx_graph)
    assert isinstance(embeddings, dict)
    assert len(embeddings) > 0
    first_key = next(iter(embeddings))
    assert len(embeddings[first_key]) == 128


async def test_train_link_predictor(networkx_graph):
    result = train_link_predictor(networkx_graph)
    assert "auc_roc" in result
    assert result["auc_roc"] > 0.5


@pytest.mark.slow
async def test_full_pipeline(neo4j_client):
    result = await run_training_pipeline(neo4j_client)
    assert "embeddings" in result
    assert "link_prediction" in result
