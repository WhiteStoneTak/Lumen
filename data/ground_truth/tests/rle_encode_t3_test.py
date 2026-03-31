"""T3 post-transform test suite for rle_encode.

Transform spec (rle_encode.TR01): Add an optional `min_run` parameter
(default 1). Only include (value, count) tuples where count >= min_run.
Raises ValueError when min_run < 1. With min_run=1, output is identical to
the original function.

These tests are run against a model's transformed implementation.
Parse failure and execution failure score 0.0 without running tests.
"""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path


def _load_func(source_path: str):
    spec = importlib.util.spec_from_file_location("_rle_t3_mod", source_path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.rle_encode


_DEFAULT_SOURCE = str(
    Path(__file__).resolve().parents[2] / "functions" / "raw" / "rle_encode.py"
)
_SOURCE = _DEFAULT_SOURCE
rle_encode = _load_func(_SOURCE)


class RleEncodeT3MinRunTests(unittest.TestCase):
    """Only runs of length >= min_run must appear in the output."""

    def test_min_run_2_filters_single_occurrences(self) -> None:
        # [1,1,2,3,3] → runs: (1,2),(2,1),(3,2). min_run=2 keeps (1,2),(3,2)
        result = rle_encode([1, 1, 2, 3, 3], min_run=2)
        self.assertEqual(result, [(1, 2), (3, 2)])

    def test_min_run_3_keeps_only_long_runs(self) -> None:
        # [a,a,a,b,b,c] → runs: (a,3),(b,2),(c,1). min_run=3 keeps (a,3)
        result = rle_encode(["a", "a", "a", "b", "b", "c"], min_run=3)
        self.assertEqual(result, [("a", 3)])

    def test_min_run_filters_all_returns_empty(self) -> None:
        # [1,2,3] → runs: (1,1),(2,1),(3,1). min_run=2 → all filtered
        result = rle_encode([1, 2, 3], min_run=2)
        self.assertEqual(result, [])

    def test_min_run_1_keeps_all(self) -> None:
        result = rle_encode([1, 1, 2, 3, 3], min_run=1)
        self.assertEqual(result, [(1, 2), (2, 1), (3, 2)])

    def test_min_run_0_raises_value_error(self) -> None:
        with self.assertRaises(ValueError):
            rle_encode([1, 2, 3], min_run=0)

    def test_min_run_negative_raises_value_error(self) -> None:
        with self.assertRaises(ValueError):
            rle_encode([1, 2, 3], min_run=-1)

    def test_min_run_with_empty_input_returns_empty(self) -> None:
        result = rle_encode([], min_run=2)
        self.assertEqual(result, [])


class RleEncodeT3OriginalBehaviourPreservedTests(unittest.TestCase):
    """Original behaviour must be preserved with default min_run=1."""

    def test_basic_encoding(self) -> None:
        self.assertEqual(rle_encode([1, 1, 2, 3, 3]), [(1, 2), (2, 1), (3, 2)])

    def test_all_same(self) -> None:
        self.assertEqual(rle_encode(["a", "a", "a"]), [("a", 3)])

    def test_empty_input_returns_empty(self) -> None:
        self.assertEqual(rle_encode([]), [])

    def test_no_runs_each_singleton(self) -> None:
        self.assertEqual(rle_encode([1, 2, 3]), [(1, 1), (2, 1), (3, 1)])

    def test_non_adjacent_duplicates_separate_tuples(self) -> None:
        self.assertEqual(rle_encode([1, 2, 1]), [(1, 1), (2, 1), (1, 1)])


if __name__ == "__main__":
    unittest.main()
