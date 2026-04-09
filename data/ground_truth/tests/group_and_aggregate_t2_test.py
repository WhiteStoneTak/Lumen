"""T2 test suite for group_and_aggregate.

Correct behaviour: groups (key, value) pairs and computes per-group count,
sum, min, and max. The min field tracks the running minimum.

Introduced bug (wrong_comparison_operator): the min-update condition uses
`value > entry["min"]` (greater-than) instead of `value < entry["min"]`
(less-than). This makes 'min' track the running maximum instead of minimum.
"""

import unittest
from pathlib import Path


def _load_func(source_path: str):
    import importlib.util
    spec = importlib.util.spec_from_file_location("_gaa_mod", source_path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.group_and_aggregate


_DEFAULT_SOURCE = str(
    Path(__file__).resolve().parents[2] / "functions" / "raw" / "group_and_aggregate.py"
)
_SOURCE = _DEFAULT_SOURCE
group_and_aggregate = _load_func(_SOURCE)


class GroupAndAggregateCorrectBehaviourTests(unittest.TestCase):
    """These tests all pass against the correct source."""

    def test_empty_returns_empty_dict(self):
        self.assertEqual(group_and_aggregate([]), {})

    def test_single_pair(self):
        result = group_and_aggregate([("a", 5)])
        self.assertEqual(result, {"a": {"count": 1, "sum": 5, "min": 5, "max": 5}})

    def test_two_same_keys(self):
        result = group_and_aggregate([("x", 5), ("x", 5)])
        self.assertEqual(result, {"x": {"count": 2, "sum": 10, "min": 5, "max": 5}})

    def test_docstring_example(self):
        result = group_and_aggregate([("a", 3), ("b", 1), ("a", 7)])
        self.assertEqual(result["a"], {"count": 2, "sum": 10, "min": 3, "max": 7})
        self.assertEqual(result["b"], {"count": 1, "sum": 1, "min": 1, "max": 1})

    def test_min_is_actual_minimum(self):
        result = group_and_aggregate([("k", 10), ("k", 3), ("k", 7)])
        self.assertEqual(result["k"]["min"], 3)


class GroupAndAggregateBugDetectionTests(unittest.TestCase):
    """These tests specifically expose the wrong_comparison_operator bug.

    The buggy version uses `value > entry["min"]` to update min, so it
    updates whenever value is larger than the current min — tracking the
    maximum, not the minimum.
    """

    def test_min_field_is_minimum_not_maximum(self):
        # ("a", 3), ("a", 7): min should be 3, max should be 7
        # buggy: min gets updated when 7 > 3 (true), so min becomes 7
        result = group_and_aggregate([("a", 3), ("a", 7)])
        self.assertEqual(
            result["a"]["min"], 3,
            msg=f"min should be 3 but got {result['a']['min']}; "
                "buggy version uses > instead of <, tracking maximum in 'min' field",
        )

    def test_min_with_decreasing_sequence(self):
        # values 10, 5, 1: min = 1, max = 10
        result = group_and_aggregate([("k", 10), ("k", 5), ("k", 1)])
        self.assertEqual(
            result["k"]["min"], 1,
            msg=f"min should be 1 but got {result['k']['min']}",
        )
        self.assertEqual(result["k"]["max"], 10)

    def test_min_differs_from_max_when_values_differ(self):
        result = group_and_aggregate([("x", 1), ("x", 100)])
        self.assertNotEqual(
            result["x"]["min"], result["x"]["max"],
            msg=f"min and max should differ: {result['x']}; "
                "buggy version sets both to 100",
        )
        self.assertEqual(result["x"]["min"], 1)
        self.assertEqual(result["x"]["max"], 100)
