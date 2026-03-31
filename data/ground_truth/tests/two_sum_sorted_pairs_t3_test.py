"""T3 post-transform test suite for two_sum_sorted_pairs.

Transform spec (two_sum_sorted_pairs.TR01): Change the return type from value
pairs (a, b) to index pairs (i, j) where i < j and nums[i] + nums[j] == target.
Return index pairs in ascending order of i.

These tests are run against a model's transformed implementation.
Parse failure and execution failure score 0.0 without running tests.
"""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path


def _load_func(source_path: str):
    spec = importlib.util.spec_from_file_location("_tss_t3_mod", source_path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.two_sum_sorted_pairs


_DEFAULT_SOURCE = str(
    Path(__file__).resolve().parents[2] / "functions" / "raw" / "two_sum_sorted_pairs.py"
)
_SOURCE = _DEFAULT_SOURCE
two_sum_sorted_pairs = _load_func(_SOURCE)


class TwoSumSortedPairsT3IndexPairTests(unittest.TestCase):
    """Transformed function must return index pairs, not value pairs."""

    def test_returns_index_tuples_basic(self) -> None:
        # [1,2,3,4,6] target=6: 2+4=6 at indices 1 and 3
        result = two_sum_sorted_pairs([1, 2, 3, 4, 6], 6)
        self.assertEqual(result, [(1, 3)])

    def test_index_pair_not_value_pair(self) -> None:
        # Original returns [(2, 4)] (values); transform must return [(1, 3)] (indices)
        nums = [1, 2, 3, 4, 6]
        result = two_sum_sorted_pairs(nums, 6)
        self.assertNotEqual(result, [(2, 4)])
        self.assertEqual(result, [(1, 3)])

    def test_i_less_than_j_in_all_pairs(self) -> None:
        result = two_sum_sorted_pairs([1, 2, 3, 4, 6], 6)
        for i, j in result:
            self.assertLess(i, j)

    def test_values_at_indices_sum_to_target(self) -> None:
        nums = [1, 2, 3, 4, 6]
        target = 6
        result = two_sum_sorted_pairs(nums, target)
        for i, j in result:
            self.assertEqual(nums[i] + nums[j], target)

    def test_empty_no_pairs(self) -> None:
        result = two_sum_sorted_pairs([1, 2, 3], 10)
        self.assertEqual(result, [])

    def test_sorted_by_first_index(self) -> None:
        nums = [1, 2, 3, 4, 6]
        result = two_sum_sorted_pairs(nums, 6)
        first_indices = [p[0] for p in result]
        self.assertEqual(first_indices, sorted(first_indices))

    def test_multiple_pairs_all_index_based(self) -> None:
        # [1,2,4,5] target=6: 1+5=6 at (0,3), 2+4=6 at (1,2)
        nums = [1, 2, 4, 5]
        result = two_sum_sorted_pairs(nums, 6)
        self.assertIn((0, 3), result)
        self.assertIn((1, 2), result)
        for i, j in result:
            self.assertEqual(nums[i] + nums[j], 6)


class TwoSumSortedPairsT3EdgeCaseTests(unittest.TestCase):
    """Edge cases for index-pair return semantics."""

    def test_return_type_is_list(self) -> None:
        result = two_sum_sorted_pairs([1, 2, 3, 4, 6], 6)
        self.assertIsInstance(result, list)

    def test_elements_are_tuples_of_ints(self) -> None:
        nums = [1, 2, 3, 4, 6]
        result = two_sum_sorted_pairs(nums, 6)
        for pair in result:
            self.assertIsInstance(pair, tuple)
            self.assertEqual(len(pair), 2)
            self.assertIsInstance(pair[0], int)
            self.assertIsInstance(pair[1], int)

    def test_indices_are_valid(self) -> None:
        nums = [1, 2, 3, 4, 6]
        result = two_sum_sorted_pairs(nums, 6)
        for i, j in result:
            self.assertGreaterEqual(i, 0)
            self.assertLess(j, len(nums))


if __name__ == "__main__":
    unittest.main()
