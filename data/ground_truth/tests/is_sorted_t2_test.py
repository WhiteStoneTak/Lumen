"""T2 test suite for is_sorted.

Correct behavior: is_sorted(items) returns True iff items is in non-decreasing
order (equal adjacent elements are allowed).
Introduced bug (wrong_comparison_operator): line 7 uses `items[i] >= items[i+1]`
instead of `items[i] > items[i+1]`, so equal adjacent elements trigger an early
return of False, incorrectly rejecting non-strictly-decreasing lists.

Run against the correct source:  python -m unittest data/ground_truth/tests/is_sorted_t2_test.py
Run against the buggy source:    tests with duplicate adjacent values fail.
"""

import sys
import unittest
from pathlib import Path


def _load_func(source_path: str):
    import importlib.util

    spec = importlib.util.spec_from_file_location("_is_sorted_mod", source_path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.is_sorted


_DEFAULT_SOURCE = str(
    Path(__file__).resolve().parents[2] / "functions" / "raw" / "is_sorted.py"
)
_SOURCE = _DEFAULT_SOURCE
is_sorted = _load_func(_SOURCE)


class IsSortedCorrectBehaviourTests(unittest.TestCase):
    """These tests all pass against the correct source."""

    def test_empty_list_returns_true(self) -> None:
        self.assertTrue(is_sorted([]))

    def test_single_element_returns_true(self) -> None:
        self.assertTrue(is_sorted([42]))

    def test_ascending_list_returns_true(self) -> None:
        self.assertTrue(is_sorted([1, 2, 3, 4]))

    def test_descending_list_returns_false(self) -> None:
        self.assertFalse(is_sorted([4, 3, 2, 1]))

    def test_equal_adjacent_elements_returns_true(self) -> None:
        # BUG TARGET: buggy version uses >= so [1, 1, 2] triggers i=0: 1 >= 1 → True → return False.
        self.assertTrue(is_sorted([1, 1, 2]))

    def test_all_equal_returns_true(self) -> None:
        # BUG TARGET: buggy version returns False for [5, 5, 5].
        self.assertTrue(is_sorted([5, 5, 5]))

    def test_two_equal_elements_returns_true(self) -> None:
        # BUG TARGET: buggy version returns False for [3, 3].
        self.assertTrue(is_sorted([3, 3]))

    def test_unsorted_with_duplicates_returns_false(self) -> None:
        self.assertFalse(is_sorted([1, 3, 2]))

    def test_two_element_ascending_returns_true(self) -> None:
        self.assertTrue(is_sorted([1, 2]))

    def test_two_element_descending_returns_false(self) -> None:
        self.assertFalse(is_sorted([2, 1]))


class IsSortedBugDetectionTests(unittest.TestCase):
    """Directly expose the wrong_comparison_operator bug (>= instead of >)."""

    def test_list_with_adjacent_equal_values_must_be_sorted(self) -> None:
        result = is_sorted([2, 2, 3])
        self.assertTrue(result,
                        msg=f"Expected True but got {result}; buggy version returns False for equal adjacent elements")

    def test_constant_list_must_be_sorted(self) -> None:
        result = is_sorted([7, 7, 7, 7])
        self.assertTrue(result,
                        msg=f"Expected True but got {result}; buggy version returns False")


if __name__ == "__main__":
    unittest.main()
