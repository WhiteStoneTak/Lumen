"""T2 test suite for count_vowels.

Correct behavior: count_vowels(s) returns the count of vowel characters (a e i o u)
in s, case-insensitively.
Introduced bug (off_by_one): line 9 uses `count += 2` instead of `count += 1`,
doubling the contribution of every vowel.

Run against the correct source:  python -m unittest data/ground_truth/tests/count_vowels_t2_test.py
Run against the buggy source:    the count tests fail for strings with any vowels.
"""

import sys
import unittest
from pathlib import Path


def _load_func(source_path: str):
    import importlib.util

    spec = importlib.util.spec_from_file_location("_cv_mod", source_path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.count_vowels


_DEFAULT_SOURCE = str(
    Path(__file__).resolve().parents[2] / "functions" / "raw" / "count_vowels.py"
)
_SOURCE = _DEFAULT_SOURCE
count_vowels = _load_func(_SOURCE)


class CountVowelsCorrectBehaviourTests(unittest.TestCase):
    """These tests all pass against the correct source."""

    def test_empty_string_returns_zero(self) -> None:
        self.assertEqual(count_vowels(""), 0)

    def test_no_vowels_returns_zero(self) -> None:
        self.assertEqual(count_vowels("bcd"), 0)

    def test_single_lowercase_vowel(self) -> None:
        # BUG TARGET: buggy version returns 2 instead of 1.
        self.assertEqual(count_vowels("a"), 1)

    def test_single_uppercase_vowel(self) -> None:
        # BUG TARGET: buggy version returns 2 instead of 1.
        self.assertEqual(count_vowels("A"), 1)

    def test_all_five_vowels_lowercase(self) -> None:
        # BUG TARGET: buggy version returns 10 instead of 5.
        self.assertEqual(count_vowels("aeiou"), 5)

    def test_mixed_word(self) -> None:
        # "hello" has 2 vowels: e, o.
        # BUG TARGET: buggy version returns 4 instead of 2.
        self.assertEqual(count_vowels("hello"), 2)

    def test_non_alpha_characters_ignored(self) -> None:
        self.assertEqual(count_vowels("h3ll0!"), 0)

    def test_case_insensitive_mixed(self) -> None:
        # "AeIoU" has 5 vowels.
        self.assertEqual(count_vowels("AeIoU"), 5)

    def test_consonants_not_counted(self) -> None:
        self.assertEqual(count_vowels("rhythm"), 0)


class CountVowelsBugDetectionTests(unittest.TestCase):
    """Directly expose the off_by_one bug (count += 2 instead of count += 1)."""

    def test_single_vowel_not_doubled(self) -> None:
        result = count_vowels("e")
        self.assertEqual(result, 1, msg=f"Expected 1 but got {result}; buggy version returns 2")

    def test_two_vowels_not_doubled(self) -> None:
        result = count_vowels("ai")
        self.assertEqual(result, 2, msg=f"Expected 2 but got {result}; buggy version returns 4")


if __name__ == "__main__":
    unittest.main()
