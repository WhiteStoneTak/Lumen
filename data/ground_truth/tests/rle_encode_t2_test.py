"""T2 test suite for rle_encode.

Correct behaviour: consecutive equal values are collapsed into (value, count)
pairs; non-consecutive duplicates produce separate tuples; order is preserved.

Introduced bug (incorrect_variable_reference): line 22 assigns
`current = items[-1]` instead of `current = item`.  When a run boundary is
detected, the tracker is reset to the *last element of the original input*
rather than the element that started the new run.  This causes intermediate
run values to be merged into or dropped from the final tuple.
"""

import unittest
from pathlib import Path


def _load_func(source_path: str):
    import importlib.util
    spec = importlib.util.spec_from_file_location("_rle_mod", source_path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.rle_encode


_DEFAULT_SOURCE = str(
    Path(__file__).resolve().parents[2] / "functions" / "raw" / "rle_encode.py"
)
_SOURCE = _DEFAULT_SOURCE
rle_encode = _load_func(_SOURCE)


class RleEncodeCorrectBehaviourTests(unittest.TestCase):
    """These tests all pass against the correct source."""

    def test_empty_returns_empty(self):
        self.assertEqual(rle_encode([]), [])

    def test_single_element(self):
        self.assertEqual(rle_encode([7]), [(7, 1)])

    def test_all_same(self):
        self.assertEqual(rle_encode([2, 2, 2]), [(2, 3)])

    def test_all_distinct(self):
        self.assertEqual(rle_encode([1, 2, 3]), [(1, 1), (2, 1), (3, 1)])

    def test_mixed_runs(self):
        self.assertEqual(rle_encode([1, 1, 2, 3, 3]), [(1, 2), (2, 1), (3, 2)])

    def test_non_adjacent_same_value(self):
        self.assertEqual(rle_encode([1, 2, 1]), [(1, 1), (2, 1), (1, 1)])

    def test_strings(self):
        self.assertEqual(rle_encode(["a", "a", "b", "a"]), [("a", 2), ("b", 1), ("a", 1)])


class RleEncodeBugDetectionTests(unittest.TestCase):
    """These tests specifically expose the incorrect_variable_reference bug.

    The bug sets current=items[-1] on run transition; intermediate values are lost.
    """

    def test_intermediate_value_is_encoded(self):
        # items=[1,1,2,3,3], items[-1]=3
        # buggy: after (1,2) is appended, current=3 not 2 → (3,3) not (2,1),(3,2)
        result = rle_encode([1, 1, 2, 3, 3])
        self.assertEqual(
            result, [(1, 2), (2, 1), (3, 2)],
            msg=f"Expected [(1,2),(2,1),(3,2)] but got {result}; "
                "buggy version skips the (2,1) tuple because current becomes items[-1]=3",
        )

    def test_three_distinct_runs_all_present(self):
        # items=[10,10,20,30], items[-1]=30
        # buggy: after (10,2), current=30; 20!=30 so append (30,1) then 30==30 count→2
        # → [(10,2),(30,1),(30,2)] which is wrong and doesn't match
        result = rle_encode([10, 10, 20, 30])
        self.assertEqual(
            result, [(10, 2), (20, 1), (30, 1)],
            msg=f"Expected [(10,2),(20,1),(30,1)] but got {result}; "
                "buggy version loses the (20,1) run",
        )
