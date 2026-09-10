import sys
from pathlib import Path

import numpy as np
import pytest

HERE = Path(__file__).parents[1] / "experiments/memory-budget"
sys.path.insert(0, str(HERE))

from benchmark_v2 import ranking_metrics, semantic_order
from generate_dataset import generate


def test_dataset_nested_scenarios_and_answer_equivalence():
    small, queries = generate(100, 11, "old")
    large, repeated = generate(500, 11, "balanced")
    assert [record["content"] for record in small] == [record["content"] for record in large[:100]]
    assert queries == repeated
    records = {record["memory_id"]: record for record in small}
    assert all(records[q["target_memory_id"]]["canonical_id"] == q["target_canonical_id"] for q in queries)
    assert len({q["family"] for q in queries if q["split"] == "test"}) == 18
    assert {q["family"] for q in queries if q["split"] == "test"}.isdisjoint(
        q["family"] for q in queries if q["split"] == "dev"
    )
    assert all(
        records[record["supersedes_id"]]["event_order"] < record["event_order"]
        for record in small
        if record["supersedes_id"]
    )
    ages = [record["event_order"] for record in large if record["memory_id"].startswith("current")]
    assert min(ages) < 0.1 and max(ages) > 0.9
    assert records["duplicate-0"]["canonical_id"] == "current-0"


def test_semantic_budget_backfill_and_equivalent_mrr():
    records = [
        {"memory_id": "old", "canonical_id": "old", "event_order": 0},
        {"memory_id": "new", "canonical_id": "new", "event_order": 1},
        {"memory_id": "copy", "canonical_id": "new", "event_order": 2},
    ]
    vectors = np.array([[0.0, 1.0], [1.0, 0.0], [1.0, 0.0]], dtype=np.float32)
    order, representatives = semantic_order(records, vectors, 0.95)
    assert order == [2, 0, 1] and representatives == 2
    result = ranking_metrics(
        records,
        [2, 0],
        np.array([[0, 1]]),
        [{"target_memory_id": "new", "target_canonical_id": "new", "superseded_memory_id": "old"}],
    )
    assert result["recall_at_1"] == 1
    assert result["exact_recall_at_1"] == 0
    assert result["mrr"] == 1
    assert result["target_fact_retained"] == 1


def test_mrr_is_not_truncated_and_superseded_fact_is_not_equivalent():
    records = [{"memory_id": f"m{i}", "canonical_id": f"m{i}"} for i in range(7)]
    result = ranking_metrics(
        records,
        list(range(7)),
        np.array([list(range(7))]),
        [{"target_memory_id": "m6", "target_canonical_id": "m6", "superseded_memory_id": "m0"}],
    )
    assert result["recall_at_5"] == 0
    assert result["mrr"] == pytest.approx(1 / 7)
    assert result["target_fact_retained"] == 1
    assert result["superseded_fact_at_1"] == 1


def test_missing_target_stays_in_denominator():
    records = [{"memory_id": "old", "canonical_id": "old"}]
    result = ranking_metrics(
        records,
        [0],
        np.array([[0], [0]]),
        [
            {"target_memory_id": "new", "target_canonical_id": "new", "superseded_memory_id": "old"},
            {"target_memory_id": "old", "target_canonical_id": "old", "superseded_memory_id": "previous"},
        ],
    )
    assert result["recall_at_5"] == 0.5
    assert result["target_fact_retained"] == 0.5
