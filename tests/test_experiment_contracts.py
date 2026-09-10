import json

import pytest

from longmem.config import config_path
from longmem.experiment_contracts import (
    canonical_condition,
    canonical_event_order,
    canonical_modality,
    canonical_target,
    metric_key,
)
from longmem.experiment_io import append_jsonl, read_json, read_jsonl, source_hashes, write_json


def test_config_precedence(monkeypatch, tmp_path):
    environment = tmp_path / "environment.yaml"
    explicit = tmp_path / "explicit.yaml"
    monkeypatch.setenv("LONGMEM_CONFIG", str(environment))
    assert config_path() == environment.resolve()
    assert config_path(explicit) == explicit.resolve()


def test_v01_names_have_unambiguous_canonical_adapters():
    assert canonical_target({"target": "fact-1"}) == {
        "target_memory_id": "fact-1",
        "target_canonical_id": "fact-1",
    }
    assert canonical_event_order({"timestamp": 0.25}) == 0.25
    assert canonical_condition("consolidated") == "consolidation_strip_temporal_cue"
    assert canonical_condition("merged_keep_current") == "consolidation_keep_temporal_cue"
    assert canonical_modality("pdf") == "native_text"
    assert canonical_modality("ocr") == "ocr_text"
    assert metric_key("retrieval", "recall", k=5) == "retrieval.recall_at_5"


def test_contracts_reject_ambiguous_values():
    with pytest.raises(ValueError):
        canonical_target({})
    with pytest.raises(ValueError):
        canonical_event_order({"timestamp": "2026-09-05T00:00:00+00:00"})
    with pytest.raises(ValueError):
        canonical_modality("pdf_file")
    with pytest.raises(ValueError):
        metric_key("retrieval", "recall", k=0)


def test_shared_experiment_io_is_deterministic_and_strict(tmp_path):
    document = tmp_path / "nested" / "record.json"
    write_json(document, {"text": "知识", "value": 1})
    assert document.read_bytes().endswith(b"\n")
    assert read_json(document) == {"text": "知识", "value": 1}

    stream = tmp_path / "records.jsonl"
    append_jsonl(stream, {"id": 1})
    append_jsonl(stream, {"id": 2})
    assert read_jsonl(stream) == [{"id": 1}, {"id": 2}]
    stream.write_text(stream.read_text() + "\n")
    with pytest.raises(ValueError, match="Blank JSONL"):
        read_jsonl(stream)


def test_source_hash_keys_are_project_relative_and_unique(tmp_path):
    source = tmp_path / "a" / "same.py"
    source.parent.mkdir()
    source.write_text("value = 1\n")
    hashes = source_hashes([source], root=tmp_path)
    assert list(hashes) == ["a/same.py"]
    assert len(hashes["a/same.py"]) == 64
