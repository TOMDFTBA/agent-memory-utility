# 官方数据入口与后续取样协议

以下名称来自本地 VisRAG 的 `visrag_scripts/eval_retriever/eval.sh` 和 README。当前三路实验仍使用本地两篇论文的页面；没有下载或评测这些数据集。

上游检索评测脚本列出 ArxivQA、ChartQA、MP-DocVQA、InfoVQA、PlotQA、SlideVQA，仓库 ID 规则为 `openbmb/VisRAG-Ret-Test-${SUB_DATASET}`。例如：[ChartQA](https://huggingface.co/datasets/openbmb/VisRAG-Ret-Test-ChartQA)、[SlideVQA](https://huggingface.co/datasets/openbmb/VisRAG-Ret-Test-SlideVQA)。具体可用文件、版本与许可应在实际取数时核验。

后续取样可优先选 5 个问题，保留其全部已标注证据页，再按固定种子取干扰页，总页数控制在 12–20。必须在模型运行前保存 dataset revision、query ID、page ID、qrels 与随机种子，不按模型成败筛选。多证据问题不能随意只指定一个目标页。

这些数据未必提供 PDF 原生文本，因此不能强凑三路：只有页面图像时，采用视觉/OCR 两路；若要新增文本真值，需要单独标注并说明来源。当前 `run_demo.py` 尚未实现这些数据集的导入，使用它们需新增导入适配器。

小子集结果只适合案例分析，不可冒充官方完整 benchmark 成绩。应把“找对页面”和“读对图表答案”分开；后者需要视觉生成器与答案评分协议。
