"""Shared deterministic token-budget selector; no future task access."""
import math
import random


def select(costs, scores, budget, positive_only=False):
    if set(costs) != set(scores) or budget < 0:
        raise ValueError('Invalid selector inputs')
    if any(type(c) is not int or c <= 0 for c in costs.values()):
        raise ValueError('Costs must be positive token counts')
    if any(not math.isfinite(v) for v in scores.values()):
        raise ValueError('Scores must be finite')
    selected, spent = [], 0
    for mid in sorted(costs, key=lambda m: (-scores[m], m)):
        if positive_only and scores[mid] <= 0:
            continue
        if spent + costs[mid] <= budget:
            selected.append(mid)
            spent += costs[mid]
    return selected


def baseline_scores(rows, policy, seed=0):
    if policy == 'recency':
        return {r['memory_id']: -r['features']['recency_rank'] for r in rows}
    if policy == 'retrieval_frequency':
        return {r['memory_id']: r['features']['retrieval_frequency'] for r in rows}
    if policy == 'random':
        rng = random.Random(seed)
        return {mid: rng.random() for mid in sorted(r['memory_id'] for r in rows)}
    raise ValueError('Unknown historical policy')
