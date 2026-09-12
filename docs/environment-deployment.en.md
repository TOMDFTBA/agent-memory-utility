# AMD/ROCm Environment Deployment and Validation Report

English | [简体中文](environment-deployment.md)

This report records the actual v0.1 deployment scope on one AMD host, including compatibility work and reproduction commands. It does not claim that every training and inference path of the four upstream projects was reproduced.

## Validation summary

Validation date: 2026-09-04.

Host: AMD Ryzen AI Max+ 395, Radeon 8060S, 128 GiB RAM, ROCm 7.14.60850, and PyTorch 2.10.0.

| Project | Validated scope | Result | Not covered |
|---|---|---:|---|
| UltraRAG | Core MCP `sayhello` orchestration and this project's memory pipeline | PASS | UI, corpus parsing, Milvus, full extras, local vLLM |
| MiniCPM-Embedding | 2.4B BF16 text embedding inference | PASS | Training, FlashAttention |
| VisRAG | VisRAG-Ret text and image encoding | PASS | VisRAG-Gen, EVisRAG 2.0, training |
| RAG-DDR | MiniCPM Generation LoRA inference | PASS | KR module, full two-stage pipeline, training |

Each project used its own `.venv/` with `--system-site-packages` to reuse the host's working ROCm PyTorch installation. No CUDA PyTorch wheel was installed, and the system ROCm installation was not modified.

## Recommended project deployment

### CPU and CI path

Python 3.11 or 3.12 is recommended for storage, recovery, and experiment-code validation:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -e '.[mcp,test]'
.venv/bin/python -m pytest -q
.venv/bin/python scripts/demo.py --mode test
```

Test mode uses deterministic substitutes and does not load real models. Its results must not be presented as semantic retrieval quality.

### AMD/ROCm model path

First install a PyTorch build compatible with the host ROCm stack through an AMD-supported method. Reuse that installation instead of installing a CUDA wheel:

```bash
python3 -m venv --system-site-packages .venv
.venv/bin/python -m pip install -e '.[models,mcp,experiments,test]'
cp configs/local.example.yaml configs/local.yaml
```

Place MiniCPM-Embedding and MiniCPM-2B-SFT outside the repository and configure their paths in `configs/local.yaml`. ROCm PyTorch exposes an AMD GPU through the same `device: cuda` interface used by PyTorch CUDA builds. Model loading is local-only and does not download weights at runtime.

Recommended validation order:

```bash
.venv/bin/python -c "import torch; print(torch.__version__, torch.version.hip, torch.cuda.is_available())"
.venv/bin/python scripts/demo.py --mode test
.venv/bin/python scripts/demo.py --mode model
```

To connect an external UltraRAG checkout:

```bash
.venv/bin/python scripts/setup.py --ultrarag /path/to/UltraRAG
```

The validated host used Python 3.13.5 with an explicit `--allow-unsupported-python` exception for the minimal orchestration path. This is a compatibility exception, not the recommended setup for a new machine.

## Four-stage experiment environments

### Status definitions

| Status | Meaning |
|---|---|
| PASS | Executed through the real entry point on the AMD host and checked against expected output |
| PARTIAL | Only the path needed by this project was validated; the result does not cover the entire upstream project |
| TEST ONLY | Deterministic substitutes or small test data validated engineering behavior only |
| NOT TESTED | The dependency or upstream path was not run end to end |
| NOT APPLICABLE | A CUDA-specific path was intentionally not used on the ROCm host |

### Validation matrix

| Stage | Main components | Environment source | Status | Entry point |
|---|---|---|---|---|
| 1. Persistent memory | JSONL, SQLite, FAISS CPU, FastMCP, UltraRAG CLI, MiniCPM embedding/SFT | Project `.venv`, system ROCm PyTorch, external models and UltraRAG checkout | PASS; full UltraRAG extras are PARTIAL | `pytest`, `demo.py --mode test/model` |
| 2. Memory budget | MiniCPM-Embedding, FAISS CPU, NumPy, matplotlib, vector cache | Project `.venv`, system ROCm PyTorch, external embedding weights | PASS, 300 formal runs | `benchmark_v2.py` → verify/report/analyze |
| 3. Memory utility | MiniCPM-2B-SFT, Transformers, SentencePiece, matplotlib | Project `.venv`, system ROCm PyTorch, external SFT base | PASS, 594 main responses and 648 control responses; RAG-DDR training NOT TESTED | `run_ablation.py`, `run_controls.py` |
| 4. Multimodal case study | VisRAG-Ret, MiniCPM-Embedding, TorchVision, timm, Pillow, Poppler, Tesseract | Existing VisRAG `.venv`, system ROCm, OCR from project cache or PATH | PASS, three-way retrieval over 8 pages × 5 queries; generation and training NOT TESTED | `run_demo.py` → verify/analyze |

A PASS only covers the path actually called here. For example, using MiniCPM-2B-SFT to evaluate memory utility does not reproduce RAG-DDR's complete KR-to-Generation training pipeline.

### Stage 1: persistent memory and UltraRAG-style pipeline

Runtime components:

- Python JSONL and SQLite; Linux `fcntl` file locking.
- `faiss-cpu==1.15.0` and NumPy for the vector projection; no GPU FAISS.
- FastMCP 3.4.4 for the stdio memory server.
- An external UltraRAG checkout installed editable with `--no-deps` for the minimal CLI/MCP path.
- MiniCPM-Embedding and MiniCPM-2B-SFT in real mode; HashEmbedder and fixed generation in test mode.

```bash
.venv/bin/python -m pytest -q tests/test_store.py
.venv/bin/python scripts/demo.py --mode test
.venv/bin/python scripts/demo.py --mode model
```

Only `model` mode validates ROCm embedding, generation, and cross-process write-back. Audit runs remain local and are excluded from version control.

### Stage 2: memory-budget benchmark

This stage trains no model. It runs embedding, retention policies, and FAISS CPU retrieval using:

- MiniCPM-Embedding BF16 with document batch 8 and query batch 1.
- Single-threaded FAISS `IndexFlatIP` over normalized float32 vectors.
- Content-addressed NumPy caches keyed by model version and the complete text list.
- The non-interactive matplotlib `Agg` backend.

```bash
.venv/bin/python experiments/memory-budget/benchmark_v2.py \
  --calibration-file experiments/memory-budget/configs/frozen-v2.json \
  --output experiments/memory-budget/results/new-full
.venv/bin/python experiments/memory-budget/verify_results.py \
  experiments/memory-budget/results/new-full
.venv/bin/python experiments/memory-budget/report_v2.py \
  experiments/memory-budget/results/new-full
.venv/bin/python experiments/memory-budget/analyze_v2.py \
  experiments/memory-budget/results/new-full
```

The `hash-test` backend is for engineering checks only. It must not use real-model frozen thresholds or support semantic-quality claims. Publication retains frozen configuration, aggregate reports, verification records, and figures rather than raw run directories and large caches.

### Stage 3: memory-utility generation

The main experiment loads MiniCPM-2B-SFT through the project Generator without loading a RAG-DDR LoRA. Its environment therefore needs only:

- Transformers 4.51.3, SentencePiece, and Safetensors.
- ROCm PyTorch BF16 greedy generation with a 2,048-token input limit.
- NumPy and matplotlib for scoring, aggregation, and figures.

It does not require PEFT, TRL, vLLM, or DeepSpeed.

```bash
.venv/bin/python experiments/memory-utility/generate_dataset.py
.venv/bin/python experiments/memory-utility/run_ablation.py \
  --output experiments/memory-utility/results/new-run
.venv/bin/python experiments/memory-utility/report.py \
  experiments/memory-utility/results/new-run
```

The control study uses the same base model with a separate development-set protocol selection, frozen protocol, and test run. PEFT is needed only for the separate PARTIAL RAG-DDR LoRA validation path.

### Stage 4: VisRAG, native PDF text, and OCR

This stage reuses `../VisRAG/.venv`, which already contains compatible TorchVision, Accelerate, timm, Pillow, and VisRAG remote model code. The project's generic `experiments` extra is not a replacement for the full VisRAG environment.

Additional local runtimes:

- Poppler CLI: `pdftoppm` for page rendering and `pdftotext` for native text extraction.
- Tesseract 5.5 with English data, available through PATH or downloaded into `cache/tesseract` by `setup_ocr.py` on a compatible Debian host.
- VisRAG-Ret and MiniCPM-Embedding weights outside the repository.

```bash
../VisRAG/.venv/bin/python experiments/multimodal-retrieval-mini/run_demo.py \
  --output experiments/multimodal-retrieval-mini/results/my-rerun
../VisRAG/.venv/bin/python experiments/multimodal-retrieval-mini/verify_run.py \
  experiments/multimodal-retrieval-mini/results/my-rerun
../VisRAG/.venv/bin/python experiments/multimodal-retrieval-mini/analyze_cases.py \
  experiments/multimodal-retrieval-mini/results/my-rerun
```

The first command requires a visible ROCm GPU; verification and analysis do not. Missing Tesseract, English data, or valid OCR output causes an explicit failure. Native PDF text is never used as a silent OCR fallback. The Debian package script is not a universal container image and still relies on compatible system libraries.

## Installation layers and compatibility changes

| Layer | Actual treatment | Upstream source modified? |
|---|---|---:|
| System runtime | Reused ROCm 7.14, PyTorch 2.10, TorchVision, and Poppler; installed no duplicate CUDA runtime | No |
| Project Python environment | Added FAISS CPU, FastMCP, Transformers, SentencePiece, Safetensors, matplotlib, and Pillow | No |
| OCR runtime | Used Tesseract and English data from PATH or project cache | No |
| UltraRAG compatibility | Minimal `--no-deps` install, console script, and PATH adjustment | No |
| VisRAG compatibility | Disabled CUDA FlashAttention/DeepSpeed/vLLM paths and supplied missing `timm` | No |
| RAG-DDR generation compatibility | Replaced CUDA vLLM with Transformers `generate()`; adapted local MiniCPM model code to the current DynamicCache API | **Yes, local model code only** |

The only recorded source compatibility patch lives outside this repository in the local MiniCPM base directory. With the same older model code and Transformers 4.51, a reproducer must apply an equivalent `get_max_length()` / `get_max_cache_shape()` compatibility treatment or select mutually compatible official versions.

## Upstream-specific notes

### UltraRAG

- Validated UltraRAG 0.3.0.2, FastMCP 3.4.4, and MCP 1.29.1 on the minimal MCP path.
- Did not install CUDA 12.9 PyTorch, CUDA vLLM, `faiss-gpu-cu12`, DeepSpeed, or all extras.
- Python 3.13 is outside the upstream `<3.13` declaration and required an explicit local exception.
- The stdio subprocess must find the project Python by placing `.venv/bin` first on PATH.
- Generation on AMD uses Transformers/ROCm or a compatible API, not the CUDA vLLM path.

### MiniCPM-Embedding

- Completed BF16 text encoding to normalized 2,304-dimensional vectors on Radeon 8060S.
- Did not enable `flash_attention_2`; used native PyTorch scaled-dot-product attention.
- Uses `trust_remote_code=True`, so only trusted, fixed model sources should be loaded.
- Validation used Transformers 4.51.3; the model revision is recorded in configuration and technical-lineage documentation.

### VisRAG

- VisRAG-Ret completed text-query and image encoding to 2,304-dimensional vectors.
- CUDA Toolkit, DeepSpeed, and CUDA FlashAttention requirements were removed from the path; upstream repository source was not modified.
- `timm`, omitted from the relevant upstream dependency declaration, was installed explicitly.
- VisRAG-Gen, EVisRAG 2.0, training, and vLLM remain unvalidated.

### RAG-DDR

- Validated Transformers/ROCm inference for the `Gen_model_Minicpm_2.4b` LoRA and MiniCPM-2B-SFT base.
- Used FAISS CPU instead of CUDA FAISS and Transformers `generate()` instead of CUDA vLLM.
- For Transformers 4.51 compatibility, local model code adapts the old `DynamicCache.get_max_length()` call to `get_max_cache_shape()` through `getattr`, preserving support for both APIs.
- The upstream `kr_model_for_Minicpm_2.4b` checkpoint actually points to Llama 3 8B with width 4,096 and cannot load into the MiniCPM base with width 2,304. The KR module and full two-stage pipeline are therefore not marked PASS.

## ROCm compatibility principles

1. Probe and reuse a working system PyTorch/ROCm stack before installing another GPU runtime.
2. Remove or bypass CUDA-specific dependencies without marking unexecuted paths as working.
3. Prefer generic PyTorch/Transformers paths and FAISS CPU.
4. Scope every PASS to a concrete model, entry point, and output; do not extrapolate to training, all extras, or paper reproduction.
5. Keep model weights, caches, virtual environments, and machine-local paths out of version control.

## Known limitations

- No clean-room reproduction has been completed on a second AMD host.
- The host environment inherits system site-packages, so it does not establish a conflict-free full `pip check` from scratch.
- Performance numbers apply only to this host and software combination.
- Upstream repositories and models retain their own licenses; this repository redistributes neither their source nor their weights.

See [technical lineage](technical-lineage.en.md) for upstream versions and roles, and [project validation](validation.en.md) for project-level acceptance evidence. Chinese versions remain available alongside both documents.
