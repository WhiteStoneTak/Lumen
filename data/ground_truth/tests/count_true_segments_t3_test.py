"""T3 post-transform test suite for count_true_segments.

Transform spec (count_true_segments.TR01): Add an optional `min_length`
parameter (default 1). Only count a True segment when its length is at least
min_length. Raises ValueError when min_length < 1. With min_length=1, output
is identical to the original function.

These tests are run against a model's transformed implementation.
Parse failure and execution failure score 0.0 without running tests.
"""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path


def _load_func(source_path: str):
    spec = importlib.util.spec_from_file_location("_cts_t3_mod", source_path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.count_true_segments


_DEFAULT_SOURCE = str(
    Path(__file__).resolve().parents[2] / "functions" / "raw" / "count_true_segments.py"
)
_SOURCE = _DEFAULT_SOURCE
count_true_segments = _load_func(_SOURCE)


class CountTrueSegmentsT3MinLengthTests(unittest.TestCase):
    """Only segments with length >= min_length must be counted."""

    def test_min_length_2_filters_single_true(self) -> None:
        # [T,F,T,T] → segments: length-1 at idx 0, length-2 at idx 2. min=2 → count=1
        result = count_true_segments([True, False, True, True], min_length=2)
        self.assertEqual(result, 1)

    def test_min_length_2_counts_longer_segments(self) -> None:
        # [T,T,F,T,T,T] → segments: length-2 and length-3. Both >= 2 → count=2
        result = count_true_segments(
            [True, True, False, True, True, True], min_length=2
        )
        self.assertEqual(result, 2)

    def test_min_length_3_filters_shorter_segments(self) -> None:
        # [T,T,F,T,T,T] → segments: length-2 filtered, length-3 counts → count=1
        result = count_true_segments(
            [True, True, False, True, True, True], min_length=3
        )
        self.assertEqual(result, 1)

    def test_min_length_filters_all_returns_zero(self) -> None:
        # [T,F,T] → both segments length 1; min=2 → count=0
        result = count_true_segments([True, False, True], min_length=2)
        self.assertEqual(result, 0)

    def test_min_length_1_behaves_like_original(self) -> None:
        result = count_true_segments([True, True, False, True], min_length=1)
        self.assertEqual(result, 2)

    def test_min_length_0_raises_value_error(self) -> None:
        with self.assertRaises(ValueError):
            count_true_segments([True, False], min_length=0)

    def test_min_length_negative_raises_value_error(self) -> None:
        with self.assertRaises(ValueError):
            count_true_segments([True, False], min_length=-1)

    def test_min_length_with_empty_input_returns_zero(self) -> None:
        result = count_true_segments([], min_length=2)
        self.assertEqual(result, 0)

    def test_min_length_with_trailing_segment(self) -> None:
        # Trailing True segment must also be subject to min_length filter
        result = count_true_segments([False, True, True, True], min_length=2)
        self.assertEqual(result, 1)


class CountTrueSegmentsT3OriginalBehaviourPreservedTests(unittest.TestCase):
    """Original behaviour must be preserved with default min_length=1."""

    def test_two_segments(self) -> None:
        self.assertEqual(count_true_segments([True, True, False, True]), 2)

    def test_all_false_returns_zero(self) -> None:
        self.assertEqual(count_true_segments([False, False]), 0)

    def test_all_true_one_segment(self) -> None:
        self.assertEqual(count_true_segments([True, True, True]), 1)

    def test_empty_returns_zero(self) -> None:
        self.assertEqual(count_true_segments([]), 0)

    def test_alternating_counts_each_true(self) -> None:
        self.assertEqual(
            count_true_segments([True, False, True, False, True]), 3
        )


if __name__ == "__main__":
    unittest.main()
