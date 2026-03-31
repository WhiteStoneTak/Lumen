"""T3 post-transform test suite for group_and_aggregate.

Transform spec (group_and_aggregate.TR01): Change aggregation fields from
{count, sum, min, max} to {count, mean, range} where mean = sum/count (float)
and range = max - min. The 'sum', 'min', 'max' keys must not appear in output.

These tests are run against a model's transformed implementation.
Parse failure and execution failure score 0.0 without running tests.
"""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path


def _load_func(source_path: str):
    spec = importlib.util.spec_from_file_location("_ga_t3_mod", source_path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.group_and_aggregate


_DEFAULT_SOURCE = str(
    Path(__file__).resolve().parents[2] / "functions" / "raw" / "group_and_aggregate.py"
)
_SOURCE = _DEFAULT_SOURCE
group_and_aggregate = _load_func(_SOURCE)


class GroupAndAggregateT3MeanRangeTests(unittest.TestCase):
    """Transformed function must return {count, mean, range} per group."""

    def test_basic_count_mean_range(self) -> None:
        result = group_and_aggregate([("a", 3), ("b", 1), ("a", 7)])
        self.assertIn("a", result)
        self.assertIn("b", result)
        self.assertEqual(result["a"]["count"], 2)
        self.assertAlmostEqual(result["a"]["mean"], 5.0)
        self.assertEqual(result["a"]["range"], 4)
        self.assertEqual(result["b"]["count"], 1)
        self.assertAlmostEqual(result["b"]["mean"], 1.0)
        self.assertEqual(result["b"]["range"], 0)

    def test_no_sum_key_in_result(self) -> None:
        result = group_and_aggregate([("x", 1), ("x", 3)])
        for val in result.values():
            self.assertNotIn("sum", val)

    def test_no_min_key_in_result(self) -> None:
        result = group_and_aggregate([("x", 1), ("x", 3)])
        for val in result.values():
            self.assertNotIn("min", val)

    def test_no_max_key_in_result(self) -> None:
        result = group_and_aggregate([("x", 1), ("x", 3)])
        for val in result.values():
            self.assertNotIn("max", val)

    def test_mean_is_float(self) -> None:
        result = group_and_aggregate([("a", 2), ("a", 4)])
        self.assertIsInstance(result["a"]["mean"], float)

    def test_range_is_max_minus_min(self) -> None:
        result = group_and_aggregate([("a", 1), ("a", 5), ("a", 3)])
        self.assertEqual(result["a"]["range"], 4)  # 5 - 1

    def test_empty_returns_empty_dict(self) -> None:
        result = group_and_aggregate([])
        self.assertEqual(result, {})

    def test_single_group_single_value(self) -> None:
        result = group_and_aggregate([("x", 10)])
        self.assertEqual(result["x"]["count"], 1)
        self.assertAlmostEqual(result["x"]["mean"], 10.0)
        self.assertEqual(result["x"]["range"], 0)


class GroupAndAggregateT3StructureTests(unittest.TestCase):
    """Structure validation and preserved behaviours."""

    def test_return_type_is_dict(self) -> None:
        result = group_and_aggregate([("a", 1)])
        self.assertIsInstance(result, dict)

    def test_keys_in_insertion_order(self) -> None:
        result = group_and_aggregate([("b", 1), ("a", 2), ("c", 3)])
        self.assertEqual(list(result.keys()), ["b", "a", "c"])

    def test_count_correct_for_multivalue(self) -> None:
        result = group_and_aggregate([("z", 1), ("z", 2), ("z", 3)])
        self.assertEqual(result["z"]["count"], 3)
        self.assertAlmostEqual(result["z"]["mean"], 2.0)
        self.assertEqual(result["z"]["range"], 2)


if __name__ == "__main__":
    unittest.main()
