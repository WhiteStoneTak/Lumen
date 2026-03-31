"""T3 post-transform test suite for equal_width_buckets.

Transform spec (equal_width_buckets.TR01): Change from equal-width buckets to
equal-frequency (quantile) buckets. Sort the values, divide into n_buckets
roughly equal groups (earlier buckets get one extra when uneven), assign
0-indexed bucket by rank group. Return assignments in input order.

These tests are run against a model's transformed implementation.
Parse failure and execution failure score 0.0 without running tests.
"""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path


def _load_func(source_path: str):
    spec = importlib.util.spec_from_file_location("_ewb_t3_mod", source_path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.equal_width_buckets


_DEFAULT_SOURCE = str(
    Path(__file__).resolve().parents[2] / "functions" / "raw" / "equal_width_buckets.py"
)
_SOURCE = _DEFAULT_SOURCE
equal_width_buckets = _load_func(_SOURCE)


class EqualWidthBucketsT3QuantileTests(unittest.TestCase):
    """Transformed function must use equal-frequency (quantile) bucketing."""

    def test_basic_quantile_even_split(self) -> None:
        # [1,2,3,4,5,6] n=3: 2 per bucket → [0,0,1,1,2,2]
        result = equal_width_buckets([1, 2, 3, 4, 5, 6], 3)
        self.assertEqual(result, [0, 0, 1, 1, 2, 2])

    def test_not_equal_width(self) -> None:
        # Skewed data [1,2,3,100] n=2:
        # Equal-width: width=99/2=49.5, bucket0=[1..50.5)=[1,2,3], bucket1=[50.5..100]=[100]
        # → [0,0,0,1] (original equal-width behaviour)
        # Equal-freq: 2 per bucket, lower half=[1,2]→0, upper half=[3,100]→1 → [0,0,1,1]
        result = equal_width_buckets([1, 2, 3, 100], 2)
        # Must differ from equal-width result [0,0,0,1]
        self.assertNotEqual(result, [0, 0, 0, 1])
        self.assertEqual(result, [0, 0, 1, 1])

    def test_return_type_list_of_ints(self) -> None:
        result = equal_width_buckets([1, 2, 3, 4], 2)
        self.assertIsInstance(result, list)
        for v in result:
            self.assertIsInstance(v, int)

    def test_all_same_value(self) -> None:
        # All same: all go in bucket 0
        result = equal_width_buckets([5, 5, 5, 5], 2)
        self.assertEqual(result, [0, 0, 0, 0])

    def test_bucket_indices_valid_range(self) -> None:
        n_buckets = 4
        result = equal_width_buckets([1, 2, 3, 4, 5, 6, 7, 8], n_buckets)
        for v in result:
            self.assertGreaterEqual(v, 0)
            self.assertLess(v, n_buckets)

    def test_length_matches_input(self) -> None:
        values = [3.0, 1.0, 4.0, 1.0, 5.0, 9.0]
        result = equal_width_buckets(values, 3)
        self.assertEqual(len(result), len(values))

    def test_single_bucket(self) -> None:
        # n_buckets=1: all values go in bucket 0
        result = equal_width_buckets([1, 5, 3, 2, 4], 1)
        self.assertEqual(result, [0, 0, 0, 0, 0])

    def test_input_order_preserved(self) -> None:
        # [6,1,4,2,3,5] n=3: sorted=[1,2,3,4,5,6], 2 per bucket
        # 1→0, 2→0, 3→1, 4→1, 5→2, 6→2
        # Input order: 6→2, 1→0, 4→1, 2→0, 3→1, 5→2
        result = equal_width_buckets([6, 1, 4, 2, 3, 5], 3)
        self.assertEqual(result, [2, 0, 1, 0, 1, 2])


class EqualWidthBucketsT3StructureTests(unittest.TestCase):
    """Structural invariants and preserved behaviours."""

    def test_n1_bucket_all_zero(self) -> None:
        result = equal_width_buckets([10, 20, 30], 1)
        self.assertEqual(result, [0, 0, 0])

    def test_uneven_split_first_buckets_larger(self) -> None:
        # 5 values, 3 buckets: first 2 buckets get 2, last gets 1
        # [1,2,3,4,5] n=3: sizes [2,2,1] → [0,0,1,1,2]
        result = equal_width_buckets([1, 2, 3, 4, 5], 3)
        counts = [result.count(i) for i in range(3)]
        # First two buckets should be >= last
        self.assertGreaterEqual(counts[0], counts[2])


if __name__ == "__main__":
    unittest.main()
