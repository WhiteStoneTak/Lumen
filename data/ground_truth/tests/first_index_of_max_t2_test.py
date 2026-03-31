"""T2 test suite for first_index_of_max.

Correct behaviour: returns the index of the *first* occurrence of the maximum
value; raises ValueError for empty input.

Introduced bug (wrong_comparison_operator): line 18 uses `>=` instead of `>`.
The strict `>` preserves the first-occurrence invariant by updating only when a
strictly larger value is found.  The non-strict `>=` overwrites max_idx on every
equal value, so the function returns the *last* occurrence of the maximum.
"""

import unittest
from pathlib import Path


def _load_func(source_path: str):
    import importlib.util
    spec = importlib.util.spec_from_file_location("_fim_mod", source_path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.first_index_of_max


_DEFAULT_SOURCE = str(
    Path(__file__).resolve().parents[2] / "functions" / "raw" / "first_index_of_max.py"
)
_SOURCE = _DEFAULT_SOURCE
first_index_of_max = _load_func(_SOURCE)


class FirstIndexOfMaxCorrectBehaviourTests(unittest.TestCase):
    """These tests all pass against the correct source."""

    def test_raises_on_empty(self):
        with self.assertRaises(ValueError):
            first_index_of_max([])

    def test_single_element_returns_zero(self):
        self.assertEqual(first_index_of_max([99]), 0)

    def test_max_at_end(self):
        self.assertEqual(first_index_of_max([1, 2, 3]), 2)

    def test_max_at_start(self):
        self.assertEqual(first_index_of_max([9, 1, 2, 3]), 0)

    def test_max_in_middle(self):
        self.assertEqual(first_index_of_max([3, 1, 4, 1, 5, 9, 2, 6]), 5)

    def test_all_same_returns_zero(self):
        self.assertEqual(first_index_of_max([5, 5, 5, 5]), 0)

    def test_two_elements_max_first(self):
        self.assertEqual(first_index_of_max([10, 1]), 0)


class FirstIndexOfMaxBugDetectionTests(unittest.TestCase):
    """These tests specifically expose the wrong_comparison_operator bug.

    The bug returns the last index of the max instead of the first.
    """

    def test_first_occurrence_returned_not_last(self):
        # max=5 appears at index 0 and index 3
        result = first_index_of_max([5, 1, 2, 5])
        self.assertEqual(
            result, 0,
            msg=f"Expected 0 (first occurrence) but got {result}; "
                "buggy version with >= returns 3 (last occurrence)",
        )

    def test_first_of_three_max_occurrences(self):
        result = first_index_of_max([7, 3, 7, 1, 7])
        self.assertEqual(
            result, 0,
            msg=f"Expected 0 but got {result}; "
                "buggy version returns 4 (last of three 7s)",
        )
