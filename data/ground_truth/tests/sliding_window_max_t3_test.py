"""T3 post-transform test suite for sliding_window_max.

Transform spec (sliding_window_max.TR01): Change the function to return the
absolute index (within nums) of the maximum element in each sliding window,
instead of the maximum value itself. Ties broken by leftmost index.

These tests are run against a model's transformed implementation.
Parse failure and execution failure score 0.0 without running tests.
"""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path


def _load_func(source_path: str):
    spec = importlib.util.spec_from_file_location("_swm_t3_mod", source_path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.sliding_window_max


_DEFAULT_SOURCE = str(
    Path(__file__).resolve().parents[2] / "functions" / "raw" / "sliding_window_max.py"
)
_SOURCE = _DEFAULT_SOURCE
sliding_window_max = _load_func(_SOURCE)


class SlidingWindowMaxT3IndexReturnTests(unittest.TestCase):
    """The function must return absolute indices of window maxima, not values."""

    def test_basic_returns_indices(self) -> None:
        # [1,3,2,4,1], k=3
        # i=0: window [1,3,2], max=3 at local pos 1 → abs idx 0+1=1
        # i=1: window [3,2,4], max=4 at local pos 2 → abs idx 1+2=3
        # i=2: window [2,4,1], max=4 at local pos 1 → abs idx 2+1=3
        result = sliding_window_max([1, 3, 2, 4, 1], 3)
        self.assertEqual(result, [1, 3, 3])

    def test_single_window(self) -> None:
        # [5,3,7], k=3: only window [5,3,7], max=7 at local pos 2 → abs idx 2
        result = sliding_window_max([5, 3, 7], 3)
        self.assertEqual(result, [2])

    def test_size_one_windows_return_self_indices(self) -> None:
        # k=1: each window is one element, max is at local pos 0 → abs idx = i
        result = sliding_window_max([3, 1, 4, 1, 5], 1)
        self.assertEqual(result, [0, 1, 2, 3, 4])

    def test_empty_returns_empty(self) -> None:
        result = sliding_window_max([], 2)
        self.assertEqual(result, [])

    def test_k_greater_than_length_returns_empty(self) -> None:
        result = sliding_window_max([1, 2], 3)
        self.assertEqual(result, [])

    def test_ties_leftmost_wins(self) -> None:
        # [1,3,3,1], k=2
        # i=0: [1,3], max=3 at local pos 1 → abs 1
        # i=1: [3,3], max=3 at local pos 0 (leftmost) → abs 1
        # i=2: [3,1], max=3 at local pos 0 → abs 2
        result = sliding_window_max([1, 3, 3, 1], 2)
        self.assertEqual(result, [1, 1, 2])

    def test_result_values_are_indices_not_values(self) -> None:
        # [10,20,30], k=2: result should be [1,2] (indices), not [20,30] (values)
        result = sliding_window_max([10, 20, 30], 2)
        self.assertEqual(result, [1, 2])
        self.assertNotIn(20, result)
        self.assertNotIn(30, result)

    def test_k_zero_returns_empty(self) -> None:
        result = sliding_window_max([1, 2, 3], 0)
        self.assertEqual(result, [])


class SlidingWindowMaxT3EdgeCaseTests(unittest.TestCase):
    """Edge cases for empty, k boundary conditions."""

    def test_k_equals_length(self) -> None:
        # [2,5,1,4], k=4: one window, max=5 at local pos 1 → abs idx 1
        result = sliding_window_max([2, 5, 1, 4], 4)
        self.assertEqual(result, [1])

    def test_monotone_increasing(self) -> None:
        # [1,2,3,4,5], k=3
        # i=0: [1,2,3], max=3 at local pos 2 → abs 2
        # i=1: [2,3,4], max=4 at local pos 2 → abs 3
        # i=2: [3,4,5], max=5 at local pos 2 → abs 4
        result = sliding_window_max([1, 2, 3, 4, 5], 3)
        self.assertEqual(result, [2, 3, 4])

    def test_monotone_decreasing(self) -> None:
        # [5,4,3,2,1], k=3
        # i=0: [5,4,3], max=5 at local pos 0 → abs 0
        # i=1: [4,3,2], max=4 at local pos 0 → abs 1
        # i=2: [3,2,1], max=3 at local pos 0 → abs 2
        result = sliding_window_max([5, 4, 3, 2, 1], 3)
        self.assertEqual(result, [0, 1, 2])

    def test_all_same_values_leftmost(self) -> None:
        # [5,5,5], k=2: all ties → leftmost in each window
        # i=0: [5,5] → local pos 0 → abs 0
        # i=1: [5,5] → local pos 0 → abs 1
        result = sliding_window_max([5, 5, 5], 2)
        self.assertEqual(result, [0, 1])


if __name__ == "__main__":
    unittest.main()
