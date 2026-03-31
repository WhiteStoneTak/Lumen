"""T3 post-transform test suite for count_true_segments.

Transform spec (count_true_segments.TR01): Change the return type from `int`
to `list`. Instead of counting True segments, return a list of the lengths of
each True segment in order of appearance.

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


class CountTrueSegmentsT3LengthListTests(unittest.TestCase):
    """The function must return a list of segment lengths, not an integer count."""

    def test_basic_returns_length_list(self) -> None:
        # [T,T,F,T]: segments of length 2 and 1 → [2,1]
        result = count_true_segments([True, True, False, True])
        self.assertEqual(result, [2, 1])

    def test_all_false_returns_empty_list(self) -> None:
        result = count_true_segments([False, False])
        self.assertEqual(result, [])

    def test_all_true_single_segment(self) -> None:
        result = count_true_segments([True, True, True])
        self.assertEqual(result, [3])

    def test_empty_returns_empty_list(self) -> None:
        result = count_true_segments([])
        self.assertEqual(result, [])

    def test_alternating_unit_segments(self) -> None:
        result = count_true_segments([True, False, True, False, True])
        self.assertEqual(result, [1, 1, 1])

    def test_multiple_segments_various_lengths(self) -> None:
        # [F,T,T,T,F,T,F,T,T]: segments 3, 1, 2 → [3,1,2]
        result = count_true_segments([False, True, True, True, False, True, False, True, True])
        self.assertEqual(result, [3, 1, 2])

    def test_trailing_segment_included(self) -> None:
        # [F,T,T]: trailing segment of length 2 → [2]
        result = count_true_segments([False, True, True])
        self.assertEqual(result, [2])

    def test_return_type_is_list(self) -> None:
        result = count_true_segments([True, False, True])
        self.assertIsInstance(result, list)

    def test_not_returning_integer(self) -> None:
        # Original returns int 2 for this input; transformed must return [2,1]
        result = count_true_segments([True, True, False, True])
        self.assertNotIsInstance(result, int)
        self.assertEqual(result, [2, 1])


class CountTrueSegmentsT3LengthAccuracyTests(unittest.TestCase):
    """Lengths in the output list must be correct."""

    def test_single_leading_segment(self) -> None:
        result = count_true_segments([True, False, False])
        self.assertEqual(result, [1])

    def test_two_equal_segments(self) -> None:
        result = count_true_segments([True, True, False, True, True])
        self.assertEqual(result, [2, 2])

    def test_long_segment_followed_by_short(self) -> None:
        result = count_true_segments([True, True, True, True, False, True])
        self.assertEqual(result, [4, 1])

    def test_list_length_equals_segment_count(self) -> None:
        result = count_true_segments([True, False, True, False, True, False, True])
        self.assertEqual(len(result), 4)


if __name__ == "__main__":
    unittest.main()
