"""T3 post-transform test suite for count_vowels.

Transform spec (count_vowels.TR01): The function must also count 'y' and 'Y'
as vowels (in addition to a, e, i, o, u). The counting must remain
case-insensitive.

These tests are run against a model's transformed implementation.
Parse failure and execution failure score 0.0 without running tests.
"""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path


def _load_func(source_path: str):
    spec = importlib.util.spec_from_file_location("_cv_t3_mod", source_path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.count_vowels


_DEFAULT_SOURCE = str(
    Path(__file__).resolve().parents[2] / "functions" / "raw" / "count_vowels.py"
)
_SOURCE = _DEFAULT_SOURCE
count_vowels = _load_func(_SOURCE)


class CountVowelsT3YAsVowelTests(unittest.TestCase):
    """'y' and 'Y' must now be counted as vowels."""

    def test_lowercase_y_counted(self) -> None:
        # The original does not count y. The transformed version must.
        result = count_vowels("y")
        self.assertEqual(result, 1)

    def test_uppercase_y_counted(self) -> None:
        result = count_vowels("Y")
        self.assertEqual(result, 1)

    def test_gym_has_one_y_vowel(self) -> None:
        # 'g', 'm' are not vowels; 'y' is now a vowel
        result = count_vowels("gym")
        self.assertEqual(result, 1)

    def test_rhythm_has_y(self) -> None:
        # 'r', 'h', 't', 'h', 'm' are consonants; 'y' is now a vowel
        result = count_vowels("rhythm")
        self.assertEqual(result, 1)

    def test_yay_has_three_vowels(self) -> None:
        # 'y', 'a', 'y' -> all three are vowels under the new definition
        result = count_vowels("yay")
        self.assertEqual(result, 3)

    def test_case_insensitive_y(self) -> None:
        # 'Y', 'a', 'Y' -> all three are vowels
        result = count_vowels("YaY")
        self.assertEqual(result, 3)


class CountVowelsT3OriginalBehaviourPreservedTests(unittest.TestCase):
    """Original behavior for a, e, i, o, u must be preserved."""

    def test_empty_string_still_zero(self) -> None:
        self.assertEqual(count_vowels(""), 0)

    def test_no_vowels_still_zero(self) -> None:
        # 'b', 'c', 'd' are consonants; no y
        self.assertEqual(count_vowels("bcd"), 0)

    def test_standard_vowels_still_counted(self) -> None:
        self.assertEqual(count_vowels("aeiou"), 5)

    def test_hello_still_two_vowels(self) -> None:
        # e, o
        self.assertEqual(count_vowels("hello"), 2)

    def test_non_alpha_still_ignored(self) -> None:
        self.assertEqual(count_vowels("h3ll0!"), 0)


if __name__ == "__main__":
    unittest.main()
