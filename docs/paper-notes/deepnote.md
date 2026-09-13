# DeepNote：从检索片段到问题条件化的证据笔记

[English](deepnote.en.md) | 简体中文

阅读与源码检查日期：2026-09-14。上游固定为 [thunlp/DeepNote@cc2f013](https://github.com/thunlp/DeepNote/tree/cc2f0132737e04ec2d895e8c21673cee612ca1e7)。本文补充 v0.1 的技术联系，不新增冻结实验阶段，也不声称复现论文效果。

## 方法回答什么问题？

DeepNote 将 note 作为一次问题求解中不断积累、修订的证据状态：初次检索后生成 note，根据当前最好 note 构造下一次检索问题，结合新增片段修订 note，经比较后决定是否替换，最后用保留的 note 回答。

它不等同于离线把 chunk 换成 note 再建索引。源码中的 init_note、refine_note 和 compare_note 都接收当前 query；因此这种 note 首先是 query-conditioned working evidence，而不是已经证明可跨未来任务复用的持久记忆。[实现](https://github.com/thunlp/DeepNote/blob/cc2f0132737e04ec2d895e8c21673cee612ca1e7/src/main.py#L165)

```text
query → retrieve → initial note
                    ↓
            new query → retrieve → refine → compare
                    ↑                         ↓
                    └──── retained best note ─┘
                                  ↓
                                answer
```

## 源码与最小检查

| 机制 | 源码观察 | 本地检查边界 |
|---|---|---|
| 初始 note | 当前 query 与检索 refs 一起进入模板 | 未评估生成质量 |
| note 更新 | 比较器认可时替换 best_note | 模拟返回验证接受与拒绝分支 |
| 停止 | max_step 与失败次数上限；失败次数是累计值 | False / True / False 序列在两次失败后停止 |
| 最终回答 | gen_answer 读取 best_note，而非无条件读取最后一次修订 | 两次拒绝时保留 initial note |
| provenance | 保存 ref_log、note_log、query_log | 不等于 note 内每个事实都有稳定引用 ID |

本次只抽取并执行上游 retrieve_note 控制函数，检索、note 生成和比较器全部使用确定性 stub；没有导入其带 API/模型初始化的 CLI，也没有训练或生成真实答案。两项检查通过，记录见[源码检查](../../studies/deepnote/results/v01-source-probe/probes.json)。

## 与 v0.1/v0.2 的联系

v0.1 已区分“检索到”与“回答正确”。DeepNote 提供的是中间证据组织的参考，不补写成 v0.1 已实现模块。v0.2 的 future retention 决策只能用过去信息；不能把看到未来测试 query 后生成的 note 作为该决策的历史输入。

下一次独立实验可研究：固定检索结果后改变证据组织方式，能否减少检索命中但回答错误？这是待验证的假设。

## 后续受控实验边界

首个对照建议使用 raw_evidence、plain_summary、structured_note 三种 representation；它们不写入 retention candidate。固定原始证据、generator、答案评分及最终 read budget。另记组织阶段的模型调用、输入/输出 tokens 和耗时，不能把 note 的构造成本隐藏在较短最终 prompt 后面。

测量 answer.exact_match、answer.token_f1、支持事实保留、来源可追溯和错误新增事实。来源检查需要逐事实核验，不能以“附带 ID”代替真实性。

若只改证据表示，称为 DeepNote-inspired evidence organization；若加入自适应检索，再控制检索轮数和总计算预算。当前不训练原论文的偏好数据流程，也不提前选择最优表示。

## 命名与复用

复用 longmem.config、longmem.generation、既有实验评分接口、longmem.experiment_io；检索结果和 memory_id 保持可回查。未来 note 是派生表示，记录 source_memory_ids，不覆盖原 memory_id 或原文本。如需 prompt 变体，使用独立组织接口，保留冻结实验实现。

本次实现仅位于 studies/memory_studies，使用 longmem-study-v1 与 study_id，和正式实验的 experiment_id 分开。[执行入口与固定来源](../../studies/deepnote/README.md)。

来源：[论文](https://aclanthology.org/2025.findings-emnlp.1073/)、[固定源码](https://github.com/thunlp/DeepNote/tree/cc2f0132737e04ec2d895e8c21673cee612ca1e7)。
