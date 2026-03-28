"""T3 post-transform test suite for is_sorted.

Transform spec (is_sorted.TR01): The function must require strictly ascending
order. Each element must be strictly less than the next. A list with equal
adjacent elements must return False. Empty and single-element lists still
return True.

These tests are run against a model's transformed implementation.
Parse failure and execution failure score 0.0 without running tests.
"""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path


def _load_func(source_path: str):
    spec = importlib.util.spec_from_file_location("_is_sorted_t3_mod", source_path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.is_sorted


_DEFAULT_SOURCE = str(
    Path(__file__).resolve().parents[2] / "functions" / "raw" / "is_sorted.py"
)
_SOURCE = _DEFAULT_SOURCE
is_sorted = _load_func(_SOURCE)


class IsSortedT3StrictAscendingTests(unittest.TestCase):
    """Equal adjacent elements must now return False (strictly ascending only)."""

    def test_equal_adjacent_elements_returns_false(self) -> None:
        # Non-decreasing [1, 1, 2] is not strictly ascending
        self.assertFalse(is_sorted([1, 1, 2]))

    def test_all_equal_returns_false(self) -> None:
        # [5, 5, 5] is not strictly ascending
        self.assertFalse(is_sorted([5, 5, 5]))

    def test_two_equal_elements_returns_false(self) -> None:
        # [3, 3] is not strictly ascending
        self.assertFalse(is_sorted([3, 3]))

    def test_strictly_ascending_returns_true(self) -> None:
        self.assertTrue(is_sorted([1, 2, 3, 4]))

    def test_strictly_ascending_two_elements(self) -> None:
        self.assertTrue(is_sorted([1, 2]))


class IsSortedT3OriginalBehaviourPreservedTests(unittest.TestCase):
    """Original behavior for edge cases and clearly descending inputs is preserved."""

    def test_empty_list_still_returns_true(self) -> None:
        self.assertTrue(is_sorted([]))

    def test_single_element_still_returns_true(self) -> None:
        self.assertTrue(is_sorted([42]))

    def test_descending_still_returns_false(self) -> None:
        self.assertFalse(is_sorted([4, 3, 2, 1]))

    def test_unsorted_with_duplicates_still_false(self) -> None:
        self.assertFalse(is_sorted([1, 3, 2]))

    def test_two_descending_still_false(self) -> None:
        self.assertFalse(is_sorted([2, 1]))


if __name__ == "__main__":
    unittest.main()
