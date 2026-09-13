# E1 真实模型实验报告

后端：model；运行状态：COMPLETE。
轨迹数：12；逐题条件运行：576；存储删除标签：48。

| Split | Full EM | No memory EM | Storage deletion EM |
|---|---:|---:|---:|
| train | 1.000 | 0.000 | 0.719 |
| validation | 0.750 | 0.000 | 0.656 |
| test | 0.875 | 0.000 | 0.688 |

## 场景分项

| 场景 | Full EM | No memory EM | 标签分布 |
|---|---:|---:|---|
| complementarity | 0.500 | 0.000 | {'positive': 5, 'zero': 6, 'negative': 1} |
| frequent_but_useless | 1.000 | 0.000 | {'positive': 3, 'zero': 9} |
| old_but_useful | 1.000 | 0.000 | {'positive': 3, 'zero': 9} |
| redundancy | 1.000 | 0.000 | {'zero': 12} |

Full − no_memory 的轨迹均值差：0.875；轨迹 bootstrap 95% 区间：[0.667, 1.000]。
标签分布：{'positive': 11, 'zero': 36, 'negative': 1}；最大重复标准差：0.000；最低符号一致率：1.000。
累计逐题运行耗时：401.6 秒；单次中位数：0.775 秒（不含前置模型摘要/历史特征处理）。
开发验收门槛 ready_for_stage2：True。

## 解释边界

这是固定模型、固定窗口上的合成数据结果。重复使用确定性解码，不代表随机采样下的可靠性。
bootstrap 仅反映当前轨迹样本，退化区间不能解释为总体没有不确定性；压力场景平均数不代表自然任务分布。
存储删除平均 EM 混合不同删除对象，价值判断应以配对 U/V_LOO 为准。零标签可能有多种来源；行为记录不能证明模型内部利用过程。
自动门槛是开发测量门槛，不等于已经证明预测器有效；测试标签仅用于 hindsight 评估。
