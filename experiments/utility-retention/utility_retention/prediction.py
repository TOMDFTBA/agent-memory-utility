"""Small signed ridge models; inference has no target or future-query interface."""
import numpy as np

FEATURES = ('recency_rank', 'age', 'retrieval_frequency', 'history_observed', 'historical_similarity', 'memory_tokens')
GROUPS = {
    'full': FEATURES,
    'no_frequency': tuple(f for f in FEATURES if f != 'retrieval_frequency'),
    'no_recency': tuple(f for f in FEATURES if f not in ('recency_rank', 'age')),
    'recency_frequency': ('recency_rank', 'age', 'retrieval_frequency'),
}


def matrix(features, names):
    if not features or any(set(row) != set(FEATURES) for row in features):
        raise ValueError('Features must exactly match historical whitelist')
    result = np.array([[np.nan if row[k] is None else float(row[k]) for k in names] for row in features])
    if np.isinf(result).any():
        raise ValueError('Nonfinite feature')
    for row in features:
        if any(row[k] is None for k in FEATURES if k != 'historical_similarity'):
            raise ValueError('Only historical similarity can be missing')
        if not row['history_observed'] and row['historical_similarity'] is not None:
            raise ValueError('Unobserved history cannot have similarity')
    return result


def fit(rows, group, alpha):
    if any(r['target']['uncertain'] for r in rows):
        raise ValueError('Uncertain labels require a new explicit training protocol')
    names = GROUPS[group]
    x = matrix([r['features'] for r in rows], names)
    medians = [float(np.median(c[np.isfinite(c)])) if np.isfinite(c).any() else 0.0 for c in x.T]
    x = np.where(np.isnan(x), medians, x)
    means, scales = x.mean(axis=0), x.std(axis=0)
    scales[scales == 0] = 1
    x = (x - means) / scales
    y = np.array([r['target']['value'] for r in rows], dtype=float)
    if not np.isfinite(y).all() or alpha <= 0:
        raise ValueError('Invalid labels or ridge regularization')
    intercept = float(y.mean())
    weights = np.linalg.solve(x.T @ x + alpha * np.eye(len(names)), x.T @ (y - intercept))
    return dict(kind='ridge', group=group, alpha=alpha, features=list(names),
                medians=medians, means=means.tolist(), scales=scales.tolist(),
                weights=weights.tolist(), intercept=intercept, training_rows=len(rows))


def predict(model, features):
    matrix(features, FEATURES)  # Validate even for the constant baseline.
    if model['kind'] == 'zero':
        return [0.0] * len(features)
    x = matrix(features, model['features'])
    x = np.where(np.isnan(x), model['medians'], x)
    return (((x - model['means']) / model['scales']) @ np.array(model['weights']) + model['intercept']).tolist()
