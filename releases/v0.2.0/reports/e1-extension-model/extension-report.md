# E1 扩展实验报告

新增 48 条轨迹，192 个 storage 标签；主实验 2304 次、开发诊断 216 次真实推理。

| Split | 轨迹 | 标签 | 正/零/负/不确定分布 | Full−none | 95% CI |
|---|---:|---:|---|---:|---|
| train | 24 | 96 | {'positive': 22, 'zero': 72, 'negative': 2} | 0.875 | [0.7708333333333334, 0.9583333333333334] |
| validation | 12 | 48 | {'positive': 9, 'zero': 38, 'negative': 1} | 0.792 | [0.5416666666666666, 1.0] |
| test | 12 | 48 | {'positive': 8, 'zero': 39, 'negative': 1} | 0.792 | [0.5416666666666666, 1.0] |

## 开发互补诊断

| 条件 | EM | 相对 full 配对差异 |
|---|---:|---:|
| full | 0.389 | +0.000 |
| support_only | 0.556 | +0.167 |
| support_reversed | 0.444 | +0.056 |
| prefix_only | 0.000 | -0.389 |
| suffix_only | 0.000 | -0.389 |

完整上下文的支持证据覆盖率：1.000。
错误分类（含重复，不是独立样本）：{'full': {'half_only': 27, 'full_answer_with_extra_text': 6, 'correct': 21}, 'support_only': {'half_only': 24, 'correct': 30}, 'support_reversed': {'half_only': 30, 'correct': 24}, 'prefix_only': {'half_only': 54}, 'suffix_only': {'half_only': 54}}。

诊断仅使用开发轨迹；条件和模型未根据测试结果修改。支持证据条件的差异涉及证据覆盖、上下文长度和顺序，不能仅归因于一个内部机制。

## 交接与验收

交接行数：{'train': 96, 'validation': 48, 'test-features': 48, 'test-labels.hindsight': 48}。仅提供历史特征；train/validation 配标签，test features 与 hindsight labels 分开。
高频场景核验：True；E2 开发测量门槛：True。
门槛通过不代表预测器已有效，也不保证当前训练样本充足。未训练 E2；不确定标签保留原值和标志，不当作零。

仍是共享合成语法的压力样本，不代表自然分布或未见模板泛化。每轨迹二题涉及同一事实；统计单位为轨迹。三次确定性重复衡量执行稳定性，不衡量随机解码噪声。
