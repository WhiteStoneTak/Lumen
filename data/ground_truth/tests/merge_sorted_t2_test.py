"""T2 test suite for merge_sorted.

Correct behaviour: merges two ascending-sorted lists into one ascending-sorted
list containing all elements from both inputs.

Introduced bug (missing_boundary_check): the drain loop for b uses
`j < len(b) - 1` instead of `j < len(b)`.  When b has remaining elements
after the main merge loop, the last element of b's remainder is never appended.
"""

import unittest
from pathlib import Path


def _load_func(source_path: str):
    import importlib.util
    spec = importlib.util.spec_from_file_location("_ms_mod", source_path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.merge_sorted


_DEFAULT_SOURCE = str(
    Path(__file__).resolve().parents[2] / "functions" / "raw" / "merge_sorted.py"
)
_SOURCE = _DEFAULT_SOURCE
merge_sorted = _load_func(_SOURCE)


class MergeSortedCorrectBehaviourTests(unittest.TestCase):
    """These tests all pass against the correct source."""

    def test_both_empty(self):
        self.assertEqual(merge_sorted([], []), [])

    def test_a_empty(self):
        self.assertEqual(merge_sorted([], [1, 2, 3]), [1, 2, 3])

    def test_b_empty(self):
        self.assertEqual(merge_sorted([1, 2, 3], []), [1, 2, 3])

    def test_equal_length_interleaved(self):
        self.assertEqual(merge_sorted([1, 3, 5], [2, 4, 6]), [1, 2, 3, 4, 5, 6])

    def test_a_entirely_before_b(self):
        self.assertEqual(merge_sorted([1, 2], [3, 4]), [1, 2, 3, 4])

    def test_b_entirely_before_a(self):
        self.assertEqual(merge_sorted([5, 6], [1, 2]), [1, 2, 5, 6])

    def test_duplicates_preserved(self):
        self.assertEqual(merge_sorted([1, 2, 2], [2, 3]), [1, 2, 2, 2, 3])


class MergeSortedBugDetectionTests(unittest.TestCase):
    """These tests specifically expose the missing_boundary_check bug.

    The bug drops the last element when b has remaining elements after the merge loop.
    """

    def test_b_longer_last_element_present(self):
        # a=[1,3], b=[2,4,6] → a exhausted first; b remainder=[4,6]
        # buggy: j < len(b)-1=2 → appends b[1]=4 but not b[2]=6
        result = merge_sorted([1, 3], [2, 4, 6])
        self.assertEqual(
            result, [1, 2, 3, 4, 6],
            msg=f"Expected [1,2,3,4,6] but got {result}; "
                "buggy version drops the last element of b's remainder (6)",
        )

    def test_result_length_equals_sum_of_inputs(self):
        a, b = [1, 3], [2, 4, 6]
        result = merge_sorted(a, b)
        self.assertEqual(
            len(result), len(a) + len(b),
            msg=f"Expected length {len(a)+len(b)} but got {len(result)}: {result}; "
                "buggy version loses b's last remaining element",
        )
