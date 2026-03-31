"""T3 post-transform test suite for remove_adjacent_dups.

Transform spec (remove_adjacent_dups.TR01): Change the return type from
`list` to `tuple`. Return `(result, removed_count)` where `result` is the
deduplicated list and `removed_count` is the total number of elements removed.

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


class RemoveAdjacentDupsT3TupleReturnTests(unittest.TestCase):
    """The transformed function must return (result_list, removed_count) tuple."""

    def test_basic_returns_tuple(self) -> None:
        # [1,1,2,3,3,3,2]: len=7, result=[1,2,3,2] len=4, removed=3
        result = remove_adjacent_dups([1, 1, 2, 3, 3, 3, 2])
        self.assertEqual(result, ([1, 2, 3, 2], 3))

    def test_empty_returns_tuple_zero(self) -> None:
        result = remove_adjacent_dups([])
        self.assertEqual(result, ([], 0))

    def test_single_returns_tuple_zero(self) -> None:
        result = remove_adjacent_dups([7])
        self.assertEqual(result, ([7], 0))

    def test_removed_count_all_same(self) -> None:
        # [5,5,5,5]: len=4, result=[5] len=1, removed=3
        result = remove_adjacent_dups([5, 5, 5, 5])
        self.assertEqual(result, ([5], 3))

    def test_removed_count_no_dups(self) -> None:
        # [1,2,3]: no adjacent dups, removed=0
        result = remove_adjacent_dups([1, 2, 3])
        self.assertEqual(result, ([1, 2, 3], 0))

    def test_type_is_tuple(self) -> None:
        result = remove_adjacent_dups([1, 1, 2])
        self.assertIsInstance(result, tuple)
        self.assertEqual(len(result), 2)

    def test_first_element_is_list(self) -> None:
        result = remove_adjacent_dups([1, 1, 2])
        self.assertIsInstance(result[0], list)
        self.assertEqual(result[0], [1, 2])

    def test_second_element_is_int(self) -> None:
        result = remove_adjacent_dups([1, 1, 2])
        self.assertIsInstance(result[1], int)
        self.assertEqual(result[1], 1)


class RemoveAdjacentDupsT3DeduplicationPreservedTests(unittest.TestCase):
    """The deduplication logic (which items remain) must be correct in result[0]."""

    def test_result_list_collapses_adjacents(self) -> None:
        result = remove_adjacent_dups([1, 1, 2, 3, 3, 3, 2])
        self.assertEqual(result[0], [1, 2, 3, 2])

    def test_result_list_empty_input(self) -> None:
        result = remove_adjacent_dups([])
        self.assertEqual(result[0], [])

    def test_result_list_no_adjacent_dups(self) -> None:
        result = remove_adjacent_dups([1, 2, 3])
        self.assertEqual(result[0], [1, 2, 3])

    def test_result_list_preserves_non_adjacent(self) -> None:
        # [1,2,1]: no adjacent dups, all 3 preserved
        result = remove_adjacent_dups([1, 2, 1])
        self.assertEqual(result[0], [1, 2, 1])


if __name__ == "__main__":
    unittest.main()
