"""T2 test suite for camel_to_snake.

Correct behaviour: converts camelCase / PascalCase identifiers to snake_case,
including abbreviation handling (e.g. XMLParser -> xml_parser).

Introduced bug (wrong_comparison_operator): the abbreviation-boundary condition
uses `or` instead of `and` in `prev_is_upper or next_is_lower`. This fires
for any uppercase letter followed by a lowercase letter, adding spurious
leading underscores to PascalCase inputs like 'CamelCase'.
"""

import unittest
from pathlib import Path


def _load_func(source_path: str):
    import importlib.util
    spec = importlib.util.spec_from_file_location("_cts_mod", source_path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.camel_to_snake


_DEFAULT_SOURCE = str(
    Path(__file__).resolve().parents[2] / "functions" / "raw" / "camel_to_snake.py"
)
_SOURCE = _DEFAULT_SOURCE
camel_to_snake = _load_func(_SOURCE)


class CamelToSnakeCorrectBehaviourTests(unittest.TestCase):
    """These tests all pass against the correct source."""

    def test_empty_string(self):
        self.assertEqual(camel_to_snake(""), "")

    def test_already_lower(self):
        self.assertEqual(camel_to_snake("hello"), "hello")

    def test_simple_camel(self):
        self.assertEqual(camel_to_snake("camelCase"), "camel_case")

    def test_xml_parser_abbreviation(self):
        self.assertEqual(camel_to_snake("XMLParser"), "xml_parser")

    def test_get_https_response(self):
        self.assertEqual(camel_to_snake("getHTTPSResponse"), "get_https_response")

    def test_single_uppercase(self):
        self.assertEqual(camel_to_snake("A"), "a")


class CamelToSnakeBugDetectionTests(unittest.TestCase):
    """These tests specifically expose the wrong_comparison_operator bug.

    The buggy version uses `prev_is_upper or next_is_lower` instead of `and`,
    causing PascalCase like 'CamelCase' to get a spurious leading underscore
    because 'C' is followed by 'a' (next_is_lower=True) — the elif fires even
    though prev_is_upper is False.
    """

    def test_pascal_case_no_leading_underscore(self):
        # 'C' in 'CamelCase': prev_is_upper=False, next_is_lower=True
        # buggy `or` condition fires -> '_camel_case'
        result = camel_to_snake("CamelCase")
        self.assertEqual(
            result, "camel_case",
            msg=f"Expected 'camel_case' but got '{result}'; "
                "buggy `or` condition adds a spurious leading underscore",
        )

    def test_simple_pascal_no_leading_underscore(self):
        result = camel_to_snake("Hello")
        self.assertEqual(
            result, "hello",
            msg=f"Expected 'hello' but got '{result}'; "
                "buggy `or` condition fires on first uppercase followed by lowercase",
        )

    def test_multi_word_pascal_correct(self):
        result = camel_to_snake("MyVariable")
        self.assertEqual(
            result, "my_variable",
            msg=f"Expected 'my_variable' but got '{result}'",
        )
