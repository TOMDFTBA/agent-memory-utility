# 使用与验证

[English](usage.en.md) | 简体中文

以下命令均从仓库根目录执行，推荐 Python 3.11 或 3.12。Study 源码核验需要历史提交 `ea7b5713ab5fd00d975fabb6fad81082817ed100`；请使用完整克隆，或在运行 `studies/verify.py` 前获取该提交。

## 快速验证

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

`test` 模式不加载模型，只验证存储、MCP 和编排链路。确定性测试向量与 `[TEST ONLY]` 输出不能用于声明真实语义质量。

Ruff 检查公共代码、测试、脚本、集成层、v0.2 活跃源码与 studies；归档源码保持原样。恢复命令校验并展开发布归档，不下载模型。

## 真实模型与 AMD/ROCm

复制示例配置并填写仓库外的模型路径：

```bash
cp configs/local.example.yaml configs/local.yaml
.venv/bin/python -m pip install -e '.[models,mcp,experiments]'
.venv/bin/python scripts/demo.py --mode model
```

真实模型运行需要适合硬件的 PyTorch、MiniCPM-Embedding 和 MiniCPM-2B-SFT。模型加载使用本地文件模式，不会自动下载权重。

本项目已在 Radeon 8060S、ROCm 7.14 和 PyTorch 2.10 上验证限定范围的 UltraRAG、MiniCPM-Embedding、VisRAG 与 RAG-DDR 路径。完整安装范围、ROCm 兼容修改和未覆盖项见 [AMD/ROCm 环境部署与验证报告](environment-deployment.md)。上游 commit 与技术用途见 [技术谱系](technical-lineage.md)。

## 记忆库命令

无本地模型时使用测试配置：

```bash
.venv/bin/longmem --config configs/test.yaml write 'Alice prefers Vim.' --id alice-v1
.venv/bin/longmem --config configs/test.yaml write 'Alice prefers Neovim.' --id alice-v2 --supersedes alice-v1
.venv/bin/longmem --config configs/test.yaml search 'What editor does Alice prefer?' --top-k 3
.venv/bin/longmem --config configs/test.yaml get alice-v1
.venv/bin/longmem --config configs/test.yaml list --include-superseded
.venv/bin/longmem --config configs/test.yaml rebuild-index
```

写入时不要求立即加载模型；首次检索或重建索引时才生成向量。`LONGMEM_STORE_DIR` 可以覆盖数据目录。

## UltraRAG-style 集成

`integrations/ultrarag-memory/src/ultrarag-memory.py` 提供独立 stdio MCP 服务，暴露 `memory_write`、`memory_search`、`memory_get`、`prompt_construction`、`generator` 和 `remember_response`。

pipeline 为：

```text
memory_search → prompt_construction → generator → remember_response
```

外部 UltraRAG checkout 可以通过以下方式接入：

```bash
.venv/bin/python scripts/setup.py --ultrarag /path/to/UltraRAG
export PATH="$PWD/.venv/bin:$PATH"
export LONGMEM_CONFIG="$PWD/configs/local.yaml"
ultrarag build configs/ultrarag-memory.yaml
ultrarag run configs/ultrarag-memory.yaml
```

## 实验复现

每个实验目录包含独立协议和命令：

- [Memory budget](../experiments/memory-budget/README.md)
- [Memory utility](../experiments/memory-utility/README.md)
- [Multimodal retrieval mini](../experiments/multimodal-retrieval-mini/README.md)

v0.1 冻结结果保留原格式。v0.2 复用共享配置、I/O、embedding 和 generation，并用独立列表检索视图实施删除；跨版本 baseline 与预算单位的区别见[实验开发指南](experiment-development-guide.md)。

版本库保留代码、协议、配置、数据集和公开报告。v0.2 完整逐题证据与历史源码合并为一份校验归档，results 目录由恢复命令生成；v0.1 的排除规则保持不变。模型权重、缓存及未获再分发许可的论文页面不进入发布。
