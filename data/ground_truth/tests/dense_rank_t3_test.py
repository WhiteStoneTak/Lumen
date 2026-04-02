"""T3 post-transform test suite for dense_rank.

Transform spec (dense_rank.TR01): Change ranking from dense rank to standard
competition rank (1224 ranking). Tied items get the LOWEST rank in their group,
and the next rank after a tie group skips by the size of the tie.
Example: [100, 90, 90, 80] -> [1, 2, 2, 4] (not dense [1, 2, 2, 3]).

These tests are run against a model's transformed implementation.
Parse failure and execution failure score 0.0 without running tests.
"""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path


def _load_func(source_path: str):
    spec = importlib.util.spec_from_file_location("_dr_t3_mod", source_path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.dense_rank


_DEFAULT_SOURCE = str(
    Path(__file__).resolve().parents[2] / "functions" / "raw" / "dense_rank.py"
)
_SOURCE = _DEFAULT_SOURCE
dense_rank = _load_func(_SOURCE)


class DenseRankT3CompetitionRankTests(unittest.TestCase):
    """Transformed function must implement standard competition (1224) ranking."""

    def test_tie_gets_same_rank_competition(self) -> None:
        # [100, 90, 90, 80]: competition ranks [1, 2, 2, 4]
        # Dense would give [1, 2, 2, 3]; competition skips to 4 after 2-way tie
        result = dense_rank([100, 90, 90, 80])
        self.assertEqual(result, [1, 2, 2, 4])

    def test_no_tie_same_as_dense(self) -> None:
        # No ties: competition and dense are identical
        result = dense_rank([10, 8, 6, 4])
        self.assertEqual(result, [1, 2, 3, 4])

    def test_triple_tie_skips_to_four(self) -> None:
        # [5, 5, 5, 1]: three-way tie at top, all rank 1; next distinct value
        # skips to rank 4 (not 2 as dense would give)
        result = dense_rank([5, 5, 5, 1])
        self.assertEqual(result, [1, 1, 1, 4])

    def test_return_type_is_list(self) -> None:
        result = dense_rank([3.0, 1.0, 4.0])
        self.assertIsInstance(result, list)

    def test_next_rank_after_tie_skips(self) -> None:
        # After a 2-way tie at rank R, the next rank must be R+2, not R+1
        # [10, 10, 5, 1]: ranks [1, 1, 3, 4]
        result = dense_rank([10, 10, 5, 1])
        self.assertEqual(result, [1, 1, 3, 4])

    def test_two_groups_with_ties(self) -> None:
        # [9, 9, 7, 7]: two groups of 2; ranks [1, 1, 3, 3]
        result = dense_rank([9, 9, 7, 7])
        self.assertEqual(result, [1, 1, 3, 3])


class DenseRankT3EdgeCaseTests(unittest.TestCase):
    """Edge cases for competition rank."""

    def test_single_element(self) -> None:
        result = dense_rank([42])
        self.assertEqual(result, [1])

    def test_empty_returns_empty(self) -> None:
        result = dense_rank([])
        self.assertEqual(result, [])

    def test_all_tied(self) -> None:
        # All same value: all rank 1
        result = dense_rank([5, 5, 5])
        self.assertEqual(result, [1, 1, 1])


if __name__ == "__main__":
    unittest.main()
