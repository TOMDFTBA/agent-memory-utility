"""Numerical replay may tolerate roundoff, but not different scientific decisions."""
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'experiments/utility-retention'))
from utility_retention.numeric_replay import replay_equal


def test_roundoff_and_discrete_decisions():
    expected = {'weights': [0.1, 0.0], 'storage_ids': ['m1'], 'budget': 32}
    assert replay_equal({'weights': [0.1 + 1e-14, 1e-14], 'storage_ids': ['m1'], 'budget': 32}, expected)
    assert not replay_equal({**expected, 'storage_ids': ['m2']}, expected)
    assert not replay_equal({**expected, 'budget': 33}, expected)
    assert not replay_equal({**expected, 'weights': [0.101, 0.0]}, expected)
    assert not replay_equal({'x': 1}, {'x': True})
    assert not replay_equal([float('nan')], [float('nan')])
    assert not replay_equal([float('inf')], [float('inf')])
