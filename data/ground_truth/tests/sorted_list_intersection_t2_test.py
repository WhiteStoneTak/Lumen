"""T2 test suite for sorted_list_intersection.

Correct behaviour: multiset intersection of two sorted lists. Each value
appears min(count_in_a, count_in_b) times. Both pointers i and j are
advanced after a match.

Introduced bug (missing_boundary_check): after a match, only `i` is advanced;
`j` is not incremented. This allows the same b[j] to match multiple elements
from a, producing too many copies in the result.
"""

import unittest
from pathlib import Path


def _load_func(source_path: str):
    import importlib.util
    spec = importlib.util.spec_from_file_location("_sli_mod", source_path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.sorted_list_intersection


_DEFAULT_SOURCE = str(
    Path(__file__).resolve().parents[2] / "functions" / "raw" / "sorted_list_intersection.py"
)
_SOURCE = _DEFAULT_SOURCE
sorted_list_intersection = _load_func(_SOURCE)


class SortedListIntersectionCorrectBehaviourTests(unittest.TestCase):
    """These tests all pass against the correct source."""

    def test_empty_a_returns_empty(self):
        self.assertEqual(sorted_list_intersection([], [1, 2]), [])

    def test_empty_b_returns_empty(self):
        self.assertEqual(sorted_list_intersection([1, 2], []), [])

    def test_no_common_elements(self):
        self.assertEqual(sorted_list_intersection([1, 2, 3], [4, 5, 6]), [])

    def test_docstring_example(self):
        self.assertEqual(
            sorted_list_intersection([1, 2, 2, 3], [2, 2, 3, 4]),
            [2, 2, 3],
        )

    def test_single_common_element(self):
        self.assertEqual(sorted_list_intersection([1, 2, 3], [2, 4]), [2])


class SortedListIntersectionBugDetectionTests(unittest.TestCase):
    """These tests specifically expose the missing j += 1 bug.

    The buggy version keeps j fixed after a match, so b[j] can match
    every remaining equal element in a. With [2,2] and [2,2], the correct
    result is [2,2] but the bug produces [2,2,2,2].
    """

    def test_repeated_elements_correct_count(self):
        # a=[2,2], b=[2,2]: min count is 2, so result should be [2,2]
        # buggy: j stays at 0; a[0]=2 matches b[0]=2 (j fixed), a[1]=2 matches
        # b[0]=2 again -> [2, 2, 2, 2] (but actually j is still 0)
        # Wait: after matching a[0], i becomes 1; b[j=0] still 2;
        # a[1]=2 == b[0]=2 -> appends again -> [2,2] then i=2, loop ends.
        # Actually with [2,2] vs [2,2]: i=0,j=0 match append, i=1; a[1]=b[0]=2 append, i=2 -> [2,2]
        # The real trigger: [2,2] vs [2]: should give [2], but buggy gives [2,2]
        result = sorted_list_intersection([2, 2], [2])
        self.assertEqual(
            result, [2],
            msg=f"Expected [2] but got {result}; "
                "buggy version matches b[0]=2 twice because j is never advanced",
        )

    def test_two_copies_in_b_capped_by_a(self):
        # a=[2], b=[2,2]: correct result [2], buggy also [2] (i exhausted first)
        result = sorted_list_intersection([2], [2, 2])
        self.assertEqual(result, [2])

    def test_more_in_a_than_b_capped_correctly(self):
        # a=[1,1,1], b=[1,1]: result should be [1,1]
        # buggy: after first match i=1, j stays 0; a[1]=b[0] match i=2,j=0;
        # a[2]=b[0] match i=3, loop ends -> [1,1,1] (too many)
        result = sorted_list_intersection([1, 1, 1], [1, 1])
        self.assertEqual(
            result, [1, 1],
            msg=f"Expected [1,1] but got {result}; "
                "buggy version returns [1,1,1] because j never advances past b's copies",
        )
