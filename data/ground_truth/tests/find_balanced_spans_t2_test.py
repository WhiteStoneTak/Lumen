"""T2 test suite for find_balanced_spans.

Correct behaviour: returns (start, end) pairs for top-level balanced bracket
spans. Nested brackets are not returned separately — only the outermost span.

Introduced bug (missing_boundary_check): the `if depth == 0:` guard before
`span_start = i` is missing. Without it, span_start is overwritten on every
open bracket, including nested ones. For nested input, the reported start is
the last nested open bracket, not the outermost one.
"""

import unittest
from pathlib import Path


def _load_func(source_path: str):
    import importlib.util
    spec = importlib.util.spec_from_file_location("_fbs_mod", source_path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.find_balanced_spans


_DEFAULT_SOURCE = str(
    Path(__file__).resolve().parents[2] / "functions" / "raw" / "find_balanced_spans.py"
)
_SOURCE = _DEFAULT_SOURCE
find_balanced_spans = _load_func(_SOURCE)


class FindBalancedSpansCorrectBehaviourTests(unittest.TestCase):
    """These tests all pass against the correct source."""

    def test_no_brackets_returns_empty(self):
        self.assertEqual(find_balanced_spans("no brackets", "(", ")"), [])

    def test_single_pair(self):
        self.assertEqual(find_balanced_spans("(hello)", "(", ")"), [(0, 6)])

    def test_two_top_level_pairs(self):
        self.assertEqual(find_balanced_spans("(a)(b)", "(", ")"), [(0, 2), (3, 5)])

    def test_deeply_nested_returns_outermost(self):
        self.assertEqual(find_balanced_spans("((()))", "(", ")"), [(0, 5)])

    def test_example_from_docstring(self):
        self.assertEqual(
            find_balanced_spans("a(b(c)d)e(f)", "(", ")"),
            [(1, 7), (9, 11)],
        )


class FindBalancedSpansBugDetectionTests(unittest.TestCase):
    """These tests specifically expose the missing_boundary_check bug.

    The buggy version overwrites span_start on every open bracket, including
    nested ones, so the reported start for a nested span is wrong.
    """

    def test_nested_span_start_is_outermost(self):
        # "a(b(c)d)": outer '(' is at index 1, inner '(' at index 3.
        # buggy: span_start = 3 (last open bracket) -> reports (3, 7) not (1, 7)
        result = find_balanced_spans("a(b(c)d)e(f)", "(", ")")
        self.assertEqual(
            result[0][0], 1,
            msg=f"Outermost span should start at 1 but got start={result[0][0]}; "
                "buggy version overwrites span_start with nested open bracket position",
        )

    def test_nested_span_full_correct(self):
        result = find_balanced_spans("a(b(c)d)e(f)", "(", ")")
        self.assertEqual(
            result, [(1, 7), (9, 11)],
            msg=f"Expected [(1,7),(9,11)] but got {result}",
        )

    def test_double_nested_outermost_span(self):
        # "((()))": outer '(' at 0; buggy span_start becomes 1 then 2
        result = find_balanced_spans("((()))", "(", ")")
        self.assertEqual(
            result, [(0, 5)],
            msg=f"Expected [(0,5)] but got {result}; "
                "buggy version sets span_start to inner bracket position",
        )
