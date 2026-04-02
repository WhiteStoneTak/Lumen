"""T3 post-transform test suite for camel_to_snake.

Transform spec (camel_to_snake.TR01): Change the return type from a snake_case
string to a list of the individual word segments extracted during conversion.
'camelCase' -> ['camel', 'case']. All segments are lowercase with no
underscores. Empty string input returns [].

These tests are run against a model's transformed implementation.
Parse failure and execution failure score 0.0 without running tests.
"""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path


def _load_func(source_path: str):
    spec = importlib.util.spec_from_file_location("_cts_t3_mod", source_path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.camel_to_snake


_DEFAULT_SOURCE = str(
    Path(__file__).resolve().parents[2] / "functions" / "raw" / "camel_to_snake.py"
)
_SOURCE = _DEFAULT_SOURCE
camel_to_snake = _load_func(_SOURCE)


class CamelToSnakeT3SegmentListTests(unittest.TestCase):
    """Transformed function must return a list of lowercase word segments."""

    def test_basic_returns_list(self) -> None:
        result = camel_to_snake("camelCase")
        self.assertEqual(result, ["camel", "case"])

    def test_result_is_list_not_string(self) -> None:
        result = camel_to_snake("camelCase")
        self.assertIsInstance(result, list)
        self.assertNotIsInstance(result, str)

    def test_three_words(self) -> None:
        result = camel_to_snake("myVariableName")
        self.assertEqual(result, ["my", "variable", "name"])

    def test_acronym_is_single_segment(self) -> None:
        # 'XMLParser' -> ['xml', 'parser']
        result = camel_to_snake("XMLParser")
        self.assertEqual(result, ["xml", "parser"])

    def test_no_underscores_in_segments(self) -> None:
        result = camel_to_snake("myVariableName")
        for segment in result:
            self.assertNotIn("_", segment)

    def test_all_lowercase_input(self) -> None:
        result = camel_to_snake("hello")
        self.assertEqual(result, ["hello"])

    def test_multi_acronym(self) -> None:
        # 'getHTTPSResponse' -> ['get', 'https', 'response']
        result = camel_to_snake("getHTTPSResponse")
        self.assertEqual(result, ["get", "https", "response"])


class CamelToSnakeT3EdgeCaseTests(unittest.TestCase):
    """Edge cases for segment list output."""

    def test_empty_returns_empty_list(self) -> None:
        result = camel_to_snake("")
        self.assertEqual(result, [])

    def test_pascal_case(self) -> None:
        # 'PascalCase' -> ['pascal', 'case']
        result = camel_to_snake("PascalCase")
        self.assertEqual(result, ["pascal", "case"])

    def test_segments_all_lowercase(self) -> None:
        result = camel_to_snake("XMLParser")
        for segment in result:
            self.assertEqual(segment, segment.lower())


if __name__ == "__main__":
    unittest.main()
