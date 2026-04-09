"""T2 test suite for merge_intervals.

Correct behaviour: merges overlapping and touching intervals. Two intervals
[a,b] and [c,d] are merged when c <= b (touching counts).

Introduced bug (wrong_comparison_operator): the overlap check uses
`next_start < current[1]` (strict) instead of `next_start <= current[1]`.
Touching intervals where next_start == current[1] are not merged.
"""

import unittest
from pathlib import Path


def _load_func(source_path: str):
    import importlib.util
    spec = importlib.util.spec_from_file_location("_mi_mod", source_path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.merge_intervals


_DEFAULT_SOURCE = str(
    Path(__file__).resolve().parents[2] / "functions" / "raw" / "merge_intervals.py"
)
_SOURCE = _DEFAULT_SOURCE
merge_intervals = _load_func(_SOURCE)


class MergeIntervalsCorrectBehaviourTests(unittest.TestCase):
    """These tests all pass against the correct source."""

    def test_empty_returns_empty(self):
        self.assertEqual(merge_intervals([]), [])

    def test_single_interval(self):
        self.assertEqual(merge_intervals([[1, 5]]), [[1, 5]])

    def test_non_overlapping(self):
        self.assertEqual(merge_intervals([[1, 2], [3, 4]]), [[1, 2], [3, 4]])

    def test_overlapping_merged(self):
        self.assertEqual(
            merge_intervals([[1, 3], [2, 6], [8, 10], [15, 18]]),
            [[1, 6], [8, 10], [15, 18]],
        )

    def test_all_overlap_single_result(self):
        self.assertEqual(merge_intervals([[1, 4], [2, 3]]), [[1, 4]])


class MergeIntervalsBugDetectionTests(unittest.TestCase):
    """These tests specifically expose the wrong_comparison_operator bug.

    The buggy version uses strict < so touching intervals (next_start == current_end)
    are not merged even though the docstring says they should be.
    """

    def test_touching_intervals_are_merged(self):
        # [1,2] and [2,4]: next_start=2 == current[1]=2 -> should merge to [1,4]
        # buggy: 2 < 2 is False -> not merged, returns [[1,2],[2,4]]
        result = merge_intervals([[1, 2], [2, 4]])
        self.assertEqual(
            result, [[1, 4]],
            msg=f"Expected [[1,4]] but got {result}; "
                "buggy version uses < instead of <=, failing to merge touching intervals",
        )

    def test_docstring_touching_example(self):
        result = merge_intervals([[1, 4], [4, 5]])
        self.assertEqual(
            result, [[1, 5]],
            msg=f"Expected [[1,5]] but got {result}; "
                "buggy version returns [[1,4],[4,5]] because 4 < 4 is False",
        )

    def test_three_touching_intervals(self):
        result = merge_intervals([[0, 1], [1, 2], [2, 3]])
        self.assertEqual(
            result, [[0, 3]],
            msg=f"Expected [[0,3]] but got {result}; "
                "all three touching intervals should merge into one",
        )
