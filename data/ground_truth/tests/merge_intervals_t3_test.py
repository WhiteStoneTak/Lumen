"""T3 post-transform test suite for merge_intervals.

Transform spec (merge_intervals.TR01): Change the function to return the total
number of integer points covered by at least one interval, rather than the list
of merged intervals. Return a single integer. Empty input returns 0.

These tests are run against a model's transformed implementation.
Parse failure and execution failure score 0.0 without running tests.
"""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path


def _load_func(source_path: str):
    spec = importlib.util.spec_from_file_location("_mi_t3_mod", source_path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.merge_intervals


_DEFAULT_SOURCE = str(
    Path(__file__).resolve().parents[2] / "functions" / "raw" / "merge_intervals.py"
)
_SOURCE = _DEFAULT_SOURCE
merge_intervals = _load_func(_SOURCE)


class MergeIntervalsT3CoveredLengthTests(unittest.TestCase):
    """Transformed function must return total covered integer point count."""

    def test_basic_covered_length(self) -> None:
        # [1,3],[2,6],[8,10]: covers 1..6 (6 pts) and 8..10 (3 pts) = 9
        result = merge_intervals([[1, 3], [2, 6], [8, 10]])
        self.assertEqual(result, 9)

    def test_return_type_is_int(self) -> None:
        result = merge_intervals([[1, 3], [2, 6], [8, 10]])
        self.assertIsInstance(result, int)

    def test_not_a_list(self) -> None:
        # Original returns a list; transform must return int
        result = merge_intervals([[1, 3]])
        self.assertNotIsInstance(result, list)

    def test_non_overlapping_intervals(self) -> None:
        # [1,2],[4,6]: 2 pts + 3 pts = 5
        result = merge_intervals([[1, 2], [4, 6]])
        self.assertEqual(result, 5)

    def test_touching_intervals(self) -> None:
        # [1,2],[2,4]: covers 1,2,3,4 = 4 pts
        result = merge_intervals([[1, 2], [2, 4]])
        self.assertEqual(result, 4)

    def test_empty_returns_zero(self) -> None:
        result = merge_intervals([])
        self.assertEqual(result, 0)

    def test_single_interval(self) -> None:
        # [3,7]: covers 3,4,5,6,7 = 5 pts
        result = merge_intervals([[3, 7]])
        self.assertEqual(result, 5)

    def test_contained_interval(self) -> None:
        # [1,10],[3,5]: covered = 1..10 = 10 pts
        result = merge_intervals([[1, 10], [3, 5]])
        self.assertEqual(result, 10)


class MergeIntervalsT3EdgeCaseTests(unittest.TestCase):
    """Edge cases for covered-length semantics."""

    def test_identical_intervals(self) -> None:
        # Two identical [2,5]: covered = 2..5 = 4 pts
        result = merge_intervals([[2, 5], [2, 5]])
        self.assertEqual(result, 4)

    def test_single_point_interval(self) -> None:
        # [3,3]: covers just point 3 = 1 pt
        result = merge_intervals([[3, 3]])
        self.assertEqual(result, 1)

    def test_multiple_disjoint(self) -> None:
        # [1,1],[3,3],[5,5]: 1+1+1 = 3 pts
        result = merge_intervals([[1, 1], [3, 3], [5, 5]])
        self.assertEqual(result, 3)


if __name__ == "__main__":
    unittest.main()
