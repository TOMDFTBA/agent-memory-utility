# Agent Memory Utility｜智能体记忆效用

[English](README.md) | 简体中文

从检索走向保留：一个可复现的实验框架，用于测量长期 Agent Memory 存了什么、检索到什么，以及模型真正利用了什么。

长期运行的 Agent 会持续积累事实、回答和外部知识。本项目将这种持续增长拆解为一组可以验证的研究问题。

## 研究路径

v0.1 建立持久化、检索增长、回答效用和多模态案例的实验基底。当前版本 v0.2 研究：在不观察未来任务的条件下，历史信号能否帮助决定哪些记忆值得保留？

```mermaid
flowchart LR
    A[v0.1 基底<br/>存储、检索与回答效用] --> B[v0.2 当前版本<br/>未来价值预测与预算保留]
    B --> C[v0.3 下一问题<br/>替代证据与集合条件化价值]
```

## v0.2 关键发现

- **历史价值预测改善了本组预算决策。** 在 24 条独立合成轨迹上，utility_aware 相对冻结 importance 的三主预算平均 EM 差异为 +0.2014，轨迹 bootstrap 描述性 95% 区间为 [0.0972, 0.3056]。该结论不表示每个预算都稳定获益。[正式结果](releases/v0.2.0/reports/e3-formal-model/report.md)
- **真实单条 LOO 分数不足以区分所有保留集合。** 冗余证据的删除边际值可同时为零，而并列最优集合的实际答案表现不同。E4 支持的是目标的不可辨识性，不是所有 LOO 最优集合都次优。[集合诊断](releases/v0.2.0/reports/e4-diagnostic-model/report.md)
- **下一步需要同时考虑替代证据和生成限制。** 精确预测分数和选择未提升本实验平均 EM；高预算仍有证据读全但组合回答失败的情况。尚未验证 graph、consolidation 或在线长期收益。

以上结果限定于四类等比例合成压力场景、固定 MiniCPM 系统、每快照四条 memory 和两题窗口，不代表自然用户分布或跨模型泛化。

## v0.2 交付物

| 阶段 | 可复现交付物 |
|---|---|
| E1：未来价值测量 | storage deletion、窗口标签、历史特征与开发诊断 |
| E2：价值预测 | 仅历史特征的 Ridge、验证集模型选择与冻结基线 |
| E3：预算保留 | 24 条正式轨迹、600 个唯一回答条件、配对比较与成本分项 |
| E4：集合依赖 | 两组各 24 条轨迹、1536 个枚举条件、1152 个背景交互 |

[发布与复验说明](docs/v0.2-release.md) · [四阶段运行入口](experiments/utility-retention/README.md) · [v0.1 前序基底](docs/v0.1-four-stage-implementation-log.md)

## 快速验证

推荐使用 Python 3.11 或 3.12：

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -e '.[mcp,test,quality,experiments]'
.venv/bin/python -m ruff check src tests scripts integrations experiments/utility-retention --exclude "**/results/**"
.venv/bin/python scripts/release_artifacts.py restore-results
.venv/bin/python scripts/audit_v02.py
.venv/bin/python -m pytest -q
.venv/bin/python scripts/demo.py --mode test
```

`test` 模式不加载模型，只验证存储、MCP 和编排链路。确定性测试向量与 `[TEST ONLY]` 输出不能用于声明真实语义质量。

Ruff 检查公共代码、测试、脚本、集成层及 v0.2 活跃源码；归档源码保持原样。恢复命令校验并展开发布归档，不下载模型。

## 结果与文档

[文档导航](docs/README.md)

- [系统架构与恢复机制](docs/architecture.md) ([English](docs/architecture.en.md))
- [第一阶段验收](docs/validation.md) ([English](docs/validation.en.md))
- [Memory-budget 完整报告](experiments/memory-budget/results/v0.1/report.md) ([English](experiments/memory-budget/results/v0.1/report.en.md))
- [Memory-utility 完整报告](experiments/memory-utility/results/v0.1/report.md) ([English](experiments/memory-utility/results/v0.1/report.en.md))
- [Multimodal 三路对照](experiments/multimodal-retrieval-mini/results/v0.1/report.md) ([English](experiments/multimodal-retrieval-mini/results/v0.1/report.en.md))
- [技术谱系与上游边界](docs/technical-lineage.md) ([English](docs/technical-lineage.en.md))
- [v0.1 四阶段实施日志](docs/v0.1-four-stage-implementation-log.md)
- [v0.2 四阶段实施计划](docs/v0.2-four-stage-implementation-plan.md)
- [Memory-utility 补充控制](experiments/memory-utility/controls/results/v0.1-test/report.md)
- [多模态方向判断](docs/multimodal-memory-relevance.md)
- [实验命名与模块开发指南](docs/experiment-development-guide.md) ([English](docs/experiment-development-guide.en.md))

## 版本收尾研究

- [DeepNote 方法联系](docs/paper-notes/deepnote.md)：作为 v0.1 收尾，补充证据组织讨论，已完成源码与控制流程检查。
- [PilotDeck memory study](studies/pilotdeck-memory/README.md)：接在 v0.2 E1–E4 之后收尾，补充捕获、抽取和整理流程讨论，附已有 E4 案例映射。

两项研究没有新增原版本的模型效果结论；完整平台、表示实验及预算 baseline 尚未执行。[范围与复用](studies/README.md)

## 真实模型与 AMD/ROCm

复制示例配置并填写仓库外的模型路径：

```bash
cp configs/local.example.yaml configs/local.yaml
.venv/bin/python -m pip install -e '.[models,mcp,experiments]'
.venv/bin/python scripts/demo.py --mode model
```

真实模型运行需要适合硬件的 PyTorch、MiniCPM-Embedding 和 MiniCPM-2B-SFT。模型加载使用本地文件模式，不会自动下载权重。

本项目已在 Radeon 8060S、ROCm 7.14 和 PyTorch 2.10 上验证限定范围的 UltraRAG、MiniCPM-Embedding、VisRAG 与 RAG-DDR 路径。完整安装范围、ROCm 兼容修改和未覆盖项见 [AMD/ROCm 环境部署与验证报告](docs/environment-deployment.md)。上游 commit 与技术用途见 [技术谱系](docs/technical-lineage.md)。

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

- [Memory budget](experiments/memory-budget/README.md)
- [Memory utility](experiments/memory-utility/README.md)
- [Multimodal retrieval mini](experiments/multimodal-retrieval-mini/README.md)

v0.1 冻结结果保留原格式。v0.2 复用共享配置、I/O、embedding 和 generation，并用独立列表检索视图实施删除；跨版本 baseline 与预算单位的区别见[实验开发指南](docs/experiment-development-guide.md)。

版本库保留代码、协议、配置、数据集和公开报告。v0.2 完整逐题证据与历史源码合并为一份校验归档，results 目录由恢复命令生成；v0.1 的排除规则保持不变。模型权重、缓存及未获再分发许可的论文页面不进入发布。

## 已知限制

- 当前为本地单库，没有用户/session 隔离。
- 检索没有默认相似度阈值，top-k 命中不保证相关。
- 自动回写回答标记为未验证，但 v0.1 尚未默认隔离 generated memory；这可能形成反馈污染。
- 当前事件日志按 session 全量 replay，尚未针对长期吞吐优化。
- Memory-budget 和 utility 数据以英文合成模板为主，尚无新的 blind real-world test set。
- Multimodal 实验规模很小，且不同路径使用不同 encoder，不能隔离出纯粹的 modality 因果效应。
- AMD/ROCm 真实模型路径尚未在第二台干净主机复验。

## 来源与发布状态

四个上游项目不作为源码 vendoring 到本仓库，模型权重也不进入版本控制。相关来源、版本和许可边界见 [技术谱系](docs/technical-lineage.md)。

## 作者与引用

钟启轩（Qixuan Zhong）— [GitHub：TOMDFTBA](https://github.com/TOMDFTBA) — [ORCID：0009-0006-8392-1658](https://orcid.org/0009-0006-8392-1658)

机器可读的引用信息见 [`CITATION.cff`](CITATION.cff)。

当前发布验证见 [v0.2 发布说明](docs/v0.2-release.md)；历史记录见 [v0.1 发布检查清单](docs/release-checklist.md)。本仓库自有代码和文档采用 Apache License 2.0；上游模型、数据集、论文材料及第三方代码仍分别受其自身许可证约束。
