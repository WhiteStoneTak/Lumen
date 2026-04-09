"""T2 test suite for peak_valley_indices.

Correct behaviour: returns the indices of strict local peaks and valleys.
Strict peak at i: nums[i] > nums[i-1] AND nums[i] > nums[i+1].
Strict valley at i: nums[i] < nums[i-1] AND nums[i] < nums[i+1].
Boundary elements are never peaks/valleys. Plateaus are not included.

Introduced bug (wrong_comparison_operator): peak condition uses '>='
instead of '>' for both comparisons, so plateau-edge elements (where
mid equals one neighbour) are falsely classified as peaks.
"""

import unittest
from pathlib import Path


def _load_func(source_path: str):
    import importlib.util
    spec = importlib.util.spec_from_file_location("_pvi_mod", source_path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.peak_valley_indices


_DEFAULT_SOURCE = str(
    Path(__file__).resolve().parents[2] / "functions" / "raw" / "peak_valley_indices.py"
)
_SOURCE = _DEFAULT_SOURCE
peak_valley_indices = _load_func(_SOURCE)


class PeakValleyIndicesCorrectBehaviourTests(unittest.TestCase):
    """These tests all pass against the correct source."""

    def test_empty_and_short_lists(self):
        self.assertEqual(peak_valley_indices([]), [])
        self.assertEqual(peak_valley_indices([1]), [])
        self.assertEqual(peak_valley_indices([1, 2]), [])

    def test_no_peaks_or_valleys_monotone(self):
        self.assertEqual(peak_valley_indices([1, 2, 3, 4, 5]), [])

    def test_docstring_example(self):
        result = peak_valley_indices([1, 3, 2, 0, 4, 1])
        self.assertEqual(result, [("peak", 1), ("valley", 3), ("peak", 4)])

    def test_alternating_peak_valley(self):
        result = peak_valley_indices([3, 1, 3, 1])
        self.assertEqual(result, [("valley", 1), ("peak", 2)])

    def test_single_valley(self):
        result = peak_valley_indices([5, 1, 5])
        self.assertEqual(result, [("valley", 1)])

    def test_single_peak(self):
        result = peak_valley_indices([1, 5, 1])
        self.assertEqual(result, [("peak", 1)])


class PeakValleyIndicesBugDetectionTests(unittest.TestCase):
    """These tests specifically expose the wrong_comparison_operator bug.

    The bug uses >= instead of > for the peak check, causing plateau
    boundaries to be falsely reported as peaks.
    """

    def test_plateau_not_reported_as_peak(self):
        # [1, 3, 3, 2]: index 1 has mid=3, left=1, right=3
        # Buggy: 3>=1 and 3>=3 -> True -> reports ("peak", 1)
        # Correct: 3>1 and 3>3 -> False -> no peak at index 1
        result = peak_valley_indices([1, 3, 3, 2])
        self.assertNotIn(
            ("peak", 1), result,
            msg=f"Index 1 is not a strict peak (3 is not > 3); "
                f"buggy >= would return it; got: {result}",
        )

    def test_plateau_not_reported_as_peak_interior(self):
        # [1, 3, 3, 3, 2]: all 3-valued indices; none is a strict peak
        result = peak_valley_indices([1, 3, 3, 3, 2])
        peaks = [idx for (kind, idx) in result if kind == "peak"]
        self.assertEqual(peaks, [],
                         msg=f"No strict peaks in a plateau; got peaks at {peaks}")

    def test_equal_right_neighbour_not_peak(self):
        # [2, 4, 4, 1]: index 1, mid=4, right=4; not a strict peak
        result = peak_valley_indices([2, 4, 4, 1])
        self.assertNotIn(
            ("peak", 1), result,
            msg=f"Index 1 (mid=4 not > right=4) must not be a peak; got {result}",
        )

    def test_strict_peak_still_detected(self):
        # Regression: verify strict peaks survive the fix
        result = peak_valley_indices([1, 5, 2])
        self.assertIn(
            ("peak", 1), result,
            msg=f"Index 1 is a strict peak (5>1 and 5>2) and must appear; got {result}",
        )


if __name__ == "__main__":
    unittest.main()
