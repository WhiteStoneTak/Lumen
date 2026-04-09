"""T2 test suite for max_subarray_bounds.

Correct behaviour: returns (start, end, total) of the maximum-sum contiguous
subarray using Kadane's algorithm. Ties go to the earliest starting subarray.

Introduced bug (wrong_comparison_operator): the best-update condition uses
`cur_sum >= best_sum` instead of `cur_sum > best_sum`. When a later subarray
ties the current best sum, it overwrites the earlier result, violating the
'earliest start' tie-breaking policy.
"""

import unittest
from pathlib import Path


def _load_func(source_path: str):
    import importlib.util
    spec = importlib.util.spec_from_file_location("_msb_mod", source_path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.max_subarray_bounds


_DEFAULT_SOURCE = str(
    Path(__file__).resolve().parents[2] / "functions" / "raw" / "max_subarray_bounds.py"
)
_SOURCE = _DEFAULT_SOURCE
max_subarray_bounds = _load_func(_SOURCE)


class MaxSubarrayBoundsCorrectBehaviourTests(unittest.TestCase):
    """These tests all pass against the correct source."""

    def test_empty_returns_zeros(self):
        self.assertEqual(max_subarray_bounds([]), (0, 0, 0))

    def test_single_element(self):
        self.assertEqual(max_subarray_bounds([1]), (0, 0, 1))

    def test_all_negative_returns_max_element(self):
        self.assertEqual(max_subarray_bounds([-3, -1, -2]), (1, 1, -1))

    def test_docstring_example(self):
        self.assertEqual(
            max_subarray_bounds([-2, 1, -3, 4, -1, 2, 1, -5, 4]),
            (3, 6, 6),
        )

    def test_all_positive(self):
        self.assertEqual(max_subarray_bounds([1, 2, 3]), (0, 2, 6))


class MaxSubarrayBoundsBugDetectionTests(unittest.TestCase):
    """These tests specifically expose the wrong_comparison_operator bug.

    The buggy version uses >= in the update condition, so any later subarray
    with equal sum overwrites the earlier one, violating earliest-start policy.
    """

    def test_tie_prefers_earliest_start(self):
        # [1, -1, 1]: subarray [1] at 0 has sum=1; subarray [1] at 2 also sum=1.
        # Earliest start (0) should win.
        # buggy: [1] at index 2 gets selected because cur_sum(1) >= best_sum(1)
        result = max_subarray_bounds([1, -1, 1])
        self.assertEqual(
            result[0], 0,
            msg=f"Expected start=0 (earliest tie) but got start={result[0]}; "
                "buggy >= condition overwrites earlier result with later equal-sum subarray",
        )

    def test_tie_returns_correct_start_index(self):
        result = max_subarray_bounds([1, -1, 1])
        self.assertEqual(
            result, (0, 0, 1),
            msg=f"Expected (0, 0, 1) but got {result}; "
                "buggy version returns (2, 2, 1) — later tied subarray wins",
        )

    def test_non_tie_case_still_correct(self):
        # Verify non-tie path is unaffected
        result = max_subarray_bounds([2, -1, 3])
        self.assertEqual(result, (0, 2, 4))
