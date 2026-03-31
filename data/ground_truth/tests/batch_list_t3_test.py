"""T3 post-transform test suite for batch_list.

Transform spec (batch_list.TR01): Add an optional `pad` parameter (default
None). When pad is not None, the final batch is padded to exactly batch_size
elements by appending pad. When pad is None, the final batch is left as-is
(original behaviour).

These tests are run against a model's transformed implementation.
Parse failure and execution failure score 0.0 without running tests.
"""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path


def _load_func(source_path: str):
    spec = importlib.util.spec_from_file_location("_bl_t3_mod", source_path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.batch_list


_DEFAULT_SOURCE = str(
    Path(__file__).resolve().parents[2] / "functions" / "raw" / "batch_list.py"
)
_SOURCE = _DEFAULT_SOURCE
batch_list = _load_func(_SOURCE)


class BatchListT3PaddingTests(unittest.TestCase):
    """When pad is not None, the final batch must be padded to batch_size."""

    def test_pad_zero_fills_short_final_batch(self) -> None:
        result = batch_list([1, 2, 3, 4, 5], 2, pad=0)
        self.assertEqual(result, [[1, 2], [3, 4], [5, 0]])

    def test_pad_none_string_fills_final_batch(self) -> None:
        result = batch_list([1, 2, 3], 2, pad="x")
        self.assertEqual(result, [[1, 2], [3, "x"]])

    def test_pad_when_items_exactly_divisible_no_padding_added(self) -> None:
        # 4 items, batch_size=2 → no short batch → no padding needed
        result = batch_list([1, 2, 3, 4], 2, pad=0)
        self.assertEqual(result, [[1, 2], [3, 4]])

    def test_pad_fills_all_remaining_slots(self) -> None:
        # 1 item, batch_size=3 → final batch needs 2 padding elements
        result = batch_list([7], 3, pad=-1)
        self.assertEqual(result, [[7, -1, -1]])

    def test_pad_with_single_full_batch_no_padding(self) -> None:
        result = batch_list([1, 2, 3], 3, pad=0)
        self.assertEqual(result, [[1, 2, 3]])

    def test_pad_preserves_inner_batch_values(self) -> None:
        result = batch_list([10, 20, 30, 40, 50], 3, pad=0)
        self.assertEqual(result, [[10, 20, 30], [40, 50, 0]])


class BatchListT3OriginalBehaviourPreservedTests(unittest.TestCase):
    """Original behaviour must be preserved when pad=None (default)."""

    def test_split_with_remainder(self) -> None:
        self.assertEqual(batch_list([1, 2, 3, 4, 5], 2), [[1, 2], [3, 4], [5]])

    def test_single_batch(self) -> None:
        self.assertEqual(batch_list([1, 2, 3, 4, 5], 5), [[1, 2, 3, 4, 5]])

    def test_empty_items_returns_empty(self) -> None:
        self.assertEqual(batch_list([], 3), [])

    def test_batch_size_less_than_one_returns_empty(self) -> None:
        self.assertEqual(batch_list([1, 2], 0), [])

    def test_batch_size_one_wraps_each(self) -> None:
        self.assertEqual(batch_list([1, 2, 3], 1), [[1], [2], [3]])


if __name__ == "__main__":
    unittest.main()
