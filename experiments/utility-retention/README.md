# Utility-aware retention v0.2

E1–E4 已完成。实验从固定快照出发，测量未来窗口中的删除边际价值，再用历史特征预测并驱动预算保留，最后诊断单条价值的非加性。

结果限定于固定 MiniCPM 系统、英文合成压力轨迹和一次性保留决策。完整研究边界与发布文件说明见 [v0.2 发布说明](../../docs/v0.2-release.md)（[English](../../docs/v0.2-release.en.md)）。

## 阶段与结果

| 阶段 | 完成内容 | 结果 |
|---|---|---|
| E1 | 48 条扩展轨迹、2304 个主条件、216 个开发对照 | [扩展报告](../../releases/v0.2.0/reports/e1-extension-model/extension-report.md) |
| E2 | 13 个候选、260 个唯一验证回答、冻结 full-a10 | [开发报告](../../releases/v0.2.0/reports/e2-development-model/report.md) |
| E3 | 补齐基线、24 条新轨迹、600 个正式回答条件 | [正式报告](../../releases/v0.2.0/reports/e3-formal-model/report.md) |
| E3 补充 | 重放历史特征、检索与 tokens，补充成本与失败归因 | [补充报告](../../releases/v0.2.0/reports/e3-supplement-model/report.md) |
| E4 | 1536 个枚举条件、1152 个背景交互、独立集合复核 | [诊断报告](../../releases/v0.2.0/reports/e4-diagnostic-model/report.md) |

阶段编号统一为 E1–E4；历史日志中的 Stage 1–4 表示相同实验阶段，不与 v0.1 的四项技术支点混用。历史报告中“尚未训练/执行下一阶段”描述的是该报告生成时的范围，不是当前版本状态。

## 快速复验

在仓库根目录安装 package 后运行；不需要手工设置实验目录的 PYTHONPATH：

```bash
.venv/bin/python scripts/release_artifacts.py restore-results
.venv/bin/python scripts/audit_v02.py
.venv/bin/python -m pytest -q
```

恢复命令校验归档及每个文件，拒绝覆盖不同内容。`results/` 是本地恢复目录，默认不纳入 Git；公开报告和完整校验归档位于 `releases/v0.2.0/`。

发布审计只读重算 E1 标签、E2 预测与选择、E3/E4 策略与统计，并验证冻结证据字节。它不重新生成答案、不重放 GPU 检索，也不替代已有模型审计。两个早期 pilot 的原 runner 没有完整保存，发布审计明确报告该历史源码缺口；冻结 E1 及后续主实验保留了源码证据。

## 新运行入口

所有输出使用新目录，不能覆盖已恢复的冻结结果。真实模型通过公共 `load_config`、`--model-config` 或 `LONGMEM_CONFIG` 配置；模型不自动下载。`test` 后端只验证工程流程。

```bash
.venv/bin/python experiments/utility-retention/run.py --backend test --output /tmp/utility-retention-pilot
.venv/bin/python experiments/utility-retention/evaluate.py /tmp/utility-retention-pilot
```

| 阶段 | 入口 | 协议 |
|---|---|---|
| E1 | `run.py`、`evaluate.py`、`report.py` | [主协议](protocol.md)、[冻结压力集](protocol-e1-frozen.md)、[扩展](protocol-e1-extension.md) |
| E2 | `e2.py prepare/run/audit --output PATH` | [开发协议](protocol-e2-development.md) |
| E3 基线 | `e3_baselines.py prepare/run/audit --output PATH` | [基线协议](protocol-e3-baselines-development.md) |
| E3 正式 | `e3_formal.py prepare/run/audit --output PATH` | [正式协议](protocol-e3-formal-test.md)、[运行前澄清](protocol-e3-formal-clarification.md) |
| E3 补充 | `e3_supplement.py prepare/run/audit --output PATH` | [补充协议](protocol-e3-supplement.md) |
| E4 | `e4.py prepare/run/audit --output PATH` | [诊断协议](protocol-e4-diagnostic.md) |

这些 prepare 命令要求空目录，默认前序依赖由 restore-results 提供。新运行的源码身份与历史运行不同，保存在各自 manifest；本次发布不将新入口运行冒充原冻结实验。

## 命名与复用

- `candidate` 表示模型候选、策略或精确集合候选；`full-a10` 是模型 ID，`full` 是全量参照。
- 新删除计划写 `intervention=storage_deletion`。旧 `candidate=storage_deletion` 仅由只读 adapter 转换，不修改原 JSON。
- E1 `condition` 是历史干预字段，不能直接当作 v0.1 内容条件传给 `canonical_condition`。
- `hindsight_loo` 是真实 LOO 加排序装入；`hindsight_loo_sum_optimal` 是精确分数和；`best_subset` 是同窗口实际得分最优。三者不互称 oracle。
- 公共配置、I/O、embedding、generation 与答案评分由 `longmem` 提供。E1 构造、报告和诊断实现在 `utility_retention` 内，顶层文件保留兼容 CLI。
- E2–E4 共用 selector、predict、response validation、汇总与配对统计；各阶段生命周期维持独立冻结边界。
- `longmem-experiment-v1` 表示公共 envelope 版本，不等于软件版本。具体 artifact 的字段和跨版本 baseline 变体见[开发指南](../../docs/experiment-development-guide.md)。

## 历史源码与发布源码

原始 manifest、回答及源码快照没有重写。发布映射记录归档源码与当前实现的校验关系；映射只适用于这次已验证的源码移动、评分提取、后端别名和诊断 adapter。未注册修改仍会失败。

若要运行原始源码而不是发布兼容审计，在新目录恢复指定阶段的源码视图：

```bash
.venv/bin/python scripts/release_artifacts.py restore --output /tmp/utility-retention-frozen --source-run e1-extension-model
```

完整命令和源码恢复边界见[发布说明](../../docs/v0.2-release.md)。不要修改原 manifest 以绕过身份检查。
