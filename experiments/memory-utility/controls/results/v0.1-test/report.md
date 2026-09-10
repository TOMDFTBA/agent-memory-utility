# 第三阶段补充实验：时间措辞与输出协议

开发集 6 个主题 × 6 条件 × 4 协议 = 144 次；按开发集 EM 选择 `plain_line`。冻结后在原有 54 个问题上运行 12 条件，共 648 次。

## 开发集协议选择

| 协议 | 开发集 EM |
|---|---:|
| chat_line | 0.556 |
| chat_eos | 0.556 |
| plain_line | 0.639 |
| plain_eos | 0.583 |

所有条件同权，平分按预先规定的 chat_line、chat_eos、plain_line、plain_eos 顺序选择。仅用 seed 77 的开发主体；测试主体不参与协议选择。

## 冻结协议下的结果

| 条件 | EM | F1 | 效用 | Recall@k | 命中但答错 |
|---|---:|---:|---:|---:|---:|
| no_memory | 0.000 | 0.000 | +0.000 | — | — |
| relevant | 1.000 | 1.000 | +1.000 | — | — |
| irrelevant | 0.241 | 0.241 | +0.241 | — | — |
| conflicting | 1.000 | 1.000 | +1.000 | — | — |
| consolidation_keep_temporal_cue | 1.000 | 1.000 | +1.000 | — | — |
| consolidation_strip_temporal_cue | 0.704 | 0.704 | +0.704 | — | — |
| retrieved:full-1:k1 | 0.630 | 0.630 | +0.630 | 0.630 | 0 |
| retrieved:full-1:k3 | 1.000 | 1.000 | +1.000 | 1.000 | 0 |
| retrieved:full-1:k5 | 0.944 | 0.944 | +0.944 | 1.000 | 3 |
| retrieved:semantic_dedup-0.5:k1 | 0.296 | 0.296 | +0.296 | 0.296 | 0 |
| retrieved:semantic_dedup-0.5:k3 | 0.648 | 0.648 | +0.648 | 0.519 | 0 |
| retrieved:semantic_dedup-0.5:k5 | 0.574 | 0.574 | +0.574 | 0.519 | 4 |

## 配对控制

保留 Currently 相对删除前缀：平均 EM 差 +0.296；改善 16、恶化 0、不变 38 个问题。

两种整合的事实、来源与所选版本相同，正文只差 Currently 前缀。保留前缀与 Relevant 的输入正文完全一致，所有对应输出也一致；这不证明整合优于原始单条正确事实。前缀也增加 token，未做等长度同义改写对照。

| 条件 | 原协议 EM | 冻结协议 EM | 改善数 | 恶化数 |
|---|---:|---:|---:|---:|
| no_memory | 0.000 | 0.000 | 0 | 0 |
| relevant | 1.000 | 1.000 | 0 | 0 |
| irrelevant | 0.241 | 0.241 | 0 | 0 |
| conflicting | 1.000 | 1.000 | 0 | 0 |
| consolidation_keep_temporal_cue | 1.000 | 1.000 | 0 | 0 |
| consolidation_strip_temporal_cue | 0.352 | 0.704 | 19 | 0 |
| retrieved:full-1:k1 | 0.630 | 0.630 | 0 | 0 |
| retrieved:full-1:k3 | 0.889 | 1.000 | 6 | 0 |
| retrieved:full-1:k5 | 0.944 | 0.944 | 0 | 0 |
| retrieved:semantic_dedup-0.5:k1 | 0.296 | 0.296 | 0 | 0 |
| retrieved:semantic_dedup-0.5:k3 | 0.593 | 0.648 | 3 | 0 |
| retrieved:semantic_dedup-0.5:k5 | 0.574 | 0.574 | 0 | 0 |

原协议来自未覆盖的第一版回答；keep 对照映射原 Relevant，strip 映射原 Consolidated；已核验所有原始内容提示一致。跨协议差异可能包含对话包装与终止规则，不能一概解释为模型知识改善。

## 代表案例

- wording_improves / 11:Person002:language:0：标准答案 Rust；保留前缀 `Rust`；删除前缀 `UNKNOWN.`；全量 top-5 `Rust.`。
- wording_equal / 11:Person001:city:0：标准答案 Perth；保留前缀 `Perth.`；删除前缀 `Perth.`；全量 top-5 `Perth.`。
- remaining_retrieval_error / 22:Person005:project:0：标准答案 Delta；保留前缀 `Delta.`；删除前缀 `UNKNOWN`；全量 top-5 `Atlas.`。

## 限制与可复现性

这是一轮由第一版观察驱动的后续诊断，原测试集已被观察，不能声称新的盲测。开发集仅六个主题，选择稳定性有限；54 个问题仍来自 18 个主题 × 三种子。
主 EM 的规范化规则未改。*_line 在首个非空文本后的换行停止，并删除边界之后的后缀；不读取 gold。保留原始输出、实际 token ID、终止原因与协议后答案。*_eos 为 EOS 或固定 24-token 上限。
Chat 包装使用本地 tokenizer 中已有模板，plain 使用原始文本；生成参数均为 greedy、use_cache=False、24 新 tokens、2048 输入上限。
未训练模型、未扩充答案空间、未评测引用或真实长会话；无关记忆偶然答对和目标缺失时猜对的问题仍存在。
全部结果均为描述性配对统计。模型元数据与源码有散列，外部权重分片未散列。详见 design.json、frozen-protocol.json、manifest.json、responses.jsonl 与 verification.json。
