"""T3 post-transform test suite for find_balanced_spans.

Transform spec (find_balanced_spans.TR01): Change to return ALL balanced spans
including nested ones, instead of only the outermost spans. Every matching
bracket pair at any nesting depth appears as a (start, end) tuple. Results
are ordered by start index ascending.

These tests are run against a model's transformed implementation.
Parse failure and execution failure score 0.0 without running tests.
"""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path


def _load_func(source_path: str):
    spec = importlib.util.spec_from_file_location("_fbs_t3_mod", source_path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.find_balanced_spans


_DEFAULT_SOURCE = str(
    Path(__file__).resolve().parents[2] / "functions" / "raw" / "find_balanced_spans.py"
)
_SOURCE = _DEFAULT_SOURCE
find_balanced_spans = _load_func(_SOURCE)


class FindBalancedSpansT3AllSpansTests(unittest.TestCase):
    """Transformed function must return ALL spans including nested ones."""

    def test_nested_returns_all_three_spans(self) -> None:
        # '((()))': three nested spans [(0,5), (1,4), (2,3)]
        # Original returns only [(0, 5)]; transformed must return all three
        result = find_balanced_spans("((()))", "(", ")")
        self.assertEqual(result, [(0, 5), (1, 4), (2, 3)])

    def test_sequential_both_returned(self) -> None:
        # '()()': no nesting; both outer spans returned
        result = find_balanced_spans("()()", "(", ")")
        self.assertEqual(result, [(0, 1), (2, 3)])

    def test_nested_inside_sequential(self) -> None:
        # '(())()': inner span (1,2) must appear; result [(0,3),(1,2),(4,5)]
        result = find_balanced_spans("(())()", "(", ")")
        self.assertEqual(result, [(0, 3), (1, 2), (4, 5)])

    def test_two_levels_nesting(self) -> None:
        # 'a(b(c)d)e': outer (1,7), inner (3,5)
        result = find_balanced_spans("a(b(c)d)e", "(", ")")
        self.assertEqual(result, [(1, 7), (3, 5)])

    def test_count_exceeds_original(self) -> None:
        # For nested input, transformed result has more spans than original
        result = find_balanced_spans("((()))", "(", ")")
        self.assertGreater(len(result), 1)

    def test_sorted_by_start_index(self) -> None:
        result = find_balanced_spans("((()))", "(", ")")
        starts = [s for s, e in result]
        self.assertEqual(starts, sorted(starts))


class FindBalancedSpansT3EdgeCaseTests(unittest.TestCase):
    """Edge cases for all-spans output."""

    def test_empty_string_returns_empty(self) -> None:
        result = find_balanced_spans("", "(", ")")
        self.assertEqual(result, [])

    def test_no_brackets_returns_empty(self) -> None:
        result = find_balanced_spans("abc", "(", ")")
        self.assertEqual(result, [])

    def test_single_pair(self) -> None:
        result = find_balanced_spans("(x)", "(", ")")
        self.assertEqual(result, [(0, 2)])


if __name__ == "__main__":
    unittest.main()
