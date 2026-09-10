# 第二阶段实验结论与第三阶段衔接

1. 全量历史从 100 增至 10000 条时，等价事实 Recall@5 从 1.000 变为 0.949，Recall@1 从 0.759 变为 0.718。这反映该固定查询集面对新增干扰项的变化，不是新增主体问题的评估。
2. 在 10000 条、保留 50% 的同等预算下，均衡场景的近期策略 Recall@5 为 0.537，语义去重优先策略为 0.519；旧知识场景近期策略为 0.000。策略表现依赖目标事实的时间分布。
3. 全量 10000 条的 FAISS 索引为 87.89 MiB，50% 预算索引为 43.95 MiB。全量内存搜索 P50 为 1.743 ms，而查询编码 P50 为 34.659 ms。分项合成检索 P50 为 36.421 ms，不代表完整服务延迟。

## 额外归一化指标

以下为端点描述性差值，不是线性拟合或因果结论。召回损失以百分点计，可以为负。

| 场景 | 策略 | 预算 | 每压缩10%的 Recall@5 损失（百分点） |
|---|---|---:|---:|
| balanced | importance | 25% | 8.46 |
| balanced | importance | 50% | 9.26 |
| balanced | importance | 75% | 10.00 |
| balanced | recency | 25% | 9.69 |
| balanced | recency | 50% | 8.24 |
| balanced | recency | 75% | 7.41 |
| balanced | semantic_dedup | 25% | 9.44 |
| balanced | semantic_dedup | 50% | 8.61 |
| balanced | semantic_dedup | 75% | 7.41 |
| old | importance | 25% | 8.46 |
| old | importance | 50% | 9.26 |
| old | importance | 75% | 10.00 |
| old | recency | 25% | 12.65 |
| old | recency | 50% | 18.98 |
| old | recency | 75% | 37.96 |
| old | semantic_dedup | 25% | 12.41 |
| old | semantic_dedup | 50% | 18.61 |
| old | semantic_dedup | 75% | 37.22 |

均衡场景全量索引：从 100 到 10000 条，FAISS 搜索 P50 的端点差值约为 0.1750 ms/千条。

## 下一阶段

使用 utility-candidates.json 中的代表性查询建立 No memory / Relevant / Irrelevant / Conflicting / Consolidated 五条件对照，比较检索命中与答案得分。候选案例是按失败类型挑选的诊断样本，不是无偏测试集。

特别检查旧事实排第一时模型是否仍能利用 top-5 中的新事实；去重后目标缺失是否会损害答案；以及保留更多事实的收益能否抵消上下文开销。

本阶段没有评估生成器得分，不能据此宣称哪种策略最有利于推理。主实验限制、阈值选择、计时口径及完整结果见 report.md 和上级 README。
