"""T3 post-transform test suite for merge_sorted.

Transform spec (merge_sorted.TR01): Change the merge semantics to deduplicate.
Return a sorted list containing only values that appear in exactly one of the
two input lists; values present in both lists are excluded.

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


class MergeSortedT3ExclusiveMergeTests(unittest.TestCase):
    """Values appearing in both lists must be excluded from the result."""

    def test_basic_common_excluded(self) -> None:
        # 3 appears in both → excluded; result [1,2,4,5]
        result = merge_sorted([1, 3, 5], [2, 3, 4])
        self.assertEqual(result, [1, 2, 4, 5])

    def test_no_common_full_merge(self) -> None:
        # No common values → result is the full sorted merge
        result = merge_sorted([1, 3, 5], [2, 4, 6])
        self.assertEqual(result, [1, 2, 3, 4, 5, 6])

    def test_all_common_returns_empty(self) -> None:
        result = merge_sorted([1, 2, 3], [1, 2, 3])
        self.assertEqual(result, [])

    def test_one_empty_returns_other(self) -> None:
        result = merge_sorted([], [1, 2])
        self.assertEqual(result, [1, 2])

    def test_both_empty_returns_empty(self) -> None:
        result = merge_sorted([], [])
        self.assertEqual(result, [])

    def test_common_value_with_duplicate_in_one_list(self) -> None:
        # a=[1,2,2], b=[2,3]: 2 in both → excluded; unique-to-a=1, unique-to-b=3 → [1,3]
        result = merge_sorted([1, 2, 2], [2, 3])
        self.assertEqual(result, [1, 3])

    def test_result_is_sorted(self) -> None:
        result = merge_sorted([1, 3, 5], [2, 3, 4])
        self.assertEqual(result, sorted(result))

    def test_common_multiple_values_excluded(self) -> None:
        # [1,2,3],[2,3,4,5]: 2,3 common → excluded; [1,4,5]
        result = merge_sorted([1, 2, 3], [2, 3, 4, 5])
        self.assertEqual(result, [1, 4, 5])


class MergeSortedT3OriginalFailsTests(unittest.TestCase):
    """Tests that confirm original function returns different results."""

    def test_original_would_include_common(self) -> None:
        # Original returns [1,2,3,3,4,5]; new must return [1,2,4,5]
        result = merge_sorted([1, 3, 5], [2, 3, 4])
        self.assertNotIn(3, result)
        self.assertEqual(result, [1, 2, 4, 5])

    def test_symmetric_difference_semantics(self) -> None:
        # Only values unique to one list
        result = merge_sorted([1, 4], [2, 4])
        # 4 in both → excluded; 1 only in a, 2 only in b → [1,2]
        self.assertEqual(result, [1, 2])

    def test_large_overlap(self) -> None:
        result = merge_sorted([1, 2, 3, 4], [3, 4, 5, 6])
        # 3,4 in both → excluded; remaining [1,2,5,6]
        self.assertEqual(result, [1, 2, 5, 6])

    def test_single_element_in_each_no_overlap(self) -> None:
        result = merge_sorted([1], [2])
        self.assertEqual(result, [1, 2])


if __name__ == "__main__":
    unittest.main()
