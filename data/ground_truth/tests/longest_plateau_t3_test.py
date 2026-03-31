"""T3 post-transform test suite for longest_plateau.

Transform spec (longest_plateau.TR01): Change the tie-breaking policy so that
when multiple runs tie for the maximum length, the LAST (latest-start) longest
plateau is returned instead of the first. All other behaviour is unchanged.

These tests are run against a model's transformed implementation.
Parse failure and execution failure score 0.0 without running tests.
"""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path


def _load_func(source_path: str):
    spec = importlib.util.spec_from_file_location("_lp_t3_mod", source_path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.longest_plateau


_DEFAULT_SOURCE = str(
    Path(__file__).resolve().parents[2] / "functions" / "raw" / "longest_plateau.py"
)
_SOURCE = _DEFAULT_SOURCE
longest_plateau = _load_func(_SOURCE)


class LongestPlateauT3LastStartTests(unittest.TestCase):
    """Transformed function must return LAST longest plateau on ties."""

    def test_last_plateau_wins_on_two_way_tie(self) -> None:
        # [3,3,1,2,2]: runs of length 2 at (0,1,3) and (3,4,2). Last-start wins.
        result = longest_plateau([3, 3, 1, 2, 2])
        self.assertEqual(result, (3, 4, 2))

    def test_last_plateau_wins_on_three_way_tie(self) -> None:
        # [1,1,2,2,3,3]: three length-2 runs; last-start is (4,5,3)
        result = longest_plateau([1, 1, 2, 2, 3, 3])
        self.assertEqual(result, (4, 5, 3))

    def test_original_first_start_behavior_is_gone(self) -> None:
        # Original would return (0,1,3) for [3,3,1,2,2]; transform must NOT
        result = longest_plateau([3, 3, 1, 2, 2])
        self.assertNotEqual(result[0], 0)

    def test_unique_longest_unaffected(self) -> None:
        # No tie: [1,2,2,2,3] only longest run is (1,3,2)
        result = longest_plateau([1, 2, 2, 2, 3])
        self.assertEqual(result, (1, 3, 2))

    def test_later_longer_run_still_wins(self) -> None:
        # [1,1,2,2,2]: run of 2 then run of 3; longer always wins regardless
        result = longest_plateau([1, 1, 2, 2, 2])
        self.assertEqual(result, (2, 4, 2))

    def test_empty_returns_sentinel(self) -> None:
        result = longest_plateau([])
        self.assertEqual(result, (-1, -1, None))

    def test_single_element(self) -> None:
        result = longest_plateau([5])
        self.assertEqual(result, (0, 0, 5))


class LongestPlateauT3StructureTests(unittest.TestCase):
    """Structural and preserved-behaviour tests."""

    def test_return_type_is_tuple(self) -> None:
        result = longest_plateau([1, 1, 2])
        self.assertIsInstance(result, tuple)
        self.assertEqual(len(result), 3)

    def test_all_same_single_run(self) -> None:
        # Only one run, no tie possible
        result = longest_plateau([7, 7, 7])
        self.assertEqual(result, (0, 2, 7))

    def test_last_in_list_of_length_2_ties(self) -> None:
        # [5,5,6,6,7,7,8,8]: four length-2 runs; last-start is (6,7,8)
        result = longest_plateau([5, 5, 6, 6, 7, 7, 8, 8])
        self.assertEqual(result, (6, 7, 8))


if __name__ == "__main__":
    unittest.main()
