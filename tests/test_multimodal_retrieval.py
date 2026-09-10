"""Boundary coverage and page-level score attribution; no model/GPU required."""
import importlib.util
from pathlib import Path

import numpy as np
import pytest

path = Path(__file__).resolve().parents[1] / 'experiments/multimodal-retrieval-mini/run_demo.py'
spec = importlib.util.spec_from_file_location('multimodal_demo', path)
demo = importlib.util.module_from_spec(spec)
spec.loader.exec_module(demo)


def test_tail_and_exact_boundary_are_covered_once_outside_overlap():
    for n in [1, 512, 513, 960, 2457]:
        ranges = list(demo.chunk_ranges(n, 512, 64))
        covered = set()
        for start, end in ranges:
            assert 0 < end - start <= 512
            covered.update(range(start, end))
        assert covered == set(range(n))
        assert ranges[-1][1] == n
        assert len(ranges) == 1 or ranges[-2][1] < n


def test_invalid_or_empty_chunks_fail():
    for params in [(0, 512, 64), (5, 0, 0), (5, 64, 64), (5, 64, -1)]:
        with pytest.raises(ValueError):
            list(demo.chunk_ranges(*params))


def test_page_aggregation_preserves_owners_with_interleaved_chunks():
    scores = np.array([[.2, .9, .8], [.7, .1, .3]])
    np.testing.assert_allclose(demo.aggregate(scores, [0, 1, 0], 2), [[.8, .9], [.7, .1]])
    with pytest.raises(ValueError):
        demo.aggregate(scores, [0, 0, 0], 2)
