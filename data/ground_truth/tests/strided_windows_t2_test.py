"""T2 test suite for strided_windows.

Correct behaviour: extracts full-sized windows starting at 0, stride, 2*stride...
The loop condition is `i + size <= n` (inclusive), so the last window that fits
exactly at the end is included.

Introduced bug (off_by_one): the loop condition uses `i + size < n` (strict)
instead of `i + size <= n`. The last valid full window starting at position
i where i + size == n exactly is excluded.
"""

import unittest
from pathlib import Path


def _load_func(source_path: str):
    import importlib.util
    spec = importlib.util.spec_from_file_location("_sw_mod", source_path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.strided_windows


_DEFAULT_SOURCE = str(
    Path(__file__).resolve().parents[2] / "functions" / "raw" / "strided_windows.py"
)
_SOURCE = _DEFAULT_SOURCE
strided_windows = _load_func(_SOURCE)


class StridedWindowsCorrectBehaviourTests(unittest.TestCase):
    """These tests all pass against the correct source."""

    def test_empty_returns_empty(self):
        self.assertEqual(strided_windows([], 3, 1), [])

    def test_size_larger_than_list_returns_empty(self):
        self.assertEqual(strided_windows([1, 2], 3, 1), [])

    def test_docstring_example_stride_one(self):
        self.assertEqual(
            strided_windows([1, 2, 3, 4, 5], 3, 1),
            [[1, 2, 3], [2, 3, 4], [3, 4, 5]],
        )

    def test_docstring_example_stride_two(self):
        self.assertEqual(
            strided_windows([1, 2, 3, 4, 5], 3, 2),
            [[1, 2, 3], [3, 4, 5]],
        )

    def test_partial_windows_included(self):
        self.assertEqual(
            strided_windows([1, 2, 3, 4, 5], 3, 2, include_partial=True),
            [[1, 2, 3], [3, 4, 5], [5]],
        )


class StridedWindowsBugDetectionTests(unittest.TestCase):
    """These tests specifically expose the off_by_one loop condition bug.

    The buggy version uses `i + size < n` (strict), so the final window
    is dropped when i + size == n exactly (the window fits perfectly).
    """

    def test_last_window_fits_exactly_is_included(self):
        # [1,2,3], size=3, stride=1: only window at i=0, i+3==3==n -> included
        # buggy: 0+3 < 3 is False -> returns []
        result = strided_windows([1, 2, 3], 3, 1)
        self.assertEqual(
            result, [[1, 2, 3]],
            msg=f"Expected [[1,2,3]] but got {result}; "
                "buggy version drops the window when i+size==n (uses < instead of <=)",
        )

    def test_exact_fit_at_end_after_stride(self):
        # [1,2,3,4], size=2, stride=2: windows at i=0 ([1,2]) and i=2 ([3,4])
        # i=2: 2+2=4==n -> included; buggy: 4 < 4 is False -> drops [3,4]
        result = strided_windows([1, 2, 3, 4], 2, 2)
        self.assertEqual(
            result, [[1, 2], [3, 4]],
            msg=f"Expected [[1,2],[3,4]] but got {result}; "
                "buggy version misses last window [3,4] because 2+2<4 is False",
        )

    def test_size_equals_length_returns_one_window(self):
        result = strided_windows([5, 6, 7, 8], 4, 1)
        self.assertEqual(
            result, [[5, 6, 7, 8]],
            msg=f"Expected [[5,6,7,8]] but got {result}",
        )
