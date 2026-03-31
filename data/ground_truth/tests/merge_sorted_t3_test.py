"""T3 post-transform test suite for merge_sorted.

Transform spec (merge_sorted.TR01): Add an optional `descending` parameter
(default False). When descending=True, both inputs are sorted descending and
the merged result must also be in descending order. With descending=False,
behaviour is identical to the original function (ascending merge).

These tests are run against a model's transformed implementation.
Parse failure and execution failure score 0.0 without running tests.
"""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path


def _load_func(source_path: str):
    spec = importlib.util.spec_from_file_location("_ms_t3_mod", source_path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.merge_sorted


_DEFAULT_SOURCE = str(
    Path(__file__).resolve().parents[2] / "functions" / "raw" / "merge_sorted.py"
)
_SOURCE = _DEFAULT_SOURCE
merge_sorted = _load_func(_SOURCE)


class MergeSortedT3DescendingTests(unittest.TestCase):
    """When descending=True, both inputs and the result must be in descending order."""

    def test_descending_basic(self) -> None:
        result = merge_sorted([6, 4, 2], [5, 3, 1], descending=True)
        self.assertEqual(result, [6, 5, 4, 3, 2, 1])

    def test_descending_unequal_lengths(self) -> None:
        result = merge_sorted([6, 5, 4, 3], [2, 1], descending=True)
        self.assertEqual(result, [6, 5, 4, 3, 2, 1])

    def test_descending_one_empty(self) -> None:
        result = merge_sorted([], [5, 3, 1], descending=True)
        self.assertEqual(result, [5, 3, 1])

    def test_descending_both_empty(self) -> None:
        result = merge_sorted([], [], descending=True)
        self.assertEqual(result, [])

    def test_descending_duplicates_preserved(self) -> None:
        result = merge_sorted([5, 3, 3], [4, 3, 1], descending=True)
        self.assertEqual(result, [5, 4, 3, 3, 3, 1])

    def test_descending_single_elements(self) -> None:
        result = merge_sorted([10], [7], descending=True)
        self.assertEqual(result, [10, 7])


class MergeSortedT3OriginalBehaviourPreservedTests(unittest.TestCase):
    """Original ascending-merge behaviour must be preserved with descending=False."""

    def test_ascending_merge_basic(self) -> None:
        self.assertEqual(merge_sorted([1, 3, 5], [2, 4, 6]), [1, 2, 3, 4, 5, 6])

    def test_ascending_unequal_lengths(self) -> None:
        self.assertEqual(merge_sorted([1, 2], [3, 4, 5, 6]), [1, 2, 3, 4, 5, 6])

    def test_ascending_one_empty(self) -> None:
        self.assertEqual(merge_sorted([], [1, 2]), [1, 2])

    def test_ascending_both_empty(self) -> None:
        self.assertEqual(merge_sorted([], []), [])

    def test_ascending_duplicates_preserved(self) -> None:
        self.assertEqual(merge_sorted([1, 2, 2], [2, 3]), [1, 2, 2, 2, 3])


if __name__ == "__main__":
    unittest.main()
