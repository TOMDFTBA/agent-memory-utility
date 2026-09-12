# Stage 1 Validation Record

[Chinese version](validation.md)

Validation date: 2026-09-05 (Asia/Shanghai). Repository publication and clean CI status were verified separately for the public v0.1 release.

## Accepted scope

| Task | Implementation and evidence |
|---|---|
| Unified project skeleton | Python package, configuration, tests, documentation, demo artifacts, and ignore rules |
| Memory schema | Eight required fields, stable IDs, version marker, and auditable supersession chains |
| Persistence | JSONL-first commit, SQLite projection, FAISS CPU index, and versioned vector cache |
| Core interfaces | `write`, `get`, `search`, `list`, and `rebuild_index` through Python and CLI |
| MCP | Independent stdio service exercised through real process calls |
| UltraRAG | Official console CLI build/run with the four-step pipeline completed |
| Cross-session recovery | One MCP process writes and exits; a second retrieves through UltraRAG; a third independently verifies persistence |
| Model path | ROCm MiniCPM-Embedding and MiniCPM SFT with FAISS CPU |
| Auditable output | Memory IDs, hits, similarities, answer text, and evidence IDs recorded in audit JSON |
| Presentation artifact | README, Mermaid architecture, one-command demo, and a 2–3 minute recording script |

## Automated tests

```bash
.venv/bin/python -m pytest -q
```

The current suite contains 42 tests across all four stages. Stage 1 coverage includes read/write behavior, logical retries, ID conflicts, independent-process restart, retrieval, missing or damaged projections, JSONL-first recovery, torn tails, corrupt-line rejection, missing-log rejection, supersession, embedding-version updates, thread/process concurrency, complete JSONL-only recovery, and input validation.

Engineering tests use an explicitly named `HashEmbedder` test double and do not support claims about semantic retrieval quality. The public repository also runs the CPU suite on Python 3.11 and 3.12 in GitHub Actions.

## End-to-end validation

```bash
.venv/bin/python scripts/demo.py --mode test
.venv/bin/python scripts/demo.py --mode model
```

Both modes passed on the validated host. The real-model case stored:

- `alice-editor`: Alice prefers Neovim as her code editor.
- `bob-garden`: Bob grows tomatoes in his garden.
- Query: What editor does Alice prefer?
- Generated answer: `Neovim`.

In that run, the relevant fact scored approximately 0.5304, the distractor 0.0777, and the written-back answer 0.5780. This is a reviewable minimal case, not an accuracy benchmark.

The model did not emit evidence IDs in the answer body. The system preserved provenance through `metadata.evidence_ids` and the audit JSON. These IDs identify evidence supplied to the generator; they do not prove that every item affected the model's answer.

Machine-local audit files are written as `artifacts/demo/latest-test.json` and `artifacts/demo/latest-model.json`, pointing to run directories whose stdout, stderr, and persistence files are intentionally excluded from version control.

## Limitations and unaccepted paths

- Installation and the AMD/ROCm path were validated on one host, not repeated on a second clean AMD machine.
- The scoped UltraRAG installation intentionally omits dependencies for unused optional paths; full upstream dependency consistency is not claimed.
- Some GPU and MCP checks required authorized host execution rather than the restricted sandbox.
- Source filtering, an irrelevant-memory threshold, long-term write-back contamination controls, and scale optimization remain future work.
- This record validates Stage 1. Later evidence is documented in the memory-budget, memory-utility, and multimodal reports.
