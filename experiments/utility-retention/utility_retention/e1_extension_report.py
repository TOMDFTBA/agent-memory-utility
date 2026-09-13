"""E1 extension audit, split-safe handoff, and development diagnostic report."""
import argparse
from collections import Counter, defaultdict
from pathlib import Path
from statistics import mean

import numpy as np
from longmem.experiment_io import read_json, read_jsonl, sha256_file, write_json
from .e1_report import summarize as summarize_main
from .e1_diagnosis import summarize as summarize_diagnosis, validate_responses


FEATURES = ('recency_rank', 'age', 'retrieval_frequency', 'history_observed', 'historical_similarity', 'memory_tokens')


def handoff_rows(snapshots, features, labels):
    metadata = {s['snapshot_id']: s for s in snapshots}
    feature_index = {(f['snapshot_id'], f['memory_id']): f for f in features}
    label_index = {(r['snapshot_id'], r['memory_id']): r for r in labels if r['condition'] == 'storage_deletion'}
    expected = {(s['snapshot_id'], m['memory_id']) for s in snapshots for m in s['memories']}
    if set(feature_index) != expected or set(label_index) != expected:
        raise ValueError('Incomplete feature/label join')
    outputs = {name: [] for name in ('train', 'validation', 'test-features', 'test-labels.hindsight')}
    for key in sorted(expected):
        sid, mid = key
        split = metadata[sid]['split']
        row = dict(snapshot_id=sid, trajectory_id=metadata[sid]['trajectory_id'], memory_id=mid,
                   features={k: feature_index[key][k] for k in FEATURES})
        target = {k: label_index[key][k] for k in ('value', 'label', 'uncertain', 'standard_deviation', 'sign_stability')}
        if split == 'test':
            outputs['test-features'].append(row)
            outputs['test-labels.hindsight'].append(dict(snapshot_id=sid, memory_id=mid, target=target))
        else:
            outputs[split].append(dict(**row, target=target))
    return outputs


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--main-output', type=Path, required=True)
    parser.add_argument('--diagnostic-output', type=Path, required=True)
    args = parser.parse_args()
    output = args.main_output
    summary = summarize_main(output)
    data = read_json(output/'dataset-manifest.json')
    features = read_json(output/'history-features.json')
    labels = read_json(output/'future-value-labels.json')
    raw = read_jsonl(output/'responses.jsonl')
    diagnostic_manifest = read_json(args.diagnostic_output/'manifest.json')
    if diagnostic_manifest['status'] != 'COMPLETE':
        raise ValueError('Incomplete diagnosis')
    if diagnostic_manifest['main_manifest_sha256'] != sha256_file(output/'manifest.json'):
        raise ValueError('Diagnostic baseline identity mismatch')
    if diagnostic_manifest['main_responses_sha256'] != sha256_file(output/'responses.jsonl'):
        raise ValueError('Diagnostic baseline responses changed')
    development = [s for s in data['snapshots'] if s.get('scenario') == 'complementarity' and s['split'] != 'test']
    diag_raw = read_jsonl(args.diagnostic_output/'responses.jsonl')
    validate_responses(development, data['seeds'], diag_raw)
    diagnosis = summarize_diagnosis(development, diag_raw, raw)
    if diagnosis != read_json(args.diagnostic_output/'summary.json'):
        raise ValueError('Diagnostic summary mismatch')
    outputs = handoff_rows(data['snapshots'], features, labels)
    for name, rows in outputs.items():
        write_json(output/'handoff'/f'{name}.json', rows)
    rng = np.random.default_rng(20260912)
    split_stats = {}
    for split in ('train', 'validation', 'test'):
        subset = [label for label in labels if label['condition'] == 'storage_deletion' and label['split'] == split]
        groups = defaultdict(list)
        for r in raw:
            if r['split'] == split and r['condition'] in ('full', 'no_memory'):
                groups[(r['trajectory_id'], r['condition'])].append(r['metrics']['answer.exact_match'])
        tids = sorted({tid for tid, _ in groups})
        diffs = [mean(groups[(tid, 'full')]) - mean(groups[(tid, 'no_memory')]) for tid in tids]
        ci = np.quantile(rng.choice(diffs, size=(5000, len(diffs))).mean(axis=1), [0.025, 0.975]).tolist()
        split_stats[split] = dict(trajectory_count=len(tids), label_count=len(subset),
                                  distribution=dict(Counter(label['label'] for label in subset)),
                                  nonzero_fraction=mean(label['value'] != 0 for label in subset),
                                  full_minus_no_memory=mean(diffs), trajectory_bootstrap_95_ci=ci)
    feature_index = {(r['snapshot_id'], r['memory_id']): r for r in features}
    frequency_audit = []
    for s in data['snapshots']:
        if s.get('scenario') == 'frequent_but_useless':
            meta = s['diagnostic_metadata']
            observed = feature_index[(s['snapshot_id'], meta['frequent_memory_id'])]['retrieval_frequency']
            frequency_audit.append(dict(snapshot_id=s['snapshot_id'], observed=observed,
                                        expected=meta['expected_history_count'], passed=observed == meta['expected_history_count']))
    audit = dict(main_summary=summary, split_stats=split_stats, diagnosis=diagnosis,
                 historical_frequency_audit=frequency_audit,
                 frequency_scenario_valid=all(r['passed'] for r in frequency_audit),
                 handoff_counts={name: len(rows) for name, rows in outputs.items()},
                 ready_for_e2_development=summary['ready_for_stage2'] and all(r['passed'] for r in frequency_audit),
                 main_manifest_sha256=sha256_file(output/'manifest.json'), diagnostic_manifest_sha256=sha256_file(args.diagnostic_output/'manifest.json'))
    write_json(output/'extension-summary.json', audit)
    lines = ['# E1 扩展实验报告', '',
             f"新增 {summary['trajectory_count']} 条轨迹，{sum(x['label_count'] for x in split_stats.values())} 个 storage 标签；主实验 {len(raw)} 次、开发诊断 {len(diag_raw)} 次真实推理。", '',
             '| Split | 轨迹 | 标签 | 正/零/负/不确定分布 | Full−none | 95% CI |', '|---|---:|---:|---|---:|---|']
    for split, item in split_stats.items():
        lines.append(f"| {split} | {item['trajectory_count']} | {item['label_count']} | {item['distribution']} | {item['full_minus_no_memory']:.3f} | {item['trajectory_bootstrap_95_ci']} |")
    lines += ['', '## 开发互补诊断', '', '| 条件 | EM | 相对 full 配对差异 |', '|---|---:|---:|']
    for c, em in diagnosis['scores'].items():
        delta = diagnosis['paired_differences_vs_full'].get(c, {}).get('mean', 0)
        lines.append(f'| {c} | {em:.3f} | {delta:+.3f} |')
    lines += ['', f"完整上下文的支持证据覆盖率：{diagnosis['full_support_coverage']:.3f}。",
              f"错误分类（含重复，不是独立样本）：{diagnosis['behavior_by_condition']}。", '',
              '诊断仅使用开发轨迹；条件和模型未根据测试结果修改。支持证据条件的差异涉及证据覆盖、上下文长度和顺序，不能仅归因于一个内部机制。', '',
              '## 交接与验收', '',
              f"交接行数：{audit['handoff_counts']}。仅提供历史特征；train/validation 配标签，test features 与 hindsight labels 分开。",
              f"高频场景核验：{audit['frequency_scenario_valid']}；E2 开发测量门槛：{audit['ready_for_e2_development']}。",
              '门槛通过不代表预测器已有效，也不保证当前训练样本充足。未训练 E2；不确定标签保留原值和标志，不当作零。', '',
              '仍是共享合成语法的压力样本，不代表自然分布或未见模板泛化。每轨迹二题涉及同一事实；统计单位为轨迹。三次确定性重复衡量执行稳定性，不衡量随机解码噪声。', '']
    (output/'extension-report.md').write_text('\n'.join(lines), encoding='utf-8')
    print({k: v for k, v in audit.items() if k in ('split_stats', 'handoff_counts', 'frequency_scenario_valid', 'ready_for_e2_development')})


if __name__ == '__main__':
    main()
