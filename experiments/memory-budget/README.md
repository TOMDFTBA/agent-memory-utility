# 第二阶段：记忆预算与检索实验

本目录保留开发历史说明，但正式入口已经收敛为 v0.1。使用 MiniCPM-Embedding，不训练模型，不向第一阶段记忆库回写任何实验内容。

## 当前运行与结果

- 原始先导结果：100/500 条、单一编辑器主题；作为开发期输出保留在本地，不随正式发布提交。
- [原始排名诊断](results/pilot-diagnosis.json)：90 次查询的 top-1 均为同一实体的旧事实。定位了错误类型，但不宣称解释模型内部原因。当前编码实现与本地官方 README 的 Query 前缀、mean pooling 一致。
- v2 小规模复验：两场景、100/500 条、三种子、三个预算，共 120 组；作为开发期输出保留在本地。
- [v0.1 完整结果](results/v0.1/report.md)：两场景、五档规模、三种子、三个预算，共 300 组。
- [初步结论与第三阶段衔接](results/v0.1/observations.md)：三条数据观察、归一化成本指标，以及 10 个诊断案例。
- [结果核验](results/v0.1/verification.json)：300 组预算、主题隔离、逐查询召回和保留率均通过检查。

## 从数据到图表

从项目根目录运行，每次指定新的输出目录。真实模型需要本机 GPU；不自动降级为 Hash。

```bash
.venv/bin/python experiments/memory-budget/benchmark.py \
  --calibration-file experiments/memory-budget/configs/frozen-v0.1.json \
  --output experiments/memory-budget/results/new-full
.venv/bin/python experiments/memory-budget/verify_results.py experiments/memory-budget/results/new-full
.venv/bin/python experiments/memory-budget/report.py experiments/memory-budget/results/new-full
.venv/bin/python experiments/memory-budget/analyze.py experiments/memory-budget/results/new-full
```

首次重新校准可省略 `--calibration-file`，仅使用 seed=77 的开发查询；不能依据测试结果挑选阈值。现有 `frozen-v0.1.json` 来自小规模复验，阈值 0.90，并校验模型版本。更换模型应重新做开发集校准。

默认规模 100/500/1,000/5,000/10,000，种子 11/22/33，计时重复 5 次。`--sizes 100 500` 运行先导；`--backend hash-test` 仅工程验证，不得使用真实模型的冻结阈值文件或宣称语义质量。依赖沿用项目虚拟环境，绘图额外使用 matplotlib。

语料编码按种子一次编码最大规模，其余规模和场景复用相同文本向量。缓存以模型版本和完整文本列表散列寻址；删除专用缓存后可重新生成。每组保存语料、查询、top-5 预测、索引 ID 映射和校验值、原始计时样本。每个预算的索引建成并测量后移除二进制副本，避免重复占用数 GB；可从缓存精确重建并校验：

```bash
.venv/bin/python experiments/memory-budget/build_index.py \
  experiments/memory-budget/results/v0.1 balanced-10000-11/semantic_dedup-0.5
```

## 数据与可比较性

- 固定 24 个主体事实，6 种关系（编辑器、城市、编程语言、交通、饮料、项目）。每个事实有旧版本、新版本，12 个新版本有完全相同的重复副本。
- 6 个开发主题与 18 个测试主题按主体隔离，覆盖各关系和多个时间位置。每主题 4 条查询改写，共 72 条测试查询/种子。主实验种子不使用校准种子 77。
- `old` 场景将目标放在较早位置；`balanced` 将目标时间分布到整个区间。两个场景只有时间元数据不同，内容与查询一致。检索文本表达 Currently/Previously，不含绝对日期。
- 不同规模语料嵌套，查询固定，旧事实始终保留在原始候选语料中。无关项和其他实体的相似事实随规模增加。
- 重要度为随机元数据，对同一事实家族一致；它不代表“已知效用”，不使用测试答案设置优先级。
- 重复项固定为 12 条，比例随规模下降；尚未做固定重复率的独立消融。

## 策略与评分

Full 保留 100%；Recency、Importance、Semantic dedup 各比较 25%/50%/75% 固定预算。

语义策略先按新到旧，用精确最近邻相似度阈值贪心筛选代表项；代表项按该顺序优先占预算，不足预算时按原有时间顺序补回被抑制项。它是**去重优先的预算保留策略**，不是单纯阈值压缩。记录代表项数量和选择耗时；最坏仍是平方复杂度。

开发集在 0.90/0.95/0.98 三个阈值间，以三个预算的平均等价事实 Recall@5 选择；主实验冻结后不再修改。

主指标 Recall@1/5 和 MRR 按 `canonical_id` 识别等价事实；并同时报告原始 `memory_id` 的精确 ID 指标。MRR 使用完整候选排名，未命中为零，不截断在 top-5。保留策略删除目标时仍计入分母；`target_retained` 分离“目标已删除”与“目标在库但未检索到”。等价关系由生成器给出，仅用于评分，不供语义保留算法使用。旧事实不会因属于同一主体被认作正确答案。

## 计时和成本

- FAISS CPU 固定单线程、IndexFlatIP、归一化 float32；MiniCPM 使用配置中的 GPU、bf16、文档 batch=8，查询 batch=1。
- 查询先预热，每种子 72 条 × 5 次，打乱执行顺序，保存 360 个查询编码样本；其样本在场景/规模/策略间共享，降低重复计算，也意味着这些计时不是独立样本。
- 每个策略索引单独预热，同样执行 360 次 top-5 搜索，保存原始样本。完整排名的 MRR 计算不计入搜索延迟。
- `retrieval` 延迟为对应查询编码样本与搜索样本之和，属于分项合成估计，不是现场端到端测量。不包含模型/索引加载、事件日志重放、MCP、回写或 prompt 构造。
- 报告 P50/P95，汇总为三个种子的分位数均值和总体标准差；不将 SD 当成置信区间。
- 索引大小只计 FAISS 二进制；token 使用 embedding 模型 tokenizer 计算 top-5 文本，不含提示模板。它是统一成本代理，并非任意生成模型的实际计费 token。
- 选择时间、建索引时间单独记录；语义排序复用于三个预算，各预算行报告其完整选择成本，不可将三行当成独立运行成本相加。

## 解释限制

这是英文合成数据的规模研究，主体数仍小，改写不等于独立问题，跨种子复用主题结构。不能把结果推广成真实长期聊天、所有重要度算法或任意硬件的性能结论。第三阶段需进一步判断命中事实是否改善回答，而不是只看召回。

旧版重复 runner 已移除。开发期 smoke、pilot 和 v2-full 目录仅留在本地或由 `.gitignore` 排除；公开结果以 `results/v0.1` 为唯一口径。
