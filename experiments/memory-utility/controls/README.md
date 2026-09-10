# 第三阶段补充控制实验

补充两项检查：输出协议是否造成第一版格式失分，以及整合记忆删除 `Currently` 前缀是否影响回答。第一版脚本、配置、594 条回答及主结果图保持原样。

## 复现

从主项目根目录运行：

```bash
.venv/bin/python experiments/memory-utility/controls/control_common.py
.venv/bin/python experiments/memory-utility/controls/run_controls.py dev --output experiments/memory-utility/controls/results/new-dev
.venv/bin/python experiments/memory-utility/controls/run_controls.py freeze --output experiments/memory-utility/controls/results/new-dev --frozen experiments/memory-utility/controls/new-frozen.json
.venv/bin/python experiments/memory-utility/controls/run_controls.py test --output experiments/memory-utility/controls/results/new-test --frozen experiments/memory-utility/controls/new-frozen.json
.venv/bin/python experiments/memory-utility/controls/report_controls.py experiments/memory-utility/controls/results/new-test --dev experiments/memory-utility/controls/results/new-dev
```

真实运行需要本机 GPU 与现有 MiniCPM 模型；不会下载或训练模型，也不静默切换到测试替身。同目录可续跑，配置/数据/源码/模型元数据不符时拒绝续跑。完整输出再次运行只验证并退出，不重新加载模型。

`--backend test` 仅测试工程链路；开发输出会标记 test，不能冻结为真实模型评测协议。测试用冻结文件应另存，如 `--frozen /tmp/longmem-test-protocol.json`。不要覆盖正式 `frozen-protocol.json`。

## 设计

- `dev.jsonl`：seed 77 的六个开发主题，每主题第一条查询，主体与测试集隔离。
- `test.jsonl`：原 54 个问题；这是已观察数据的后续诊断，不能称为新盲测。
- 开发阶段六条件 × 四协议 × 六问题 = 144 条；按六条件平均 EM 选择，平分按固定协议顺序。选择函数只接受 dev manifest。
- 候选协议：plain_eos、plain_line、chat_eos、chat_line。Chat 模板来自本地 tokenizer；其他内容提示不变。`*_line` 在出现非空文本后的第一个换行处停止，不读取或匹配标准答案。
- 冻结后每个测试问题运行六控制条件和六个真实检索回放条件，共 648 条。
- 六控制条件：无记忆、相关、无关、新旧冲突、保留 Currently 的整合、删除 Currently 的整合。
- 两个整合版本均由原冲突记忆按时间选择最新项，事实值与 provenance 相同。保留前缀的正文等于 Relevant，因此也是确定性一致性检查；不把相同文本当作两种独立策略的有效性证据。

生成限制与原版相同：greedy、use_cache=False、最多 24 个新 token、2048 输入 token。规范化 EM/F1 未修改。每条记录保存原始输出、协议答案、生成 token ID、终止原因和完整提示。首次模型加载在计时前完成，本轮耗时与第一版含首条加载的时间不直接比较。

## 文件与结果

- [固定设计](design.json)、[开发集选择](frozen-protocol.json)
- [补充结果报告](results/test/report.md)
- [配对差值](results/test/paired-effects.json)、[核验记录](results/test/verification.json)
- [对比图](results/test/control-comparison.png)

报告会验证开发集选择、输入与源码散列、模型元数据、完整配对、提示、评分、原版内容提示一致性，以及 Relevant/保留前缀输出一致性。源权重分片未散列，模型元数据散列不能替代权重身份保证。

## 边界

六主题开发集很小；平均 EM 包含无关记忆偶然猜对，不能当作一般输出协议排名。Currently 增加两个左右的 token，未做等长度占位对照，因此结论只支持该具体措辞干预，不区分纯长度与语义作用。检索记录、答案空间、单模型与主体重复等原有限制仍存在。
