# Usage and verification

English | [简体中文](usage.md)

Run commands from the repository root. Python 3.11 or 3.12 is recommended. Study provenance verification needs the historical commit `ea7b5713ab5fd00d975fabb6fad81082817ed100`; use a full clone, or fetch that commit before running `studies/verify.py`.

## Quick verification

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -e '.[mcp,test,quality,experiments]'
.venv/bin/python -m ruff check src tests scripts integrations experiments/utility-retention studies --exclude "**/results/**"
.venv/bin/python scripts/release_artifacts.py restore-results
.venv/bin/python scripts/audit_v02.py
PYTHONPATH=src .venv/bin/python studies/verify.py
.venv/bin/python -m pytest -q
.venv/bin/python scripts/demo.py --mode test
```

Test mode validates storage, MCP, and orchestration with deterministic test doubles. It does not load model weights, and its vectors and `[TEST ONLY]` outputs are not semantic-quality evidence.

Ruff covers shared code, tests, scripts, integrations, active v0.2 sources, and studies. Archived sources remain unchanged. The restore command verifies and expands local evidence without downloading models.

## Real models and AMD/ROCm

Copy the example configuration and point it to model directories outside this repository:

```bash
cp configs/local.example.yaml configs/local.yaml
.venv/bin/python -m pip install -e '.[models,mcp,experiments]'
.venv/bin/python scripts/demo.py --mode model
```

Real-model execution requires hardware-compatible PyTorch, MiniCPM-Embedding, and MiniCPM-2B-SFT installations. Models are loaded from local files; the runtime does not download weights automatically.

The scoped UltraRAG, MiniCPM-Embedding, VisRAG, and RAG-DDR paths were validated on Radeon 8060S, ROCm 7.14, and PyTorch 2.10. The [AMD/ROCm deployment report](environment-deployment.en.md) records exact coverage, compatibility changes, and exclusions; upstream revisions are listed in the [technical lineage](technical-lineage.en.md).

## Memory-store CLI

Use the test configuration when local models are unavailable:

```bash
.venv/bin/longmem --config configs/test.yaml write 'Alice prefers Vim.' --id alice-v1
.venv/bin/longmem --config configs/test.yaml write 'Alice prefers Neovim.' --id alice-v2 --supersedes alice-v1
.venv/bin/longmem --config configs/test.yaml search 'What editor does Alice prefer?' --top-k 3
.venv/bin/longmem --config configs/test.yaml get alice-v1
.venv/bin/longmem --config configs/test.yaml list --include-superseded
.venv/bin/longmem --config configs/test.yaml rebuild-index
```

Writes do not load the embedding model immediately. Vectors are generated on the first search or index rebuild. `LONGMEM_STORE_DIR` can override the configured data directory.

## UltraRAG-style integration

`integrations/ultrarag-memory/src/ultrarag-memory.py` is a standalone stdio MCP server exposing `memory_write`, `memory_search`, `memory_get`, `prompt_construction`, `generator`, and `remember_response`.

```text
memory_search → prompt_construction → generator → remember_response
```

An external UltraRAG checkout can be connected as follows:

```bash
.venv/bin/python scripts/setup.py --ultrarag /path/to/UltraRAG
export PATH="$PWD/.venv/bin:$PATH"
export LONGMEM_CONFIG="$PWD/configs/local.yaml"
ultrarag build configs/ultrarag-memory.yaml
ultrarag run configs/ultrarag-memory.yaml
```

## Reproducing the experiments

- [Memory budget](../experiments/memory-budget/README.md)
- [Memory utility](../experiments/memory-utility/README.md)
- [Multimodal retrieval mini](../experiments/multimodal-retrieval-mini/README.md)

v0.1 results retain their frozen formats. v0.2 reuses configuration, I/O, embedding, and generation, with an isolated list retrieval view for deletion. Cross-version baseline variants and budget units are documented in the [experiment guide](experiment-development-guide.en.md).

The repository includes code, protocols, configurations, datasets, and browsable reports. Full v0.2 responses and historical sources are shipped once in a checksum-pinned archive; restore materializes the ignored results directory. v0.1 exclusions remain unchanged. Model weights, caches, and paper-page derivatives without redistribution clearance remain excluded.
