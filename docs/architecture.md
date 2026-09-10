# 第一阶段架构与恢复约定

```mermaid
flowchart LR
    Q[用户查询] --> U[UltraRAG YAML pipeline]
    U --> S[Memory MCP Server]
    S --> E[MiniCPM-Embedding / ROCm]
    E --> F[FAISS CPU 向量检索]
    F --> P[带 memory_id 的证据与提示词]
    P --> G[MiniCPM 生成 / ROCm]
    G --> A[回答]
    A --> W[记忆写入 + 来源与证据 ID]
    W --> J[JSONL 事件日志]
    J --> D[SQLite 结构化状态与向量缓存]
    D --> F
```

本阶段实现 Agent Memory 分支。外部知识库可在后续接入同一提示词构建阶段；当前 demo 不声称已接入外部 KB。

## 数据与接口

`Memory` 包含 `memory_id/content/timestamp/importance/source/embedding_version/supersedes/metadata`。
ID 在日志和 SQLite 中为字符串主键。FAISS 内部使用连续整数位置，`index.json` 的 `memory_ids` 数组提供可审计的一一映射，不生成第二套业务 ID。

- `write`：先验证、持有目录级跨进程文件锁，追加 JSONL 并 `fsync`，再更新 SQLite。
- `get`：按 ID 返回记录，允许读取已被替代的历史。
- `list`：默认返回有效记忆，支持包含历史。
- `search`：默认只检索有效记忆，返回完整记录和余弦相似度。
- `rebuild_index`：从 SQLite 向量缓存或重新编码构建 FAISS。

没有指定 ID 时，以内容、来源、重要度、替代关系和 metadata 的规范 JSON 摘要生成 ID；相同逻辑写入重试不新增事件。需要记录两次内容相同但独立发生的事件时，调用者应传不同 ID 或不同 `metadata.session_id`。指定 ID 的不同载荷会报错。

`supersedes` 必须指向已有的有效记录，避免自环、不存在引用和分叉替代。旧记录仍保留。新记录到达后即替代旧记录，当前实现不按任意回填 timestamp 推断事实的新旧。

## 崩溃与恢复

| 情况 | 行为 |
|---|---|
| JSONL 已落盘，SQLite 未提交 | 下次操作重放日志，补全状态 |
| JSONL 尾部写了一半，没有换行 | 保存 `torn-*.bin`，截去未提交尾部，保留此前完整事件 |
| 已完成的日志行损坏 | 报告行号并停止，不静默跳过 |
| SQLite 丢失 | 从 JSONL 重建记录；需要时重新生成向量 |
| FAISS 或 manifest 丢失/校验失败 | 从 SQLite 向量缓存或记忆内容重建 |
| embedding 版本变化 | 使用新版本缓存和索引，不修改历史事件的原始版本 |
| JSONL 丢失但 SQLite 仍有记录 | 停止并要求恢复日志备份，不把数据库误认作完整历史 |

索引写入采用临时文件、`fsync` 和原子替换。manifest 包含版本、维度、ID 映射和索引文件 SHA-256；两文件之间崩溃会导致校验失配，随后自动重建。
JSONL 是权威历史，SQLite 和 FAISS 是派生数据。运行期间不能手工改写日志；应定期备份整个数据目录。
SQLite 文件损坏不是自动删除的理由：停止服务、备份损坏文件，移走 SQLite 后从完整 JSONL 恢复。

## 向量与生成

MiniCPM 使用本地模型、自带 tokenizer、官方均值池化和 L2 归一化。模型内部已经施加位置权重，外部不再重复加权。查询前缀为 `Query: `，文档不加前缀。
版本摘要包含模型修订、配置、模型代码、tokenizer 内容、权重文件大小/修改时间、截断长度和查询前缀。
这是本地缓存失效标识，不是模型权重的密码学校验；发布实验时应固定可信的模型 commit 与权重校验和。

生成器使用已有 MiniCPM SFT 基座，第一阶段不加载 RAG-DDR LoRA、不进行训练。
`use_cache=False` 避免旧 MiniCPM 代码和新 Transformers 的 KV cache API 冲突，适合短演示但不是吞吐优化。
回答以 `source=generated` 和 `metadata.verified=false` 写入，并记录所有检索证据 ID。它们目前也可被再次检索，不能将模型回写当成用户确认事实；来源筛选与效用策略属于后续实验。

## 第一版边界

- Linux/Unix 本地文件系统，依赖 `fcntl.flock`，不支持 Windows 或分布式并发。
- 每次操作扫描日志；写入后下一次检索重建有效集合的索引。适用于最小工程验证，规模实验前应测量并优化。
- SQLite 缓存历史 embedding 版本，当前未做缓存清理。
- 检索是 top-k 相似度，没有经标注数据校准的相关性阈值，可能返回无关项。
- 单库无用户隔离、无鉴权；stdio 服务应仅由受信任的本地调用者启动。
- 不含 graph memory、自动反思、多智能体或第二至第四阶段实验。
