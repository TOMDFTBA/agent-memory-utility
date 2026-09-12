# AMD/ROCm 环境部署与验证报告

[English](environment-deployment.en.md) | 简体中文

本文记录 v0.1 在一台 AMD 主机上的实际部署范围、兼容处理和复验方法。它是特定主机的验证报告，不表示四个上游项目的全部训练与推理功能均已复现。

## 验证摘要

验证日期：2026-09-04。

验证主机：AMD Ryzen AI Max+ 395、Radeon 8060S、128 GiB 内存、ROCm 7.14.60850、PyTorch 2.10.0。

| 项目 | 实际验证范围 | 结果 | 未覆盖范围 |
|---|---|---:|---|
| UltraRAG | 核心 MCP `sayhello` 编排，以及本项目的 memory pipeline | PASS | UI、语料解析、Milvus、完整 extras、本地 vLLM |
| MiniCPM-Embedding | 2.4B BF16 文本向量推理 | PASS | 训练、FlashAttention |
| VisRAG | VisRAG-Ret 文本与图像编码 | PASS | VisRAG-Gen、EVisRAG 2.0、训练 |
| RAG-DDR | MiniCPM Generation LoRA 推理 | PASS | KR 模块、完整双阶段流水线、训练 |

四个项目分别使用自己的 `.venv/`，通过 `--system-site-packages` 复用主机已有的 ROCm PyTorch。没有重复安装 CUDA 版 PyTorch，也没有修改系统 ROCm。

## 本项目的推荐部署

### CPU / CI 路径

推荐在 Python 3.11 或 3.12 上验证存储、恢复和实验代码：

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -e '.[mcp,test]'
.venv/bin/python -m pytest -q
.venv/bin/python scripts/demo.py --mode test
```

`test` 模式使用确定性测试替身，不加载真实模型，也不能用于声明语义检索质量。

### AMD/ROCm 模型路径

先由 AMD 官方支持的方式安装与本机 ROCm 匹配的 PyTorch，再复用该安装创建项目环境。不要安装 CUDA wheel。

```bash
python3 -m venv --system-site-packages .venv
.venv/bin/python -m pip install -e '.[models,mcp,experiments,test]'
cp configs/local.example.yaml configs/local.yaml
```

将已下载的 MiniCPM-Embedding 与 MiniCPM-2B-SFT 放在仓库外，并在 `configs/local.yaml` 填入路径。ROCm PyTorch 与 CUDA PyTorch 一样通过 `device: cuda` 访问 AMD GPU。真实模型加载设置为本地文件模式，不会在运行时自动下载权重。

验证顺序：

```bash
.venv/bin/python -c "import torch; print(torch.__version__, torch.version.hip, torch.cuda.is_available())"
.venv/bin/python scripts/demo.py --mode test
.venv/bin/python scripts/demo.py --mode model
```

如果需要接入外部 UltraRAG checkout：

```bash
.venv/bin/python scripts/setup.py --ultrarag /path/to/UltraRAG
```

本机使用 Python 3.13.5 时曾通过 `--allow-unsupported-python` 安装最小编排路径；这是兼容例外，不是推荐的新机器配置。

## 按四阶段复现实验环境

### 状态定义

| 状态 | 含义 |
|---|---|
| PASS | 已在上述 AMD 主机上以真实入口运行，并检查了预期输出 |
| PARTIAL | 只验证了该阶段所需的有限路径，不能外推到上游项目全部功能 |
| TEST ONLY | 使用确定性替身或小型测试数据，只验证工程行为 |
| NOT TESTED | 依赖或上游路径没有完成端到端运行 |
| NOT APPLICABLE | CUDA 专用路径没有在该 ROCm 主机上采用 |

### 阶段依赖与验证矩阵

| 阶段 | 主要组件 | 本机环境来源 | 验证状态 | 复验入口 |
|---|---|---|---|---|
| 1. Persistent memory | JSONL、SQLite、FAISS CPU、FastMCP、UltraRAG CLI、MiniCPM embedding/SFT | 项目 `.venv` 复用系统 ROCm PyTorch；外部模型与 UltraRAG checkout | PASS；全量 UltraRAG extras 为 PARTIAL | `pytest`、`demo.py --mode test/model` |
| 2. Memory budget | MiniCPM-Embedding、FAISS CPU、NumPy、matplotlib、向量缓存 | 项目 `.venv`；系统 ROCm PyTorch；仓库外 embedding 权重 | PASS，300 组正式运行 | `benchmark.py` → verify/report/analyze |
| 3. Memory utility | MiniCPM-2B-SFT、Transformers、SentencePiece、matplotlib | 项目 `.venv`；系统 ROCm PyTorch；仓库外 SFT 基座 | PASS，594 次主实验及 648 次补充控制；RAG-DDR 训练为 NOT TESTED | `run_ablation.py`、`run_controls.py` |
| 4. Multimodal case study | VisRAG-Ret、MiniCPM-Embedding、TorchVision、timm、Pillow、Poppler、Tesseract | 复用 VisRAG 独立 `.venv` 和系统 ROCm；OCR 位于项目缓存或 PATH | PASS，8 页 × 5 问三路检索；生成与训练为 NOT TESTED | `run_demo.py` → verify/analyze |

矩阵中的 PASS 只覆盖本项目实际调用的路径。例如第三阶段使用 MiniCPM-2B-SFT 评测记忆效用，不等于完成 RAG-DDR 的 KR→Generation 训练复现。

### 阶段一：Persistent memory 与 UltraRAG-style pipeline

核心运行依赖：

- Python 标准库的 JSONL 与 SQLite；Linux 上使用 `fcntl` 文件锁。
- `faiss-cpu==1.15.0` 和 NumPy 保存向量投影；没有安装 CUDA FAISS。
- FastMCP 3.4.4 提供 stdio memory server。
- UltraRAG 使用外部源码 checkout，并以 `--no-deps` 可编辑安装最小 CLI/MCP 路径。
- 真实模式加载 MiniCPM-Embedding 与 MiniCPM-2B-SFT；测试模式使用 HashEmbedder 和固定生成输出。

复验：

```bash
.venv/bin/python -m pytest -q tests/test_store.py
.venv/bin/python scripts/demo.py --mode test
.venv/bin/python scripts/demo.py --mode model
```

`test` 模式是 TEST ONLY；`model` 模式才验证 ROCm embedding、生成和跨进程回写。端到端审计目录默认保留在本地，不纳入版本控制。

### 阶段二：Memory-budget benchmark

这一阶段不训练模型，只批量运行 embedding、保留策略和 FAISS CPU 检索。正式运行使用：

- MiniCPM-Embedding BF16，文档 batch 8、查询 batch 1。
- FAISS `IndexFlatIP`，CPU 单线程，索引输入为归一化 float32。
- NumPy `.npy` 缓存按模型版本与完整文本列表散列寻址。
- matplotlib 使用无界面的 `Agg` backend 生成报告图。

```bash
.venv/bin/python experiments/memory-budget/benchmark.py \
  --calibration-file experiments/memory-budget/configs/frozen-v0.1.json \
  --output experiments/memory-budget/results/new-full
.venv/bin/python experiments/memory-budget/verify_results.py \
  experiments/memory-budget/results/new-full
.venv/bin/python experiments/memory-budget/report.py \
  experiments/memory-budget/results/new-full
.venv/bin/python experiments/memory-budget/analyze.py \
  experiments/memory-budget/results/new-full
```

`--backend hash-test` 仅适合工程检查，不得套用真实模型的冻结阈值或用于语义质量结论。运行可能产生大量缓存和逐组原始输出；正式发布只保留冻结配置、汇总、验证记录与图表。

### 阶段三：Memory-utility generation

主实验直接使用项目 Generator 加载 MiniCPM-2B-SFT，不加载 RAG-DDR LoRA；因此其环境比单独的 RAG-DDR 上游验证更小：

- Transformers 4.51.3、SentencePiece、Safetensors。
- ROCm PyTorch BF16 greedy generation，输入上限 2048 tokens。
- NumPy 与 matplotlib 用于评分、汇总和绘图。
- 主实验不需要 PEFT、TRL、vLLM 或 Deepspeed。

```bash
.venv/bin/python experiments/memory-utility/generate_dataset.py
.venv/bin/python experiments/memory-utility/run_ablation.py \
  --output experiments/memory-utility/results/new-run
.venv/bin/python experiments/memory-utility/report.py \
  experiments/memory-utility/results/new-run
```

补充控制实验使用同一基座模型，但有独立的开发集协议选择、冻结协议和测试运行，详见该实验目录的 README。单独验证 RAG-DDR LoRA 时才需要 PEFT；那条 PARTIAL 上游路径不应被列为本阶段主实验的必要依赖。

### 阶段四：VisRAG / PDF text / OCR

这一阶段复用了 `../VisRAG/.venv`，因为该环境已经验证 TorchVision、Accelerate、timm、Pillow 和 VisRAG 的远程模型代码。项目根目录的 `experiments` extra 只补充通用绘图与 Pillow，不能代替完整 VisRAG 环境。

系统或独立运行时还需要：

- Poppler CLI：`pdftoppm` 负责页面渲染，`pdftotext` 提取原生文本。
- Tesseract 5.5 和英文语言数据；可从 PATH 使用，也可由 `setup_ocr.py` 在兼容 Debian 主机下载固定包并解压到 `cache/tesseract`。
- VisRAG-Ret 与 MiniCPM-Embedding 权重均放在仓库外。

```bash
../VisRAG/.venv/bin/python experiments/multimodal-retrieval-mini/run_demo.py \
  --output experiments/multimodal-retrieval-mini/results/my-rerun
../VisRAG/.venv/bin/python experiments/multimodal-retrieval-mini/verify_run.py \
  experiments/multimodal-retrieval-mini/results/my-rerun
../VisRAG/.venv/bin/python experiments/multimodal-retrieval-mini/analyze_cases.py \
  experiments/multimodal-retrieval-mini/results/my-rerun
```

首次命令需要可见的 ROCm GPU，后两项无需 GPU。缺少 Tesseract、英文数据或有效 OCR 输出时会显式失败，不会静默使用 PDF 原生文本代替。Debian 固定包脚本依赖目标系统的动态库，不是通用容器镜像。

### 安装层级与兼容修改清单

| 层级 | 实际处理 | 是否修改上游源码 |
|---|---|---:|
| 系统运行时 | 复用 ROCm 7.14、PyTorch 2.10、TorchVision、Poppler；没有重复安装 CUDA runtime | 否 |
| 项目 Python 环境 | 安装 FAISS CPU、FastMCP、Transformers、SentencePiece、Safetensors、matplotlib、Pillow | 否 |
| OCR 独立运行时 | Tesseract 与英文数据通过 PATH 或项目缓存提供 | 否 |
| UltraRAG 兼容 | 最小 `--no-deps` 安装、使用 console script、调整 PATH | 否 |
| VisRAG 兼容 | 关闭 CUDA FlashAttention/Deepspeed/vLLM 路径，补充遗漏的 `timm` | 否 |
| RAG-DDR 生成兼容 | Transformers `generate()` 替代 CUDA vLLM；本地 MiniCPM 模型代码兼容新版 DynamicCache API | **是，仅本地模型代码** |

这里唯一记录的源码兼容补丁位于仓库外的 MiniCPM 基座目录，并未复制进本仓库。公开复验者若使用同一旧模型代码与 Transformers 4.51，需要自行应用等价的 `get_max_length()` / `get_max_cache_shape()` 兼容处理，或者选择相互兼容的官方版本组合。

## 各上游项目的兼容记录

### UltraRAG

- 验证了 UltraRAG 0.3.0.2、FastMCP 3.4.4 和 MCP 1.29.1 的最小 MCP 路径。
- 没有安装 CUDA 12.9 PyTorch、CUDA vLLM、`faiss-gpu-cu12`、Deepspeed 或全量 extras。
- Python 3.13 超出上游声明的 `<3.13` 范围，本机使用显式兼容例外。
- stdio 子服务依赖 PATH 找到正确的 Python，运行时需要将项目 `.venv/bin` 放在 PATH 首位。
- AMD 主机上的生成后端采用 Transformers/ROCm 或兼容 API，不使用 CUDA vLLM 路径。

### MiniCPM-Embedding

- 模型以 BF16 在 Radeon 8060S 上完成文本编码，输出 2304 维归一化向量。
- 没有启用 `flash_attention_2`，使用 PyTorch 原生 scaled-dot-product attention。
- 使用 `trust_remote_code=True` 加载上游自定义模型代码，因此只应使用可信、固定版本的模型来源。
- 本机验证使用 Transformers 4.51.3；模型 revision 记录在示例配置和技术谱系中。

### VisRAG

- VisRAG-Ret 完成文本查询和图像的 2304 维编码。
- 移除了 CUDA Toolkit、Deepspeed 和 CUDA FlashAttention 要求；未修改上游仓库代码。
- 上游依赖未列出的 `timm` 是实际模型加载所需依赖，本机显式补装。
- VisRAG-Gen、EVisRAG 2.0、训练与 vLLM 尚未验证，不能从当前结果推断可用。

### RAG-DDR

- 验证了 `Gen_model_Minicpm_2.4b` LoRA 与 MiniCPM-2B-SFT 基座的 Transformers/ROCm 推理。
- 使用 FAISS CPU 替代 CUDA FAISS，使用 Transformers `generate()` 替代官方 CUDA vLLM 路径。
- 为兼容 Transformers 4.51，在本地模型代码中将旧的 `DynamicCache.get_max_length()` 调用兼容到 `get_max_cache_shape()`；补丁通过 `getattr` 同时支持新旧 API。
- 上游 `kr_model_for_Minicpm_2.4b` 检查点实际指向 Llama 3 8B 且维度为 4096，不能加载到隐藏维度 2304 的 MiniCPM 基座。因此 KR 模块和完整双阶段流水线没有被声明为通过。

## ROCm 兼容原则

1. 优先探测并复用系统已有 PyTorch/ROCm，而不是再次安装 GPU 运行时。
2. 删除或绕过 CUDA 专用依赖，但不把未运行的路径标记为可用。
3. 优先使用 PyTorch/Transformers 的通用路径和 FAISS CPU。
4. 每项 PASS 都限定到具体模型、入口和输出，不外推到训练、全量 extras 或论文指标复现。
5. 模型权重、缓存、虚拟环境和本机路径不进入版本控制。

## 已知限制

- 尚未在第二台干净 AMD 主机完成 clean-room 复验。
- 本机继承了系统 site-packages，不能据此声称全量 `pip check` 无冲突。
- 性能数字只代表这台主机和当时的软件组合。
- 上游仓库和模型仍受各自许可证约束；本仓库不再分发其权重或源码。

上游版本、用途和来源见 [技术谱系](technical-lineage.md)，项目级验收见 [验证记录](validation.md)。
