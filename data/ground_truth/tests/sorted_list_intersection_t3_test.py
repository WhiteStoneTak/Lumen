"""T3 post-transform test suite for sorted_list_intersection.

Transform spec (sorted_list_intersection.TR01): Change from multiset
intersection to multiset symmetric difference. If element x appears m times
in a and n times in b, include abs(m-n) copies in result when m != n, 0 when
m == n. Result is sorted ascending.

These tests are run against a model's transformed implementation.
Parse failure and execution failure score 0.0 without running tests.
"""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path


def _load_func(source_path: str):
    spec = importlib.util.spec_from_file_location("_sli_t3_mod", source_path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.sorted_list_intersection


_DEFAULT_SOURCE = str(
    Path(__file__).resolve().parents[2] / "functions" / "raw" / "sorted_list_intersection.py"
)
_SOURCE = _DEFAULT_SOURCE
sorted_list_intersection = _load_func(_SOURCE)


class SortedListIntersectionT3SymDiffTests(unittest.TestCase):
    """Transformed function must implement multiset symmetric difference."""

    def test_basic_symmetric_difference(self) -> None:
        # a=[1,1,2,3], b=[1,1,1,3,3]
        # 1: 2 vs 3 -> 1 copy; 2: 1 vs 0 -> 1 copy; 3: 1 vs 2 -> 1 copy
        result = sorted_list_intersection([1, 1, 2, 3], [1, 1, 1, 3, 3])
        self.assertEqual(result, [1, 2, 3])

    def test_excess_copies_included(self) -> None:
        # a=[2,2,2], b=[2,2]: 3 vs 2 -> 1 copy of 2
        result = sorted_list_intersection([2, 2, 2], [2, 2])
        self.assertEqual(result, [2])

    def test_disjoint_lists_returns_union(self) -> None:
        # No common elements: all appear in result
        result = sorted_list_intersection([1, 3, 5], [2, 4, 6])
        self.assertEqual(result, [1, 2, 3, 4, 5, 6])

    def test_equal_counts_excluded(self) -> None:
        # a=[1,1,2], b=[1,1,3]: 1 appears equal (2 vs 2) -> excluded
        # 2 appears 1 vs 0 -> 1 copy; 3 appears 0 vs 1 -> 1 copy
        result = sorted_list_intersection([1, 1, 2], [1, 1, 3])
        self.assertEqual(result, [2, 3])

    def test_differs_from_intersection(self) -> None:
        # Symmetric difference != intersection for overlapping lists
        # a=[1,2,3], b=[2,3,4]: intersection=[2,3]; sym_diff=[1,4]
        result = sorted_list_intersection([1, 2, 3], [2, 3, 4])
        self.assertEqual(result, [1, 4])

    def test_result_sorted(self) -> None:
        result = sorted_list_intersection([1, 3, 5], [2, 4, 6])
        self.assertEqual(result, sorted(result))


class SortedListIntersectionT3EdgeCaseTests(unittest.TestCase):
    """Edge cases for symmetric difference."""

    def test_empty_first_list(self) -> None:
        result = sorted_list_intersection([], [1, 2, 3])
        self.assertEqual(result, [1, 2, 3])

    def test_empty_second_list(self) -> None:
        result = sorted_list_intersection([1, 2], [])
        self.assertEqual(result, [1, 2])

    def test_both_empty(self) -> None:
        result = sorted_list_intersection([], [])
        self.assertEqual(result, [])

    def test_identical_lists_returns_empty(self) -> None:
        # All elements equal counts -> symmetric difference is empty
        result = sorted_list_intersection([1, 2, 3], [1, 2, 3])
        self.assertEqual(result, [])


if __name__ == "__main__":
    unittest.main()
