"""T2 test suite for clamp.

Correct behavior: clamp(value, lo, hi) returns value clamped to [lo, hi].
Introduced bug (wrong_comparison_operator): line 8 uses `value < hi` instead of
`value > hi`, so values greater than hi are returned as hi only when they happen
to be less than hi (never), causing values above hi to pass through unclamped.

Run against the correct source:  python -m unittest data/ground_truth/tests/clamp_t2_test.py
Run against the buggy source:    copy buggy source into scope and run; the high-clamp test fails.
"""

import sys
import unittest
from pathlib import Path


def _load_func(source_path: str):
    """Load `clamp` from an explicit source file path."""
    import importlib.util

    spec = importlib.util.spec_from_file_location("_clamp_mod", source_path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.clamp


# By default, import from the canonical raw source so the suite passes.
_DEFAULT_SOURCE = str(
    Path(__file__).resolve().parents[2] / "functions" / "raw" / "clamp.py"
)
_SOURCE = _DEFAULT_SOURCE
clamp = _load_func(_SOURCE)


class ClampCorrectBehaviourTests(unittest.TestCase):
    """These tests all pass against the correct source."""

    def test_value_below_lo_is_clamped_to_lo(self) -> None:
        self.assertEqual(clamp(0.0, 5.0, 10.0), 5.0)

    def test_value_above_hi_is_clamped_to_hi(self) -> None:
        # BUG TARGET: buggy version returns value (15.0) because `value < hi`
        # (15 < 10 is False) so control falls through to `return value`.
        self.assertEqual(clamp(15.0, 5.0, 10.0), 10.0)

    def test_value_within_range_is_returned_unchanged(self) -> None:
        self.assertEqual(clamp(7.0, 5.0, 10.0), 7.0)

    def test_value_equal_to_lo_is_returned_as_lo(self) -> None:
        self.assertEqual(clamp(5.0, 5.0, 10.0), 5.0)

    def test_value_equal_to_hi_is_returned_as_hi(self) -> None:
        self.assertEqual(clamp(10.0, 5.0, 10.0), 10.0)

    def test_negative_range(self) -> None:
        self.assertEqual(clamp(-1.0, -5.0, -2.0), -2.0)

    def test_zero_width_interval(self) -> None:
        self.assertEqual(clamp(3.0, 7.0, 7.0), 7.0)


class ClampBugDetectionTests(unittest.TestCase):
    """These tests specifically expose the wrong_comparison_operator bug.

    The bug changes `value > hi` to `value < hi` on line 8.
    For any value strictly above hi, the buggy function returns value instead of hi.
    """

    def test_value_well_above_hi_must_clamp(self) -> None:
        result = clamp(100.0, 0.0, 1.0)
        self.assertEqual(result, 1.0, msg=f"Expected 1.0 but got {result}; buggy version returns 100.0")

    def test_value_just_above_hi_must_clamp(self) -> None:
        result = clamp(10.001, 0.0, 10.0)
        self.assertAlmostEqual(result, 10.0, places=3,
                               msg=f"Expected 10.0 but got {result}; buggy version returns 10.001")


if __name__ == "__main__":
    unittest.main()
