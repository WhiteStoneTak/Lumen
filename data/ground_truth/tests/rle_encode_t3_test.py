"""T3 post-transform test suite for rle_encode.

Transform spec (rle_encode.TR01): Change the output format from a list of
(value, count) tuples to a flat interleaved list [value1, count1, value2,
count2, ...]. Run-detection logic remains unchanged.

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


class RleEncodeT3FlatOutputTests(unittest.TestCase):
    """The function must return a flat interleaved [value, count, ...] list."""

    def test_basic_flat_output(self) -> None:
        # [1,1,2,3,3] → runs: (1,2),(2,1),(3,2) → flat: [1,2,2,1,3,2]
        result = rle_encode([1, 1, 2, 3, 3])
        self.assertEqual(result, [1, 2, 2, 1, 3, 2])

    def test_all_same_flat(self) -> None:
        # ['a','a','a'] → run: ('a',3) → flat: ['a',3]
        result = rle_encode(["a", "a", "a"])
        self.assertEqual(result, ["a", 3])

    def test_empty_returns_empty(self) -> None:
        result = rle_encode([])
        self.assertEqual(result, [])

    def test_single_element(self) -> None:
        # [5] → run: (5,1) → flat: [5,1]
        result = rle_encode([5])
        self.assertEqual(result, [5, 1])

    def test_no_runs_interleaved(self) -> None:
        # [1,2,3] → runs: (1,1),(2,1),(3,1) → flat: [1,1,2,1,3,1]
        result = rle_encode([1, 2, 3])
        self.assertEqual(result, [1, 1, 2, 1, 3, 1])

    def test_output_is_flat_list_not_tuples(self) -> None:
        result = rle_encode([1, 1, 2])
        self.assertIsInstance(result, list)
        for item in result:
            self.assertNotIsInstance(item, tuple)

    def test_length_is_double_run_count(self) -> None:
        # [1,1,2,3,3] → 3 runs → output length 6
        result = rle_encode([1, 1, 2, 3, 3])
        self.assertEqual(len(result), 6)

    def test_original_tuple_format_not_returned(self) -> None:
        result = rle_encode([1, 1, 2])
        self.assertNotEqual(result, [(1, 2), (2, 1)])


class RleEncodeT3RunLogicPreservedTests(unittest.TestCase):
    """Run-detection logic must be preserved; only output format changes."""

    def test_non_adjacent_duplicates_separate_runs(self) -> None:
        # [1,2,1] → runs: (1,1),(2,1),(1,1) → flat: [1,1,2,1,1,1]
        result = rle_encode([1, 2, 1])
        self.assertEqual(result, [1, 1, 2, 1, 1, 1])

    def test_two_distinct_runs(self) -> None:
        # [3,3,3,2,2] → runs: (3,3),(2,2) → flat: [3,3,2,2]
        result = rle_encode([3, 3, 3, 2, 2])
        self.assertEqual(result, [3, 3, 2, 2])

    def test_alternating_values(self) -> None:
        # [1,2,1,2] → runs: (1,1),(2,1),(1,1),(2,1) → flat: [1,1,2,1,1,1,2,1]
        result = rle_encode([1, 2, 1, 2])
        self.assertEqual(result, [1, 1, 2, 1, 1, 1, 2, 1])

    def test_empty_input_returns_empty(self) -> None:
        self.assertEqual(rle_encode([]), [])


if __name__ == "__main__":
    unittest.main()
