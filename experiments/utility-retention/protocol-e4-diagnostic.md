# v0.2 E4 冻结诊断协议

2026-09-13。独立E4，不重新拟合E2、不修改E1/E2/E3源码和冻结结果。prepare在模型运行前复制协议、配置、数据和源码并计算hash。完成以manifest及独立audit为准。

## 数据和目标

区分预测、预算启发式、单条目标的非加性/不可辨别性以及生成器限制。不预设graph有效或要求方法获胜。

e3_posthoc完整复用E3正式24轨迹，属于事后解释。e4_independent新增24轨迹，四场景各6、N=4、H=2；沿用E1扩展语法及E3数据adapter，structure_seed=2026091701、surface_seed=2026091702，检查与E1扩展所有split及E3正式的实体、答案、文本、ID不重叠。测试fixture用2026091801/2026091802。支持标注不进历史特征或可部署选择。两组分开统计，不声称未见语法泛化；两题同源相关，统计单位是轨迹。

先完成4记忆闭环，不要求扩大到8–12条。每快照全部16子集，两组共1536个子集/问题/seed条件。评估包括full等预算不可行子集供LOO和交互；best_subset只从各预算可行集合中选取。

## 系统、命名和复用

沿用E3 MiniCPM-Embedding + MiniCPM-2B-SFT、prompt、评分、token序列化、top_k=3、B_read=1024、generation_seed=20260912。存储预算10%/25%/50%/75%，主平均仅后三项。沿用full-a10、importance规则、dedup=0.8和random三个seed。full豁免store预算。

唯一入口e4.py，模块utility_retention.e4、e4_analysis、e4_controls、e4_report。复用Engine、historical_features、score、serialize、predict（经make_deployable）、select、baseline评分、make_deployable、hindsight_plans、loo_labels、expected_conditions、verify_responses、summarize、paired、failure_analysis、公共I/O/model_identity。无fit调用、动态加载、全局路径修改或冻结共享源重构。

candidate继续表示策略，新增局部候选predicted_sum_optimal、hindsight_loo_sum_optimal；后者和best_subset不可部署。前者只读past和预测。hindsight_loo仍为真实LOO+原排序选择器；full-a10是模型ID，full是参照。不修改冻结共享contracts。

diagnostic=subset_enumeration仅请求存储条件，不进策略排名。condition=context_deletion/context_support_forward/context_support_reversed仅用于独立上下文对照。存储响应key仍为(snapshot_id, sorted storage_ids, query_id, seed)；上下文key另含condition、deleted_memory_id，不共用缓存。metrics用命名空间；cohorts.json为输入映射、cohort-summaries.json为汇总，避免输入输出同名。

## 精确集合和并列

对全部预算可行集合分别最大化预测分数和、full集合真实LOO和、实际窗口EM。分数差≤1e-12算并列，优先小token成本、少记录、稳定ID，不按未来EM打破前两个目标的并列；允许空集。保存所有加总最优集合ID、实际EM范围和所选EM。best_subset按最高EM、成本、条数、ID选择；只有完整枚举才使用该名称，缺失不当零。

冗余LOO全零时，有效子集可能同样为最优，应报告目标不可辨别而不是所有LOO最优解都失败。实际EM差异可负，不能强制拆成非负误差。除实际EM外检查同一分数和的最优值。

## 机制与预算

每快照全部6记忆对、各4背景，计算I=F(C+i+j)-F(C+i)-F(C+j)+F(C)。保存四集合及分数、条件边际。支持对单独汇总，空背景/全部背景分开，记录正零负，不把相关背景当独立样本。

复用支持集成本和失败分类：答对、放不下、未保留、未读全、读全答错。替代支持取最小成本，互补求和。正确但无标注支持另记。核验old顺序及frequent指定干扰的真实历史命中。

每个互补快照每题4个上下文条件：支持ID正序/反序的仅支持上下文；从full实际上下文分别删两条支持、不补位。它们不进存储最优排名。单条/联合storage条件已全枚举。长度、顺序、覆盖变化不能归成单一内部因果机制。

## 冻结、重复与完成

可部署greedy及精确预测选择在未来评估前封存。best_subset选定后，对其全部唯一条件用相同seed独立模型调用复核，不缓存、不按复核重选。保存变化；确定性重复不估计随机解码方差，不消除同一窗口挑最大值的泛化乐观偏差。

父E3审计通过、所有顶层hash不变、模型/源码/检索配置一致才原样继承600回答和96 importance。继承文件进新输入hash，保存父身份，绝不仅凭ID命中。新响应逐条持久化、身份一致续跑，控制与复核分开JSONL。成本区分继承和新调用。

上限1536枚举条件、96新importance、1600新回答（增量+复核+上下文）、7200秒新逐例累计模型时间。运行前检查枚举量，运行中及最后检查实耗。超限保留FAILED，不冒充COMPLETE。

验收：父结果不变、预测选择重算、全部枚举覆盖、预算核验、LOO/并列/交互/评分/失败/轨迹统计/成本重算、上下文和独立复核完整、实际token重算。效果来自model backend。bootstrap=5000，seed=20260912，区间仅描述性，不追加效果门槛。

v0.3方向：真实/预测差→历史预测；精确/启发式同目标差→选择器；集合最优/单条目标及并列范围差→集合条件化价值；best_subset低且支持齐全→组合回答。负结果照常交付。
