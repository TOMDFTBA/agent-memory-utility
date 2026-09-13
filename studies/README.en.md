# Knowledge-to-memory studies

English | [简体中文](README.md)

DeepNote closes v0.1 after its four stages; PilotDeck closes v0.2 after E1–E4. Both studies use pinned upstream revisions, source evidence, and scoped checks. They are not additional numbered experiments and do not use the retention candidate namespace.

| Study | Version placement | Completed evidence | Not executed |
|---|---|---|---|
| [DeepNote](deepnote/README.en.md) | v0.1 closing study: evidence organization between retrieval and utilization | Source review and two stub control-flow probes | Real note generation, adaptive retrieval, or training |
| [PilotDeck](pilotdeck-memory/README.en.md) | v0.2 closing study: set dependence and memory pipelines | Source review, four upstream pure-function probes, and four existing E4 case mappings | Model extraction, Dream, full platform, or budget baseline |

## Naming and reuse

- `longmem-study-v1` describes study manifests; `study_id` identifies the study and `probe_id` identifies a check. These are not formal `longmem-experiment-v1` results.
- `representation` and `transformation` are proposed fields for future protocols, not additions to frozen contracts.
- `memory_studies` is the single implementation package. Top-level `run.py` and `build_case_map.py` are entry points. They reuse longmem I/O and hashing, without duplicating model backends, selectors, or scoring.
- Upstream code is read and scoped functions executed from external checkouts, not vendored. Each study records commits, reviewed file hashes, and permanent links.
- Real-model experiments require a separate protocol, budgets, and experiment directory. The present studies do not claim this evidence.

Both languages preserve the same scope, source pins, and evidence boundaries. Keep v0.1 Stage 1–4 and v0.2 E1–E4; closing studies are not E5. Original model results remain frozen.

## Evidence verification

Run `PYTHONPATH=src python studies/verify.py` from a checkout containing commit `ea7b5713ab5fd00d975fabb6fad81082817ed100`. The first v0.1 probe lives in `deepnote/results/v01-source-probe/`; its exact sources are read from that commit. The combined-study runs use the current pinned implementation. `source-history.json` lists each source reference explicitly. A shallow clone must fetch that commit before verification. No historical manifest is rewritten.
