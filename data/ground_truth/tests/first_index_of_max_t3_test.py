"""T3 post-transform test suite for first_index_of_max.

Transform spec (first_index_of_max.TR01): Add an optional `default` parameter
with a sentinel default value. When nums is empty and default is provided
(not the sentinel), return default instead of raising ValueError. When nums is
empty and no default is provided, continue to raise ValueError (original
behaviour). All other behaviour is unchanged.

These tests are run against a model's transformed implementation.
Parse failure and execution failure score 0.0 without running tests.
"""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path


def _load_func(source_path: str):
    spec = importlib.util.spec_from_file_location("_fiom_t3_mod", source_path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.first_index_of_max


_DEFAULT_SOURCE = str(
    Path(__file__).resolve().parents[2] / "functions" / "raw" / "first_index_of_max.py"
)
_SOURCE = _DEFAULT_SOURCE
first_index_of_max = _load_func(_SOURCE)


class FirstIndexOfMaxT3DefaultParameterTests(unittest.TestCase):
    """When default is provided, empty input returns default instead of raising."""

    def test_default_minus_one_returned_for_empty(self) -> None:
        result = first_index_of_max([], default=-1)
        self.assertEqual(result, -1)

    def test_default_none_returned_for_empty(self) -> None:
        result = first_index_of_max([], default=None)
        self.assertIsNone(result)

    def test_default_zero_returned_for_empty(self) -> None:
        result = first_index_of_max([], default=0)
        self.assertEqual(result, 0)

    def test_default_not_used_when_list_nonempty(self) -> None:
        # Non-empty list: default is ignored, normal result returned
        result = first_index_of_max([3, 1, 4], default=-1)
        self.assertEqual(result, 2)

    def test_default_string_value_returned_for_empty(self) -> None:
        result = first_index_of_max([], default="not_found")
        self.assertEqual(result, "not_found")


class FirstIndexOfMaxT3OriginalBehaviourPreservedTests(unittest.TestCase):
    """Original behaviour must be preserved: empty input raises, non-empty works normally."""

    def test_empty_list_raises_value_error(self) -> None:
        with self.assertRaises(ValueError):
            first_index_of_max([])

    def test_first_occurrence_of_max_returned(self) -> None:
        self.assertEqual(first_index_of_max([3, 1, 4, 1, 5, 9, 2, 6]), 5)

    def test_first_of_tied_max(self) -> None:
        self.assertEqual(first_index_of_max([5, 5, 5]), 0)

    def test_ascending_list(self) -> None:
        self.assertEqual(first_index_of_max([1, 2, 3]), 2)

    def test_single_element(self) -> None:
        self.assertEqual(first_index_of_max([42]), 0)

    def test_descending_list(self) -> None:
        self.assertEqual(first_index_of_max([9, 5, 3, 1]), 0)


if __name__ == "__main__":
    unittest.main()
