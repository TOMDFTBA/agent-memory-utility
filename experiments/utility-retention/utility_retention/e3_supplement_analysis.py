"""Post-test E3 descriptive analysis; no model fitting, policy tuning or inference."""
from collections import defaultdict
from statistics import mean

from .e2_metrics import response_key

CATEGORIES = ('correct', 'budget_infeasible', 'support_not_retained', 'support_not_retrieved', 'supported_but_wrong')


def failure_category(em, supports, costs, budget, stored, context, exempt=False):
    minimum = min(sum(costs[mid] for mid in set(group)) for group in supports)
    feasible = exempt or minimum <= budget
    retained = any(set(group) <= set(stored) for group in supports)
    retrieved = any(set(group) <= set(context) for group in supports)
    if em == 1:
        category = 'correct'
    elif not feasible:
        category = 'budget_infeasible'
    elif not retained:
        category = 'support_not_retained'
    elif not retrieved:
        category = 'support_not_retrieved'
    else:
        category = 'supported_but_wrong'
    return dict(category=category, minimum_support_tokens=minimum, support_feasible=feasible,
                support_retained=retained, support_retrieved=retrieved,
                correct_without_annotated_support=bool(em == 1 and not retrieved))


def analyze(plans, responses, snapshots, features):
    data = {s['snapshot_id']: s for s in snapshots}
    costs = {(r['snapshot_id'], r['memory_id']): r['features']['memory_tokens'] for r in features}
    index = {response_key(r['snapshot_id'], r['storage_ids'], r['query_id'], r['seed']): r for r in responses}
    rows = []
    for p in plans:
        s = data[p['snapshot_id']]
        cs = {m['memory_id']: costs[s['snapshot_id'], m['memory_id']] for m in s['memories']}
        for q in s['future_queries']:
            key = response_key(s['snapshot_id'], p['storage_ids'], q['query_id'], p['seed'])
            r = index[key]
            diagnostic = failure_category(r['metrics']['answer.exact_match'], q['supporting_memory_sets'], cs,
                                          p['budget_tokens'], p['storage_ids'],
                                          [m['memory_id'] for m in r['context']], p['candidate'] == 'full')
            metrics = {f'diagnostic.{c}_rate': int(diagnostic['category'] == c) for c in CATEGORIES}
            metrics.update({'retention.record_count': len(p['storage_ids']),
                            'retention.budget_utilization': p['store_tokens']/p['budget_tokens']
                            if p['candidate'] != 'full' and p['budget_tokens'] else None,
                            'cost.unused_store_tokens': p['budget_tokens']-p['store_tokens'] if p['candidate'] != 'full' else None,
                            'retention.no_record_fits': int(min(cs.values()) > p['budget_tokens']) if p['candidate'] != 'full' else 0,
                            'retention.empty_rate': int(not p['storage_ids']),
                            'retention.support_feasible_rate': int(diagnostic['support_feasible']),
                            'answer.correct_without_annotated_support_rate': int(diagnostic['correct_without_annotated_support'])})
            rows.append(dict(snapshot_id=s['snapshot_id'], trajectory_id=s['trajectory_id'], scenario=s['scenario'],
                             candidate=p['candidate'], budget_ratio=p['budget_ratio'], selection_seed=p['selection_seed'],
                             query_id=q['query_id'], response_key=[key[0], list(key[1]), key[2], key[3]], **diagnostic, metrics=metrics))
    # Average random seeds and questions inside each trajectory before population/family summaries.
    groups = defaultdict(list)
    for r in rows:
        groups[r['candidate'], r['budget_ratio'], r['trajectory_id'], r['scenario']].append(r['metrics'])
    def average(ms):
        return {k: mean(m[k] for m in ms if m[k] is not None) if any(m[k] is not None for m in ms) else None for k in ms[0]}
    per_trajectory = [dict(candidate=c, budget_ratio=b, trajectory_id=t, scenario=f, metrics=average(ms))
                      for (c, b, t, f), ms in sorted(groups.items())]
    grouped = defaultdict(list)
    for r in per_trajectory:
        grouped[r['candidate'], r['budget_ratio'], 'all'].append(r['metrics'])
        grouped[r['candidate'], r['budget_ratio'], r['scenario']].append(r['metrics'])
    aggregates = [dict(candidate=c, budget_ratio=b, scenario=f, trajectory_count=len(ms), metrics=average(ms))
                  for (c, b, f), ms in sorted(grouped.items())]
    return dict(query_diagnostics=rows, per_trajectory=per_trajectory, aggregates=aggregates)


def gain_distribution(summary, snapshots):
    family = {s['trajectory_id']: s['scenario'] for s in snapshots}
    rows = summary['per_trajectory']+summary['primary_per_trajectory']
    groups = defaultdict(dict)
    for r in rows:
        if r['candidate'] in ('utility_aware', 'importance'):
            groups[r['budget_ratio'], r['trajectory_id']][r['candidate']] = r['metrics']['answer.exact_match']
    trajectories = []
    for (budget, tid), values in sorted(groups.items(), key=lambda item: (str(item[0][0]), item[0][1])):
        if set(values) != {'utility_aware', 'importance'}:
            raise ValueError('Missing paired policy')
        difference = values['utility_aware']-values['importance']
        trajectories.append(dict(budget_ratio=budget, trajectory_id=tid, scenario=family[tid],
                                 outcome='win' if difference > 1e-12 else 'loss' if difference < -1e-12 else 'tie',
                                 metrics={'answer.paired_em_difference': difference}, policy_em=values))
    grouped = defaultdict(list)
    for r in trajectories:
        grouped[str(r['budget_ratio']), 'all'].append(r)
        grouped[str(r['budget_ratio']), r['scenario']].append(r)
    aggregates = [dict(budget_ratio=rs[0]['budget_ratio'], scenario=f, trajectory_count=len(rs),
                       outcomes={o: sum(r['outcome'] == o for r in rs) for o in ('win', 'tie', 'loss')},
                       metrics={'answer.paired_em_difference': mean(r['metrics']['answer.paired_em_difference'] for r in rs)})
                  for (_, f), rs in sorted(grouped.items())]
    return dict(per_trajectory=trajectories, aggregates=aggregates)


def case_list(analysis, plans, responses, snapshots, features, predictions, labels):
    data = {s['snapshot_id']: s for s in snapshots}
    pp = {(r['snapshot_id'], r['memory_id']): v for r, v in zip(features, predictions, strict=True)}
    costs = {(r['snapshot_id'], r['memory_id']): r['features']['memory_tokens'] for r in features}
    loo = {(r['snapshot_id'], r['memory_id']): r['loo_value'] for r in labels}
    index = {response_key(r['snapshot_id'], r['storage_ids'], r['query_id'], r['seed']): r for r in responses}
    plan_index = {(p['snapshot_id'], p['candidate'], p['budget_ratio']): p for p in plans if p['selection_seed'] is None}
    rows = [r for r in analysis['query_diagnostics'] if r['candidate'] == 'utility_aware' and r['budget_ratio'] in (.25, .5, .75)]
    chosen, missing = [], []
    for kind in ('budget_infeasible', 'support_not_retained', 'support_not_retrieved', 'redundancy_hindsight', 'complementarity_generation'):
        eligible = []
        for r in rows:
            match = r['category'] == kind
            if kind == 'complementarity_generation':
                match = r['scenario'] == 'complementarity' and r['category'] == 'supported_but_wrong'
            if kind == 'redundancy_hindsight':
                hp = plan_index[r['snapshot_id'], 'hindsight_loo', r['budget_ratio']]
                hr = index[response_key(r['snapshot_id'], hp['storage_ids'], r['query_id'], hp['seed'])]
                match = r['scenario'] == 'redundancy' and r['category'] == 'correct' and hr['metrics']['answer.exact_match'] == 0
            if match:
                eligible.append(r)
        # Prefer distinct snapshots, so two paraphrases are not presented as independent cases.
        selected, seen = [], set()
        for r in sorted(eligible, key=lambda r: (r['snapshot_id'], r['query_id'], r['budget_ratio'])):
            if r['snapshot_id'] not in seen:
                selected.append(r)
                seen.add(r['snapshot_id'])
            if len(selected) == 2:
                break
        if not selected:
            missing.append(kind)
        for r in selected:
            s = data[r['snapshot_id']]
            q = next(q for q in s['future_queries'] if q['query_id'] == r['query_id'])
            comparisons = []
            for name in ('utility_aware', 'importance', 'hindsight_loo', 'full'):
                p = plan_index[r['snapshot_id'], name, r['budget_ratio']]
                key = response_key(r['snapshot_id'], p['storage_ids'], r['query_id'], p['seed'])
                response = index[key]
                comparisons.append(dict(candidate=name, storage_ids=p['storage_ids'], budget_tokens=p['budget_tokens'],
                                         store_tokens=p['store_tokens'], context_ids=[m['memory_id'] for m in response['context']],
                                         generated_answer=response['generated_answer'], metrics=response['metrics'], response_key=[key[0], list(key[1]), key[2], key[3]]))
            chosen.append(dict(case_id=f'e3-case-{len(chosen)+1:02d}', case_type=kind, snapshot_id=s['snapshot_id'],
                               trajectory_id=s['trajectory_id'], scenario=s['scenario'], query=q, budget_ratio=r['budget_ratio'],
                               diagnostic=r, memories=[dict(m, token_cost=costs[s['snapshot_id'], m['memory_id']],
                               predicted_value=pp[s['snapshot_id'], m['memory_id']], loo_value=loo[s['snapshot_id'], m['memory_id']])
                               for m in s['memories']], comparisons=comparisons))
    return dict(cases=chosen, absent_case_types=missing,
                scope='Post-hoc E3 examples, not blind E4 data; no subset enumeration or causal attribution')
