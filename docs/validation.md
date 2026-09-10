# 第一阶段验收记录

验证日期：2026-09-05（Asia/Shanghai）。

## 已完成

| 任务 | 实现与证据 |
|---|---|
| 统一工程骨架 | 独立 Git 仓库、Python 包、配置、测试、文档、demo 目录与 `.gitignore` |
| 记忆结构 | 八个要求字段、稳定 ID、版本标记、可审计替代链 |
| 持久化 | JSONL 先落盘，SQLite 投影，FAISS CPU 索引与版本缓存 |
| 核心接口 | write/get/search/list/rebuild_index，CLI 和 Python API |
| MCP | 独立 stdio 服务，真实进程调用 memory_write/search/get |
| UltraRAG | 官方 console CLI build/run，四步 pipeline 完整执行 |
| 跨会话 | 第一个 MCP 进程写入并结束；第二个进程经 UltraRAG 检索并使用；第三个独立进程复查 |
| 模型路径 | 本机 ROCm MiniCPM-Embedding + MiniCPM SFT，FAISS CPU |
| 可审计输出 | 原始 memory_id、命中内容、相似度、回答与 evidence_ids 存入 audit JSON |
| 展示交付 | README、Mermaid 架构图、一条 demo 命令、2–3 分钟录屏脚本 |

## 自动化测试

```bash
.venv/bin/python -m pytest -q
```

覆盖 20 个测试用例：写入读取、逻辑重试、ID 冲突、独立进程重启、检索命中、索引丢失/损坏、SQLite 丢失、日志先提交后的恢复、未完成尾部、完整坏行拒绝、日志丢失拒绝、事实替代、embedding 版本更新、线程与进程并发、仅凭 JSONL 完整恢复、参数校验。

工程测试采用明确的 HashEmbedder 测试替身，不能据此声称语义检索质量。

## 端到端实测

```bash
.venv/bin/python scripts/demo.py --mode test
.venv/bin/python scripts/demo.py --mode model
```

两种模式均 PASS。真实模型的输入为：

- `alice-editor`：Alice prefers Neovim as her code editor.
- `bob-garden`：Bob grows tomatoes in his garden.
- 问题：What editor does Alice prefer?
- 模型生成原文：`Neovim`。

原始事实在复查中的相似度约为 0.5304，干扰事实约为 0.0777；回写回答约为 0.5780。这只是可复查的最小案例，不是准确率 benchmark。
模型没有在回答正文中按提示格式输出 ID；完整证据引用由系统的 `metadata.evidence_ids` 与 audit JSON 保存。该字段记录提供给生成器的证据，不证明模型实际利用了每一条。

审计文件：

- `artifacts/demo/latest-test.json`
- `artifacts/demo/latest-model.json`

每个文件记录独立运行目录；该目录下的 stdout/stderr 和持久化文件不进入版本控制。

## 已知限制与未验收项

- 已初始化本地仓库，未发布 GitHub，也未制作视频文件；已交付可执行录屏脚本。
- 安装流程和本机环境已验证；没有实际访问第二台新机器做安装复验。
- `pip check` 未通过全量依赖一致性检查：UltraRAG 的非核心依赖没有全部安装，继承的系统环境有无关依赖冲突，详见 `technical-lineage.md`。
- 沙箱内 GPU 不可见，且 MCP stdio 握手挂起；端到端演示在获准的本机环境完成。
- 来源过滤、无关记忆阈值、长期回写污染与规模优化尚未实现，应由后续阶段评估。
- 本记录为第一阶段验收；第二阶段后续进展见 [记忆预算实验](../experiments/memory-budget/README.md)。第三、第四阶段不在本记录验收范围。
