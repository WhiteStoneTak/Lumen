"""T3 post-transform test suite for strided_windows.

Transform spec (strided_windows.TR01): Return windows in REVERSE order —
last window first, first window last. Individual window contents are unchanged;
only the ordering of windows in the output list is reversed.

These tests are run against a model's transformed implementation.
Parse failure and execution failure score 0.0 without running tests.
"""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path


def _load_func(source_path: str):
    spec = importlib.util.spec_from_file_location("_sw_t3_mod", source_path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.strided_windows


_DEFAULT_SOURCE = str(
    Path(__file__).resolve().parents[2] / "functions" / "raw" / "strided_windows.py"
)
_SOURCE = _DEFAULT_SOURCE
strided_windows = _load_func(_SOURCE)


class StridedWindowsT3ReversedOrderTests(unittest.TestCase):
    """Transformed function must return windows in reverse order."""

    def test_basic_reversed(self) -> None:
        # Original: [[1,2,3],[2,3,4],[3,4,5]]
        # Reversed: [[3,4,5],[2,3,4],[1,2,3]]
        result = strided_windows([1, 2, 3, 4, 5], 3, 1)
        self.assertEqual(result, [[3, 4, 5], [2, 3, 4], [1, 2, 3]])

    def test_last_window_is_first(self) -> None:
        # First element of result must equal the last window of original
        result = strided_windows([1, 2, 3, 4, 5], 3, 1)
        self.assertEqual(result[0], [3, 4, 5])

    def test_window_contents_unchanged(self) -> None:
        # Individual windows are not internally reversed
        result = strided_windows([1, 2, 3, 4, 5], 3, 1)
        for window in result:
            # Each window must appear as a forward-order slice somewhere
            self.assertEqual(len(window), 3)
        # Check a specific window's content
        self.assertIn([1, 2, 3], result)
        self.assertIn([3, 4, 5], result)

    def test_not_original_order(self) -> None:
        # For multi-window input, first element must NOT be the first
        # window of the original
        result = strided_windows([1, 2, 3, 4, 5], 3, 1)
        self.assertNotEqual(result[0], [1, 2, 3])

    def test_stride_two_reversed(self) -> None:
        # Original stride=2: [[1,2,3],[3,4,5]]
        # Reversed: [[3,4,5],[1,2,3]]
        result = strided_windows([1, 2, 3, 4, 5], 3, 2)
        self.assertEqual(result, [[3, 4, 5], [1, 2, 3]])


class StridedWindowsT3EdgeCaseTests(unittest.TestCase):
    """Edge cases for reversed window order."""

    def test_single_window_unchanged(self) -> None:
        # Only one window: reversing has no effect
        result = strided_windows([1, 2, 3], 3, 1)
        self.assertEqual(result, [[1, 2, 3]])

    def test_empty_returns_empty(self) -> None:
        result = strided_windows([], 3, 1)
        self.assertEqual(result, [])

    def test_no_full_windows_returns_empty(self) -> None:
        # Window size larger than list: no windows
        result = strided_windows([1, 2], 5, 1)
        self.assertEqual(result, [])


if __name__ == "__main__":
    unittest.main()
