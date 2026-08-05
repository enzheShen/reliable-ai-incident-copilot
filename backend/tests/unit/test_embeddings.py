import json
import os
from pathlib import Path

import pytest

from app.services.embeddings import cosine_similarity, deterministic_embedding, runbook_embedding

DATA_DIR = Path(os.getenv("DATA_DIR", Path(__file__).parents[3] / "data"))


def test_embedding_is_deterministic_and_normalized() -> None:
    first = deterministic_embedding("Redis connection refused")
    second = deterministic_embedding("Redis connection refused")
    assert first == second
    assert len(first) == 384
    assert cosine_similarity(first, first) == pytest.approx(1.0)


def test_fixed_dataset_has_required_cardinality_and_labels() -> None:
    runbooks = json.loads((DATA_DIR / "runbooks/runbooks.json").read_text())
    incidents = json.loads((DATA_DIR / "incidents/synthetic-incidents.json").read_text())
    evaluation_lines = (DATA_DIR / "evaluation/evaluation.jsonl").read_text().splitlines()
    assert len(runbooks) == 12
    assert len(incidents) == 60
    assert len(evaluation_lines) == 60
    assert {item["expected_runbook_id"] for item in incidents} == {item["id"] for item in runbooks}
    vectors = {item["id"]: runbook_embedding(item["title"], item["keywords"]) for item in runbooks}
    for fixture in incidents:
        incident = fixture["incident"]
        query = " ".join(
            [
                incident["symptoms"],
                *incident["logs"],
                *incident["metrics"].keys(),
                *incident["recent_changes"],
            ]
        )
        query_vector = deterministic_embedding(query)
        best = max(
            vectors,
            key=lambda runbook_id: cosine_similarity(query_vector, vectors[runbook_id]),
        )
        assert best == fixture["expected_runbook_id"]
