"""E2 boundary, decision, metric and durable-run checks."""
import copy
import json
import subprocess
import sys
from pathlib import Path

import numpy as np
import pytest

HERE = Path(__file__).parents[1] / 'experiments/utility-retention'
sys.path.insert(0, str(HERE))
from utility_retention.prediction import fit, predict  # noqa: E402
from utility_retention.policies import select  # noqa: E402
from utility_retention.e2_metrics import prediction_metrics  # noqa: E402
from utility_retention.e2 import audit, verify_responses  # noqa: E402


def rows():
    return json.loads((HERE/'results/e1-extension-model/handoff/train.json').read_text())


def test_predict_cannot_accept_future_fields_or_refit():
    data = rows()
    model = fit(data, 'full', 1)
    original = copy.deepcopy(model)
    features = [copy.deepcopy(r['features']) for r in data[:2]]
    predict(model, features)
    features[0]['age'] = 100000
    predict(model, features)
    assert model == original
    features[0]['supporting_memory_ids'] = ['secret']
    with pytest.raises(ValueError, match='whitelist'):
        predict(model, features)


def test_ridge_recovers_signal_and_keeps_negative_values():
    data = rows()[:12]
    for i, r in enumerate(data):
        r['features']['age'] = i
        r['target']['value'] = (i-5)/10
    model = fit(data, 'full', .001)
    predictions = predict(model, [r['features'] for r in data])
    assert min(predictions) < 0
    assert np.mean(abs(np.array(predictions)-[r['target']['value'] for r in data])) < .01


def test_missing_history_and_uncertain_labels():
    data = rows()[:8]
    for r in data:
        r['features']['historical_similarity'] = None
        r['features']['history_observed'] = False
    model = fit(data, 'full', 1)
    assert np.isfinite(predict(model, [r['features'] for r in data])).all()
    data[0]['target']['uncertain'] = True
    with pytest.raises(ValueError, match='Uncertain'):
        fit(data, 'full', 1)


def test_selector_budget_skip_ties_and_signed_scores():
    costs = {'a': 10, 'b': 4, 'c': 3, 'd': 1}
    scores = {'a': 9, 'b': 1, 'c': 1, 'd': -1}
    assert select(costs, scores, 7, True) == ['b', 'c']
    assert select(costs, scores, 8, True) == ['b', 'c']
    assert select(costs, scores, 8, False) == ['b', 'c', 'd']
    assert select(costs, dict.fromkeys(costs, 0), 30, True) == []


def test_undefined_ranks_not_zero():
    data = rows()[:4]
    for r in data:
        r['target']['value'] = 0
    report = prediction_metrics(data, [0]*len(data))
    assert report['metrics']['prediction.spearman'] is None
    assert report['metrics']['prediction.negative_recall'] is None


@pytest.fixture(scope='module')
def e2_run(tmp_path_factory):
    output = tmp_path_factory.mktemp('e2')/'run'
    for action in ('prepare', 'run'):
        subprocess.run([sys.executable, str(HERE/'e2.py'), action, '--backend', 'test', '--output', str(output)], check=True)
    return output


def test_full_replay_and_resume(e2_run):
    assert audit(e2_run)['passed']
    before = (e2_run/'responses.jsonl').read_bytes()
    subprocess.run([sys.executable, str(HERE/'e2.py'), 'run', '--backend', 'test', '--output', str(e2_run)], check=True)
    assert (e2_run/'responses.jsonl').read_bytes() == before
    assert not json.loads((e2_run/'manifest.json').read_text())['test_evaluated']


@pytest.mark.parametrize('damage', ['missing', 'score', 'storage', 'context', 'budget', 'duplicate'])
def test_response_corruption_rejected(e2_run, damage):
    def load(name):
        return json.loads((e2_run/f'{name}.json').read_text())
    records = [json.loads(line) for line in (e2_run/'responses.jsonl').read_text().splitlines()]
    if damage == 'missing':
        records.pop()
    elif damage == 'score':
        records[0]['metrics']['answer.exact_match'] = 99
    elif damage == 'storage':
        records[0]['storage_ids'] = ['unexpected']
    elif damage == 'context':
        r = next(r for r in records if r['context'])
        r['context'][0]['content'] = 'corrupted'
    elif damage == 'budget':
        records[0]['memory_tokens'] = 999999
    else:
        records.append(records[0])
    with pytest.raises(ValueError):
        verify_responses(load('plans'), load('validation-snapshots'), records, load('settings'))
