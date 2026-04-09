"""T2 test suite for frequency_table.

Correct behaviour: returns (value, count, cumulative_fraction) tuples sorted
by value, where cumulative_fraction is the running sum of counts divided by
total (i.e. uses the cumulative variable, not the per-item count).

Introduced bug (incorrect_variable_reference): cumulative_fraction is computed
as `count / total` instead of `cumulative / total`. This gives the per-value
relative frequency instead of the cumulative fraction. All non-final values
have wrong cumulative_fraction.
"""

import unittest
from pathlib import Path


def _load_func(source_path: str):
    import importlib.util
    spec = importlib.util.spec_from_file_location("_ft_mod", source_path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.frequency_table


_DEFAULT_SOURCE = str(
    Path(__file__).resolve().parents[2] / "functions" / "raw" / "frequency_table.py"
)
_SOURCE = _DEFAULT_SOURCE
frequency_table = _load_func(_SOURCE)


class FrequencyTableCorrectBehaviourTests(unittest.TestCase):
    """These tests all pass against the correct source."""

    def test_empty_returns_empty(self):
        self.assertEqual(frequency_table([]), [])

    def test_single_value(self):
        result = frequency_table([42])
        self.assertEqual(result, [(42, 1, 1.0)])

    def test_all_same(self):
        result = frequency_table([3, 3, 3])
        self.assertEqual(result, [(3, 3, 1.0)])

    def test_docstring_example(self):
        result = frequency_table([3, 1, 2, 1, 3, 3])
        self.assertAlmostEqual(result[0][2], 1 / 3)
        self.assertAlmostEqual(result[1][2], 0.5)
        self.assertAlmostEqual(result[2][2], 1.0)

    def test_last_cumulative_fraction_is_one(self):
        result = frequency_table([1, 2, 3])
        self.assertAlmostEqual(result[-1][2], 1.0)


class FrequencyTableBugDetectionTests(unittest.TestCase):
    """These tests specifically expose the incorrect_variable_reference bug.

    The buggy version uses `count / total` instead of `cumulative / total`,
    giving per-item relative frequency instead of cumulative fraction.
    For example, with [3, 1, 2, 1, 3, 3]:
      value=1 (count=2): buggy gives 2/6=0.333, correct gives 2/6=0.333 (same!)
      value=2 (count=1): buggy gives 1/6=0.167, correct gives 3/6=0.5 (different)
    """

    def test_middle_value_cumulative_fraction_is_cumulative(self):
        # [3, 1, 2, 1, 3, 3]: sorted keys: 1(count=2), 2(count=1), 3(count=3)
        # cumulative at value=2: (2+1)/6 = 0.5
        # buggy: 1/6 ~ 0.167
        result = frequency_table([3, 1, 2, 1, 3, 3])
        self.assertAlmostEqual(
            result[1][2], 0.5,
            msg=f"Cumulative fraction for value=2 should be 0.5 but got {result[1][2]}; "
                "buggy version uses count/total=1/6 instead of cumulative/total=3/6",
        )

    def test_first_two_value_cumulative_increases(self):
        # [1, 2]: sorted: 1(count=1, cumfrac=0.5), 2(count=1, cumfrac=1.0)
        # buggy: both give 1/2=0.5; correct gives 0.5 then 1.0
        result = frequency_table([1, 2])
        self.assertAlmostEqual(result[0][2], 0.5)
        self.assertAlmostEqual(
            result[1][2], 1.0,
            msg=f"Cumulative fraction for last value should be 1.0 but got {result[1][2]}; "
                "buggy version also gives 0.5 for the second value",
        )

    def test_cumulative_fractions_are_non_decreasing(self):
        result = frequency_table([3, 1, 2, 1, 3, 3])
        fracs = [row[2] for row in result]
        for i in range(1, len(fracs)):
            self.assertGreaterEqual(
                fracs[i], fracs[i - 1],
                msg=f"Cumulative fractions must be non-decreasing: {fracs}; "
                    "buggy version produces per-item fractions that can be non-monotone",
            )
