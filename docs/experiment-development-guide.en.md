# Experiment Naming and Module Development Guide

[简体中文](experiment-development-guide.md)

This guide defines the contracts for the v0.1 foundation and later experiments. v0.1 completed a breaking migration: canonical fields, shared modules, and one runner per experiment are now in place, and the formal results were regenerated. Older formats are local development history rather than supported release interfaces.

## Design principles

1. Give each concept one canonical name.
2. Keep wall-clock timestamps, synthetic event order, and measured duration in separate fields.
3. Use separate namespaces for memory selection, content consolidation, and retrieval modality.
4. Record experiments with a stable schema; reporting code must read that schema rather than infer field meanings.
5. Reuse shared I/O, hashing, runtime metadata, and model configuration instead of reimplementing them in new experiments.
6. Never silently rewrite frozen results after a refactor; use an adapter when older formats must remain readable.

## Canonical fields

### Memories and targets

| Canonical name | Type | Meaning | v0.1 compatibility source |
|---|---|---|---|
| `memory_id` | string | ID of one physical memory record | `memory_id` |
| `canonical_id` | string | ID shared by equivalent facts | `canonical_id` |
| `target_memory_id` | string | Physical record that must be matched exactly | `target`, only when both IDs were identical in old data |
| `target_canonical_id` | string | Equivalent fact accepted by the task | `target` |
| `supersedes_id` | string/null | Physical memory replaced by this record | `supersedes` |

New experiments must not use an ambiguous standalone `target`. Exact-record and equivalent-fact matches must be measured separately.

### Time and order

| Canonical name | Type | Meaning |
|---|---|---|
| `created_at` | ISO 8601 string | Actual memory-write time, including a time-zone offset |
| `event_order` | integer/float | Relative event order in synthetic data |
| `recency_rank` | integer | Recency rank under an explicit rule; 0 is newest |
| `duration_seconds` | float | Duration of one operation or inference |

`canonical_event_order()` can read the floating-point `timestamp` used by older synthetic data. New data must write `event_order`; it must not be passed to the core `Memory.timestamp` field or compared with real wall-clock time.

### Policies and conditions

Retention policies decide which records remain:

```text
full
random
recency
importance
semantic_dedup
utility_aware
oracle_utility
```

Content conditions decide what the generator receives:

```text
no_memory
relevant
irrelevant
conflicting
consolidation_keep_temporal_cue
consolidation_strip_temporal_cue
```

Do not use `merged` to mean deduplication, selection, and summarization at once. `canonical_condition()` maps the v0.1 names `consolidated`, `merged_keep_current`, and `merged_strip_current` to their canonical forms.

### Retrieval modalities

Use:

```text
visual
native_text
ocr_text
```

Do not introduce the ambiguous names `pdf` or `ocr`. `canonical_modality()` maps older results.

### Metrics

Metric keys follow `<namespace>.<metric>`:

```text
retention.target_fact_rate
retention.exact_memory_rate
retrieval.recall_at_1
retrieval.recall_at_5
retrieval.mrr
answer.exact_match
answer.token_f1
answer.hit_but_wrong_rate
cost.index_bytes
cost.retrieval_p50_ms
```

New outputs place metrics inside a `metrics` object. Do not mix names such as `recall1` and `recall_at_1`, or combine flat `exact_match` fields with nested `scores` objects.

## Configuration conventions

Every new runner supports:

```text
--model-config PATH
--output PATH
--backend NAME
--seed N or --seeds N...
```

Configuration precedence is:

```text
explicit command-line argument > LONGMEM_CONFIG > configs/local.yaml
```

Use `longmem.config.load_config()` rather than hard-coding or independently parsing model paths. Public manifests record logical model names, revisions, and file digests—not absolute paths.

Keep backend names scoped by responsibility:

- embedding: `minicpm`, `hash_test`
- generation: `transformers`, `evidence_test`
- experiment execution: `model`, `test`

Configuration files still accept the v0.1 hyphenated values `hash-test` and `evidence-test`; new Python identifiers, enums, and values should use underscores.

## Module boundaries

Recommended structure:

```text
src/longmem/
  config.py                 # single configuration entry point
  experiment_io.py          # JSON/JSONL, hashes, runtime metadata
  experiment_contracts.py   # names, schema version, v0.1 adapters
  embedder.py               # embedding backends
  generation.py             # generation backends

experiments/<experiment>/
  protocol.md               # frozen questions, hypotheses, and metrics
  dataset.py                # data construction only
  policies.py               # selection/consolidation policies only
  run.py                    # orchestration, not generic I/O
  evaluate.py               # scoring against the result schema
  report.py                 # tables and figures only
  configs/
  results/
```

`run.py` must not dynamically import a same-named script from another stage or modify an imported module's global search path. Cross-stage reuse belongs in `src/longmem` or a uniquely named package.

## Shared I/O

New experiments use [experiment_io.py](../src/longmem/experiment_io.py):

```python
from longmem.experiment_io import (
    append_jsonl,
    read_jsonl,
    runtime_metadata,
    source_hashes,
    write_json,
)
```

- JSON is UTF-8, rejects NaN, uses stable indentation, and ends with a newline.
- Manifests and aggregate files use atomic replacement.
- Every JSONL line must be an object; blank or corrupted lines fail explicitly.
- Source-hash keys use repository-relative paths to avoid collisions and machine-local path disclosure.
- Long inference jobs append one JSONL record at a time so interrupted runs remain auditable.

## Minimum manifest fields

```json
{
  "schema_version": "longmem-experiment-v1",
  "experiment_id": "utility-retention-v0.2",
  "status": "RUNNING",
  "protocol_sha256": "...",
  "dataset_sha256": "...",
  "source_hashes": {},
  "model": {
    "name": "MiniCPM-2B-SFT",
    "revision": "...",
    "metadata_sha256": {}
  },
  "runtime": {},
  "parameters": {}
}
```

Write `RUNNING` when execution begins and atomically update it to `COMPLETE` only after all outputs pass validation. A resumed run must compare protocol, dataset, source, model, and parameter identities.

## v0.1 migration status

- Stage 2 uses `event_order`, explicit target IDs, and nested query/prediction structures; the old runner was removed.
- Stage 3 main and control experiments share canonical answers, scoring, and retrieval fields; the formal main run and frozen controls were regenerated.
- Stage 4 uses a separate page-data module and the names `visual`, `native_text`, and `ocr_text`; the old dynamic-import runner was removed and the experiment rerun.
- `experiment_contracts.py` retains a small set of old-format adapters for reading local history only. New artifacts must not write legacy fields.

Any change to a formal runner must write to a new output directory and rerun the corresponding validation. An old report must never silently point to changed source code.

## New-experiment checklist

- [ ] Freeze the protocol before execution.
- [ ] Do not use a bare `target` or floating-point `timestamp`.
- [ ] Use canonical policy, condition, and modality names.
- [ ] Put metrics in a namespaced `metrics` object.
- [ ] Support the shared configuration entry point; do not hard-code machine-local paths.
- [ ] Use shared experiment I/O and repository-relative source hashes.
- [ ] Label test backends explicitly; they cannot support model-quality claims.
- [ ] Never overwrite an existing run directory.
- [ ] Complete validation before changing the manifest from `RUNNING` to `COMPLETE`.
- [ ] State dataset, model, hardware, and statistical boundaries in the report.
