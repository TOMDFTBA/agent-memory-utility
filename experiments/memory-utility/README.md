# 第三阶段：Memory Utility

在第二阶段冻结数据上比较“检索到”与“答对”。不训练模型，不修改第一阶段记忆库，不依据生成结果选择评测样本。

## 运行

从项目根目录执行（真实模型需要本机 GPU，沙箱可能不可见）：

```bash
.venv/bin/python experiments/memory-utility/generate_dataset.py
.venv/bin/python experiments/memory-utility/run_ablation.py --output experiments/memory-utility/results/new-run
.venv/bin/python experiments/memory-utility/report.py experiments/memory-utility/results/new-run
```

同一输出目录可续跑；数据、配置或推理源码变化时拒绝续跑，使用新目录。逐条回答立即写入 JSONL；不吞掉推理错误。意外中断若产生不完整末行，会明确报 JSON 错误，应先备份并移除不完整末行再续跑。生成数据时会重写 dataset.jsonl 及其 manifest；默认输入不变时输出确定。

工程测试不加载模型，结果明确标记 `test`，不能作为模型效果：

```bash
.venv/bin/python experiments/memory-utility/run_ablation.py --backend test --limit 2 --output experiments/memory-utility/results/new-smoke
.venv/bin/python experiments/memory-utility/report.py experiments/memory-utility/results/new-smoke
.venv/bin/python -m pytest -q
```

## 固定实验设计

- 三种子 11/22/33，各取 18 个测试主题的第一个改写，共 54 个问题。没有使用按失败挑选的 utility-candidates 作为测试集；主题结构仍跨种子重复。
- 每个问题 5 种控制条件 + 2 种真实检索策略 × top-1/3/5，共 594 次生成。
- 五条件：空证据、正确当前事实、另一主体的无关事实、新旧事实（交替顺序）、时间戳规则整合新旧事实。
- 整合模块只读取输入记忆，不读取 query 或 gold；按 subject/relation 选时间最新项，保留 source_ids，并去掉 Currently 前缀。与冲突条件比较同时改变长度、旧事实有无和措辞，不能归因于纯压缩。
- 检索回放使用第二阶段 balanced-10000 三种子的 full-1 与 semantic_dedup-0.5。保留原排名，通过 canonical_id 计算命中；保留状态读取对应索引 ID 映射。仅回放推理，不重复计时检索。
- MiniCPM-2B-SFT 使用现有 Generator，greedy decoding、最多 24 个新 token、输入上限 2048；超限报错。采用固定纯文本短答案模板，未调优 chat template。
- 不向生成器提供 gold、canonical_id、保留标签或评分信息，仅输入记忆正文与问题。

## 指标与核验

主指标为短答案规范化 Exact Match，补充 token F1；规范化忽略大小写、标点及英文冠词，但不接受仅包含正确词的长回答。Utility 是逐问题相对 No memory 的 EM 差值。报告各条件正/负效用数量、种子间 SD、生成 tokenizer 的记忆 tokens。

真实检索条件另报 Recall@k、目标被删数量、检索未命中数量及命中但答错数量。后一项不能证明模型内部没有使用证据。固定合成事实的规则整合不会自动产生事实损坏；若回答恶化，要区分措辞变化和评分格式影响。

report.py 核验数据散列、配对完整性、重复、原始提示、证据 ID、标准答案、重算评分与检索标签，再生成 JSON/CSV/Markdown/PNG。原始提示、回答、耗时和证据 ID 均可复查。

## 结果

- [真实模型报告](results/v0.1/report.md)
- [五条件结果图](results/v0.1/memory-utility-table.png)
- [技术说明](../../docs/memory-utility-note.md)

限制：英文合成数据、单生成模型、18 个主体主题、仅时间均衡场景、单一整合规则、无独立长度匹配和固定 token 预算试验，不使用 LLM judge。无关项可能与目标具有相同答案值，偶然答对不能解释为有效使用了该主体的证据。冲突案例含显式 Currently/Previously 提示，不能推广到隐式或矛盾时间线。

## 后续控制实验

已增加独立的[时间措辞与输出协议控制实验](controls/README.md)：先在六个开发主题上选择并冻结协议，再回到原测试集比较保留/删除 Currently 的整合版本。第一版结果保留，补充报告单独记录；这不是新盲测。
