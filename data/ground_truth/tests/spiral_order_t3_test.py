"""T3 post-transform test suite for spiral_order.

Transform spec (spiral_order.TR01): Change from clockwise to counter-clockwise
spiral. Counter-clockwise: start top-left, go DOWN the left column, then RIGHT
along the bottom row, then UP the right column, then LEFT along the top row,
then repeat inward.

These tests are run against a model's transformed implementation.
Parse failure and execution failure score 0.0 without running tests.
"""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path


def _load_func(source_path: str):
    spec = importlib.util.spec_from_file_location("_so_t3_mod", source_path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.spiral_order


_DEFAULT_SOURCE = str(
    Path(__file__).resolve().parents[2] / "functions" / "raw" / "spiral_order.py"
)
_SOURCE = _DEFAULT_SOURCE
spiral_order = _load_func(_SOURCE)


class SpiralOrderT3CounterClockwiseTests(unittest.TestCase):
    """Transformed function must traverse in counter-clockwise order."""

    def test_3x3_counter_clockwise(self) -> None:
        # CCW: down-left col, right-bottom row, up-right col, left-top row, center
        # Down col0: 1,4,7 → Right row2 cols1-2: 8,9 → Up col2 rows1-0: 6,3 → Left row0 col1: 2 → center: 5
        result = spiral_order([[1, 2, 3], [4, 5, 6], [7, 8, 9]])
        self.assertEqual(result, [1, 4, 7, 8, 9, 6, 3, 2, 5])

    def test_not_clockwise(self) -> None:
        # Clockwise 3x3 is [1,2,3,6,9,8,7,4,5]; CCW must differ
        result = spiral_order([[1, 2, 3], [4, 5, 6], [7, 8, 9]])
        self.assertNotEqual(result, [1, 2, 3, 6, 9, 8, 7, 4, 5])

    def test_2x2_counter_clockwise(self) -> None:
        # Down col0: 1,3 → Right row1 col1: 4 → Up col1 row0: 2 → done
        result = spiral_order([[1, 2], [3, 4]])
        self.assertEqual(result, [1, 3, 4, 2])

    def test_single_row_ccw(self) -> None:
        # Single row: down gives first element only, then right rest
        # Down col0 row0: 1 → Right row0 cols1-3: 2,3,4 → nothing else
        result = spiral_order([[1, 2, 3, 4]])
        self.assertEqual(result, [1, 2, 3, 4])

    def test_single_col_ccw(self) -> None:
        # Single col: down gives all, nothing else
        result = spiral_order([[1], [2], [3]])
        self.assertEqual(result, [1, 2, 3])

    def test_empty_returns_empty(self) -> None:
        result = spiral_order([])
        self.assertEqual(result, [])

    def test_single_element(self) -> None:
        result = spiral_order([[5]])
        self.assertEqual(result, [5])


class SpiralOrderT3PreservationTests(unittest.TestCase):
    """Structural invariants that must still hold."""

    def test_all_elements_included(self) -> None:
        matrix = [[1, 2, 3], [4, 5, 6], [7, 8, 9]]
        result = spiral_order(matrix)
        self.assertEqual(sorted(result), list(range(1, 10)))

    def test_correct_length(self) -> None:
        matrix = [[1, 2, 3, 4], [5, 6, 7, 8]]
        result = spiral_order(matrix)
        self.assertEqual(len(result), 8)

    def test_4x4_starts_with_left_col(self) -> None:
        # CCW starts by going DOWN the left column: first 4 elements are col 0
        matrix = [
            [1,  2,  3,  4],
            [5,  6,  7,  8],
            [9,  10, 11, 12],
            [13, 14, 15, 16],
        ]
        result = spiral_order(matrix)
        # First 4 in CCW: down left col = 1,5,9,13
        self.assertEqual(result[:4], [1, 5, 9, 13])


if __name__ == "__main__":
    unittest.main()
