"""Bounded float comparison for cross-platform numerical replay, not artifact identity."""
import math


def replay_equal(actual, expected):
    if type(actual) is not type(expected):
        return False
    if isinstance(actual, float):
        return (math.isfinite(actual) and math.isfinite(expected)
                and math.isclose(actual, expected, rel_tol=1e-10, abs_tol=1e-12))
    if isinstance(actual, dict):
        return actual.keys() == expected.keys() and all(replay_equal(actual[k], expected[k]) for k in actual)
    if isinstance(actual, list):
        return len(actual) == len(expected) and all(replay_equal(a, b) for a, b in zip(actual, expected))
    return actual == expected
