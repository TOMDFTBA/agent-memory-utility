"""Exact finite-set E4 diagnostics. No fitting, generation, or future-aware deployable selection."""
import math
from collections import defaultdict
from itertools import combinations
from statistics import mean

from .e2_metrics import paired, response_key, summarize
from .e3_formal import hindsight_plans, loo_labels
from .e3_supplement_analysis import analyze as failure_analysis

EXACT_PREDICTED = 'predicted_sum_optimal'
EXACT_LOO = 'hindsight_loo_sum_optimal'
CORE = ('utility_aware', EXACT_PREDICTED, 'hindsight_loo', EXACT_LOO, 'best_subset')


def subsets(ids):
    ids = sorted(ids)
    return [list(c) for n in range(len(ids)+1) for c in combinations(ids, n)]


def enumeration_plans(past, seed):
    return [dict(snapshot_id=s['snapshot_id'], diagnostic='subset_enumeration', storage_ids=ids, seed=seed)
            for s in past for ids in subsets(m['memory_id'] for m in s['memories'])]


def optimum(feasible, scores):
    """Ties: smaller token cost, then cardinality, then sorted IDs; never future EM."""
    values = [sum(scores[m] for m in r['storage_ids']) for r in feasible]
    top = max(values)
    tied = [r for r, v in zip(feasible, values, strict=True) if abs(v-top) <= 1e-12]
    chosen = min(tied, key=lambda r: (r['store_tokens'], len(r['storage_ids']), r['storage_ids']))
    return chosen, tied, top


def exact_predicted_plans(past, features, predictions, settings):
    values = {(r['snapshot_id'], r['memory_id']): v for r, v in zip(features, predictions, strict=True)}
    costs = {(r['snapshot_id'], r['memory_id']): r['features']['memory_tokens'] for r in features}
    result = []
    for s in past:
        sid = s['snapshot_id']
        ids = sorted(m['memory_id'] for m in s['memories'])
        all_sets = [dict(storage_ids=a, store_tokens=sum(costs[sid, m] for m in a)) for a in subsets(ids)]
        for ratio in settings['budget_ratios']:
            budget = math.floor(sum(costs[sid, m] for m in ids)*ratio)
            chosen, _, _ = optimum([a for a in all_sets if a['store_tokens'] <= budget],
                                    {m: values[sid, m] for m in ids})
            result.append(dict(snapshot_id=sid, candidate=EXACT_PREDICTED, selection_seed=None,
                               budget_ratio=ratio, budget_tokens=budget, **chosen, seed=settings['generation_seed']))
    return result


def subset_table(snapshots, features, responses, seed):
    index = {response_key(r['snapshot_id'], r['storage_ids'], r['query_id'], r['seed']): r for r in responses}
    costs = {(r['snapshot_id'], r['memory_id']): r['features']['memory_tokens'] for r in features}
    table = []
    for s in snapshots:
        sid = s['snapshot_id']
        for ids in subsets(m['memory_id'] for m in s['memories']):
            rr = [index[response_key(sid, ids, q['query_id'], seed)] for q in s['future_queries']]
            table.append(dict(snapshot_id=sid, trajectory_id=s['trajectory_id'], scenario=s['scenario'],
                              storage_ids=ids, store_tokens=sum(costs[sid, m] for m in ids),
                              metrics={k: mean(r['metrics'][k] for r in rr) for k in rr[0]['metrics']},
                              query_response_keys=[[sid, ids, r['query_id'], seed] for r in rr]))
    return table


def derive(snapshots, features, predictions, deployable, responses, settings, cohorts):
    seed = settings['generation_seed']
    table = subset_table(snapshots, features, responses, seed)
    labels = loo_labels(snapshots, responses, seed)
    loo = {(r['snapshot_id'], r['memory_id']): r['loo_value'] for r in labels}
    predicted = {(r['snapshot_id'], r['memory_id']): v for r, v in zip(features, predictions, strict=True)}
    by_sid = defaultdict(list)
    for row in table:
        by_sid[row['snapshot_id']].append(row)
    plans = [dict(p) for p in deployable] + hindsight_plans(features, labels, settings)
    for p in plans:
        p.pop('selection_seconds', None)
    ties, interactions = [], []
    for s in snapshots:
        sid = s['snapshot_id']
        ids = sorted(m['memory_id'] for m in s['memories'])
        rows = by_sid[sid]
        full_cost = next(r['store_tokens'] for r in rows if r['storage_ids'] == ids)
        lookup = {tuple(r['storage_ids']): r['metrics']['answer.exact_match'] for r in rows}
        for ratio in settings['budget_ratios']:
            budget = math.floor(full_cost*ratio)
            feasible = [r for r in rows if r['store_tokens'] <= budget]
            best_score = max(r['metrics']['answer.exact_match'] for r in feasible)
            best_ties = [r for r in feasible if r['metrics']['answer.exact_match'] == best_score]
            best = min(best_ties, key=lambda r: (r['store_tokens'], len(r['storage_ids']), r['storage_ids']))
            for name, values in ((EXACT_PREDICTED, predicted), (EXACT_LOO, loo)):
                chosen, tied, top = optimum(feasible, {m: values[sid, m] for m in ids})
                heuristic_name = 'utility_aware' if name == EXACT_PREDICTED else 'hindsight_loo'
                heuristic = next(p for p in plans if p['snapshot_id'] == sid and
                                 p['candidate'] == heuristic_name and p['budget_ratio'] == ratio)
                heuristic_sum = sum(values[sid, m] for m in heuristic['storage_ids'])
                if name == EXACT_LOO:
                    plans.append(dict(snapshot_id=sid, candidate=name, selection_seed=None, budget_ratio=ratio,
                                      budget_tokens=budget, storage_ids=chosen['storage_ids'],
                                      store_tokens=chosen['store_tokens'], seed=seed))
                ties.append(dict(snapshot_id=sid, cohort=cohorts[sid], scenario=s['scenario'], candidate=name,
                                 budget_ratio=ratio, feasible_subset_count=len(feasible), optimal_subset_count=len(tied),
                                 selected_ids=chosen['storage_ids'], optimal_subsets=[r['storage_ids'] for r in tied],
                                 metrics={'diagnostic.optimal_score_sum': top,
                                          'diagnostic.heuristic_score_sum': heuristic_sum,
                                          'diagnostic.score_sum_gap': top-heuristic_sum,
                                          'diagnostic.tie_em_min': min(r['metrics']['answer.exact_match'] for r in tied),
                                          'diagnostic.tie_em_max': max(r['metrics']['answer.exact_match'] for r in tied),
                                          'diagnostic.selected_em': chosen['metrics']['answer.exact_match'],
                                          'diagnostic.best_subset_em': best_score}))
            plans.append(dict(snapshot_id=sid, candidate='best_subset', selection_seed=None, budget_ratio=ratio,
                              budget_tokens=budget, storage_ids=best['storage_ids'], store_tokens=best['store_tokens'], seed=seed))
        support_sets = s['future_queries'][0]['supporting_memory_sets']
        for i, j in combinations(ids, 2):
            role = ('redundant_support' if [i] in support_sets and [j] in support_sets else
                    'complementary_support' if any({i, j} <= set(g) for g in support_sets) else 'other')
            for background in subsets(m for m in ids if m not in (i, j)):
                conditions = [background, sorted(background+[i]), sorted(background+[j]), sorted(background+[i, j])]
                f0, fi, fj, fij = [lookup[tuple(a)] for a in conditions]
                interactions.append(dict(snapshot_id=sid, cohort=cohorts[sid], scenario=s['scenario'],
                                         memory_ids=[i, j], background_ids=background, pair_role=role,
                                         storage_conditions=conditions, window_scores=[f0, fi, fj, fij],
                                         metrics={'diagnostic.interaction': fij-fi-fj+f0,
                                                  'diagnostic.marginal_i_without_j': fi-f0,
                                                  'diagnostic.marginal_i_with_j': fij-fj}))
    results = {}
    contrasts = [('best_subset', c) for c in CORE[:-1]] + [
        (EXACT_PREDICTED, 'utility_aware'), (EXACT_LOO, 'hindsight_loo'), ('hindsight_loo', 'utility_aware')]
    for cohort in sorted(set(cohorts.values())):
        ss = [s for s in snapshots if cohorts[s['snapshot_id']] == cohort]
        pp = [p for p in plans if cohorts[p['snapshot_id']] == cohort]
        summary = summarize(pp, responses, ss, [dict(r, target={'value': r['loo_value']}) for r in labels])
        primary = defaultdict(list)
        for row in summary['per_trajectory']:
            if row['budget_ratio'] in settings['primary_budget_ratios']:
                primary[row['candidate'], row['trajectory_id']].append(row['metrics']['answer.exact_match'])
        pooled = {'per_trajectory': [dict(candidate=c, trajectory_id=t, budget_ratio='primary_average',
                                         metrics={'answer.exact_match': mean(v)}) for (c, t), v in sorted(primary.items())]}
        paired_rows = []
        for ratio in ['primary_average']+settings['budget_ratios']:
            for a, b in contrasts:
                row = paired(pooled if ratio == 'primary_average' else summary, a, b, ratio,
                             settings['bootstrap_seed'], settings['bootstrap_repeats'])
                row['inference'] = f'descriptive {cohort}; finite fixed-system diagnostic, no multiplicity correction'
                paired_rows.append(row)
        summary.update(primary_per_trajectory=pooled['per_trajectory'], paired_differences=paired_rows,
                       failures=failure_analysis(pp, responses, ss, features))
        results[cohort] = summary
    return dict(subset_scores=table, labels=labels, plans=plans, ties=ties, interactions=interactions, cohort_summaries=results)
