"""T2 test suite for welford_running_stats.

Correct behaviour: computes running (count, mean, population_variance) using
Welford's online algorithm. Variance at count=1 is 0.0. Population variance
is M2/n (not M2/(n-1)).

Introduced bug (incorrect_variable_reference): the M2 update uses
`delta * delta` instead of `delta * delta2`, inflating M2 for all n > 1.
After the first element the variance is wrong; after n=1 the bug is already
visible since delta != delta2 once mean has been updated.
"""

import unittest
import math
from pathlib import Path


def _load_func(source_path: str):
    import importlib.util
    spec = importlib.util.spec_from_file_location("_wrs_mod", source_path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.welford_running_stats


_DEFAULT_SOURCE = str(
    Path(__file__).resolve().parents[2] / "functions" / "raw"
    / "welford_running_stats.py"
)
_SOURCE = _DEFAULT_SOURCE
welford_running_stats = _load_func(_SOURCE)


class WelfordRunningStatsCorrectBehaviourTests(unittest.TestCase):
    """These tests all pass against the correct source."""

    def test_empty_list(self):
        self.assertEqual(welford_running_stats([]), [])

    def test_single_value(self):
        result = welford_running_stats([5.0])
        self.assertEqual(result, [(1, 5.0, 0.0)])

    def test_docstring_example(self):
        result = welford_running_stats([2.0, 4.0, 6.0])
        self.assertEqual(len(result), 3)
        n1, m1, v1 = result[0]
        self.assertEqual((n1, m1, v1), (1, 2.0, 0.0))
        n2, m2, v2 = result[1]
        self.assertEqual((n2, m2), (2, 3.0))
        self.assertAlmostEqual(v2, 1.0)
        n3, m3, v3 = result[2]
        self.assertEqual((n3, m3), (3, 4.0))
        self.assertAlmostEqual(v3, 8.0 / 3.0)

    def test_constant_sequence_zero_variance(self):
        result = welford_running_stats([7.0, 7.0, 7.0])
        for n, mean, var in result:
            self.assertAlmostEqual(var, 0.0,
                                   msg=f"Constant sequence variance must be 0; got {var} at n={n}")

    def test_count_increments(self):
        result = welford_running_stats([1.0, 2.0, 3.0])
        self.assertEqual([n for n, _, _ in result], [1, 2, 3])

    def test_mean_running_average(self):
        result = welford_running_stats([1.0, 3.0])
        _, m1, _ = result[0]
        _, m2, _ = result[1]
        self.assertAlmostEqual(m1, 1.0)
        self.assertAlmostEqual(m2, 2.0)


class WelfordRunningStatsBugDetectionTests(unittest.TestCase):
    """These tests specifically expose the incorrect_variable_reference bug.

    The bug computes M2 += delta * delta instead of M2 += delta * delta2.
    After the first element, delta is x - old_mean and delta2 is x - new_mean.
    delta != delta2 whenever n > 1, so variance is wrong from step 2 onward.
    At n=1: delta = x - 0 = x, delta2 = x - x = 0 (correct M2=0, variance=0),
    but with the bug: M2 += x*x, giving variance = x^2 instead of 0.
    """

    def test_variance_at_n1_must_be_zero(self):
        # For a single value, population variance is 0 by definition.
        # Buggy: M2 += delta*delta = (2.0-0.0)^2 = 4.0; variance = 4.0/1 = 4.0
        result = welford_running_stats([2.0])
        _, _, v1 = result[0]
        self.assertAlmostEqual(
            v1, 0.0,
            msg=f"Variance at n=1 must be 0.0; buggy uses delta^2 giving {v1}",
        )

    def test_variance_at_n2_correct(self):
        # [2.0, 4.0]: population variance = ((2-3)^2 + (4-3)^2)/2 = 1.0
        result = welford_running_stats([2.0, 4.0])
        _, _, v2 = result[1]
        self.assertAlmostEqual(
            v2, 1.0,
            msg=f"Variance after [2,4] must be 1.0; buggy inflates M2; got {v2}",
        )

    def test_variance_accumulates_correctly(self):
        # [0.0, 10.0]: population variance = 25.0
        result = welford_running_stats([0.0, 10.0])
        _, _, v2 = result[1]
        self.assertAlmostEqual(
            v2, 25.0,
            msg=f"Population variance of [0,10] must be 25.0; got {v2}",
        )

    def test_three_element_variance(self):
        # [2, 4, 6]: pop variance = ((2-4)^2+(4-4)^2+(6-4)^2)/3 = 8/3
        result = welford_running_stats([2.0, 4.0, 6.0])
        _, _, v3 = result[2]
        self.assertAlmostEqual(
            v3, 8.0 / 3.0,
            msg=f"Population variance of [2,4,6] must be 8/3 ≈ {8/3:.4f}; got {v3}",
        )


if __name__ == "__main__":
    unittest.main()
