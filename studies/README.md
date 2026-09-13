# Knowledge-to-memory studies

[English](README.en.md) | 简体中文

DeepNote 归入 v0.1 四阶段之后的收尾；PilotDeck 归入 v0.2 E1–E4 之后的收尾。两项研究，使用固定上游版本、源码证据和有明确边界的最小检查。它们不是原四阶段的新实验，也不复用 retention candidate 命名空间。

| Study | 版本归属 | 已完成证据 | 未完成部分 |
|---|---|---|---|
| [DeepNote](deepnote/README.md) / [English](deepnote/README.en.md) | v0.1 收尾：检索—利用之间的证据组织 | 源码阅读、两项 stub 控制检查 | 真实 note 组织、适应性检索或训练 |
| [PilotDeck memory](pilotdeck-memory/README.md) / [English](pilotdeck-memory/README.en.md) | v0.2 收尾：集合依赖与真实记忆流程 | 源码阅读、四项上游纯函数检查、四个已有 E4 案例映射 | 模型抽取、Dream、平台与预算 baseline |

## 命名与复用

- `longmem-study-v1` 只描述补充研究 manifest；`study_id` 区分研究，`probe_id` 区分最小检查。不能将其作为 `longmem-experiment-v1` 的正式结果读入。
- `representation` 与 `transformation` 为未来新实验的提议字段，不新增到冻结 contracts。
- `memory_studies` 是唯一补充实现 package，顶层 `run.py` 与 `build_case_map.py` 仅为入口。复用 longmem 的 I/O/hash，不另写模型 backend、selector 或评分器。
- 上游源码只在外部 checkout 中读取和执行限定函数，不 vendoring 到主仓库。固定 commit、被核查文件 hash 与永久链接保留在各 study 中。
- 若推进到真实模型实验，先制定独立协议和预算，再新增实验目录。现有研究材料不声称已完成这一步。

中英文研究页保持相同范围、固定源码和证据边界。v0.1 Stage 1–4 与 v0.2 E1–E4 保留原编号，收尾研究不编号为 E5；原模型结果保持冻结。

## 证据核验

在包含 `ea7b5713ab5fd00d975fabb6fad81082817ed100` 提交的 checkout 中运行 `PYTHONPATH=src python studies/verify.py`。第一批 v0.1 检查位于 `deepnote/results/v01-source-probe/`，从该提交读取精确源码；联合 study 检查使用当前固定实现。`source-history.json` 显式记录每次运行的源码来源。浅克隆需先获取该提交，不改写历史 manifest。
