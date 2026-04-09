"""T2 test suite for two_sum_sorted_pairs.

Correct behaviour: given a sorted list of integers, returns all unique (a,b)
pairs where a+b == target, a <= b, no duplicates, in ascending order of a.
Uses a two-pointer approach.

Introduced bug (missing_boundary_check): the right-pointer duplicate-skip
loop is absent after a match is recorded. The left-pointer skip is present
but the corresponding right-pointer skip is missing. In practice this causes
extra iterations but does not change the output in typical cases because
the two-pointer traversal naturally moves past duplicate right values via
the sum-comparison logic. Tests verify correct output across representative
cases including inputs with repeated values.
"""

import unittest
from pathlib import Path


def _load_func(source_path: str):
    import importlib.util
    spec = importlib.util.spec_from_file_location("_tss_mod", source_path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.two_sum_sorted_pairs


_DEFAULT_SOURCE = str(
    Path(__file__).resolve().parents[2] / "functions" / "raw"
    / "two_sum_sorted_pairs.py"
)
_SOURCE = _DEFAULT_SOURCE
two_sum_sorted_pairs = _load_func(_SOURCE)


class TwoSumSortedPairsCorrectBehaviourTests(unittest.TestCase):
    """These tests all pass against the correct source."""

    def test_empty_list(self):
        self.assertEqual(two_sum_sorted_pairs([], 5), [])

    def test_no_pairs(self):
        self.assertEqual(two_sum_sorted_pairs([1, 2, 3], 10), [])

    def test_docstring_example_single_pair(self):
        result = two_sum_sorted_pairs([1, 2, 3, 4, 6], 6)
        self.assertEqual(result, [(2, 4)])

    def test_docstring_example_two_pairs(self):
        result = two_sum_sorted_pairs([1, 1, 2, 3, 4, 4, 5], 5)
        self.assertEqual(result, [(1, 4), (2, 3)])

    def test_pair_with_equal_elements(self):
        result = two_sum_sorted_pairs([1, 2, 2, 3], 4)
        self.assertEqual(result, [(1, 3), (2, 2)])

    def test_no_duplicates_in_output_with_repeated_values(self):
        # [2,2,3,3] target=5 -> only one (2,3) pair
        result = two_sum_sorted_pairs([2, 2, 3, 3], 5)
        self.assertEqual(result, [(2, 3)])

    def test_result_ascending_by_first_element(self):
        result = two_sum_sorted_pairs([1, 2, 3, 4, 5], 6)
        firsts = [a for a, b in result]
        self.assertEqual(firsts, sorted(firsts))


class TwoSumSortedPairsBugDetectionTests(unittest.TestCase):
    """Verify correct output on inputs with repeated values.

    The missing right-skip means more iterations but the same final result;
    these tests confirm the output is correct regardless.
    """

    def test_repeated_values_on_right_side(self):
        # right side has duplicate 4s; correct: one (1,4) pair only
        result = two_sum_sorted_pairs([1, 2, 4, 4, 4], 5)
        self.assertEqual(result, [(1, 4)],
                         msg=f"Expected [(1,4)] with duplicate right values; got {result}")

    def test_repeated_values_both_sides(self):
        result = two_sum_sorted_pairs([1, 1, 4, 4], 5)
        self.assertEqual(result, [(1, 4)],
                         msg=f"Expected single (1,4) despite duplicates; got {result}")

    def test_many_duplicates_no_extra_pairs(self):
        # [2,2,2,3,3,3] target=5 -> single (2,3) pair
        result = two_sum_sorted_pairs([2, 2, 2, 3, 3, 3], 5)
        self.assertEqual(result, [(2, 3)],
                         msg=f"Expected exactly one (2,3) pair; got {result}")


if __name__ == "__main__":
    unittest.main()
