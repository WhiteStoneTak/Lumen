"""T2 test suite for remove_adjacent_dups.

Correct behaviour: adjacent equal values are collapsed to a single occurrence;
non-adjacent duplicates are preserved; order is maintained.

Introduced bug (incorrect_variable_reference): line 16 compares `item` against
`items[-1]` (last element of the original input) instead of `result[-1]` (last
element appended to the accumulator).  Any element equal to the final input
value is suppressed throughout the list, while earlier adjacent duplicates
pass through unchecked.
"""

import unittest
from pathlib import Path


def _load_func(source_path: str):
    import importlib.util
    spec = importlib.util.spec_from_file_location("_rad_mod", source_path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.remove_adjacent_dups


_DEFAULT_SOURCE = str(
    Path(__file__).resolve().parents[2] / "functions" / "raw" / "remove_adjacent_dups.py"
)
_SOURCE = _DEFAULT_SOURCE
remove_adjacent_dups = _load_func(_SOURCE)


class RemoveAdjacentDupsCorrectBehaviourTests(unittest.TestCase):
    """These tests all pass against the correct source."""

    def test_empty_list_returns_empty(self):
        self.assertEqual(remove_adjacent_dups([]), [])

    def test_single_element_unchanged(self):
        self.assertEqual(remove_adjacent_dups([42]), [42])

    def test_all_distinct_unchanged(self):
        self.assertEqual(remove_adjacent_dups([1, 2, 3]), [1, 2, 3])

    def test_all_same_collapsed_to_one(self):
        self.assertEqual(remove_adjacent_dups([5, 5, 5, 5]), [5])

    def test_non_adjacent_duplicates_preserved(self):
        self.assertEqual(remove_adjacent_dups([1, 2, 1]), [1, 2, 1])

    def test_mixed_runs(self):
        self.assertEqual(remove_adjacent_dups([1, 1, 2, 3, 3, 3, 2]), [1, 2, 3, 2])

    def test_strings(self):
        self.assertEqual(remove_adjacent_dups(["a", "a", "b", "b", "a"]), ["a", "b", "a"])


class RemoveAdjacentDupsBugDetectionTests(unittest.TestCase):
    """These tests specifically expose the incorrect_variable_reference bug.

    The bug compares item against items[-1] instead of result[-1].
    Any value equal to the last input element is suppressed everywhere.
    """

    def test_leading_run_of_final_value_is_collapsed(self):
        # items=[3,3,1,2,3], items[-1]=3
        # buggy: all 3s are suppressed → [1, 2]
        # correct:                      → [3, 1, 2, 3]
        result = remove_adjacent_dups([3, 3, 1, 2, 3])
        self.assertEqual(
            result, [3, 1, 2, 3],
            msg=f"Expected [3, 1, 2, 3] but got {result}; "
                "buggy version returns [1, 2] because items[-1]=3 suppresses all 3s",
        )

    def test_middle_run_of_final_value_is_collapsed(self):
        # items=[1,2,2,3], items[-1]=3
        # buggy: 3 suppressed, 2-run passes → [1, 2, 2]
        # correct:                          → [1, 2, 3]
        result = remove_adjacent_dups([1, 2, 2, 3])
        self.assertEqual(
            result, [1, 2, 3],
            msg=f"Expected [1, 2, 3] but got {result}; "
                "buggy version returns [1, 2, 2] — adjacent 2s pass because 2 != items[-1]=3",
        )
