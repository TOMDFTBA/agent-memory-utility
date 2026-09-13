"""E3 baseline supplementation boundaries and replay checks."""
import json
import subprocess
import sys
from pathlib import Path

import numpy as np
import pytest

HERE = Path(__file__).parents[1] / 'experiments/utility-retention'
sys.path.insert(0, str(HERE))
from utility_retention.baselines import dedup_select, importance_prompt, parse_importance, similarity_table  # noqa: E402
from utility_retention.e3_baselines import audit  # noqa: E402


def test_importance_prompt_and_parse_are_frozen():
    prompt = importance_prompt('User prefers rail travel.')
    assert 'no future task is known' in prompt
    assert 'User prefers rail travel.' in prompt
    assert parse_importance('5') == {'score': 5, 'valid': True}
    assert parse_importance('2.0!') == {'score': 2, 'valid': True}
    assert parse_importance('important') == {'score': 3, 'valid': False}
    with pytest.raises(ValueError):
        importance_prompt('')


def test_dedup_select_uses_past_only_and_newest_representatives():
    memories = [
        {'memory_id': 'm1', 'event_order': 1, 'content': 'old duplicate'},
        {'memory_id': 'm2', 'event_order': 2, 'content': 'new duplicate'},
        {'memory_id': 'm3', 'event_order': 3, 'content': 'distinct'},
    ]
    costs = {'m1': 5, 'm2': 5, 'm3': 5}
    table = {'memory_ids': ['m1', 'm2', 'm3'],
             'similarities': [[1, .95, .1], [.95, 1, .1], [.1, .1, 1]]}
    result = dedup_select(memories, costs, table, .9, 10)
    assert result['representatives'] == ['m3', 'm2']
    assert result['excluded'] == {'m1': 'm2'}
    assert result['storage_ids'] == ['m2', 'm3']
    with pytest.raises(ValueError, match='past-only'):
        dedup_select([dict(memories[0], future=True)], {'m1': 1}, {'memory_ids': ['m1'], 'similarities': [[1]]}, .9, 1)


def test_dedup_rejects_bad_similarity_identity():
    memories = [{'memory_id': 'm1', 'event_order': 1, 'content': 'a'}]
    with pytest.raises(ValueError):
        dedup_select(memories, {'m1': 1}, {'memory_ids': ['other'], 'similarities': [[1]]}, .9, 1)
    with pytest.raises(ValueError):
        dedup_select(memories, {'m1': 1}, {'memory_ids': ['m1'], 'similarities': [[2]]}, .9, 1)


def test_similarity_table_normalizes_and_orders_ids():
    class Embedder:
        def documents(self, texts):
            assert texts == ['a', 'b']
            return np.array([[2, 0], [1, 1]], dtype=float)

    result = similarity_table([
        {'memory_id': 'b', 'content': 'b'},
        {'memory_id': 'a', 'content': 'a'},
    ], Embedder())
    assert result['memory_ids'] == ['a', 'b']
    assert pytest.approx(result['similarities'][0][1], rel=1e-6) == 2**-0.5


@pytest.fixture(scope='module')
def e3_run(tmp_path_factory):
    output = tmp_path_factory.mktemp('e3') / 'run'
    subprocess.run([sys.executable, str(HERE/'e3_baselines.py'), 'prepare',
                    '--backend', 'test', '--output', str(output)], check=True)
    subprocess.run([sys.executable, str(HERE/'e3_baselines.py'), 'run',
                    '--backend', 'test', '--output', str(output)], check=True)
    return output


def test_e3_test_backend_replays_and_audits(e3_run):
    result = audit(e3_run, HERE/'results/e2-development-model')
    assert result['passed']
    manifest = json.loads((e3_run/'manifest.json').read_text())
    selection = json.loads((e3_run/'selection.json').read_text())
    frozen = json.loads((e3_run/'frozen-strategies.json').read_text())
    assert manifest['status'] == 'COMPLETE'
    assert manifest['ready_for_e3'] is False
    assert selection['test_evaluated'] is False
    assert selection['importance_valid_fraction'] == 1
    assert frozen['status'] == 'DEVELOPMENT_ONLY'


def test_e3_resume_is_byte_stable(e3_run):
    before = (e3_run/'responses.jsonl').read_bytes()
    subprocess.run([sys.executable, str(HERE/'e3_baselines.py'), 'run',
                    '--backend', 'test', '--output', str(e3_run)], check=True)
    assert (e3_run/'responses.jsonl').read_bytes() == before
