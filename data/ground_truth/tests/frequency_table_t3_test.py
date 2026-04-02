"""T3 post-transform test suite for frequency_table.

Transform spec (frequency_table.TR01): Change sort order from ascending value
to descending count (most frequent first). For equal counts, use ascending
value as tiebreaker. Cumulative fractions are recomputed in the new sorted order.

These tests are run against a model's transformed implementation.
Parse failure and execution failure score 0.0 without running tests.
"""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path


def _load_func(source_path: str):
    spec = importlib.util.spec_from_file_location("_ft_t3_mod", source_path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.frequency_table


_DEFAULT_SOURCE = str(
    Path(__file__).resolve().parents[2] / "functions" / "raw" / "frequency_table.py"
)
_SOURCE = _DEFAULT_SOURCE
frequency_table = _load_func(_SOURCE)


class FrequencyTableT3CountDescTests(unittest.TestCase):
    """Transformed function must sort rows by descending count."""

    def test_most_frequent_first(self) -> None:
        # [1,1,1,2,2,3]: count(1)=3, count(2)=2, count(3)=1
        # First row must be value=1 (highest count)
        result = frequency_table([1, 1, 1, 2, 2, 3])
        self.assertEqual(result[0][0], 1)
        self.assertEqual(result[0][1], 3)

    def test_return_order_by_count_desc(self) -> None:
        result = frequency_table([1, 1, 1, 2, 2, 3])
        counts = [row[1] for row in result]
        self.assertEqual(counts, sorted(counts, reverse=True))

    def test_tie_count_sorted_by_value_asc(self) -> None:
        # [1, 2, 1, 2, 3]: count(1)=2, count(2)=2, count(3)=1
        # Tie at count=2: value 1 before value 2
        result = frequency_table([1, 2, 1, 2, 3])
        self.assertEqual(result[0][0], 1)
        self.assertEqual(result[1][0], 2)

    def test_cumulative_fraction_last_row_is_one(self) -> None:
        # Last row's cumulative fraction must be 1.0
        result = frequency_table([1, 1, 1, 2, 2, 3])
        self.assertAlmostEqual(result[-1][2], 1.0)

    def test_cumulative_fraction_recomputed_in_new_order(self) -> None:
        # [1,1,1,2,2,3]: sorted by count desc: (1,3), (2,2), (3,1)
        # cumulative fractions: 3/6=0.5, 5/6≈0.833, 6/6=1.0
        result = frequency_table([1, 1, 1, 2, 2, 3])
        self.assertAlmostEqual(result[0][2], 0.5)
        self.assertAlmostEqual(result[1][2], 5 / 6)
        self.assertAlmostEqual(result[2][2], 1.0)

    def test_not_sorted_by_value(self) -> None:
        # When freq-sort != value-sort, result must be freq-sorted
        # [3,3,3,1,1,2]: value sort: (1,2,...), freq sort: (3,3,...)
        result = frequency_table([3, 3, 3, 1, 1, 2])
        self.assertEqual(result[0][0], 3)  # value 3 has count 3


class FrequencyTableT3EdgeCaseTests(unittest.TestCase):
    """Edge cases for descending-count sort."""

    def test_empty_returns_empty(self) -> None:
        result = frequency_table([])
        self.assertEqual(result, [])

    def test_single_value(self) -> None:
        result = frequency_table([5])
        self.assertEqual(result, [(5, 1, 1.0)])

    def test_all_distinct_sorted_by_value_tiebreak(self) -> None:
        # All count=1: tiebreaker is ascending value
        result = frequency_table([3, 1, 2])
        values = [row[0] for row in result]
        self.assertEqual(values, sorted(values))


if __name__ == "__main__":
    unittest.main()
