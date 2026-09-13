# E1 扩展协议 v1（真实推理前冻结）

目的：增加独立轨迹与历史信号变化，补充互补任务的测量诊断；不训练 E2 predictor，不改动既有 E1 原始结果。本协议继承 protocol.md 的时间、隔离干预、评分、抽样和标签定义。

## 扩展主实验

- generate_e1_extension.py，数据 seed=2026091301。48 条全新用户轨迹，train=24、validation=12、test=12，四场景在各 split 内均衡。每轨迹四条记忆，H=2 个连续未来任务，二题询问同一完整答案，不作为独立统计样本。
- 训练每场景6条，验证与测试各3条。身份 opaque，不在 memory ID 内编码 split、场景或答案。实体与事实独立，canonical/leakage_group 保持等价事实组在同一 split；不沿用旧实验事实。模板是共享合成语法，不能宣称对未见模板泛化。
- 随机化 memory 的事件位置（old_but_useful 的有用证据固定为最早）、中性 provenance 文本长度和历史查询次数。历史均早于决策时刻30；未来查询位于31、32。frequent_but_useless 的无用服务台记录被历史查询3–5次，真实检索频次在结果中核查；若不满足，作为场景实现失败报告，不事后重抽。
- 主模型、prompt、规范化、top_k=3、B_read=1024 均沿用前次 E1。三次确定性重复 seeds=20260912/13/14。参数阈值不变。
- 全部四类候选覆盖 storage deletion。每条轨迹从历史频次为零/非零两层各抽至多1条执行 context deletion，不能依未来表现选样。
- 最多2304次真实生成，累计逐题运行上限5400秒；达到上限则保存不完整状态，不把部分结果当完整实验。
- 测试轨迹与开发轨迹在生成数据时分开，主协议/诊断条件均预先冻结；不依据扩展测试结果修改系统。本次 E1 的测试标签只作为 hindsight 评估，后续 E2 不得用于拟合或调参。

## 互补诊断（只用 train/validation）

固定选择扩展数据的全部9条开发 complementarity 轨迹，不筛选成功或失败样本。每条2题、3个seed，提供四个上下文条件，216次额外生成，上限900秒：

1. support_only：仅包含两条标注支持证据，按快照事件顺序。
2. support_reversed：颠倒上述两条证据的顺序。
3. prefix_only：仅包含前三位证据。
4. suffix_only：仅包含后三位证据。

全部沿用主实验 prompt/generator/评分/read budget，不重新检索。baseline 使用主实验 full 原始输出。支持标注仅在这个明确标注的 hindsight 诊断使用，不进入历史特征或可部署策略。

同时记录 full 是否包含全部支持证据，以及输出是否等于 prefix/suffix、是否包含完整答案并附加其他数字、UNKNOWN 或其他错误。仅解释可观察行为：支持证据提供后的变化可能涉及长度、顺序和干扰，不能声称证明模型内部因果机制。不存在支持证明的标签不强行改判；不会通过答案抽取修补 exact match。

## 报告与交付

- 原始输出、独立重算、存储/上下文/预算检查、源码和输入摘要；运行前归档源码、协议和数据。
- 按 split、场景、轨迹汇总 full/no_memory、正零负/uncertain标签、非零比例和重复稳定性；总体与分split轨迹 bootstrap（seed20260912，5000次）95%区间。压力场景各25%，不代表自然任务分布。
- 历史特征与标签按 ID 连接输出 train/validation 交接表；test-features 单独输出，test 标签单独命名 hindsight，禁止将诊断元数据混入特征。uncertain 原值保留，不当零。
- 进入 E2 的自动门槛仍只看 train/validation memory 依赖>=0.1、每个开发标签std<=0.05且sign stability=1。分场景/标签样本数单独报告；门槛通过不保证192条标签足够训练可靠 predictor。
- 保留前次结果与当前负结果；互补失败不自动归因于 retention。若需要改变系统，应另起协议及新标签版本，而不是覆盖本次结果。
