"""T3 post-transform test suite for max_subarray_bounds.

Transform spec (max_subarray_bounds.TR01): Change the return type from a
single best-subarray tuple to a list of ALL subarrays whose sum equals the
global maximum. Return them as a list of (start, end, total) tuples sorted by
start index. Empty input returns [].

These tests are run against a model's transformed implementation.
Parse failure and execution failure score 0.0 without running tests.
"""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path


def _load_func(source_path: str):
    spec = importlib.util.spec_from_file_location("_msb_t3_mod", source_path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.max_subarray_bounds


_DEFAULT_SOURCE = str(
    Path(__file__).resolve().parents[2] / "functions" / "raw" / "max_subarray_bounds.py"
)
_SOURCE = _DEFAULT_SOURCE
max_subarray_bounds = _load_func(_SOURCE)


class MaxSubarrayBoundsT3AllMaximalTests(unittest.TestCase):
    """Transformed function must return ALL subarrays achieving global max sum."""

    def test_return_type_is_list(self) -> None:
        result = max_subarray_bounds([-2, 1, -3, 4, -1, 2, 1, -5, 4])
        self.assertIsInstance(result, list)

    def test_single_max_returns_list_with_one_tuple(self) -> None:
        # Classic Kadane example: only [4,-1,2,1] achieves sum 6
        result = max_subarray_bounds([-2, 1, -3, 4, -1, 2, 1, -5, 4])
        self.assertEqual(result, [(3, 6, 6)])

    def test_multiple_tied_max_subarrays(self) -> None:
        # [1, -1, 1]: max sum = 1
        # Subarrays achieving 1: [1] at idx 0, [1,-1,1] sums to 1, [1] at idx 2
        # Actually: [1] at 0 (sum=1), [1,-1,1] at 0-2 (sum=1), [-1,1] at 1-2 (sum=0), [1] at 2 (sum=1)
        # Maximal contiguous subarrays with sum 1: (0,0,1), (0,2,1), (2,2,1)
        result = max_subarray_bounds([1, -1, 1])
        self.assertIsInstance(result, list)
        self.assertGreater(len(result), 0)
        # All returned tuples must have the same total
        totals = set(t[2] for t in result)
        self.assertEqual(len(totals), 1)

    def test_two_equal_disjoint_max_subarrays(self) -> None:
        # [3, -10, 3]: max sum = 3, achieved by [3] at idx 0 and [3] at idx 2
        result = max_subarray_bounds([3, -10, 3])
        self.assertIsInstance(result, list)
        self.assertGreaterEqual(len(result), 2)
        # Must contain both starts 0 and 2
        starts = [t[0] for t in result]
        self.assertIn(0, starts)
        self.assertIn(2, starts)
        # All totals equal 3
        for t in result:
            self.assertEqual(t[2], 3)

    def test_sorted_by_start_index(self) -> None:
        # Verify result is sorted ascending by start index
        result = max_subarray_bounds([3, -10, 3])
        starts = [t[0] for t in result]
        self.assertEqual(starts, sorted(starts))

    def test_empty_returns_empty_list(self) -> None:
        result = max_subarray_bounds([])
        self.assertEqual(result, [])

    def test_all_negative_single_max_element(self) -> None:
        # [-3, -1, -2]: max is -1 at index 1; only (1,1,-1)
        result = max_subarray_bounds([-3, -1, -2])
        self.assertEqual(result, [(1, 1, -1)])

    def test_tuple_structure(self) -> None:
        # Each element must be a 3-tuple (start, end, total)
        result = max_subarray_bounds([1, 2, 3])
        self.assertEqual(len(result), 1)
        t = result[0]
        self.assertEqual(len(t), 3)
        start, end, total = t
        self.assertEqual(total, 6)
        self.assertEqual(start, 0)
        self.assertEqual(end, 2)


class MaxSubarrayBoundsT3EdgeCaseTests(unittest.TestCase):
    """Edge cases and structural invariants for the transformed function."""

    def test_single_element(self) -> None:
        result = max_subarray_bounds([7])
        self.assertEqual(result, [(0, 0, 7)])

    def test_all_same_positive(self) -> None:
        # [2, 2, 2]: max sum is 6, only [0,2,6]
        result = max_subarray_bounds([2, 2, 2])
        self.assertIsInstance(result, list)
        self.assertGreater(len(result), 0)
        # Maximum-sum subarray total must be 6
        max_total = max(t[2] for t in result)
        self.assertEqual(max_total, 6)

    def test_all_totals_equal_global_max(self) -> None:
        result = max_subarray_bounds([3, -10, 3])
        global_max = max(t[2] for t in result)
        for t in result:
            self.assertEqual(t[2], global_max)

    def test_not_a_single_tuple(self) -> None:
        # Original function returns a tuple, not a list; transformed must return list
        result = max_subarray_bounds([1, 2, 3])
        self.assertNotIsInstance(result, tuple)


if __name__ == "__main__":
    unittest.main()
