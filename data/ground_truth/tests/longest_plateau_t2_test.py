"""T2 test suite for longest_plateau.

Correct behaviour: returns (start, end, value) for the longest run of
consecutive equal elements. Ties go to the earliest starting run.

Introduced bug (wrong_comparison_operator): the post-loop flush uses
`cur_len >= best_len` instead of `cur_len > best_len`. When the final
run ties with the current best, it overwrites the earlier result, violating
the 'earliest start' tie-breaking policy.
"""

import unittest
from pathlib import Path


def _load_func(source_path: str):
    import importlib.util
    spec = importlib.util.spec_from_file_location("_lp_mod", source_path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.longest_plateau


_DEFAULT_SOURCE = str(
    Path(__file__).resolve().parents[2] / "functions" / "raw" / "longest_plateau.py"
)
_SOURCE = _DEFAULT_SOURCE
longest_plateau = _load_func(_SOURCE)


class LongestPlateauCorrectBehaviourTests(unittest.TestCase):
    """These tests all pass against the correct source."""

    def test_empty_returns_sentinel(self):
        self.assertEqual(longest_plateau([]), (-1, -1, None))

    def test_single_element(self):
        self.assertEqual(longest_plateau([5]), (0, 0, 5))

    def test_all_same(self):
        self.assertEqual(longest_plateau([3, 3, 3]), (0, 2, 3))

    def test_docstring_example(self):
        self.assertEqual(longest_plateau([1, 2, 2, 3, 3, 3, 1]), (3, 5, 3))

    def test_longest_is_first_segment(self):
        self.assertEqual(longest_plateau([5, 5, 5, 1, 1]), (0, 2, 5))


class LongestPlateauBugDetectionTests(unittest.TestCase):
    """These tests specifically expose the wrong_comparison_operator bug.

    The buggy version uses >= in the final flush, so a trailing run that
    ties with an earlier one overwrites it. The earliest run should win.
    """

    def test_tie_prefers_earliest_start(self):
        # [1, 1, 2, 2]: both runs have length 2. The first (1,1 at 0-1) should win.
        # buggy: trailing run [2,2] has cur_len=2 >= best_len=2, so it overwrites
        result = longest_plateau([1, 1, 2, 2])
        self.assertEqual(
            result, (0, 1, 1),
            msg=f"Expected (0, 1, 1) but got {result}; "
                "buggy version overwrites earliest run with trailing tie",
        )

    def test_trailing_tie_does_not_overwrite(self):
        # [3, 3, 4, 4, 4, 5, 5, 5]: length-3 at pos 2 and pos 5.
        # First occurrence (index 2-4, value 4) should win.
        result = longest_plateau([3, 3, 4, 4, 4, 5, 5, 5])
        self.assertEqual(
            result, (2, 4, 4),
            msg=f"Expected (2, 4, 4) but got {result}; "
                "buggy >= causes trailing equal-length run to overwrite",
        )

    def test_non_trailing_longest_wins(self):
        # [7, 7, 7, 8, 8]: longest is [7,7,7] at 0-2; trailing [8,8] shorter
        result = longest_plateau([7, 7, 7, 8, 8])
        self.assertEqual(result, (0, 2, 7))
