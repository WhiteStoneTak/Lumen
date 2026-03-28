"""T3 post-transform test suite for clamp.

Transform spec (clamp.TR01): The function must enforce the precondition
lo <= hi by raising ValueError when lo > hi. All clamping behavior must
remain unchanged for valid inputs.

These tests are run against a model's transformed implementation.
Parse failure and execution failure score 0.0 without running tests.
"""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path


def _load_func(source_path: str):
    spec = importlib.util.spec_from_file_location("_clamp_t3_mod", source_path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.clamp


_DEFAULT_SOURCE = str(
    Path(__file__).resolve().parents[2] / "functions" / "raw" / "clamp.py"
)
_SOURCE = _DEFAULT_SOURCE
clamp = _load_func(_SOURCE)


class ClampT3OriginalBehaviourTests(unittest.TestCase):
    """Original clamping behavior must be preserved for valid lo <= hi inputs."""

    def test_value_below_lo_clamped_to_lo(self) -> None:
        self.assertEqual(clamp(0.0, 5.0, 10.0), 5.0)

    def test_value_above_hi_clamped_to_hi(self) -> None:
        self.assertEqual(clamp(15.0, 5.0, 10.0), 10.0)

    def test_value_within_range_returned_unchanged(self) -> None:
        self.assertEqual(clamp(7.0, 5.0, 10.0), 7.0)

    def test_value_equal_to_lo(self) -> None:
        self.assertEqual(clamp(5.0, 5.0, 10.0), 5.0)

    def test_value_equal_to_hi(self) -> None:
        self.assertEqual(clamp(10.0, 5.0, 10.0), 10.0)

    def test_zero_width_interval(self) -> None:
        self.assertEqual(clamp(3.0, 7.0, 7.0), 7.0)

    def test_negative_range(self) -> None:
        self.assertEqual(clamp(-1.0, -5.0, -2.0), -2.0)


class ClampT3PreconditionEnforcementTests(unittest.TestCase):
    """The transformed function must raise ValueError when lo > hi."""

    def test_lo_greater_than_hi_raises_value_error(self) -> None:
        with self.assertRaises(ValueError):
            clamp(5.0, 10.0, 1.0)

    def test_lo_much_greater_than_hi_raises_value_error(self) -> None:
        with self.assertRaises(ValueError):
            clamp(0.0, 100.0, -100.0)

    def test_lo_equal_to_hi_does_not_raise(self) -> None:
        # lo == hi is valid (zero-width interval)
        result = clamp(5.0, 7.0, 7.0)
        self.assertEqual(result, 7.0)

    def test_lo_slightly_greater_than_hi_raises(self) -> None:
        with self.assertRaises(ValueError):
            clamp(0.0, 1.001, 1.0)


if __name__ == "__main__":
    unittest.main()
