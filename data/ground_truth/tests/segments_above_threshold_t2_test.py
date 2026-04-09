"""T2 test suite for segments_above_threshold.

Correct behaviour: returns all maximal contiguous sublists where every
element is strictly greater than threshold (exclusive lower bound).

Introduced bug (wrong_comparison_operator): threshold check uses '>='
instead of '>', causing elements exactly equal to the threshold to be
included in segments. Produces wrong results whenever any value equals
the threshold; passes when no value equals the threshold.
"""

import unittest
from pathlib import Path


def _load_func(source_path: str):
    import importlib.util
    spec = importlib.util.spec_from_file_location("_sat_mod", source_path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.segments_above_threshold


_DEFAULT_SOURCE = str(
    Path(__file__).resolve().parents[2] / "functions" / "raw"
    / "segments_above_threshold.py"
)
_SOURCE = _DEFAULT_SOURCE
segments_above_threshold = _load_func(_SOURCE)


class SegmentsAboveThresholdCorrectBehaviourTests(unittest.TestCase):
    """These tests all pass against the correct source."""

    def test_empty_list(self):
        self.assertEqual(segments_above_threshold([], 5), [])

    def test_no_values_above_threshold(self):
        self.assertEqual(segments_above_threshold([1, 2, 3], 5), [])

    def test_all_values_above_threshold(self):
        self.assertEqual(segments_above_threshold([6, 6, 6], 5), [[6, 6, 6]])

    def test_docstring_example(self):
        result = segments_above_threshold([1, 5, 6, 2, 8, 9, 3], 4)
        self.assertEqual(result, [[5, 6], [8, 9]])

    def test_single_run(self):
        result = segments_above_threshold([1, 2, 10, 20, 1], 5)
        self.assertEqual(result, [[10, 20]])

    def test_multiple_separated_runs(self):
        result = segments_above_threshold([10, 1, 10, 1, 10], 5)
        self.assertEqual(result, [[10], [10], [10]])


class SegmentsAboveThresholdBugDetectionTests(unittest.TestCase):
    """These tests specifically expose the wrong_comparison_operator bug.

    The bug uses >= instead of >, admitting threshold-equal values into
    segments. Detectable on any input containing values exactly equal to
    the threshold.
    """

    def test_threshold_equal_value_excluded(self):
        # threshold=4; value 4 is NOT strictly greater — must not appear in result
        # Buggy (>=): segments_above_threshold([4, 5, 6], 4) -> [[4, 5, 6]]
        # Correct (>):                                        -> [[5, 6]]
        result = segments_above_threshold([4, 5, 6], 4)
        self.assertEqual(
            result, [[5, 6]],
            msg=f"Value 4 equals threshold 4 and must be excluded; got {result}",
        )

    def test_threshold_equal_value_breaks_segment(self):
        # 5 at index 2 is == threshold; it should break the run [6,6] -> [6],[6]
        result = segments_above_threshold([6, 6, 5, 6, 6], 5)
        self.assertEqual(
            result, [[6, 6], [6, 6]],
            msg=f"Value 5 == threshold 5 must split the segment; got {result}",
        )

    def test_only_threshold_value_produces_no_segment(self):
        # All values == threshold — strict > means no segment at all
        result = segments_above_threshold([3, 3, 3], 3)
        self.assertEqual(
            result, [],
            msg=f"Values equal to threshold must not form a segment; got {result}",
        )

    def test_strictly_above_threshold_unaffected(self):
        # Regression: values clearly above threshold still returned
        result = segments_above_threshold([10, 20, 30], 5)
        self.assertEqual(result, [[10, 20, 30]],
                         msg=f"All values > threshold should form one segment; got {result}")


if __name__ == "__main__":
    unittest.main()
