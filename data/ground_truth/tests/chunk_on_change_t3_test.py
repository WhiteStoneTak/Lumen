"""T3 post-transform test suite for chunk_on_change.

Transform spec (chunk_on_change.TR01): Change output from a list of chunks
(sublists of values) to a list of (key, chunk) tuples, where key is the result
of applying the key function to the first element of each chunk.

These tests are run against a model's transformed implementation.
Parse failure and execution failure score 0.0 without running tests.
"""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path


def _load_func(source_path: str):
    spec = importlib.util.spec_from_file_location("_coc_t3_mod", source_path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.chunk_on_change


_DEFAULT_SOURCE = str(
    Path(__file__).resolve().parents[2] / "functions" / "raw" / "chunk_on_change.py"
)
_SOURCE = _DEFAULT_SOURCE
chunk_on_change = _load_func(_SOURCE)


class ChunkOnChangeT3TupleOutputTests(unittest.TestCase):
    """Transformed function must return (key, chunk) tuples."""

    def test_basic_returns_key_chunk_tuples(self) -> None:
        # Default key (identity): [(1, [1, 1]), (2, [2]), (3, [3, 3])]
        result = chunk_on_change([1, 1, 2, 3, 3])
        self.assertEqual(result, [(1, [1, 1]), (2, [2]), (3, [3, 3])])

    def test_result_is_list_of_tuples(self) -> None:
        result = chunk_on_change([1, 1, 2])
        self.assertIsInstance(result, list)
        for item in result:
            self.assertIsInstance(item, tuple)
            self.assertEqual(len(item), 2)

    def test_key_is_first_element_of_chunk(self) -> None:
        # Key function: first letter of string
        result = chunk_on_change(["ab", "ac", "b", "bc"], key=lambda s: s[0])
        # First tuple key should be 'a', second 'b'
        self.assertEqual(result[0][0], "a")
        self.assertEqual(result[1][0], "b")

    def test_chunk_is_list(self) -> None:
        result = chunk_on_change([1, 1, 2])
        for key, chunk in result:
            self.assertIsInstance(chunk, list)

    def test_not_raw_list_of_lists(self) -> None:
        # Original returns [[1, 1], [2], [3, 3]]; transformed must NOT
        result = chunk_on_change([1, 1, 2, 3, 3])
        # The result should not be a list whose first element is a list
        self.assertNotIsInstance(result[0], list)

    def test_with_explicit_key_function(self) -> None:
        # key=lambda x: x % 2 groups by parity
        result = chunk_on_change([2, 4, 3, 5, 6], key=lambda x: x % 2)
        # [2,4] → key 0; [3,5] → key 1; [6] → key 0
        self.assertEqual(result, [(0, [2, 4]), (1, [3, 5]), (0, [6])])


class ChunkOnChangeT3EdgeCaseTests(unittest.TestCase):
    """Edge cases for (key, chunk) tuple output."""

    def test_empty_input(self) -> None:
        result = chunk_on_change([])
        self.assertEqual(result, [])

    def test_single_element(self) -> None:
        result = chunk_on_change([42])
        self.assertEqual(result, [(42, [42])])

    def test_no_repeated_elements(self) -> None:
        result = chunk_on_change([1, 2, 3])
        self.assertEqual(result, [(1, [1]), (2, [2]), (3, [3])])


if __name__ == "__main__":
    unittest.main()
