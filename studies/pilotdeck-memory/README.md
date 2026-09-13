# PilotDeck：记忆流程与集合依赖研究

[English](README.en.md) | 简体中文

日期：2026-09-14。固定上游为 [OpenBMB/PilotDeck@97633a0](https://github.com/OpenBMB/PilotDeck/tree/97633a08a73eca3d65c79494f9aa31cc18fd019f)。本研究作为 v0.2 E1–E4 之后的收尾，补充系统讨论，不新增 E3 baseline，不修改冻结结果，不声称运行了完整平台或 Dream 模型流程。

## 为什么研究这个系统？

v0.2 发现，真实单条 LOO 在冗余证据上可能同时为零；互补证据读全后也可能生成错误答案。PilotDeck 提供了观察记忆进入、组织和回查路径的具体系统参照。白盒可见性是可审计条件，不等于记忆具有高 future retention value。

## 固定源码中的记忆流程

```text
Agent messages
      ↓
provider normalization → captureTurn → L0 session capture
                                          ↓
                                 heartbeat extraction
                                          ↓
                              file memories + manifests
                               ↓                    ↓
                     reasoning retrieval       staged Dream
                               ↓                rewrite/merge
                       memory attachment       snapshot/rollback
```

| 问题 | 固定源码观察 | 对研究的含义 |
|---|---|---|
| 如何捕获？ | Provider 转换 canonical messages；service 默认 last_turn、包含 assistant、单条 maxMessageChars=6000 | 捕获范围和字符上限与 token retention budget 不是同一个概念 |
| 如何抽取？ | captureTurn 进入 captureL0Session；heartbeat 调用分类和 user/project/feedback note 抽取 | 原始 turn 与最终 memory entry 不同，不能直接按行数对齐 |
| 如何存储？ | service 配置 control.sqlite 和 memory 文件目录；FileMemoryStore 管理正文与元数据 | 应保留来源与版本映射，不能只比较最终文本 |
| 如何读取？ | ReasoningRetriever 使用项目/manifest 选择及文件读取；存在数量与行数限制 | 未在本次核查路径中找到与固定 B_store/B_read 可直接等价的保留策略 |
| 如何整理？ | Dream 在 stage 中处理，生成修订条目，记录 delete/write mutations，再替换 live roots | 整理改变内容与集合，不是单纯选择子集 |
| 如何回滚？ | 保存整理前 snapshot，rollbackLastDream 调用快照恢复并重置检索状态 | 可用于前后配对核查，但本次未执行该流程 |
| 隔离是否绝对？ | 默认 workspace 路径，同时 repository 接收 globalRootDir | 不能据 README 推断所有记忆都严格禁止跨 workspace；需另测具体路由 |

源码证据：[Provider](https://github.com/OpenBMB/PilotDeck/blob/97633a08a73eca3d65c79494f9aa31cc18fd019f/src/context/memory/EdgeClawMemoryProvider.ts#L94)、[service](https://github.com/OpenBMB/PilotDeck/blob/97633a08a73eca3d65c79494f9aa31cc18fd019f/src/context/memory/edgeclaw-memory-core/src/service.ts#L620)、[heartbeat](https://github.com/OpenBMB/PilotDeck/blob/97633a08a73eca3d65c79494f9aa31cc18fd019f/src/context/memory/edgeclaw-memory-core/src/core/pipeline/heartbeat.ts#L550)、[retrieval](https://github.com/OpenBMB/PilotDeck/blob/97633a08a73eca3d65c79494f9aa31cc18fd019f/src/context/memory/edgeclaw-memory-core/src/core/retrieval/reasoning-loop.ts#L23)、[Dream](https://github.com/OpenBMB/PilotDeck/blob/97633a08a73eca3d65c79494f9aa31cc18fd019f/src/context/memory/edgeclaw-memory-core/src/core/review/dream-review.ts#L680)。完整文件 hash 见 [upstream.json](upstream.json)。

## 已运行的最小检查

直接导入上游已提交的 lib/message-utils.js，仅执行 normalizeMessages；未安装依赖或启动服务。四条输入消息分别携带代码前半段和后半段，并配有 assistant 回答。

| probe_id | 已观察结果 |
|---|---|
| last_turn | 当前调用返回最后一条 user 及其 assistant，即 u2/a2 |
| full_session | 返回 u1/a1/u2/a2 |
| user_only | 不含 assistant 时返回 u1/u2 |
| character_truncation | maxMessageChars=5 将 abcdefghij 转为 abcde... |

四项检查通过，模型调用为 0。[原始输出](results/source-probe/probes.json)、[manifest](results/source-probe/manifest.json)。运行时为本机 Node 20.19.2，低于上游 core 声明的 Node >=22.13,<23；这里只验证无依赖 JS 纯函数，不构成平台安装兼容性验证。

**last_turn 在一次调用中只返回后半段，不证明系统遗忘了前半段。** 前一轮可能已被捕获、抽取并存储。完整判断需要逐轮写入、flush 后存储检查和后续检索，本次没有运行这些模型/持久化路径。

## 从 E4 得到的案例交接

[e4-case-map.json](e4-case-map.json) 从已冻结 E4 读取四个案例：两组各一个 redundancy 和 complementarity，按稳定 snapshot ID 选择，不按最大收益挑选。保存原始支持集合、16 个子集分数及输入 hash，不新增答案或 PilotDeck 结果。

| 场景 | 后续检查 | 不能据此预判 |
|---|---|---|
| redundancy | 逐轮捕获后是否至少保留一个替代事实；Dream 前后来源是否可回查 | 不预设 Dream 会误删或一定改善 |
| complementarity | 前后半段在抽取后是否都可恢复；是否完整读入；生成是否仍失败 | 不把 last_turn 的单次输出当成长期丢失证据 |

后续必须分别记录 capture、stored entries、retrieved evidence 和 answer 四层。先定位失败发生在哪层，再判断是否需要修改 retention、组织或 generator。

## Baseline 与模块边界

当前没有名为 pilotdeck 或 whitebox_memory 的 retention candidate。若提取出可分离的淘汰规则，才在相同候选集合、generator、retriever、B_store/B_read 下做算法级比较。整个平台比较须另列 system study，不能和 E3 固定系统策略混表。

未来适配器可放入 integrations/pilotdeck-memory；实际接入前不创建空模块。memory_id 由来源标识和版本稳定映射，保留 upstream_record_id、workspace、source_memory_ids。Dream 产生的新文本用 transformation 描述，不占用 retention policy 或 E1 condition 命名空间。

复用现有评分、I/O、配置与结果读取。E4 案例直接读取已审计 subset-scores，不复制枚举器、LOO、selector 或统计实现。当前研究共享实现仅在 studies/memory_studies，顶层 studies/run.py 与 build_case_map.py 负责 CLI。

## 复现命令

在仓库根目录、安装本项目后运行。上游 checkout 的 commit 和文件 hash 必须与 upstream.json 匹配；输出使用新空目录。

```bash
python studies/run.py pilotdeck-memory --checkout /path/to/PilotDeck --output /tmp/pilotdeck-memory-probe
python scripts/release_artifacts.py restore-results
python studies/build_case_map.py --output /tmp/pilotdeck-e4-cases.json
```

本次已完成源码审查、四项捕获函数检查和已有 E4 案例映射。模型驱动的抽取/Dream/检索以及统一预算 baseline 均为后续独立实验，不作为 v0.2 发布门槛。
