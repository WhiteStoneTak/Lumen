"""T3 post-transform test suite for antidiagonals.

Transform spec (antidiagonals.TR01): Reverse the traversal direction within
each anti-diagonal. Instead of top-right to bottom-left (increasing row),
collect elements from bottom-left to top-right (decreasing row). The outer
list order (which diagonal) is unchanged; only the inner element order is
reversed.

These tests are run against a model's transformed implementation.
Parse failure and execution failure score 0.0 without running tests.
"""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path


def _load_func(source_path: str):
    spec = importlib.util.spec_from_file_location("_ad_t3_mod", source_path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.antidiagonals


_DEFAULT_SOURCE = str(
    Path(__file__).resolve().parents[2] / "functions" / "raw" / "antidiagonals.py"
)
_SOURCE = _DEFAULT_SOURCE
antidiagonals = _load_func(_SOURCE)


class AntidiagonalsT3ReversedInnerTests(unittest.TestCase):
    """Transformed function must reverse element order within each diagonal."""

    def test_2x2_inner_reversed(self) -> None:
        # Original: [[1], [2, 3], [4]]
        # Reversed inner: [[1], [3, 2], [4]]
        result = antidiagonals([[1, 2], [3, 4]])
        self.assertEqual(result, [[1], [3, 2], [4]])

    def test_3x3_middle_diagonals_reversed(self) -> None:
        # antidiagonals([[1,2,3],[4,5,6],[7,8,9]])
        # Original: [[1], [2,4], [3,5,7], [6,8], [9]]
        # Reversed: [[1], [4,2], [7,5,3], [8,6], [9]]
        result = antidiagonals([[1, 2, 3], [4, 5, 6], [7, 8, 9]])
        self.assertEqual(result, [[1], [4, 2], [7, 5, 3], [8, 6], [9]])

    def test_inner_order_differs_from_original(self) -> None:
        # For a 2x2 matrix with distinct values, a multi-element diagonal
        # must differ from original top-right-to-bottom-left order
        result = antidiagonals([[1, 2], [3, 4]])
        # Original second diagonal is [2, 3]; transformed must be [3, 2]
        self.assertEqual(result[1], [3, 2])
        self.assertNotEqual(result[1], [2, 3])

    def test_number_of_diagonals_unchanged(self) -> None:
        # Transform does not change how many diagonals there are
        mat = [[1, 2, 3], [4, 5, 6]]
        result = antidiagonals(mat)
        # 2 rows + 3 cols - 1 = 4 diagonals
        self.assertEqual(len(result), 4)

    def test_2x3_reversed_inner(self) -> None:
        # [[1,2,3],[4,5,6]]
        # Original: [[1], [2,4], [3,5], [6]]
        # Reversed inner: [[1], [4,2], [5,3], [6]]
        result = antidiagonals([[1, 2, 3], [4, 5, 6]])
        self.assertEqual(result, [[1], [4, 2], [5, 3], [6]])


class AntidiagonalsT3EdgeCaseTests(unittest.TestCase):
    """Edge cases for reversed-inner antidiagonals."""

    def test_single_row_unchanged(self) -> None:
        # Single element per diagonal: reversing has no effect
        result = antidiagonals([[1, 2, 3]])
        self.assertEqual(result, [[1], [2], [3]])

    def test_single_column_unchanged(self) -> None:
        result = antidiagonals([[1], [2], [3]])
        self.assertEqual(result, [[1], [2], [3]])

    def test_empty_matrix(self) -> None:
        result = antidiagonals([])
        self.assertEqual(result, [])


if __name__ == "__main__":
    unittest.main()
