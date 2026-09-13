# External Technical Lineage

[Chinese version](technical-lineage.md)

The four v0.1 technical foundations live outside this repository. Their source, weights, and datasets are not vendored here. Local locations below are historical validation records, not current installation requirements.

| Upstream | Role in this project | Expected local location |
|---|---|---|
| [UltraRAG](https://github.com/OpenBMB/UltraRAG) | MCP build/run orchestration | `../UltraRAG/code` |
| [MiniCPM-Embedding](https://huggingface.co/openbmb/MiniCPM-Embedding) | Semantic embeddings | `../MiniCPM-Embedding/model` |
| [RAG-DDR](https://github.com/OpenMatch/RAG-DDR) | Motivation for the utility experiment; the existing MiniCPM SFT base is reused locally | `../RAG-DDR` |
| [VisRAG](https://github.com/OpenBMB/VisRAG) | Multimodal retrieval case study | `../VisRAG` |

The validated local UltraRAG checkout was `37e0cce42e2156d710467cde77a2c0fd0114a2c4`. The MiniCPM-Embedding code checkout was `dc0f82b4466b254dddc25787bf7b1cbc28f755b0`. Local `model` directories are pre-existing snapshots. A configured revision records provenance, but the offline loader does not contact the upstream service to verify that label. All model code and weights remain governed by their upstream licenses and terms.

## Host-environment notes

The validated host reused system PyTorch 2.10.0 with ROCm 7.14, while the project virtual environment inherited system site packages. The project did not modify system PyTorch, model weights, or upstream execution code for the core UltraRAG path.

UltraRAG declares Python `>=3.11,<3.13`. The local Python 3.13.5 setup used `--ignore-requires-python` only for the minimal orchestration path; a new environment should prefer an upstream-supported Python version.

UltraRAG was installed with `--no-deps` to avoid CUDA, Milvus, corpus-parsing, and other components unused by this scoped path. Consequently, `pip check` reports missing dependencies for optional upstream paths. The inherited system environment also contains unrelated FastAPI/Starlette conflicts. Web UI and other affected paths were not used, so this environment must not be described as a complete UltraRAG dependency validation.

In the tested checkout, `python -m ultrarag.client` executes the synchronous `main()` and then attempts to pass its result to `asyncio.run`. The installed `ultrarag` console script was therefore used instead.

For exact AMD/ROCm coverage and the one recorded local source-compatibility patch, see the [environment deployment report](environment-deployment.en.md).

## Version closing studies

| Upstream | Role | Current evidence | Not claimed |
|---|---|---|---|
| [DeepNote](../studies/deepnote/README.en.md) | v0.1 closing study after Stage 1–4: evidence organization | Pinned source, two stub control probes | Offline note index or paper performance reproduction |
| [PilotDeck](../studies/pilotdeck-memory/README.en.md) | v0.2 closing study after E1–E4: memory pipelines | Pinned source, four capture-function probes, E4 case handoff | Full platform execution or retention baseline |

Sources are thunlp/DeepNote and OpenBMB/PilotDeck, with separate revisions and review scopes; they are not presented as independent products of one company. Frozen v0.1/v0.2 results are unchanged. Future representation or system experiments require separate protocols. See [study boundaries](../studies/README.en.md).
