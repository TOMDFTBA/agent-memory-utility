# 实验命名与模块开发指南

本指南约束当前 v0.1 基底及后续实验。v0.1 已完成一次破坏性迁移：规范字段、共享模块和唯一 runner 均已落地，正式结果也已重新生成。旧格式只作为本地开发历史，不再是发布接口。

## 设计原则

1. 同一概念只有一个规范名称。
2. 存储时间、合成事件顺序和运行耗时使用不同字段。
3. 记忆选择、内容整合和检索模态使用不同命名空间。
4. 实验记录使用稳定 schema；报告代码只读取 schema，不猜测字段含义。
5. 公共 I/O、hash、运行环境记录和模型配置不得在新实验中重复实现。
6. 冻结结果不因重构被静默重写；必要时通过 adapter 读取旧格式。

## 规范字段

### 记忆与目标

| 规范名称 | 类型 | 含义 | v0.1 兼容来源 |
|---|---|---|---|
| `memory_id` | string | 一条物理记忆记录的 ID | `memory_id` |
| `canonical_id` | string | 等价事实组的 ID | `canonical_id` |
| `target_memory_id` | string | 要求精确命中的物理记录 | `target`，仅在旧数据中二者相同时 |
| `target_canonical_id` | string | 任务接受的等价事实 | `target` |
| `supersedes_id` | string/null | 被该记录替代的物理记忆 | `supersedes` |

新实验不得继续使用语义不明确的单独 `target`。精确命中和等价事实命中必须分别计算。

### 时间与顺序

| 规范名称 | 类型 | 含义 |
|---|---|---|
| `created_at` | ISO 8601 string | 真实记忆写入时间，必须带时区 |
| `event_order` | integer/float | 合成数据中的事件相对顺序 |
| `recency_rank` | integer | 按指定规则计算后的新旧排名，0 为最新 |
| `duration_seconds` | float | 一次操作或推理的耗时 |

旧合成数据中的浮点 `timestamp` 仅由 `canonical_event_order()` 兼容读取。新数据必须写 `event_order`；不得将其传入核心 `Memory.timestamp`，也不得与真实墙钟时间比较。

### 策略与条件

保留策略决定“哪些记录留下”，统一使用：

```text
full
random
recency
importance
semantic_dedup
utility_aware
oracle_utility
```

内容条件决定“向生成器展示什么”，统一使用：

```text
no_memory
relevant
irrelevant
conflicting
consolidation_keep_temporal_cue
consolidation_strip_temporal_cue
```

不要用 `merged` 同时表示去重、选择与摘要。v0.1 的 `consolidated`、`merged_keep_current` 和 `merged_strip_current` 由 `canonical_condition()` 映射。

### 检索模态

统一使用：

```text
visual
native_text
ocr_text
```

不再使用含义模糊的 `pdf` 和 `ocr`。旧结果通过 `canonical_modality()` 映射。

### 指标

指标 key 使用 `<namespace>.<metric>`：

```text
retention.target_fact_rate
retention.exact_memory_rate
retrieval.recall_at_1
retrieval.recall_at_5
retrieval.mrr
answer.exact_match
answer.token_f1
answer.hit_but_wrong_rate
cost.index_bytes
cost.retrieval_p50_ms
```

新结果统一放在 `metrics` 对象中，不再混用 `recall1`、`recall_at_1`、平铺 `exact_match` 和嵌套 `scores`。

## 配置约定

所有新 runner 统一支持：

```text
--model-config PATH
--output PATH
--backend NAME
--seed N 或 --seeds N...
```

配置优先级：

```text
显式命令行参数 > LONGMEM_CONFIG > configs/local.yaml
```

使用 `longmem.config.load_config()`；不要在脚本中再次硬编码或自行解析模型路径。公开 manifest 保存模型逻辑名称、revision 与文件摘要，不保存绝对路径。

后端名称按职责分开：

- embedding：`minicpm`、`hash_test`
- generation：`transformers`、`evidence_test`
- experiment execution：`model`、`test`

配置文件暂时接受 v0.1 的连字符值 `hash-test` 和 `evidence-test`；新 Python 标识符、枚举和值优先使用下划线。

## 模块边界

推荐结构：

```text
src/longmem/
  config.py                 # 唯一配置入口
  experiment_io.py          # JSON/JSONL、hash、runtime metadata
  experiment_contracts.py   # 名称、schema version、v0.1 adapter
  embedder.py               # embedding backend
  generation.py             # generation backend

experiments/<experiment>/
  protocol.md               # 冻结问题、假设和指标
  dataset.py                # 仅构造数据
  policies.py               # 仅选择/整合策略
  run.py                    # 编排，不实现通用 I/O
  evaluate.py               # 只根据结果 schema 评分
  report.py                 # 只生成表格与图
  configs/
  results/
```

`run.py` 不应动态导入另一个阶段的同名脚本，也不应修改被导入模块的全局路径。跨阶段复用必须来自 `src/longmem` 或一个有唯一 package 名称的模块。

## 公共 I/O

新实验使用 [experiment_io.py](../src/longmem/experiment_io.py)：

```python
from longmem.experiment_io import (
    append_jsonl,
    read_jsonl,
    runtime_metadata,
    source_hashes,
    write_json,
)
```

- JSON 使用 UTF-8、禁止 NaN、固定缩进并保留结尾换行。
- manifest 与汇总文件采用原子替换。
- JSONL 每行必须是 object，空行和损坏行显式失败。
- source hash 的 key 必须是项目相对路径，避免同名文件冲突和本机路径泄露。
- 长推理输出逐条 `append_jsonl()`，支持中断后审计。

## Manifest 最低字段

```json
{
  "schema_version": "longmem-experiment-v1",
  "experiment_id": "utility-retention-v0.2",
  "status": "RUNNING",
  "protocol_sha256": "...",
  "dataset_sha256": "...",
  "source_hashes": {},
  "model": {
    "name": "MiniCPM-2B-SFT",
    "revision": "...",
    "metadata_sha256": {}
  },
  "runtime": {},
  "parameters": {}
}
```

运行开始先写 `RUNNING`，全部输出和验证成功后再原子更新为 `COMPLETE`。续跑必须比较 protocol、dataset、source、model 和 parameters identity。

## v0.1 迁移状态

- Stage 2 使用 `event_order`、明确的 target ID 与嵌套 query/prediction 结构；旧 runner 已删除。
- Stage 3 主实验与控制实验共享标准答案、评分和检索字段；正式主实验及冻结控制已重跑。
- Stage 4 使用独立页面数据模块与 `visual/native_text/ocr_text` 命名；旧动态导入 runner 已删除并重跑。
- `experiment_contracts.py` 保留少量旧格式 adapter，仅用于读取本地历史数据，不允许新产物写旧字段。

任何再次改变正式 runner 的修改都必须写入新输出目录并重跑对应验证，不能让旧报告悄悄指向新源码。

## 新实验检查清单

- [ ] protocol 在运行前冻结
- [ ] 不使用裸 `target` 或浮点 `timestamp`
- [ ] policy、condition、modality 使用规范名称
- [ ] 指标置于带 namespace 的 `metrics`
- [ ] 配置支持统一入口，不硬编码本机路径
- [ ] 使用共享 experiment I/O 和项目相对 source hash
- [ ] 测试 backend 明确标记，不能生成模型效果 claim
- [ ] 输出目录不覆盖既有运行
- [ ] manifest 从 RUNNING 转为 COMPLETE 前完成验证
- [ ] 报告明确数据、模型、硬件和统计边界
