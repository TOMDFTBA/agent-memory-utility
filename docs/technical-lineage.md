# 外部技术依赖

四个上游目录均位于主项目之外，不复制模型或上游源码到本仓库。

| 上游 | 本阶段用途 | 本地位置 |
|---|---|---|
| [UltraRAG](https://github.com/OpenBMB/UltraRAG) | MCP build/run 编排 | `../UltraRAG/code` |
| [MiniCPM-Embedding](https://huggingface.co/openbmb/MiniCPM-Embedding) | 语义向量 | `../MiniCPM-Embedding/model` |
| [RAG-DDR](https://github.com/OpenMatch/RAG-DDR) | 后续效用实验；本阶段仅复用同目录已有 MiniCPM SFT 基座 | `../RAG-DDR` |
| [VisRAG](https://github.com/OpenBMB/VisRAG) | 后续多模态实验，当前不调用 | `../VisRAG` |

本地 UltraRAG checkout：`37e0cce42e2156d710467cde77a2c0fd0114a2c4`。
本地 MiniCPM-Embedding code checkout：`dc0f82b4466b254dddc25787bf7b1cbc28f755b0`。
`model` 是本机已有 snapshot 目录；配置 revision 是来源记录，加载器不会联网验证该标签。
模型代码和权重仍遵守各自上游许可。

## 本机环境说明

复用系统 PyTorch 2.10.0 / ROCm 7.14，项目虚拟环境继承系统 site-packages。
本次没有修改系统 PyTorch、模型权重或上游执行代码。
UltraRAG 声明 Python >=3.11,<3.13；本机 3.13.5 使用显式 `--ignore-requires-python` 安装最小编排路径。此项是本机兼容例外，新机器优先使用上游支持的 Python。

UltraRAG 以 `--no-deps` 安装，避免拉入 CUDA、Milvus、语料解析等本阶段未使用的组件。因此 `pip check` 会报告未安装的上游可选使用路径依赖。继承的系统包也有 FastAPI/Starlette 等冲突，本项目没有启用这些 Web UI 路径；不能把当前环境声称为通过全量依赖一致性检查。

UltraRAG 的 `python -m ultrarag.client` 在本地版本中会在实际执行后再次对同步 `main()` 调用 `asyncio.run` 而报错，因此使用安装生成的 `ultrarag` console script。
