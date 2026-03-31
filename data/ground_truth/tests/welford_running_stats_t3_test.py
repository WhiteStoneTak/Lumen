"""T3 post-transform test suite for welford_running_stats.

Transform spec (welford_running_stats.TR01): Change from population variance
(M2 / n) to sample variance (M2 / (n - 1)) for n > 1. For n = 1, variance
remains 0.0. All other behaviour unchanged.

These tests are run against a model's transformed implementation.
Parse failure and execution failure score 0.0 without running tests.
"""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path


def _load_func(source_path: str):
    spec = importlib.util.spec_from_file_location("_wrs_t3_mod", source_path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.welford_running_stats


_DEFAULT_SOURCE = str(
    Path(__file__).resolve().parents[2] / "functions" / "raw" / "welford_running_stats.py"
)
_SOURCE = _DEFAULT_SOURCE
welford_running_stats = _load_func(_SOURCE)


class WelfordRunningStatsT3SampleVarTests(unittest.TestCase):
    """Transformed function must use sample variance (M2 / (n-1)) for n > 1."""

    def test_sample_variance_at_n2(self) -> None:
        # [2.0, 4.0]: at n=2: M2=2, sample_var = 2/(2-1) = 2.0
        # Population var would be 2/2 = 1.0
        result = welford_running_stats([2.0, 4.0])
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0], (1, 2.0, 0.0))
        self.assertAlmostEqual(result[1][2], 2.0)

    def test_not_population_variance(self) -> None:
        # Population variance for [2.0, 4.0] is 1.0; sample must be 2.0
        result = welford_running_stats([2.0, 4.0])
        self.assertNotAlmostEqual(result[1][2], 1.0)
        self.assertAlmostEqual(result[1][2], 2.0)

    def test_variance_at_n1_is_zero(self) -> None:
        result = welford_running_stats([5.0])
        self.assertEqual(result, [(1, 5.0, 0.0)])

    def test_sample_variance_three_values(self) -> None:
        # [2.0, 4.0, 6.0]:
        # n=1: (1, 2.0, 0.0)
        # n=2: M2=2, sample_var=2/1=2.0 → (2, 3.0, 2.0)
        # n=3: M2=8, sample_var=8/2=4.0 → (3, 4.0, 4.0)
        result = welford_running_stats([2.0, 4.0, 6.0])
        self.assertEqual(len(result), 3)
        self.assertEqual(result[0], (1, 2.0, 0.0))
        self.assertAlmostEqual(result[1][2], 2.0)
        self.assertAlmostEqual(result[2][2], 4.0)

    def test_mean_unchanged(self) -> None:
        # Mean should still be computed correctly
        result = welford_running_stats([2.0, 4.0, 6.0])
        self.assertAlmostEqual(result[2][1], 4.0)

    def test_empty_returns_empty(self) -> None:
        result = welford_running_stats([])
        self.assertEqual(result, [])

    def test_single_value_full_tuple(self) -> None:
        result = welford_running_stats([10.0])
        self.assertEqual(result, [(1, 10.0, 0.0)])


class WelfordRunningStatsT3StructureTests(unittest.TestCase):
    """Structural invariants that must still hold."""

    def test_return_type_is_list(self) -> None:
        result = welford_running_stats([1.0, 2.0])
        self.assertIsInstance(result, list)

    def test_elements_are_tuples(self) -> None:
        result = welford_running_stats([1.0, 2.0, 3.0])
        for item in result:
            self.assertIsInstance(item, tuple)
            self.assertEqual(len(item), 3)

    def test_count_is_correct(self) -> None:
        result = welford_running_stats([1.0, 2.0, 3.0])
        for i, (count, mean, var) in enumerate(result):
            self.assertEqual(count, i + 1)

    def test_variance_non_negative(self) -> None:
        result = welford_running_stats([3.0, 1.0, 4.0, 1.0, 5.0])
        for count, mean, var in result:
            self.assertGreaterEqual(var, 0.0)


if __name__ == "__main__":
    unittest.main()
