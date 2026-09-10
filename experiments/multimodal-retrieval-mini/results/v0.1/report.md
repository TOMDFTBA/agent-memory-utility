# 三路页面检索对照

真实 VisRAG-Ret 与 MiniCPM-Embedding；Tesseract 从同一批 PNG 识别文字。

| 问题 | 指定页 | 视觉名次 | 原生文本名次 | OCR名次 |
|---|---|---:|---:|---:|
| Find the diagram comparing the TextRAG pipeline on the left with the VisRAG pipeline on the right. | v1-p4 | 1 | 2 | 3 |
| Find the bar chart comparing TextRAG and VisRAG accuracy using MiniCPM-V and GPT-4o generators. | v1-p2 | 1 | 1 | 2 |
| Find the example comparing Japan and Spain population, with sports news interest at 35 percent. | v2-p2 | 1 | 1 | 1 |
| Which page defines position-weighted mean pooling for the retrieval embedding? | v1-p4 | 1 | 1 | 1 |
| Find the equations for per-image evidence recording and answer reasoning in EVisRAG. | v2-p3 | 1 | 1 | 1 |

## 运行口径

文本按 512 个内容 tokens 分块，相邻块重叠 64 tokens，再加模型特殊 token；直接编码原始 token ID，无截断。页面得分为其所有块的最高余弦相似度，两条文本路径使用同一模型、问题和聚合规则。

OCR 固定英文、PSM 3、OEM 1；保存识别文本、TSV 坐标/置信度及日志。未对 OCR 手工修正。页面最长边沿用 1400 px，避免把分辨率改变混入本次对照。

## 边界

这是固定 8 页、5 个手工问题上的描述性结果，目标不是穷尽相关性标注。原生文本不是完美 OCR 标准答案；两者的阅读顺序可能不同，不能直接把文本差异当字符错误率。页面得分取最大值会使块数更多的页面获得更多匹配机会。视觉与文本使用不同编码器；不能把差异全部归因于模态。没有运行生成器，没有证明答案正确或长期记忆有效。

逐问题的三路 top-3、最高分文本块和源图像链接见 cases.md；所有原始结果与向量保存在本目录。
