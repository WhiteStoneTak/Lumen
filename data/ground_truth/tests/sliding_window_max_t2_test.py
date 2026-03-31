"""T2 test suite for sliding_window_max.

Correct behaviour: returns the maximum of each k-element window as the window
slides one position at a time; the result has len(nums) - k + 1 elements.

Introduced bug (off_by_one): line 16 uses `range(len(nums) - k)` instead of
`range(len(nums) - k + 1)`.  This produces one fewer iteration than required,
omitting the final window that starts at index len(nums) - k.
"""

import unittest
from pathlib import Path


def _load_func(source_path: str):
    import importlib.util
    spec = importlib.util.spec_from_file_location("_swm_mod", source_path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.sliding_window_max


_DEFAULT_SOURCE = str(
    Path(__file__).resolve().parents[2] / "functions" / "raw" / "sliding_window_max.py"
)
_SOURCE = _DEFAULT_SOURCE
sliding_window_max = _load_func(_SOURCE)


class SlidingWindowMaxCorrectBehaviourTests(unittest.TestCase):
    """These tests all pass against the correct source."""

    def test_empty_returns_empty(self):
        self.assertEqual(sliding_window_max([], 3), [])

    def test_k_larger_than_length_returns_empty(self):
        self.assertEqual(sliding_window_max([1, 2], 5), [])

    def test_k_zero_returns_empty(self):
        self.assertEqual(sliding_window_max([1, 2, 3], 0), [])

    def test_k_equals_length_returns_single_max(self):
        self.assertEqual(sliding_window_max([3, 1, 4, 1, 5], 5), [5])

    def test_k_one_returns_nums_unchanged(self):
        self.assertEqual(sliding_window_max([3, 1, 4], 1), [3, 1, 4])

    def test_result_length(self):
        result = sliding_window_max([1, 3, 2, 4, 1], 3)
        self.assertEqual(len(result), 3)

    def test_ascending_sequence(self):
        self.assertEqual(sliding_window_max([1, 2, 3, 4, 5], 3), [3, 4, 5])


class SlidingWindowMaxBugDetectionTests(unittest.TestCase):
    """These tests specifically expose the off_by_one range bug.

    The bug omits the final window (starting at len(nums) - k).
    """

    def test_last_window_is_included(self):
        # nums=[1,3,2,4,1], k=3 → windows at 0,1,2 → [3,4,4]
        # buggy range(2): only windows at 0,1 → [3,4]
        result = sliding_window_max([1, 3, 2, 4, 1], 3)
        self.assertEqual(
            result, [3, 4, 4],
            msg=f"Expected [3,4,4] but got {result}; "
                "buggy version omits the last window [2,4,1] whose max is 4",
        )

    def test_result_has_correct_length(self):
        # len=5, k=2 → 4 windows; buggy gives 3
        nums = [5, 1, 3, 2, 4]
        result = sliding_window_max(nums, 2)
        self.assertEqual(
            len(result), 4,
            msg=f"Expected 4 windows but got {len(result)}: {result}; "
                "buggy range(len-k) produces one fewer window",
        )
