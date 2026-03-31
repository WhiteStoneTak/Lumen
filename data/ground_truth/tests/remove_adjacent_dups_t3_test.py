"""T3 post-transform test suite for remove_adjacent_dups.

Transform spec (remove_adjacent_dups.TR01): Add an optional `key` callable
parameter (default None). When key is not None, comparisons use key(item)
instead of direct value equality. key=None preserves original behaviour.

These tests are run against a model's transformed implementation.
Parse failure and execution failure score 0.0 without running tests.
"""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path


def _load_func(source_path: str):
    spec = importlib.util.spec_from_file_location("_rad_t3_mod", source_path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.remove_adjacent_dups


_DEFAULT_SOURCE = str(
    Path(__file__).resolve().parents[2] / "functions" / "raw" / "remove_adjacent_dups.py"
)
_SOURCE = _DEFAULT_SOURCE
remove_adjacent_dups = _load_func(_SOURCE)


class RemoveAdjacentDupsT3KeyFunctionTests(unittest.TestCase):
    """The transformed function must support a key callable for comparisons."""

    def test_key_abs_collapses_opposite_sign_adjacents(self) -> None:
        # abs(-1)==abs(1)==1, so -1 and 1 are adjacent duplicates under key=abs
        result = remove_adjacent_dups([-1, 1, 2], key=abs)
        self.assertEqual(result, [-1, 2])

    def test_key_lower_collapses_different_case_adjacents(self) -> None:
        result = remove_adjacent_dups(["A", "a", "B"], key=str.lower)
        self.assertEqual(result, ["A", "B"])

    def test_key_mod2_collapses_same_parity_adjacents(self) -> None:
        # 2%2==4%2==0; 3%2==1; 5%2==1
        result = remove_adjacent_dups([2, 4, 3, 5], key=lambda x: x % 2)
        self.assertEqual(result, [2, 3])

    def test_key_preserves_non_adjacent_values(self) -> None:
        # Under key=abs: 1, -2, 1 — no adjacent duplicates
        result = remove_adjacent_dups([1, -2, 1], key=abs)
        self.assertEqual(result, [1, -2, 1])

    def test_key_single_element_unchanged(self) -> None:
        result = remove_adjacent_dups([42], key=abs)
        self.assertEqual(result, [42])

    def test_key_all_same_under_key_reduces_to_one(self) -> None:
        result = remove_adjacent_dups([1, -1, 2, -2], key=abs)
        self.assertEqual(result, [1])

    def test_key_empty_input_returns_empty(self) -> None:
        result = remove_adjacent_dups([], key=abs)
        self.assertEqual(result, [])


class RemoveAdjacentDupsT3OriginalBehaviourPreservedTests(unittest.TestCase):
    """Original behaviour must be preserved when key=None (default)."""

    def test_adjacent_dups_collapsed_default(self) -> None:
        self.assertEqual(
            remove_adjacent_dups([1, 1, 2, 3, 3, 3, 2]),
            [1, 2, 3, 2],
        )

    def test_empty_list_returns_empty(self) -> None:
        self.assertEqual(remove_adjacent_dups([]), [])

    def test_single_element_unchanged(self) -> None:
        self.assertEqual(remove_adjacent_dups([7]), [7])

    def test_no_adjacent_dups_unchanged(self) -> None:
        self.assertEqual(remove_adjacent_dups([1, 2, 3]), [1, 2, 3])

    def test_non_adjacent_dups_preserved(self) -> None:
        self.assertEqual(remove_adjacent_dups([1, 2, 1]), [1, 2, 1])

    def test_all_same_reduces_to_one(self) -> None:
        self.assertEqual(remove_adjacent_dups([5, 5, 5, 5]), [5])


if __name__ == "__main__":
    unittest.main()
