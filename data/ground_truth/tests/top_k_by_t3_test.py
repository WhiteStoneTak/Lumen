"""T3 post-transform test suite for top_k_by.

Transform spec (top_k_by.TR01): Change from top-k (highest primary key) to
bottom-k (lowest primary key). Tiebreak_key semantics preserved (lower = better).
Return at most k items. If k <= 0, return [].

These tests are run against a model's transformed implementation.
Parse failure and execution failure score 0.0 without running tests.
"""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path


def _load_func(source_path: str):
    spec = importlib.util.spec_from_file_location("_tkb_t3_mod", source_path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.top_k_by


_DEFAULT_SOURCE = str(
    Path(__file__).resolve().parents[2] / "functions" / "raw" / "top_k_by.py"
)
_SOURCE = _DEFAULT_SOURCE
top_k_by = _load_func(_SOURCE)


class TopKByT3BottomKTests(unittest.TestCase):
    """Transformed function must return bottom-k (lowest primary key) items."""

    def test_basic_bottom_k(self) -> None:
        # [3,1,4,1,5] k=3 key=identity: bottom 3 = [1,1,3] sorted lowest first
        result = top_k_by([3, 1, 4, 1, 5], 3, key=lambda x: x)
        self.assertEqual(result, [1, 1, 3])

    def test_bottom_not_top(self) -> None:
        # Original top-k would return [5,4,3]; transform must NOT return that
        result = top_k_by([3, 1, 4, 1, 5], 3, key=lambda x: x)
        self.assertNotEqual(result, [5, 4, 3])

    def test_k_zero_returns_empty(self) -> None:
        result = top_k_by([1, 2, 3], 0, key=lambda x: x)
        self.assertEqual(result, [])

    def test_fewer_than_k_items(self) -> None:
        result = top_k_by([1, 2], 5, key=lambda x: x)
        self.assertEqual(sorted(result), [1, 2])

    def test_return_at_most_k_items(self) -> None:
        result = top_k_by([5, 4, 3, 2, 1], 3, key=lambda x: x)
        self.assertLessEqual(len(result), 3)

    def test_bottom_one_is_minimum(self) -> None:
        result = top_k_by([5, 3, 8, 1, 6], 1, key=lambda x: x)
        self.assertEqual(result, [1])

    def test_tiebreak_key_lower_is_better(self) -> None:
        # Items with same primary key; tiebreak by string value ascending
        # bottom-k with k=2 from ["b","a","c","a"]: all len=1, lowest primary key
        # with tiebreak, lower string = better → "a" < "b" < "c"
        result = top_k_by(["b", "a", "c", "a"], 2, key=lambda s: len(s), tiebreak_key=lambda s: s)
        # All have same primary key (len=1); tiebreak picks 2 smallest by string: "a","a"
        self.assertEqual(sorted(result), ["a", "a"])


class TopKByT3EdgeCaseTests(unittest.TestCase):
    """Edge cases and preserved semantics."""

    def test_negative_k_returns_empty(self) -> None:
        result = top_k_by([1, 2, 3], -1, key=lambda x: x)
        self.assertEqual(result, [])

    def test_single_item_k1(self) -> None:
        result = top_k_by([42], 1, key=lambda x: x)
        self.assertEqual(result, [42])

    def test_return_type_is_list(self) -> None:
        result = top_k_by([1, 2, 3], 2, key=lambda x: x)
        self.assertIsInstance(result, list)

    def test_all_same_primary_key_original_order(self) -> None:
        # All same primary key, no tiebreak: preserve original order
        result = top_k_by([3, 3, 3], 2, key=lambda x: x)
        self.assertEqual(len(result), 2)
        self.assertTrue(all(v == 3 for v in result))


if __name__ == "__main__":
    unittest.main()
