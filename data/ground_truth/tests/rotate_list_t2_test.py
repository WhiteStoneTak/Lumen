"""T2 test suite for rotate_list.

Correct behaviour: returns items rotated *left* by k positions; element at
index k becomes index 0; k is reduced modulo len(items).

Introduced bug (swapped_arguments): line 19 concatenates `items[:k] + items[k:]`
instead of `items[k:] + items[:k]`.  The expression `items[:k] + items[k:]`
always reconstructs the original list in its original order — the function
returns a copy rather than performing any rotation.
"""

import unittest
from pathlib import Path


def _load_func(source_path: str):
    import importlib.util
    spec = importlib.util.spec_from_file_location("_rl_mod", source_path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.rotate_list


_DEFAULT_SOURCE = str(
    Path(__file__).resolve().parents[2] / "functions" / "raw" / "rotate_list.py"
)
_SOURCE = _DEFAULT_SOURCE
rotate_list = _load_func(_SOURCE)


class RotateListCorrectBehaviourTests(unittest.TestCase):
    """These tests all pass against the correct source."""

    def test_empty_returns_empty(self):
        self.assertEqual(rotate_list([], 2), [])

    def test_k_zero_returns_copy(self):
        original = [1, 2, 3]
        result = rotate_list(original, 0)
        self.assertEqual(result, [1, 2, 3])

    def test_k_equals_length_returns_copy(self):
        self.assertEqual(rotate_list([1, 2, 3], 3), [1, 2, 3])

    def test_basic_left_rotation(self):
        self.assertEqual(rotate_list([1, 2, 3, 4, 5], 2), [3, 4, 5, 1, 2])

    def test_rotation_by_one(self):
        self.assertEqual(rotate_list([1, 2, 3], 1), [2, 3, 1])

    def test_k_larger_than_length(self):
        # k=7 mod 5 = 2
        self.assertEqual(rotate_list([1, 2, 3, 4, 5], 7), [3, 4, 5, 1, 2])

    def test_single_element(self):
        self.assertEqual(rotate_list([42], 1), [42])


class RotateListBugDetectionTests(unittest.TestCase):
    """These tests specifically expose the swapped_arguments bug.

    The bug returns the original list order instead of rotating it.
    """

    def test_rotation_changes_order(self):
        # rotate_list([1,2,3,4,5], 2) should be [3,4,5,1,2], not [1,2,3,4,5]
        result = rotate_list([1, 2, 3, 4, 5], 2)
        self.assertEqual(
            result, [3, 4, 5, 1, 2],
            msg=f"Expected [3,4,5,1,2] but got {result}; "
                "buggy version returns original list [1,2,3,4,5]",
        )

    def test_first_element_becomes_element_at_k(self):
        items = [10, 20, 30, 40]
        k = 1
        result = rotate_list(items, k)
        self.assertEqual(
            result[0], items[k],
            msg=f"Expected result[0]={items[k]} but got result[0]={result[0]}; "
                "buggy version leaves items[0]=10 at position 0",
        )
