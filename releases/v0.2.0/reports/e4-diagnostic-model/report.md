# v0.2 E4：集合依赖诊断

后端：model。独立审计：True。

e3_posthoc是已观察E3测试集的事后解释；e4_independent是运行前冻结的新实体/事实轨迹。
两组共享合成语法，各24条轨迹、四场景等比例、每条4记忆和2题；不构成分布外或自然用户泛化证据。

每快照完整枚举16个存储集合，每子集重新检索，固定系统、top_k=3、B_read=1024。
best_subset仅是该窗口、系统、预算、有限候选和单次确定性评估下的经验最高分。
10%预算是参照，跨预算主平均仅含25%/50%/75%。

## e3_posthoc

| 集合/参照 | 10% EM | 25% EM | 50% EM | 75% EM |
|---|---:|---:|---:|---:|
| utility_aware | 0.0000 | 0.2083 | 0.5417 | 0.8958 |
| predicted_sum_optimal | 0.0000 | 0.2083 | 0.5417 | 0.8958 |
| hindsight_loo | 0.0000 | 0.1667 | 0.5000 | 0.6458 |
| hindsight_loo_sum_optimal | 0.0000 | 0.1667 | 0.5000 | 0.6458 |
| best_subset | 0.0000 | 0.2500 | 0.7500 | 0.8958 |
| importance | 0.0000 | 0.1250 | 0.3333 | 0.5833 |
| recency | 0.0000 | 0.0833 | 0.1667 | 0.3333 |
| retrieval_frequency | 0.0000 | 0.0833 | 0.2917 | 0.3750 |
| semantic_dedup | 0.0000 | 0.0833 | 0.1667 | 0.3750 |
| random | 0.0000 | 0.1250 | 0.4028 | 0.6389 |
| full | 0.8750 | 0.8750 | 0.8750 | 0.8750 |
| no_memory | 0.0000 | 0.0000 | 0.0000 | 0.0000 |

三个主预算先在轨迹内平均；轨迹bootstrap描述性95%区间，未做多重比较校正。

| 对照 | EM差异 | 区间 |
|---|---:|---|
| best_subset − utility_aware | +0.0833 | [0.0278, 0.1389] |
| best_subset − predicted_sum_optimal | +0.0833 | [0.0278, 0.1389] |
| best_subset − hindsight_loo | +0.1944 | [0.0694, 0.3333] |
| best_subset − hindsight_loo_sum_optimal | +0.1944 | [0.0694, 0.3333] |
| predicted_sum_optimal − utility_aware | +0.0000 | [0.0000, 0.0000] |
| hindsight_loo_sum_optimal − hindsight_loo | +0.0000 | [0.0000, 0.0000] |
| hindsight_loo − utility_aware | -0.1111 | [-0.2778, 0.0417] |

### LOO并列最优

| 场景（主预算平均） | 选定EM | 最低EM均值 | 最高EM均值 | best_subset EM |
|---|---:|---:|---:|---:|
| complementarity | 0.1944 | 0.1944 | 0.1944 | 0.1944 |
| frequent_but_useless | 0.7778 | 0.7778 | 0.7778 | 0.7778 |
| old_but_useful | 0.7778 | 0.7778 | 0.7778 | 0.7778 |
| redundancy | 0.0000 | 0.0000 | 0.7778 | 0.7778 |

并列规则：分数差≤1e-12时优先小token成本、少记录、稳定ID；不读取未来EM打破加总目标并列。
最优范围包含好坏集合时，说明目标不可辨别，不能称所有LOO最优解都失败。

### 标注支持对交互

| 支持对 | 背景 | 个数 | 负/零/正 | 平均交互 |
|---|---|---:|---|---:|
| redundant_support | empty | 6 | 6/0/0 | -1.0000 |
| redundant_support | all_backgrounds | 24 | 24/0/0 | -0.9792 |
| complementary_support | empty | 6 | 0/1/5 | 0.5833 |
| complementary_support | all_backgrounds | 24 | 0/4/20 | 0.5000 |

背景条件相关，不是独立样本；语义互补不保证当前模型能组合答案。

### 互补上下文对照

| 条件 | EM |
|---|---:|
| context_deletion | 0.0000 |
| context_support_forward | 0.6667 |
| context_support_reversed | 0.3333 |

forward/reversed按支持ID正序/反序；context_deletion从full实际上下文删指定支持项、不补位。
这些是hindsight上下文诊断，不参与存储排名，不把长度/顺序/覆盖变化解释成单一内部机制。

### 主方法失败位置

| 预算 | 答对 | 放不下 | 未保留 | 未读全 | 读全答错 |
|---|---:|---:|---:|---:|---:|
| 10% | 0.00% | 100.00% | 0.00% | 0.00% | 0.00% |
| 25% | 20.83% | 75.00% | 4.17% | 0.00% | 0.00% |
| 50% | 54.17% | 25.00% | 20.83% | 0.00% | 0.00% |
| 75% | 89.58% | 0.00% | 0.00% | 0.00% | 10.42% |

## e4_independent

| 集合/参照 | 10% EM | 25% EM | 50% EM | 75% EM |
|---|---:|---:|---:|---:|
| utility_aware | 0.0000 | 0.3333 | 0.7083 | 0.8125 |
| predicted_sum_optimal | 0.0000 | 0.3333 | 0.7083 | 0.8125 |
| hindsight_loo | 0.0000 | 0.1667 | 0.5000 | 0.5625 |
| hindsight_loo_sum_optimal | 0.0000 | 0.1667 | 0.5000 | 0.5625 |
| best_subset | 0.0000 | 0.3750 | 0.7500 | 0.8542 |
| importance | 0.0000 | 0.2500 | 0.4583 | 0.5833 |
| recency | 0.0000 | 0.3333 | 0.4167 | 0.4583 |
| retrieval_frequency | 0.0000 | 0.2083 | 0.2917 | 0.3333 |
| semantic_dedup | 0.0000 | 0.2083 | 0.3750 | 0.5000 |
| random | 0.0000 | 0.2778 | 0.3750 | 0.5486 |
| full | 0.8125 | 0.8125 | 0.8125 | 0.8125 |
| no_memory | 0.0000 | 0.0000 | 0.0000 | 0.0000 |

三个主预算先在轨迹内平均；轨迹bootstrap描述性95%区间，未做多重比较校正。

| 对照 | EM差异 | 区间 |
|---|---:|---|
| best_subset − utility_aware | +0.0417 | [0.0069, 0.0833] |
| best_subset − predicted_sum_optimal | +0.0417 | [0.0069, 0.0833] |
| best_subset − hindsight_loo | +0.2500 | [0.0972, 0.4236] |
| best_subset − hindsight_loo_sum_optimal | +0.2500 | [0.0972, 0.4236] |
| predicted_sum_optimal − utility_aware | +0.0000 | [0.0000, 0.0000] |
| hindsight_loo_sum_optimal − hindsight_loo | +0.0000 | [0.0000, 0.0000] |
| hindsight_loo − utility_aware | -0.2083 | [-0.3889, -0.0417] |

### LOO并列最优

| 场景（主预算平均） | 选定EM | 最低EM均值 | 最高EM均值 | best_subset EM |
|---|---:|---:|---:|---:|
| complementarity | 0.0833 | 0.0556 | 0.1389 | 0.1389 |
| frequent_but_useless | 0.8333 | 0.8333 | 0.8333 | 0.8333 |
| old_but_useful | 0.7222 | 0.7222 | 0.7222 | 0.7222 |
| redundancy | 0.0000 | 0.0000 | 0.9444 | 0.9444 |

并列规则：分数差≤1e-12时优先小token成本、少记录、稳定ID；不读取未来EM打破加总目标并列。
最优范围包含好坏集合时，说明目标不可辨别，不能称所有LOO最优解都失败。

### 标注支持对交互

| 支持对 | 背景 | 个数 | 负/零/正 | 平均交互 |
|---|---|---:|---|---:|
| redundant_support | empty | 6 | 6/0/0 | -1.0000 |
| redundant_support | all_backgrounds | 24 | 24/0/0 | -1.0000 |
| complementary_support | empty | 6 | 0/2/4 | 0.4167 |
| complementary_support | all_backgrounds | 24 | 0/12/12 | 0.2708 |

背景条件相关，不是独立样本；语义互补不保证当前模型能组合答案。

### 互补上下文对照

| 条件 | EM |
|---|---:|
| context_deletion | 0.0000 |
| context_support_forward | 0.4167 |
| context_support_reversed | 0.5000 |

forward/reversed按支持ID正序/反序；context_deletion从full实际上下文删指定支持项、不补位。
这些是hindsight上下文诊断，不参与存储排名，不把长度/顺序/覆盖变化解释成单一内部机制。

### 主方法失败位置

| 预算 | 答对 | 放不下 | 未保留 | 未读全 | 读全答错 |
|---|---:|---:|---:|---:|---:|
| 10% | 0.00% | 100.00% | 0.00% | 0.00% | 0.00% |
| 25% | 33.33% | 62.50% | 4.17% | 0.00% | 0.00% |
| 50% | 70.83% | 25.00% | 4.17% | 0.00% | 0.00% |
| 75% | 81.25% | 0.00% | 0.00% | 0.00% | 18.75% |

## 稳定性、成本与边界

1536个枚举回答、768个子集分数、1152个背景交互可重算。
独立重新执行186个best_subset条件，答案/评分变化0个。
同seed重复仅验证确定性，不估计随机解码方差、不消除同一窗口最大值选择的泛化乐观偏差。
继承600个回答；新增1218个回答（含复核及上下文），新增96个importance。
新增逐例累计模型时间817.1秒；不等于含初始化、身份摘要、历史特征及审计的墙钟时间。

## v0.3判断规则

- 精确预测分数和与主方法之差：检查预算选择器；实际EM可能下降，分数提升不保证回答改善。
- 真实LOO与预测之差：仅作标签/预测对照，不强制非负。
- best_subset与LOO最优得分范围：区分目标不能打破并列与所有加总最优解都落后。
- 互补best_subset仍低且支持读全：优先检查固定系统组合回答限制，不能直接归结为需要graph。
- 未来修改模型须用新版本与新盲测；本轮不重新拟合。

完整数据见cohort-summaries.json、ties.json、interactions.json；逐集合案例见cases.md。
