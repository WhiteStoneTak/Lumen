"""T2 test suite for dense_rank.

Correct behaviour: assigns 1-based dense ranks to a list of values. Tied
values receive the same rank; the next distinct value gets rank+1.

Introduced bug (off_by_one): enumerate uses `start=0` instead of `start=1`,
making all ranks zero-based (0, 1, 2, ...) instead of 1-based (1, 2, 3, ...).
Every returned rank is off by one.
"""

import unittest
from pathlib import Path


def _load_func(source_path: str):
    import importlib.util
    spec = importlib.util.spec_from_file_location("_dr_mod", source_path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.dense_rank


_DEFAULT_SOURCE = str(
    Path(__file__).resolve().parents[2] / "functions" / "raw" / "dense_rank.py"
)
_SOURCE = _DEFAULT_SOURCE
dense_rank = _load_func(_SOURCE)


class DenseRankCorrectBehaviourTests(unittest.TestCase):
    """These tests all pass against the correct source."""

    def test_empty_returns_empty(self):
        self.assertEqual(dense_rank([]), [])

    def test_single_element(self):
        self.assertEqual(dense_rank([42.0]), [1])

    def test_all_equal_all_rank_one(self):
        self.assertEqual(dense_rank([5, 5, 5]), [1, 1, 1])

    def test_three_distinct_ascending(self):
        self.assertEqual(dense_rank([1.0, 2.0, 3.0]), [1, 2, 3])

    def test_docstring_example(self):
        self.assertEqual(dense_rank([3.0, 1.0, 4.0, 1.0, 5.0]), [2, 1, 3, 1, 4])

    def test_ties_share_rank(self):
        self.assertEqual(dense_rank([10, 20, 10, 30]), [1, 2, 1, 3])


class DenseRankBugDetectionTests(unittest.TestCase):
    """These tests specifically expose the off_by_one (start=0) bug.

    The buggy version starts enumeration at 0, so the minimum value gets
    rank 0 instead of 1, and all subsequent ranks are shifted down by one.
    """

    def test_minimum_rank_is_one_not_zero(self):
        result = dense_rank([10])
        self.assertEqual(
            result, [1],
            msg=f"Expected [1] but got {result}; "
                "buggy version returns [0] because enumerate starts at 0",
        )

    def test_all_ranks_one_based(self):
        result = dense_rank([3.0, 1.0, 4.0, 1.0, 5.0])
        self.assertEqual(
            result, [2, 1, 3, 1, 4],
            msg=f"Expected [2,1,3,1,4] but got {result}; "
                "buggy version returns [1,0,2,0,3] — all off by one",
        )

    def test_no_zero_in_output(self):
        result = dense_rank([5, 3, 5, 1])
        self.assertNotIn(
            0, result,
            msg=f"Dense rank must be 1-based; got {result} which contains 0",
        )
        self.assertEqual(result, [3, 2, 3, 1])
