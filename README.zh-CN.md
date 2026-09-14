# Agent Memory Utility｜智能体记忆效用

[English](README.md) | 简体中文

从检索走向保留：一个可复现的实验框架，用于研究长期 Agent Memory 存储、检索、利用什么，以及在预算下保留什么。

长期运行的 Agent 会持续积累事实、回答和外部知识。本项目将这种持续增长拆解为一组可以验证的研究问题。

## 研究路径

v0.1 建立持久化、检索增长、回答效用和多模态案例的实验基底。当前版本 v0.2 研究：在不观察未来任务的条件下，历史信号能否帮助决定哪些记忆值得保留？

```mermaid
flowchart LR
    A[v0.1 基底<br/>存储、检索与回答效用] --> B[v0.2 当前版本<br/>未来价值预测与预算保留]
    B --> C[v0.3 下一问题<br/>替代证据与集合条件化价值]
```

## v0.2 关键发现

- **仅使用历史信息的效用信号，在留出测试中改善了相对冻结 importance 的预算保留表现。**
  在 24 条独立合成轨迹上，utility_aware 相对冻结 importance 的三主预算平均 EM 差异为 +0.2014，轨迹 bootstrap 描述性 95% 区间为 [0.0972, 0.3056]。该结论不表示每个预算都稳定获益。[正式结果](releases/v0.2.0/reports/e3-formal-model/report.md)
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

## 复验与文档

CPU 验证不需要模型权重。[使用指南](docs/usage.md) 包含安装、证据恢复、测试、CLI 命令和 UltraRAG 接入；[AMD/ROCm 报告](docs/environment-deployment.md) 记录真实模型环境与验证范围。

核心文档、发布说明、实验报告和研究历史统一见[文档导航](docs/README.md)。

## 版本收尾研究

收尾研究通过源码分析和限定范围的检查，将各版本的发现联系到相关方法与系统。

- [DeepNote 方法联系](docs/paper-notes/deepnote.md)：作为 v0.1 收尾，补充证据组织讨论，已完成源码与控制流程检查。
- [PilotDeck memory study](studies/pilotdeck-memory/README.md)：接在 v0.2 E1–E4 之后收尾，补充捕获、抽取和整理流程讨论，附已有 E4 案例映射。

两项研究没有新增原版本的模型效果结论；完整平台、表示实验及预算 baseline 尚未执行。[范围与复用](studies/README.md)

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
