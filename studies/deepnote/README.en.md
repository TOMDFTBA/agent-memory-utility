# DeepNote: method connection and control-flow checks

English | [简体中文](README.md)

This closes v0.1 after Stage 1–4 with a technical-lineage study. See the [method note](../../docs/paper-notes/deepnote.en.md). No note-based retention policy or v0.1/v0.2 model experiment is added.

## Completed

- Pinned thunlp/DeepNote commit and six reviewed source/template hashes: [upstream.json](upstream.json).
- Reviewed query-conditioned initialization, refinement, comparison, cumulative failure stopping, and best_note answering.
- Executed two stub probes of upstream retrieve_note: [output](results/v01-source-probe/probes.json), [manifest](results/v01-source-probe/manifest.json).
- Specified variables, costs, and reuse boundaries for a future raw_evidence / plain_summary / structured_note comparison.

## Reproduction

```bash
python studies/run.py deepnote --checkout /path/to/DeepNote --output /tmp/deepnote-control-probe
```

Run from the repository root after installing this package. The checkout must match the pinned commit/hashes; output must be a new empty directory. Only the reviewed retrieve_note AST function executes, with stub retrieval/model calls. Upstream CLI initialization and training do not run.

The probes establish control behavior, not note quality, retrieval gains, or long-term value. A representation experiment remains future work with its own protocol and outputs; it is not backfilled into v0.1.1 or frozen v0.1 experiments.

These records were newly generated for the standalone v0.1 supplement. Earlier combined-study records remain in the development workspace; no historical manifest was rewritten.
