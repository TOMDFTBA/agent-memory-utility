# v0.1 发布检查清单

## 已完成

- [x] README 改为问题—方法—证据—复现结构
- [x] 提供可公开的 `configs/local.example.yaml`
- [x] 忽略包含本机路径的 `configs/local.yaml` 和 demo latest 文件
- [x] 排除模型、索引、缓存、原始大规模运行目录
- [x] 排除许可尚未确认的论文页面截图与 OCR 派生文件
- [x] 增加 Python 3.11/3.12 CPU CI
- [x] 独立整理 AMD/ROCm 部署和兼容记录
- [x] 收敛四阶段命名、共享 I/O/配置与唯一 runner
- [x] 用真实本地模型重新生成 Stage 2、Stage 3 主实验/控制和 Stage 4 正式结果
- [x] 通过 Stage 2（300 runs）、Stage 3（594 + 648 responses）与 Stage 4（120 page scores）核验
- [x] 检查 JSON、Markdown 本地链接、本机绝对路径和 42 项测试
- [x] 采用 Apache License 2.0，并明确上游资产不随本仓库授权
- [x] 建立英文主 README 与中文镜像 README
- [x] 添加作者姓名、GitHub、ORCID 和 `CITATION.cff`
- [x] 提供 AMD/ROCm 部署与兼容报告英文版
- [x] 添加公开 GitHub 身份 `TOMDFTBA`
- [x] 将 ORCID `0009-0006-8392-1658` 关联到作者和引用信息

## 发布前需要人工决定或执行

- [x] 复查准备提交的文件列表和仓库体积
- [x] 完成首次 commit，在固定 commit 上重新运行测试
- [ ] 将最终 commit SHA 写入发布说明或结果 manifest
- [ ] 可选：在第二台干净机器运行 CPU 安装流程
- [x] 创建并推送 GitHub 仓库
- [ ] 标记 `v0.1.0`

本清单不要求在 v0.1 中解决 utility-aware retention；该研究问题属于 v0.2。
