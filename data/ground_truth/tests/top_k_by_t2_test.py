"""T2 test suite for top_k_by.

Correct behaviour: returns the top-k items sorted by key(item) descending.
When primary keys tie, tiebreak_key(item) ascending is used as secondary key.
When still tied, original order (stable sort) is preserved. k<=0 returns [].

Introduced bug (incorrect_variable_reference): the sort key uses
`key(pair[1])` (ascending) instead of `-key(pair[1])` (descending) as the
primary key, so the function returns the k lowest-valued items rather than
the k highest.
"""

import unittest
from pathlib import Path


def _load_func(source_path: str):
    import importlib.util
    spec = importlib.util.spec_from_file_location("_tkb_mod", source_path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.top_k_by


_DEFAULT_SOURCE = str(
    Path(__file__).resolve().parents[2] / "functions" / "raw" / "top_k_by.py"
)
_SOURCE = _DEFAULT_SOURCE
top_k_by = _load_func(_SOURCE)


class TopKByCorrectBehaviourTests(unittest.TestCase):
    """These tests all pass against the correct source."""

    def test_k_zero_returns_empty(self):
        self.assertEqual(top_k_by([1, 2, 3], 0, key=lambda x: x), [])

    def test_k_negative_returns_empty(self):
        self.assertEqual(top_k_by([1, 2, 3], -1, key=lambda x: x), [])

    def test_docstring_example_top3(self):
        result = top_k_by([3, 1, 4, 1, 5], 3, key=lambda x: x)
        self.assertEqual(result, [5, 4, 3])

    def test_k_larger_than_list(self):
        result = top_k_by([1, 2], 5, key=lambda x: x)
        self.assertEqual(result, [2, 1])

    def test_top1(self):
        result = top_k_by([3, 1, 4, 1, 5, 9, 2, 6], 1, key=lambda x: x)
        self.assertEqual(result, [9])

    def test_tiebreak_key_ascending(self):
        # Ties on length; tiebreak by string value ascending
        result = top_k_by(["b", "a", "c", "a"], 3,
                          key=lambda s: len(s),
                          tiebreak_key=lambda s: s)
        self.assertEqual(result, ["a", "a", "b"])


class TopKByBugDetectionTests(unittest.TestCase):
    """These tests specifically expose the incorrect_variable_reference bug.

    The bug uses key(pair[1]) instead of -key(pair[1]), returning the k
    lowest items instead of the k highest.
    """

    def test_returns_highest_not_lowest(self):
        # Top-3 of [3,1,4,1,5] by identity must be [5,4,3], not [1,1,3]
        result = top_k_by([3, 1, 4, 1, 5], 3, key=lambda x: x)
        self.assertEqual(
            result, [5, 4, 3],
            msg=f"Must return 3 highest values [5,4,3]; "
                f"buggy version returns lowest; got {result}",
        )

    def test_top1_is_maximum(self):
        items = [10, 2, 7, 5]
        result = top_k_by(items, 1, key=lambda x: x)
        self.assertEqual(
            result, [10],
            msg=f"Top-1 must be the maximum (10); buggy returns minimum; got {result}",
        )

    def test_descending_order_in_output(self):
        # Output must be best-to-kth-best (descending)
        result = top_k_by([1, 2, 3, 4, 5], 5, key=lambda x: x)
        self.assertEqual(
            result, [5, 4, 3, 2, 1],
            msg=f"Full sorted result must be descending; got {result}",
        )

    def test_key_by_lambda(self):
        # Top-2 dicts by 'score' descending
        items = [{"name": "a", "score": 3},
                 {"name": "b", "score": 7},
                 {"name": "c", "score": 1}]
        result = top_k_by(items, 2, key=lambda d: d["score"])
        self.assertEqual(
            [d["score"] for d in result], [7, 3],
            msg=f"Top-2 by score should be [7,3]; buggy gives lowest; got {result}",
        )


if __name__ == "__main__":
    unittest.main()
