# 第四阶段：VisRAG 与 OCR 的轻量对照

已完成真实本机三路检索：页面图像 → VisRAG-Ret；PDF 原生文本 → MiniCPM-Embedding；Tesseract OCR → MiniCPM-Embedding。固定 8 页、5 个问题，指定页排第一的数量分别是 5/5、4/5、3/5。只说明这一小组的检索行为，不代表视觉普遍更优或回答正确。

[三路结果](results/v0.1/report.md) · [案例分析](results/v0.1/observations.md) · [核验记录](results/v0.1/verification.json)

为避免在许可尚未逐项确认时再分发论文页面和大段抽取文本，公开仓库不包含页面截图、OCR/PDF 全文块及带原文摘录的本地案例文件；它们可由有权访问原论文的用户在本地重新生成。排名、分数、配置、文件摘要和聚合报告仍保留。

## 本机运行

在统一项目根目录执行。已有 GPU 模型环境、Poppler，以及位于 `cache/tesseract` 的独立 OCR 安装；不需要管理员密码、不修改系统 Python。首次运行生成默认结果目录，已有目录会报错以保护实验记录。本机已有已完成结果，因此复跑请指定新目录：

```bash
../VisRAG/.venv/bin/python experiments/multimodal-retrieval-mini/run_demo.py \
  --output experiments/multimodal-retrieval-mini/results/my-rerun
../VisRAG/.venv/bin/python experiments/multimodal-retrieval-mini/verify_run.py \
  experiments/multimodal-retrieval-mini/results/my-rerun
../VisRAG/.venv/bin/python experiments/multimodal-retrieval-mini/analyze_cases.py \
  experiments/multimodal-retrieval-mini/results/my-rerun
```

第一条需要 GPU 设备访问；后两条无需 GPU。模型仅离线加载，本机路径沿用兄弟目录 `VisRAG/model-VisRAG-Ret` 和 `MiniCPM-Embedding/model`。

在另一台兼容 Debian Trixie amd64 的机器上，可以先执行：

```bash
python3 experiments/multimodal-retrieval-mini/setup_ocr.py
```

脚本通过 apt 下载固定版本的官方 Debian 包并解压到项目缓存，记录包 SHA-256，需要网络。它依赖本机已有的常见动态库，不是通用容器或完整便携运行时。其他平台应通过平台包管理器安装 Tesseract 和英文数据；主脚本可回退使用 PATH 中的 Tesseract。缺少引擎、语言数据或空白识别结果会显式失败，不用原生文本替代 OCR。

## 与上游代码的对应关系

- OCR 引擎沿用上游 `visrag_scripts/demo/ocr_pipeline/pytesseract/demo.py` 的 Tesseract 路线。本实现通过命令行调用同一引擎，以同时保存 TXT 和 TSV；未额外安装 Python 包 pytesseract。
- 上游还提供 FastDeploy + PP-OCRv3 的 layout_preserving / adjacent_merging 示例，当前没有运行它们；其作者本机路径及模型依赖需要另行适配。
- VisRAG 使用上游位置加权平均；MiniCPM 复用已核验的模型加载与版本指纹，并以 masked mean 池化，避免重复位置加权。
- 本轮保留第一轮 Poppler 渲染的 1400 px 最长边设置。上游 PyMuPDF 的 200 DPI 设置可作后续分辨率对照，不混入当前实验。

## 无截断分块

两条文本路径均按 512 个内容 token 分块，重叠 64 tokens，以原始 token ID 加特殊 token 直接输入模型，不进行 decode 后重新分词，也不截断。页面得分是所有块的最高余弦相似度。原生文本共 26 块、OCR 共 24 块；原本超长的 v2-p3 现在所有内容 token 都参与编码。

这解决的是编码输入截断，不保证 OCR 没漏字。最大块分数也会受页内块数影响。原始整页基线与分块结果不可当成只有 OCR 不同的对照。

## 产物与复查

`results/v0.1/` 保存配置、源 PDF/PNG/文本哈希、OCR 文本与 TSV、token 块和范围、全部向量、全部排名、三路 top-3 案例、版本和核验记录。PDF 与模型仍使用项目外的既有文件。

```bash
../VisRAG/.venv/bin/python experiments/multimodal-retrieval-mini/verify_run.py
.venv/bin/python -m pytest -q tests/test_multimodal_retrieval.py
```

核验重算 120 个页级分数与排名，重建 tokenizer 序列并检查每个 token 被覆盖。三项独立测试覆盖末尾/边界、不合法分块和分块跨页归属。

旧版重复 runner 已移除。当前唯一入口 `run_demo.py` 默认执行完整三路；开发期未分块结果仅保留在本地，不属于正式发布口径。

第四阶段最低交付已完成：论文笔记、本机视觉检索、真实 OCR 对比、案例和研究价值判断。当前判断仍是“作为后续扩展”。独立官方数据子集、PP-OCRv3、高分辨率对照和视觉生成效用实验属于后续增强，未声称已完成。数据入口见 [官方数据说明](official-data.md)。
