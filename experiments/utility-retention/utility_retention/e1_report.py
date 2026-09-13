"""Audited E1 summary; trajectory bootstrap is descriptive for synthetic pressure data."""
import argparse
from collections import Counter, defaultdict
from pathlib import Path
from statistics import mean, median

import numpy as np
from longmem.experiment_io import read_json, read_jsonl, write_json
from utility_retention.labeling import evaluate


def summarize(output):
    manifest = read_json(output / 'manifest.json')
    if manifest['status'] != 'COMPLETE':
        raise ValueError('Only complete runs can be reported')
    data = read_json(output / 'dataset-manifest.json')
    rows = read_jsonl(output / 'responses.jsonl')
    utilities, labels, reliability = evaluate(data['snapshots'], rows, data['seeds'], data['context_ids'],
                                             manifest['parameters']['settings'], manifest['parameters']['backend'])
    for name, expected in [('query-utility', utilities), ('future-value-labels', labels),
                           ('reliability-report', reliability)]:
        if read_json(output / f'{name}.json') != expected:
            raise ValueError(f'{name} differs from recomputed result')
    rng = np.random.default_rng(20260912)
    groups = defaultdict(list)
    for row in rows:
        groups[(row['split'], row['condition'], row['trajectory_id'])].append(row['metrics']['answer.exact_match'])
    scores = {}
    for split in ('train', 'validation', 'test'):
        scores[split] = {condition: mean(mean(values) for (sp, co, _), values in groups.items()
                                         if sp == split and co == condition)
                         for condition in sorted({r['condition'] for r in rows if r['split'] == split})}
    trajectory_differences = {tid: mean(values) - mean(groups[(split, 'no_memory', tid)])
                              for (split, condition, tid), values in groups.items() if condition == 'full'}
    values = np.array(list(trajectory_differences.values()))
    ci = np.quantile(rng.choice(values, size=(5000, len(values)), replace=True).mean(axis=1), [0.025, 0.975])
    storage = [r for r in labels if r['condition'] == 'storage_deletion']
    zero = [r for r in utilities if r['condition'] == 'storage_deletion' and r['value'] == 0]
    scenario_by_snapshot = {s['snapshot_id']: s.get('scenario', 'basic_pilot') for s in data['snapshots']}
    scenario_results = {}
    for scenario in sorted(set(scenario_by_snapshot.values())):
        subset = [r for r in rows if scenario_by_snapshot[r['snapshot_id']] == scenario]
        scenario_labels = [r for r in storage if scenario_by_snapshot[r['snapshot_id']] == scenario]
        scenario_results[scenario] = {
            'full_em': mean(r['metrics']['answer.exact_match'] for r in subset if r['condition'] == 'full'),
            'no_memory_em': mean(r['metrics']['answer.exact_match'] for r in subset if r['condition'] == 'no_memory'),
            'label_distribution': dict(Counter(r['label'] for r in scenario_labels)),
        }
    summary = dict(scores_by_scenario=scenario_results, response_count=len(rows), trajectory_count=len(values), scores_by_split=scores,
                   full_minus_no_memory=float(np.mean(values)), trajectory_bootstrap_95_ci=ci.tolist(),
                   label_distribution=dict(Counter(r['label'] for r in storage)),
                   maximum_label_std=max(r['standard_deviation'] for r in storage),
                   minimum_sign_stability=min(r['sign_stability'] for r in storage),
                   duration_seconds=sum(r['duration_seconds'] for r in rows),
                   median_response_seconds=median(r['duration_seconds'] for r in rows),
                   zero_query_diagnostics=dict(total=len(zero), not_retrieved=sum(not r['retrieved'] for r in zero),
                                               with_replacement=sum(bool(r['replacement_ids']) for r in zero),
                                               hit_but_wrong=sum(r['hit_but_wrong'] for r in zero)),
                   ready_for_stage2=reliability['ready_for_stage2'])
    write_json(output / 'summary.json', summary)
    lines = ['# E1 真实模型实验报告', '', f"后端：{manifest['parameters']['backend']}；运行状态：COMPLETE。",
             f"轨迹数：{len(values)}；逐题条件运行：{len(rows)}；存储删除标签：{len(storage)}。", '',
             '| Split | Full EM | No memory EM | Storage deletion EM |', '|---|---:|---:|---:|']
    for split, metrics in scores.items():
        lines.append(f"| {split} | {metrics.get('full', 0):.3f} | {metrics.get('no_memory', 0):.3f} | {metrics.get('storage_deletion', 0):.3f} |")
    lines += ['', '## 场景分项', '', '| 场景 | Full EM | No memory EM | 标签分布 |', '|---|---:|---:|---|']
    for scenario, metrics in scenario_results.items():
        lines.append(f"| {scenario} | {metrics['full_em']:.3f} | {metrics['no_memory_em']:.3f} | {metrics['label_distribution']} |")
    lines += ['', f"Full − no_memory 的轨迹均值差：{float(np.mean(values)):.3f}；轨迹 bootstrap 95% 区间：[{ci[0]:.3f}, {ci[1]:.3f}]。",
              f"标签分布：{summary['label_distribution']}；最大重复标准差：{summary['maximum_label_std']:.3f}；最低符号一致率：{summary['minimum_sign_stability']:.3f}。",
              f"累计逐题运行耗时：{summary['duration_seconds']:.1f} 秒；单次中位数：{summary['median_response_seconds']:.3f} 秒（不含前置模型摘要/历史特征处理）。",
              f"开发验收门槛 ready_for_stage2：{summary['ready_for_stage2']}。", '',
              '## 解释边界', '',
              '这是固定模型、固定窗口上的合成数据结果。重复使用确定性解码，不代表随机采样下的可靠性。',
              'bootstrap 仅反映当前轨迹样本，退化区间不能解释为总体没有不确定性；压力场景平均数不代表自然任务分布。',
              '存储删除平均 EM 混合不同删除对象，价值判断应以配对 U/V_LOO 为准。零标签可能有多种来源；行为记录不能证明模型内部利用过程。',
              '自动门槛是开发测量门槛，不等于已经证明预测器有效；测试标签仅用于 hindsight 评估。', '']
    (output / 'report.md').write_text('\n'.join(lines), encoding='utf-8')
    return summary


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('output', type=Path)
    print(summarize(parser.parse_args().output))
