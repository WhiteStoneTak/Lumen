"""T3 post-transform test suite for sliding_window_max.

Transform spec (sliding_window_max.TR01): Add an optional `stride` parameter
(default 1). Window starting positions advance by stride instead of 1.
Raises ValueError when stride < 1. With stride=1, output is identical to
the original function.

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


class SlidingWindowMaxT3StrideTests(unittest.TestCase):
    """The transformed function must support a stride parameter."""

    def test_stride_2_skips_every_other_window(self) -> None:
        # Windows at i=0: [1,3,2]=3; i=2: [2,4,1]=4
        result = sliding_window_max([1, 3, 2, 4, 1], 3, stride=2)
        self.assertEqual(result, [3, 4])

    def test_stride_equals_k_non_overlapping_windows(self) -> None:
        # Windows at i=0: [1,2]=2; i=2: [3,4]=4; i=4: [5,6]=6
        result = sliding_window_max([1, 2, 3, 4, 5, 6], 2, stride=2)
        self.assertEqual(result, [2, 4, 6])

    def test_stride_greater_than_k(self) -> None:
        # Windows at i=0: [1,2]=2; i=3: [4,5]=5
        result = sliding_window_max([1, 2, 3, 4, 5], 2, stride=3)
        self.assertEqual(result, [2, 5])

    def test_stride_1_same_as_default(self) -> None:
        result = sliding_window_max([1, 3, 2, 4, 1], 3, stride=1)
        self.assertEqual(result, [3, 4, 4])

    def test_stride_invalid_raises_value_error(self) -> None:
        with self.assertRaises(ValueError):
            sliding_window_max([1, 2, 3], 2, stride=0)

    def test_stride_negative_raises_value_error(self) -> None:
        with self.assertRaises(ValueError):
            sliding_window_max([1, 2, 3], 2, stride=-1)

    def test_stride_larger_than_array_returns_first_window(self) -> None:
        # Only window at i=0 is reachable
        result = sliding_window_max([1, 3, 2, 4, 1], 3, stride=10)
        self.assertEqual(result, [3])


class SlidingWindowMaxT3OriginalBehaviourPreservedTests(unittest.TestCase):
    """Original behaviour must be preserved with default stride=1."""

    def test_basic_sliding_window(self) -> None:
        self.assertEqual(sliding_window_max([1, 3, 2, 4, 1], 3), [3, 4, 4])

    def test_all_same_values(self) -> None:
        self.assertEqual(sliding_window_max([5, 5, 5], 2), [5, 5])

    def test_single_element_window(self) -> None:
        self.assertEqual(sliding_window_max([7], 1), [7])

    def test_empty_list_returns_empty(self) -> None:
        self.assertEqual(sliding_window_max([], 2), [])

    def test_k_greater_than_length_returns_empty(self) -> None:
        self.assertEqual(sliding_window_max([1, 2], 3), [])

    def test_k_zero_returns_empty(self) -> None:
        self.assertEqual(sliding_window_max([1, 2, 3], 0), [])


if __name__ == "__main__":
    unittest.main()
