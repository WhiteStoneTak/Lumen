"""T2 test suite for batch_list.

Correct behaviour: items is split into consecutive non-overlapping batches of
exactly batch_size elements, with the last batch possibly smaller.

Introduced bug (off_by_one): line 16 uses step `batch_size + 1` instead of
`batch_size` in the range call.  This advances the window start one position
beyond a full batch on each iteration, silently dropping exactly one element
between every pair of consecutive batches.
"""

import unittest
from pathlib import Path


def _load_func(source_path: str):
    import importlib.util
    spec = importlib.util.spec_from_file_location("_bl_mod", source_path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.batch_list


_DEFAULT_SOURCE = str(
    Path(__file__).resolve().parents[2] / "functions" / "raw" / "batch_list.py"
)
_SOURCE = _DEFAULT_SOURCE
batch_list = _load_func(_SOURCE)


class BatchListCorrectBehaviourTests(unittest.TestCase):
    """These tests all pass against the correct source."""

    def test_empty_returns_empty(self):
        self.assertEqual(batch_list([], 3), [])

    def test_batch_size_zero_returns_empty(self):
        self.assertEqual(batch_list([1, 2, 3], 0), [])

    def test_batch_size_negative_returns_empty(self):
        self.assertEqual(batch_list([1, 2], -1), [])

    def test_exact_multiple(self):
        self.assertEqual(batch_list([1, 2, 3, 4], 2), [[1, 2], [3, 4]])

    def test_non_multiple_last_batch_smaller(self):
        self.assertEqual(batch_list([1, 2, 3, 4, 5], 2), [[1, 2], [3, 4], [5]])

    def test_batch_size_equals_length(self):
        self.assertEqual(batch_list([1, 2, 3], 3), [[1, 2, 3]])

    def test_batch_size_larger_than_length(self):
        self.assertEqual(batch_list([1, 2], 5), [[1, 2]])


class BatchListBugDetectionTests(unittest.TestCase):
    """These tests specifically expose the off_by_one step bug.

    The bug uses step batch_size+1 instead of batch_size, dropping one element
    between every pair of consecutive batches.
    """

    def test_six_items_batched_by_two(self):
        # range(0, 6, 3) → i=0,3 → [[1,2],[4,5]] — element 3 and 6 dropped
        result = batch_list([1, 2, 3, 4, 5, 6], 2)
        self.assertEqual(
            result, [[1, 2], [3, 4], [5, 6]],
            msg=f"Expected [[1,2],[3,4],[5,6]] but got {result}; "
                "buggy version uses step=3 so elements 3 and 6 are skipped",
        )

    def test_five_items_batched_by_two_preserves_all(self):
        # All 5 elements must appear across the batches
        result = batch_list([10, 20, 30, 40, 50], 2)
        flat = [x for batch in result for x in batch]
        self.assertEqual(
            flat, [10, 20, 30, 40, 50],
            msg=f"Flattened batches {flat} != [10,20,30,40,50]; buggy step drops element 30",
        )
