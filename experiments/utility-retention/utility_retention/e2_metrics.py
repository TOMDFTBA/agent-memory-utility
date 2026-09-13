"""Prediction and trajectory-paired downstream metrics, including undefined cases."""
from collections import defaultdict
from statistics import mean

import numpy as np


def ranks(values):
    a = np.array(values)
    return np.array([float(np.sum(a < v)) + (float(np.sum(a == v)) + 1) / 2 for v in a])


def prediction_metrics(rows, predictions):
    groups = defaultdict(list)
    for row, pred in zip(rows, predictions, strict=True):
        groups[row['snapshot_id']].append((row['target']['value'], pred))
    correlations, errors = [], []
    for pairs in groups.values():
        y, p = np.array(pairs).T
        errors.append(dict(mae=float(np.mean(abs(y-p))), mse=float(np.mean((y-p)**2))))
        ry, rp = ranks(y), ranks(p)
        correlations.append(float(np.corrcoef(ry, rp)[0, 1]) if np.std(ry) > 0 and np.std(rp) > 0 else None)
    y = np.array([r['target']['value'] for r in rows])
    p = np.array(predictions)
    tp, actual, guessed = int(sum((y < 0) & (p < 0))), int(sum(y < 0)), int(sum(p < 0))
    valid = [c for c in correlations if c is not None]
    return dict(metrics={'prediction.mae': mean(e['mae'] for e in errors),
                         'prediction.mse': mean(e['mse'] for e in errors),
                         'prediction.spearman': mean(valid) if valid else None,
                         'prediction.negative_precision': tp/guessed if guessed else None,
                         'prediction.negative_recall': tp/actual if actual else None},
                defined_spearman_snapshots=len(valid), undefined_spearman_snapshots=len(correlations)-len(valid),
                negative_counts=dict(true_positive=tp, actual=actual, predicted=guessed))


def response_key(sid, ids, qid, seed):
    return (sid, tuple(sorted(ids)), qid, seed)


def summarize(plans, responses, snapshots, labels):
    index = {response_key(r['snapshot_id'], r['storage_ids'], r['query_id'], r['seed']): r for r in responses}
    snapshots = {s['snapshot_id']: s for s in snapshots}
    positive = defaultdict(set)
    for r in labels:
        if r['target']['value'] > 0:
            positive[r['snapshot_id']].add(r['memory_id'])
    groups = defaultdict(list)
    for p in plans:
        s = snapshots[p['snapshot_id']]
        rr = [index[response_key(p['snapshot_id'], p['storage_ids'], q['query_id'], p['seed'])]
              for q in s['future_queries']]
        ids = positive[p['snapshot_id']]
        metrics = {'answer.exact_match': mean(r['metrics']['answer.exact_match'] for r in rr),
                   'answer.token_f1': mean(r['metrics']['answer.token_f1'] for r in rr),
                   'cost.store_tokens': p['store_tokens'],
                   'cost.read_tokens': mean(r['memory_tokens'] for r in rr),
                   'retention.empty_rate': float(not p['storage_ids']),
                   'retention.positive_coverage': len(ids & set(p['storage_ids'])) / len(ids) if ids else None}
        groups[(p['candidate'], p['budget_ratio'], s['trajectory_id'], s.get('scenario', 'unknown'))].append(metrics)
    per_trajectory = []
    for (candidate, ratio, tid, scenario), rows in sorted(groups.items()):
        averaged = {k: mean(r[k] for r in rows if r[k] is not None)
                    if any(r[k] is not None for r in rows) else None for k in rows[0]}
        per_trajectory.append(dict(candidate=candidate, budget_ratio=ratio, trajectory_id=tid,
                                   scenario=scenario, metrics=averaged))
    grouped = defaultdict(list)
    for r in per_trajectory:
        grouped[(r['candidate'], r['budget_ratio'])].append(r)
    aggregates = []
    for (candidate, ratio), rows in sorted(grouped.items()):
        metrics = {k: mean(r['metrics'][k] for r in rows if r['metrics'][k] is not None)
                   if any(r['metrics'][k] is not None for r in rows) else None for k in rows[0]['metrics']}
        scenario_scores = {s: mean(r['metrics']['answer.exact_match'] for r in rows if r['scenario'] == s)
                           for s in sorted({r['scenario'] for r in rows})}
        aggregates.append(dict(candidate=candidate, budget_ratio=ratio, metrics=metrics,
                                scenario_em=scenario_scores, trajectory_count=len(rows),
                                positive_coverage_defined_trajectories=sum(r['metrics']['retention.positive_coverage'] is not None for r in rows)))
    return dict(aggregates=aggregates, per_trajectory=per_trajectory)


def paired(summary, candidate, baseline, ratio, seed, repeats):
    def values(name):
        return {r['trajectory_id']: r['metrics']['answer.exact_match'] for r in summary['per_trajectory']
                if r['candidate'] == name and r['budget_ratio'] == ratio}
    a, b = values(candidate), values(baseline)
    if not a or set(a) != set(b):
        raise ValueError('Unpaired trajectories')
    differences = [a[t]-b[t] for t in sorted(a)]
    rng = np.random.default_rng(seed)
    ci = np.quantile(rng.choice(differences, size=(repeats, len(differences))).mean(axis=1), [.025, .975]).tolist()
    return dict(candidate=candidate, baseline=baseline, budget_ratio=ratio,
                metrics={'answer.paired_em_difference': mean(differences)}, trajectory_bootstrap_95_ci=ci,
                trajectory_count=len(a), inference='descriptive validation; model selected on same data')
