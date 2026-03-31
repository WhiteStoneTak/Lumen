"""T3 post-transform test suite for first_index_of_max.

Transform spec (first_index_of_max.TR01): Change the tie-breaking policy.
Instead of returning the index of the first occurrence of the maximum value,
return the index of the last occurrence. Single-occurrence maxima are unchanged.

These tests are run against a model's transformed implementation.
Parse failure and execution failure score 0.0 without running tests.
"""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path


def _load_func(source_path: str):
    spec = importlib.util.spec_from_file_location("_fiom_t3_mod", source_path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.first_index_of_max


_DEFAULT_SOURCE = str(
    Path(__file__).resolve().parents[2] / "functions" / "raw" / "first_index_of_max.py"
)
_SOURCE = _DEFAULT_SOURCE
first_index_of_max = _load_func(_SOURCE)


class FirstIndexOfMaxT3LastOccurrenceTests(unittest.TestCase):
    """The function must return the LAST index of the maximum value."""

    def test_basic_last_occurrence_all_equal(self) -> None:
        # [5,5,5]: max=5, last at index 2; original returns 0
        result = first_index_of_max([5, 5, 5])
        self.assertEqual(result, 2)

    def test_unique_max_unchanged(self) -> None:
        # [3,1,4,1,5,9,2,6]: max=9 at index 5 (only occurrence)
        result = first_index_of_max([3, 1, 4, 1, 5, 9, 2, 6])
        self.assertEqual(result, 5)

    def test_last_of_multiple_maxima(self) -> None:
        # [1,5,3,5]: max=5 at indices 1 and 3; last is 3
        result = first_index_of_max([1, 5, 3, 5])
        self.assertEqual(result, 3)

    def test_max_at_end(self) -> None:
        # [1,2,3,4,5]: max=5 at index 4 (unique)
        result = first_index_of_max([1, 2, 3, 4, 5])
        self.assertEqual(result, 4)

    def test_max_at_start_unique(self) -> None:
        # [5,1,2,3]: max=5 at index 0 (unique) → same result for both policies
        result = first_index_of_max([5, 1, 2, 3])
        self.assertEqual(result, 0)

    def test_tied_max_returns_last_not_first(self) -> None:
        # [1,3,2,3,1]: max=3 at indices 1 and 3; last is 3; original returns 1
        result = first_index_of_max([1, 3, 2, 3, 1])
        self.assertEqual(result, 3)
        self.assertNotEqual(result, 1)

    def test_empty_raises_value_error(self) -> None:
        with self.assertRaises(ValueError):
            first_index_of_max([])

    def test_single_element(self) -> None:
        result = first_index_of_max([42])
        self.assertEqual(result, 0)


class FirstIndexOfMaxT3TiePolicyDifferenceTests(unittest.TestCase):
    """Confirm that last-occurrence policy diverges from first-occurrence policy."""

    def test_two_maxima_at_start_and_end(self) -> None:
        # [7,1,2,7]: max=7 at 0 and 3; last → 3, first → 0
        result = first_index_of_max([7, 1, 2, 7])
        self.assertEqual(result, 3)

    def test_three_maxima_returns_last(self) -> None:
        # [4,4,2,4]: max=4 at indices 0,1,3; last is 3
        result = first_index_of_max([4, 4, 2, 4])
        self.assertEqual(result, 3)

    def test_two_adjacent_maxima(self) -> None:
        # [1,6,6,2]: max=6 at indices 1 and 2; last is 2
        result = first_index_of_max([1, 6, 6, 2])
        self.assertEqual(result, 2)

    def test_descending_list_unique_max(self) -> None:
        # [9,5,3,1]: max=9 at index 0 (unique); same for both policies
        result = first_index_of_max([9, 5, 3, 1])
        self.assertEqual(result, 0)


if __name__ == "__main__":
    unittest.main()
