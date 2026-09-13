# E1 开发 pilot 协议

状态：工程实现与开发 pilot；不是正式冻结实验协议。修改协议或源码后必须使用新输出目录。

## 范围与数据

固定快照、一次性存储删除、固定未来窗口。输入为 JSON 数组，每项包括 trajectory_id、user_id、split、snapshot_id、event_order、memories、history_queries、future_queries。memory 包含 memory_id、canonical_id、event_order、content，可提供 leakage_group；未来问题包含 query_id、event_order、text、gold_answer、supporting_memory_sets（多个可替代的支持集合，每个集合内需要全部证据）。

先按用户/轨迹分 split，再构造窗口。生产数据需为模板改写和语义近重复指定同一 canonical_id 或 leakage_group；自动校验能识别这些组与规范化文本重合，不能自动证明任意自然语言无语义泄漏。future_queries 应由数据生产者提供连续 H 个任务；本 runner 校验顺序和边界，无法证明上游未遗漏任务。

内置数据是 6 条独立合成开发轨迹，每 split 2 条，每快照 3 条记忆，未来窗口 H=2。内置 test split 仅用于工程验证，不是正式 blind test。真实压力场景、多证据样本规模及正式窗口长度需经模型 pilot 确认。

## 系统和评分

复用 longmem 的 embedding 和 generation backend。对固定候选视图计算点积，按分数降序、memory_id 升序排序，取前 top_k；按此顺序装入可容纳的完整记录，跳过装不下的记录。不截断单条、不填充上下文。memory token 成本覆盖规范 JSON 的 memory_id/content 及记录间换行；其余元数据不提供给生成器。模型使用生成器 tokenizer，add_special_tokens=False；测试后端用 UTF-8 字节成本，不能解释为模型 token 数。

固定 prompt 要求仅返回短答案。评分沿用 v0.1 保守规范化：casefold、移除 ASCII 标点和英文冠词、规范空格；exact match 为主，空格 token F1 为辅。历史检索仅使用当时已经存在的记忆，不读取未来查询或支持标注。当前生成器 do_sample=False；不同 seed 的重复主要探测执行稳定性，不代表对随机采样分布的估计。

## 干预与标签

完整、no_memory、每条候选的 storage_deletion，使用相同问题和 seed。删除只过滤进程内视图，不连接或修改 MemoryStore/持久化日志。context_deletion 从完整上下文移除指定记录、不补位、保留顺序；按历史检索频次非零/为零两层抽样 memory，对选中 memory 的全部未来问题执行。

U = full EM - deletion EM，V_LOO = 窗口内平均 U。重复运行保存独立窗口值、均值、总体标准差及三分类符号一致率。负值表示删除有益；零值不等于内在无用。所有候选都生成标签。开发阈值见 configs/pilot.json：|V| <= minimum_effect 作为零效应；标准差超阈值或符号一致率不足标 uncertain，不丢弃原始标签。不确定标签不能在后续训练中直接当作零。

## 验收

逐题输出保存存储 IDs、检索排序、上下文、prompt、答案、得分、token 成本、seed 和运行身份。独立重算校验完整性、删除隔离、上下文不补位、预算与评分；缺失/失败不能补零。异常 manifest 标 FAILED，续跑仅复用严格身份一致的已保存记录；末尾 JSONL 损坏显式失败，需人工审计后修复。

门槛只使用 train/validation：至少两次重复、全部开发 storage 标签稳定、轨迹平均 full-no_memory 差异达到 minimum_memory_dependency。test 标签只作 hindsight 诊断。test backend 永远 ready_for_stage2=false。COMPLETE 表示当前运行及校验完整，不表示研究假设成立或 E1 科学验收通过。

正式实验前须用 model backend 测量时延、非零比例和方差，冻结规模、成本上限、采样比例、阈值与协议。当前报告提供诊断分布，尚不提供正式轨迹 bootstrap 推断；模型依赖不足或噪声过大时不得扩大 predictor。
