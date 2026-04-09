"""T2 test suite for spiral_order.

Correct behaviour: returns matrix elements in clockwise spiral order
(right, down, left, up, repeat inward). The bottom-row traversal is
guarded by `if top <= bottom:` to avoid re-traversing when only one
row remains.

Introduced bug (missing_boundary_check): the `if top <= bottom:` guard
is absent. When an odd-row-count matrix reduces to a single-row remainder,
the top row is traversed twice (once going right, once again going left),
producing duplicate elements.
"""

import unittest
from pathlib import Path


def _load_func(source_path: str):
    import importlib.util
    spec = importlib.util.spec_from_file_location("_so_mod", source_path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.spiral_order


_DEFAULT_SOURCE = str(
    Path(__file__).resolve().parents[2] / "functions" / "raw" / "spiral_order.py"
)
_SOURCE = _DEFAULT_SOURCE
spiral_order = _load_func(_SOURCE)


class SpiralOrderCorrectBehaviourTests(unittest.TestCase):
    """These tests all pass against the correct source."""

    def test_empty_matrix(self):
        self.assertEqual(spiral_order([]), [])

    def test_single_element(self):
        self.assertEqual(spiral_order([[1]]), [1])

    def test_single_row(self):
        self.assertEqual(spiral_order([[1, 2, 3, 4]]), [1, 2, 3, 4])

    def test_single_column(self):
        self.assertEqual(spiral_order([[1], [2], [3]]), [1, 2, 3])

    def test_3x3_matrix(self):
        self.assertEqual(
            spiral_order([[1, 2, 3], [4, 5, 6], [7, 8, 9]]),
            [1, 2, 3, 6, 9, 8, 7, 4, 5],
        )

    def test_2x2_matrix(self):
        self.assertEqual(spiral_order([[1, 2], [3, 4]]), [1, 2, 4, 3])


class SpiralOrderBugDetectionTests(unittest.TestCase):
    """These tests specifically expose the missing_boundary_check bug.

    Without the `if top <= bottom:` guard, a single remaining row is
    traversed both right (as the top row) and then again left (as the
    bottom row), producing duplicate elements.
    """

    def test_single_row_no_duplicates(self):
        # A 1-row matrix: top=0, bottom=0. After right traversal, top=1 > bottom=0.
        # Buggy: no guard, traverses bottom row again left -> duplicates.
        result = spiral_order([[1, 2, 3]])
        self.assertEqual(
            result, [1, 2, 3],
            msg=f"Expected [1,2,3] but got {result}; "
                "buggy version re-traverses the single row going left",
        )

    def test_3x3_correct_element_count(self):
        matrix = [[1, 2, 3], [4, 5, 6], [7, 8, 9]]
        result = spiral_order(matrix)
        self.assertEqual(
            len(result), 9,
            msg=f"Expected 9 elements but got {len(result)}: {result}; "
                "buggy version produces duplicates for odd-row matrices",
        )

    def test_3x3_no_duplicates(self):
        result = spiral_order([[1, 2, 3], [4, 5, 6], [7, 8, 9]])
        self.assertEqual(
            sorted(result), list(range(1, 10)),
            msg=f"All 9 distinct elements expected; got {result}",
        )

    def test_1x4_row_no_duplicates(self):
        result = spiral_order([[1, 2, 3, 4]])
        self.assertEqual(result, [1, 2, 3, 4],
                         msg=f"Expected [1,2,3,4] but got {result}")
