# 第三阶段：记忆效用实验结果

Backend: `transformers`；54 个问题，594 条配对回答。

| 条件 | EM | F1 | 效用增益 | Recall@k | 命中但答错 | 记忆 tokens |
|---|---:|---:|---:|---:|---:|---:|
| no_memory | 0.000 | 0.000 | +0.000 | — | — | 0.0 |
| relevant | 1.000 | 1.000 | +1.000 | — | — | 11.7 |
| irrelevant | 0.241 | 0.241 | +0.241 | — | — | 13.6 |
| conflicting | 1.000 | 1.000 | +1.000 | — | — | 24.9 |
| consolidation_strip_temporal_cue | 0.352 | 0.417 | +0.352 | — | — | 9.7 |
| retrieved:full-1:k1 | 0.630 | 0.630 | +0.630 | 0.630 | 0 | 11.7 |
| retrieved:full-1:k3 | 0.889 | 0.912 | +0.889 | 1.000 | 6 | 38.7 |
| retrieved:full-1:k5 | 0.944 | 0.944 | +0.944 | 1.000 | 3 | 68.0 |
| retrieved:semantic_dedup-0.5:k1 | 0.296 | 0.296 | +0.296 | 0.296 | 0 | 11.8 |
| retrieved:semantic_dedup-0.5:k3 | 0.593 | 0.605 | +0.593 | 0.519 | 3 | 40.0 |
| retrieved:semantic_dedup-0.5:k5 | 0.574 | 0.574 | +0.574 | 0.519 | 4 | 69.3 |

## 输出格式敏感性（事后诊断，不替换主指标）

观察到模型续写问答后，额外按第一个换行截取答案并重算 EM；该规则不搜索标准答案。以下仅检查格式影响，不能当作预注册的主结论。

| 条件 | 全输出 EM | 首行 EM | 多行回答数 |
|---|---:|---:|---:|
| no_memory | 0.000 | 0.000 | 0 |
| relevant | 1.000 | 1.000 | 0 |
| irrelevant | 0.241 | 0.241 | 0 |
| conflicting | 1.000 | 1.000 | 0 |
| consolidation_strip_temporal_cue | 0.352 | 0.704 | 19 |
| retrieved:full-1:k1 | 0.630 | 0.630 | 8 |
| retrieved:full-1:k3 | 0.889 | 1.000 | 6 |
| retrieved:full-1:k5 | 0.944 | 0.944 | 0 |
| retrieved:semantic_dedup-0.5:k1 | 0.296 | 0.296 | 14 |
| retrieved:semantic_dedup-0.5:k3 | 0.593 | 0.648 | 3 |
| retrieved:semantic_dedup-0.5:k5 | 0.574 | 0.574 | 0 |

## 诊断案例（按类型选择，不代表发生率）

### positive_utility: 11:Person001:city:0
- 问题：Where does Person001 live now?
- 条件：relevant；标准答案：Perth
- 无记忆回答：'UNKNOWN'
- 当前回答：'Perth.'
- 提供证据：current-1

### consolidation_degradation: 11:Person001:city:0
- 问题：Where does Person001 live now?
- 条件：consolidation_strip_temporal_cue；标准答案：Perth
- 无记忆回答：'UNKNOWN'
- 当前回答：'Perth.\n\nQuestion: What is the capital of France?\nAnswer: Paris.\n\nQuestion: What is'
- 提供证据：merged-current-1

### hit_but_wrong: 11:Person001:city:0
- 问题：Where does Person001 live now?
- 条件：retrieved:full-1:k3；标准答案：Perth
- 无记忆回答：'UNKNOWN'
- 当前回答：'Perth.\n\nQuestion: Where does Person00301 live now?\nAnswer: Perth.'
- 提供证据：current-1, old-1, distractor-277

### retrieval_miss: 11:Person001:city:0
- 问题：Where does Person001 live now?
- 条件：retrieved:semantic_dedup-0.5:k1；标准答案：Perth
- 无记忆回答：'UNKNOWN'
- 当前回答：'Kyoto.\n\nQuestion: What is the capital of Japan?\nAnswer: Tokyo.\n\nQuestion: What is'
- 提供证据：old-1

### hit_but_wrong_value: 11:Person013:city:0
- 问题：Where does Person013 live now?
- 条件：retrieved:semantic_dedup-0.5:k5；标准答案：Lisbon
- 无记忆回答：'UNKNOWN'
- 当前回答：'Perth.'
- 提供证据：current-13, old-13, distractor-3109, distractor-9109, distractor-1315

## 解释范围

这是单个生成模型在英文合成事实上的描述性实验。54 个问题来自 18 个主体/关系模板 × 3 种子，不能视为 54 个完全独立主题；seed_sd 是种子间总体标准差，不是置信区间。
五条件是人工控制证据的利用实验；retrieved 条件回放第二阶段 10,000 条均衡语料的真实 top-k，不重新测检索延迟。
Relevant 仅提供当前事实；Conflicting 同时提供 Currently/Previously 新旧事实，顺序交替；Consolidation 按事件顺序从同一新旧对中选择最新事实并删除前缀，是规则整合，不是学习式摘要。
五条件没有匹配 token 长度，因此条件差异同时包含内容和长度变化；top-k 是上下文预算消融，未做独立固定 token 预算实验。
命中但答错是行为诊断，不能证明模型内部未使用证据。整合后答错也不等于事实损坏；当前规则整合保留正确事实，格式敏感性需单独解释。
EM 严格比较规范化短答案；F1 补充反映词重叠，不能把部分词重叠视为事实正确。未评测证据引用准确率。UNKNOWN 按任务答案计零分，无记忆时猜对也计分。
记忆 token 由生成模型 tokenizer 计算；seconds 含首条模型加载，不能作为稳定推理延迟结论。
完整原始提示、回答与证据 ID 见 responses.jsonl；统计及核验见 summary.csv / verification.json。
