import copy
import json
import subprocess
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).parents[1] / 'experiments/utility-retention'
sys.path.insert(0, str(HERE))
from utility_retention.dataset import pilot_dataset, validate  # noqa: E402
from utility_retention.engine import Engine, historical_features, score  # noqa: E402
from utility_retention.labeling import evaluate  # noqa: E402


@pytest.fixture(scope='module')
def completed(tmp_path_factory):
    output = tmp_path_factory.mktemp('e1') / 'run'
    subprocess.run([sys.executable, str(HERE / 'run.py'), '--output', str(output)], check=True)
    return output


def load_run(output):
    data = json.loads((output / 'dataset-manifest.json').read_text())
    responses = [json.loads(line) for line in (output / 'responses.jsonl').read_text().splitlines()]
    config = json.loads((HERE / 'configs/pilot.json').read_text())
    return data, responses, config


def test_resume_and_recompute(completed):
    before = (completed / 'responses.jsonl').read_bytes()
    subprocess.run([sys.executable, str(HERE / 'run.py'), '--output', str(completed)], check=True)
    assert before == (completed / 'responses.jsonl').read_bytes()
    subprocess.run([sys.executable, str(HERE / 'evaluate.py'), str(completed)], check=True)
    manifest = json.loads((completed / 'manifest.json').read_text())
    assert manifest['status'] == 'COMPLETE'
    assert manifest['ready_for_stage2'] is False
    result = subprocess.run([sys.executable, str(HERE / 'run.py'), '--output', str(completed), '--seed', '4'],
                            capture_output=True, text=True)
    assert result.returncode != 0 and 'identity mismatch' in result.stderr


@pytest.mark.parametrize('damage', ['time', 'split', 'support', 'duplicate', 'content'])
def test_dataset_boundaries(damage):
    rows = pilot_dataset()
    if damage == 'time':
        rows[0]['history_queries'][0]['event_order'] = 12
    elif damage == 'split':
        rows[2]['memories'][0]['canonical_id'] = rows[0]['memories'][0]['canonical_id']
    elif damage == 'support':
        rows[0]['future_queries'][0]['supporting_memory_sets'] = [['missing']]
    elif damage == 'duplicate':
        rows.append(copy.deepcopy(rows[0]))
    else:
        rows[2]['memories'][0]['content'] = rows[0]['memories'][0]['content']
    with pytest.raises(ValueError):
        validate(rows)


@pytest.mark.parametrize('damage', ['missing', 'duplicate', 'score', 'storage', 'context', 'budget'])
def test_corruption_rejected(completed, damage):
    data, rows, config = load_run(completed)
    if damage == 'missing':
        rows.pop()
    elif damage == 'duplicate':
        rows.append(rows[0])
    elif damage == 'score':
        rows[0]['metrics']['answer.exact_match'] = 1
    elif damage == 'storage':
        row = next(r for r in rows if r['condition'] == 'storage_deletion')
        row['storage_ids'].append(row['deleted_memory_id'])
    elif damage == 'context':
        row = next(r for r in rows if r['condition'] == 'context_deletion')
        row['context'] = list(reversed(rows[0]['context']))
    else:
        rows[0]['memory_tokens'] = config['read_budget'] + 1
    with pytest.raises(ValueError):
        evaluate(data['snapshots'], rows, data['seeds'], data['context_ids'], config, 'test')


@pytest.mark.parametrize('sign', [1, -1, 0])
def test_signed_labels(completed, sign):
    data, rows, config = load_run(completed)
    for row in rows:
        correct = (row['condition'] == 'full') if sign == 1 else (row['condition'] != 'full') if sign == -1 else False
        row['generated_answer'] = row['gold_answer'] if correct else 'UNKNOWN'
        row['metrics'] = score(row['generated_answer'], row['gold_answer'])
    _, labels, report = evaluate(data['snapshots'], rows, data['seeds'], data['context_ids'], config, 'test')
    assert all(r['value'] == sign for r in labels)
    assert not report['ready_for_stage2']


def test_past_only_and_storage_isolation():
    snapshot = pilot_dataset()[0]
    original = copy.deepcopy(snapshot)
    engine = Engine({'embedding': {'backend': 'hash-test'}, 'generation': {'backend': 'evidence-test'}}, 'test', 1024, 3)
    features = historical_features(snapshot['memories'], snapshot['history_queries'], 10, engine)
    assert all(f['retrieval_frequency'] == 1 for f in features)
    hits, _ = engine.retrieve(snapshot['memories'][1:], snapshot['future_queries'][0]['text'])
    assert snapshot['memories'][0]['memory_id'] not in [m['memory_id'] for m in hits]
    assert snapshot == original
    with pytest.raises(ValueError):
        historical_features(snapshot['memories'], snapshot['future_queries'], 10, engine)


def test_noise_prevents_readiness(completed):
    data, rows, config = load_run(completed)
    for row in rows:
        correct = row['condition'] == 'full' and row['seed'] == data['seeds'][0]
        row['generated_answer'] = row['gold_answer'] if correct else 'UNKNOWN'
        row['metrics'] = score(row['generated_answer'], row['gold_answer'])
    _, labels, report = evaluate(data['snapshots'], rows, data['seeds'], data['context_ids'], config, 'model')
    assert all(r['uncertain'] for r in labels)
    assert not report['ready_for_stage2']


def test_partial_run_resumes(completed, tmp_path):
    import shutil
    output = tmp_path / 'resume'
    shutil.copytree(completed, output)
    path = output / 'responses.jsonl'
    original = path.read_text().splitlines()
    path.write_text('\n'.join(original[:3]) + '\n')
    manifest_path = output / 'manifest.json'
    manifest = json.loads(manifest_path.read_text())
    manifest['status'] = 'FAILED'
    manifest_path.write_text(json.dumps(manifest))
    subprocess.run([sys.executable, str(HERE / 'run.py'), '--output', str(output)], check=True)
    assert len(path.read_text().splitlines()) == len(original)
    assert path.read_text().splitlines()[:3] == original[:3]


def test_read_budget_and_historical_availability():
    snapshot = pilot_dataset()[0]
    engine = Engine({'embedding': {'backend': 'hash-test'}, 'generation': {'backend': 'evidence-test'}}, 'test', 1, 3)
    assert engine.retrieve(snapshot['memories'], 'locker')[0] == []
    history = [dict(query_id='early', event_order=1.5, text='locker')]
    features = historical_features(snapshot['memories'], history, 10, engine)
    late = next(f for f in features if f['memory_id'].endswith('m2'))
    assert late['history_observed'] is False
    assert late['historical_similarity'] is None


def test_frozen_pressure_dataset():
    from generate_e1_dataset import build
    rows = build()
    validate(rows)
    assert len(rows) == 12
    assert {s['scenario'] for s in rows} == {'old_but_useful', 'frequent_but_useless', 'redundancy', 'complementarity'}
    for snapshot in rows:
        memories = snapshot['memories']
        supports = snapshot['future_queries'][0]['supporting_memory_sets']
        assert len(memories) == 4
        if snapshot['scenario'] == 'redundancy':
            assert memories[0]['canonical_id'] == memories[1]['canonical_id']
            assert len(supports) == 2 and all(len(s) == 1 for s in supports)
        if snapshot['scenario'] == 'complementarity':
            gold = snapshot['future_queries'][0]['gold_answer']
            assert all(gold not in m['content'] for m in memories)
            assert len(supports) == 1 and len(supports[0]) == 2
        if snapshot['scenario'] == 'frequent_but_useless':
            assert len(snapshot['history_queries']) == 3


def test_report_is_json_serializable(completed):
    result = subprocess.run([sys.executable, str(HERE / 'report.py'), str(completed)],
                            capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    summary = json.loads((completed / 'summary.json').read_text())
    assert summary['response_count'] == 144
    assert summary['ready_for_stage2'] is False


def test_extension_independence_variation_and_controls():
    from generate_e1_extension import build, check_disjoint
    from generate_e1_dataset import build as previous
    from diagnose_e1 import contexts
    from collections import Counter
    rows = build()
    validate(rows)
    check_disjoint(rows, previous())
    assert Counter(s['split'] for s in rows) == {'train': 24, 'validation': 12, 'test': 12}
    assert len({s['diagnostic_metadata']['entity'] for s in rows}) == 48
    assert len({s['future_queries'][0]['gold_answer'] for s in rows}) == 48
    ranks = []
    for s in rows:
        ids = [m['memory_id'] for m in s['memories']]
        assert all(s['scenario'] not in mid and s['split'] not in mid for mid in ids)
        if s['scenario'] == 'old_but_useful':
            assert s['future_queries'][0]['supporting_memory_sets'][0] == [ids[0]]
        else:
            ranks.append(ids.index(s['diagnostic_metadata']['prefix_memory_id']))
        if s['scenario'] == 'complementarity':
            c = contexts(s)
            assert c['support_only'] == list(reversed(c['support_reversed']))
            assert len(c['prefix_only']) == len(c['suffix_only']) == 1
            assert c['prefix_only'] != c['suffix_only']
            assert all(s['future_queries'][0]['gold_answer'] not in m['content'] for m in s['memories'])
    assert len(set(ranks)) == 4


def test_extension_end_to_end(tmp_path):
    from generate_e1_extension import build
    rows = build()
    data = []
    for split in ('train', 'validation', 'test'):
        data.extend(next(s for s in rows if s['split'] == split and s['scenario'] == family)
                    for family in ('complementarity', 'frequent_but_useless'))
    dataset = tmp_path/'dataset.json'
    dataset.write_text(json.dumps(data))
    output = tmp_path/'main'
    diagnostic = tmp_path/'diagnostic'
    subprocess.run([sys.executable, str(HERE/'run.py'), '--dataset', str(dataset), '--output', str(output)], check=True)
    subprocess.run([sys.executable, str(HERE/'diagnose_e1.py'), '--main-output', str(output),
                    '--output', str(diagnostic), '--backend', 'test'], check=True)
    subprocess.run([sys.executable, str(HERE/'report_extension.py'), '--main-output', str(output),
                    '--diagnostic-output', str(diagnostic)], check=True)
    test = json.loads((output/'handoff/test-features.json').read_text())
    assert len(test) == 8
    assert all('target' not in row and 'diagnostic_metadata' not in row and 'scenario' not in row for row in test)
    assert all('gold_answer' not in str(row['features']) for row in test)
    diagnostic_rows = [json.loads(x) for x in (diagnostic/'responses.jsonl').read_text().splitlines()]
    assert len(diagnostic_rows) == 32
    assert all(row['split'] != 'test' for row in diagnostic_rows)
    before = (diagnostic/'responses.jsonl').read_bytes()
    subprocess.run([sys.executable, str(HERE/'diagnose_e1.py'), '--main-output', str(output),
                    '--output', str(diagnostic), '--backend', 'test'], check=True)
    assert before == (diagnostic/'responses.jsonl').read_bytes()
