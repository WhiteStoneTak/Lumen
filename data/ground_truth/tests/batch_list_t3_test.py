"""T3 post-transform test suite for batch_list.

Transform spec (batch_list.TR01): Each individual batch is returned in
reversed order. The batching logic (splitting into consecutive non-overlapping
groups of at most batch_size) remains unchanged; only each batch is reversed.

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


class BatchListT3ReversedBatchesTests(unittest.TestCase):
    """Each batch in the result must be in reversed order."""

    def test_basic_batches_reversed(self) -> None:
        # [1,2,3,4,5] size 2: batches [1,2],[3,4],[5] → reversed [[2,1],[4,3],[5]]
        result = batch_list([1, 2, 3, 4, 5], 2)
        self.assertEqual(result, [[2, 1], [4, 3], [5]])

    def test_single_batch_reversed(self) -> None:
        result = batch_list([1, 2, 3], 3)
        self.assertEqual(result, [[3, 2, 1]])

    def test_batch_size_one_unchanged(self) -> None:
        # size-1 batches reversed = unchanged
        result = batch_list([1, 2, 3], 1)
        self.assertEqual(result, [[1], [2], [3]])

    def test_last_partial_batch_reversed(self) -> None:
        # [1,2,3,4,5] size 3: batches [1,2,3],[4,5] → [[3,2,1],[5,4]]
        result = batch_list([1, 2, 3, 4, 5], 3)
        self.assertEqual(result, [[3, 2, 1], [5, 4]])

    def test_full_last_batch_reversed(self) -> None:
        # [1,2,3,4] size 2: batches [1,2],[3,4] → [[2,1],[4,3]]
        result = batch_list([1, 2, 3, 4], 2)
        self.assertEqual(result, [[2, 1], [4, 3]])

    def test_empty_returns_empty(self) -> None:
        result = batch_list([], 2)
        self.assertEqual(result, [])

    def test_batch_size_less_than_one_returns_empty(self) -> None:
        result = batch_list([1, 2, 3], 0)
        self.assertEqual(result, [])

    def test_reversed_differs_from_original(self) -> None:
        # [1,2] size 2: reversed → [[2,1]], not [[1,2]]
        result = batch_list([1, 2], 2)
        self.assertEqual(result, [[2, 1]])
        self.assertNotEqual(result, [[1, 2]])


class BatchListT3EdgeCaseTests(unittest.TestCase):
    """Edge cases: empty input and batch_size < 1 still return empty."""

    def test_empty_items_any_batch_size(self) -> None:
        self.assertEqual(batch_list([], 5), [])

    def test_batch_size_negative_returns_empty(self) -> None:
        self.assertEqual(batch_list([1, 2, 3], -1), [])

    def test_single_element_batch(self) -> None:
        result = batch_list([42], 3)
        self.assertEqual(result, [[42]])

    def test_two_full_batches(self) -> None:
        result = batch_list([10, 20, 30, 40], 2)
        self.assertEqual(result, [[20, 10], [40, 30]])


if __name__ == "__main__":
    unittest.main()
