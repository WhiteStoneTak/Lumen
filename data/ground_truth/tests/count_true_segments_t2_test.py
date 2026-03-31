"""T2 test suite for count_true_segments.

Correct behaviour: counts each maximal run of True values as one segment,
regardless of whether it ends at a False element or at the end of the list.

Introduced bug (missing_boundary_check): the buggy version counts a segment on
exit (when a True-run is followed by False) rather than on entry.  Any True
segment that reaches the end of the input never encounters a False transition,
so it is never counted.
"""

import unittest
from pathlib import Path


def _load_func(source_path: str):
    import importlib.util
    spec = importlib.util.spec_from_file_location("_cts_mod", source_path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.count_true_segments


_DEFAULT_SOURCE = str(
    Path(__file__).resolve().parents[2] / "functions" / "raw" / "count_true_segments.py"
)
_SOURCE = _DEFAULT_SOURCE
count_true_segments = _load_func(_SOURCE)


class CountTrueSegmentsCorrectBehaviourTests(unittest.TestCase):
    """These tests all pass against the correct source."""

    def test_empty_returns_zero(self):
        self.assertEqual(count_true_segments([]), 0)

    def test_all_false_returns_zero(self):
        self.assertEqual(count_true_segments([False, False, False]), 0)

    def test_single_true(self):
        self.assertEqual(count_true_segments([True]), 1)

    def test_segment_followed_by_false(self):
        self.assertEqual(count_true_segments([True, True, False]), 1)

    def test_two_separated_segments(self):
        self.assertEqual(count_true_segments([True, False, True]), 2)

    def test_false_true_false_true(self):
        self.assertEqual(count_true_segments([False, True, True, False, True]), 2)

    def test_alternating(self):
        self.assertEqual(count_true_segments([True, False, True, False, True]), 3)


class CountTrueSegmentsBugDetectionTests(unittest.TestCase):
    """These tests specifically expose the missing_boundary_check bug.

    The buggy version misses any True segment at the end of the list.
    """

    def test_trailing_true_segment_is_counted(self):
        # Segment ends at end of list — no False follows it
        result = count_true_segments([True, True, True])
        self.assertEqual(
            result, 1,
            msg=f"Expected 1 but got {result}; "
                "buggy version returns 0 because the segment never exits to False",
        )

    def test_two_segments_second_is_trailing(self):
        # flags=[False, True, False, True, True], second segment is trailing
        result = count_true_segments([False, True, False, True, True])
        self.assertEqual(
            result, 2,
            msg=f"Expected 2 but got {result}; "
                "buggy version returns 1 — the trailing [True,True] segment is missed",
        )
