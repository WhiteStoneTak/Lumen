"""T3 post-transform test suite for rotate_list.

Transform spec (rotate_list.TR01): Change the rotation direction from left to
right. A right rotation by k positions moves the last k elements to the front.
k is taken modulo len(items).

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
    """The function must perform RIGHT rotation (last k elements move to front)."""

    def test_basic_right_rotation(self) -> None:
        # Right by 2: last 2 [4,5] move to front → [4,5,1,2,3]
        # Original left-by-2 returns [3,4,5,1,2]
        result = rotate_list([1, 2, 3, 4, 5], 2)
        self.assertEqual(result, [4, 5, 1, 2, 3])

    def test_right_rotation_by_one(self) -> None:
        # Right by 1: last element [3] moves to front → [3,1,2]
        result = rotate_list([1, 2, 3], 1)
        self.assertEqual(result, [3, 1, 2])

    def test_full_length_rotation_identity(self) -> None:
        # k=3, len=3: k%3=0 → no rotation → [1,2,3]
        result = rotate_list([1, 2, 3], 3)
        self.assertEqual(result, [1, 2, 3])

    def test_empty_returns_empty(self) -> None:
        result = rotate_list([], 3)
        self.assertEqual(result, [])

    def test_k_zero_returns_copy(self) -> None:
        result = rotate_list([1, 2, 3], 0)
        self.assertEqual(result, [1, 2, 3])

    def test_right_differs_from_left(self) -> None:
        # Right-by-2: [4,5,1,2,3]; left-by-2: [3,4,5,1,2]
        result = rotate_list([1, 2, 3, 4, 5], 2)
        self.assertEqual(result, [4, 5, 1, 2, 3])
        self.assertNotEqual(result, [3, 4, 5, 1, 2])

    def test_k_larger_than_length(self) -> None:
        # k=7, len=5: 7%5=2 → right by 2 → [4,5,1,2,3]
        result = rotate_list([1, 2, 3, 4, 5], 7)
        self.assertEqual(result, [4, 5, 1, 2, 3])

    def test_single_element(self) -> None:
        result = rotate_list([7], 3)
        self.assertEqual(result, [7])


class RotateListT3DirectionalTests(unittest.TestCase):
    """Additional cases confirming right-rotation semantics."""

    def test_right_by_one_wraps_last(self) -> None:
        result = rotate_list([10, 20, 30, 40], 1)
        self.assertEqual(result, [40, 10, 20, 30])

    def test_right_by_two_larger_list(self) -> None:
        result = rotate_list([1, 2, 3, 4, 5, 6], 2)
        self.assertEqual(result, [5, 6, 1, 2, 3, 4])

    def test_right_by_three(self) -> None:
        result = rotate_list([1, 2, 3, 4, 5], 3)
        # last 3: [3,4,5] move to front → [3,4,5,1,2]
        self.assertEqual(result, [3, 4, 5, 1, 2])

    def test_two_elements_right_by_one(self) -> None:
        result = rotate_list([1, 2], 1)
        self.assertEqual(result, [2, 1])


if __name__ == "__main__":
    unittest.main()
