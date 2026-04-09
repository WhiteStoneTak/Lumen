"""T2 test suite for equal_width_buckets.

Correct behaviour: assigns each value to one of n_buckets equal-width
0-indexed buckets. The maximum value always goes in the last bucket
(clamped to n_buckets - 1).

Introduced bug (missing_boundary_check): the clamp
`if bucket >= n_buckets: bucket = n_buckets - 1` is missing. When v equals
max_val, int((v - min_val) / width) can return exactly n_buckets, causing
an out-of-bounds bucket index.
"""

import unittest
from pathlib import Path


def _load_func(source_path: str):
    import importlib.util
    spec = importlib.util.spec_from_file_location("_ewb_mod", source_path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.equal_width_buckets


_DEFAULT_SOURCE = str(
    Path(__file__).resolve().parents[2] / "functions" / "raw" / "equal_width_buckets.py"
)
_SOURCE = _DEFAULT_SOURCE
equal_width_buckets = _load_func(_SOURCE)


class EqualWidthBucketsCorrectBehaviourTests(unittest.TestCase):
    """These tests all pass against the correct source."""

    def test_all_equal_go_to_bucket_zero(self):
        self.assertEqual(equal_width_buckets([5, 5, 5], 3), [0, 0, 0])

    def test_two_buckets_simple(self):
        self.assertEqual(equal_width_buckets([1.0, 2.0, 3.0, 4.0, 5.0], 2), [0, 0, 1, 1, 1])

    def test_three_buckets_evenly_spaced(self):
        self.assertEqual(equal_width_buckets([10, 20, 30], 3), [0, 1, 2])

    def test_single_value_non_equal(self):
        result = equal_width_buckets([0.0, 10.0], 2)
        self.assertEqual(result[0], 0)
        self.assertEqual(result[1], 1)


class EqualWidthBucketsBugDetectionTests(unittest.TestCase):
    """These tests specifically expose the missing_boundary_check bug.

    Without the clamp, the maximum value gets bucket index == n_buckets
    (out-of-bounds). The correct implementation clamps it to n_buckets - 1.
    """

    def test_max_value_goes_to_last_bucket(self):
        # With exact boundaries: [0, 10] in 2 buckets, width=5.
        # 10 -> int((10-0)/5) = int(2.0) = 2 >= n_buckets=2 -> clamp to 1.
        result = equal_width_buckets([0.0, 5.0, 10.0], 2)
        self.assertEqual(
            result[-1], 1,
            msg=f"Max value should map to last bucket (1) but got {result[-1]}; "
                "buggy version returns 2 (out-of-bounds)",
        )

    def test_all_bucket_indices_less_than_n_buckets(self):
        values = [1.0, 2.0, 3.0, 4.0, 5.0]
        n = 2
        result = equal_width_buckets(values, n)
        for i, b in enumerate(result):
            self.assertLess(
                b, n,
                msg=f"Bucket index {b} for value {values[i]} >= n_buckets={n}; "
                    "buggy version returns out-of-bounds index for max value",
            )

    def test_three_evenly_spaced_max_in_last(self):
        result = equal_width_buckets([0.0, 10.0, 20.0], 2)
        self.assertEqual(result, [0, 1, 1],
                         msg=f"Expected [0,1,1] but got {result}")
