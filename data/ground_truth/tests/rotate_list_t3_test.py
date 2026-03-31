"""T3 post-transform test suite for rotate_list.

Transform spec (rotate_list.TR01): Add an optional `right` parameter (default
False). When right=True, rotate the list right by k positions (last k elements
become the first). When right=False, behaviour is identical to the original
function (left rotation). In both directions k is taken modulo len(items).

These tests are run against a model's transformed implementation.
Parse failure and execution failure score 0.0 without running tests.
"""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path


def _load_func(source_path: str):
    spec = importlib.util.spec_from_file_location("_rl_t3_mod", source_path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.rotate_list


_DEFAULT_SOURCE = str(
    Path(__file__).resolve().parents[2] / "functions" / "raw" / "rotate_list.py"
)
_SOURCE = _DEFAULT_SOURCE
rotate_list = _load_func(_SOURCE)


class RotateListT3RightRotationTests(unittest.TestCase):
    """When right=True, the list is rotated right by k positions."""

    def test_right_rotate_basic(self) -> None:
        # Right by 2: last 2 elements [4,5] move to front → [4,5,1,2,3]
        result = rotate_list([1, 2, 3, 4, 5], 2, right=True)
        self.assertEqual(result, [4, 5, 1, 2, 3])

    def test_right_rotate_by_one(self) -> None:
        result = rotate_list([1, 2, 3], 1, right=True)
        self.assertEqual(result, [3, 1, 2])

    def test_right_rotate_full_length_is_identity(self) -> None:
        result = rotate_list([1, 2, 3], 3, right=True)
        self.assertEqual(result, [1, 2, 3])

    def test_right_rotate_mod_applied(self) -> None:
        # k=5 for length-5 list → k%5=0 → no rotation
        result = rotate_list([1, 2, 3, 4, 5], 5, right=True)
        self.assertEqual(result, [1, 2, 3, 4, 5])

    def test_right_rotate_empty_list(self) -> None:
        result = rotate_list([], 3, right=True)
        self.assertEqual(result, [])

    def test_right_rotate_is_inverse_of_left(self) -> None:
        # right-rotate by k and then left-rotate by k should give original
        items = [1, 2, 3, 4, 5]
        after_right = rotate_list(items, 2, right=True)
        back = rotate_list(after_right, 2, right=False)
        self.assertEqual(back, items)

    def test_right_rotate_k_larger_than_length(self) -> None:
        # k=7 mod 5=2: right rotate by 2 → [4,5,1,2,3]
        result = rotate_list([1, 2, 3, 4, 5], 7, right=True)
        self.assertEqual(result, [4, 5, 1, 2, 3])


class RotateListT3OriginalBehaviourPreservedTests(unittest.TestCase):
    """Original left-rotation behaviour must be preserved with right=False."""

    def test_left_rotate_basic(self) -> None:
        self.assertEqual(rotate_list([1, 2, 3, 4, 5], 2), [3, 4, 5, 1, 2])

    def test_left_rotate_full_length_is_identity(self) -> None:
        self.assertEqual(rotate_list([1, 2, 3], 3), [1, 2, 3])

    def test_left_rotate_by_one(self) -> None:
        self.assertEqual(rotate_list([1, 2, 3], 1), [2, 3, 1])

    def test_empty_list_returns_empty(self) -> None:
        self.assertEqual(rotate_list([], 5), [])

    def test_k_zero_returns_copy(self) -> None:
        original = [1, 2, 3]
        result = rotate_list(original, 0)
        self.assertEqual(result, original)

    def test_k_larger_than_length(self) -> None:
        self.assertEqual(rotate_list([1, 2, 3, 4, 5], 7), [3, 4, 5, 1, 2])


if __name__ == "__main__":
    unittest.main()
