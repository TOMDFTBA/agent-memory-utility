# DeepNote：方法联系与控制流程检查

[English](README.en.md) | 简体中文

本项作为 v0.1 Stage 1–4 之后的收尾，补充技术谱系；完整分析见 [DeepNote 方法笔记](../../docs/paper-notes/deepnote.md)。当前没有新增 note-based retention policy，也没有修改 v0.1/v0.2 的模型实验。

## 已完成

- 固定 thunlp/DeepNote 的 commit 与六个源码/模板文件 hash：[upstream.json](upstream.json)。
- 核查 query-conditioned note 初始化、修订、比较、累计失败停止和最终 best_note 回答。
- 执行上游 retrieve_note 控制函数的两项 stub 检查；[输出](results/v01-source-probe/probes.json)、[manifest](results/v01-source-probe/manifest.json)。
- 明确未来 raw_evidence / plain_summary / structured_note 对照的变量、成本与复用边界。

## 复现

```bash
python studies/run.py deepnote --checkout /path/to/DeepNote --output /tmp/deepnote-control-probe
```

从仓库根目录运行，先安装本项目；checkout 必须匹配固定 commit/hash，输出必须为新空目录。实现只执行 AST 中经审查的 retrieve_note，模型和检索均用 stub，不运行上游 CLI 的 API 初始化或训练代码。

这两项检查证明的是控制分支行为，不证明 note 的质量、检索提升或长期价值。受控表示实验尚未执行；后续使用独立 protocol 和结果目录，不倒填 v0.1.1 或原 v0.1 冻结实验。

此处记录为独立 v0.1 补充重新运行生成；先前联合 study 的历史记录保留在开发工作区，本次没有改写历史 manifest。
