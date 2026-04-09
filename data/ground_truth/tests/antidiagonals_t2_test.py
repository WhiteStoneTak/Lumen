"""T2 test suite for antidiagonals.

Correct behaviour: returns all antidiagonals of a 2D matrix as a list of
lists. Elements within each antidiagonal are in row-ascending order.

Introduced bug (off_by_one): r_start uses `max(0, d - cols)` instead of
`max(0, d - cols + 1)`. For diagonals where d >= cols, the starting row is
one too low, causing the first element to reference a negative column index,
producing wrong or out-of-range values in those antidiagonals.
"""

import unittest
from pathlib import Path


def _load_func(source_path: str):
    import importlib.util
    spec = importlib.util.spec_from_file_location("_ad_mod", source_path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.antidiagonals


_DEFAULT_SOURCE = str(
    Path(__file__).resolve().parents[2] / "functions" / "raw" / "antidiagonals.py"
)
_SOURCE = _DEFAULT_SOURCE
antidiagonals = _load_func(_SOURCE)


class AntidiagonalsCorrectBehaviourTests(unittest.TestCase):
    """These tests all pass against the correct source."""

    def test_empty_matrix_returns_empty(self):
        self.assertEqual(antidiagonals([]), [])

    def test_single_element(self):
        self.assertEqual(antidiagonals([[42]]), [[42]])

    def test_2x2_matrix(self):
        self.assertEqual(antidiagonals([[1, 2], [3, 4]]), [[1], [2, 3], [4]])

    def test_1x3_row(self):
        self.assertEqual(antidiagonals([[1, 2, 3]]), [[1], [2], [3]])

    def test_3x1_column(self):
        self.assertEqual(antidiagonals([[1], [2], [3]]), [[1], [2], [3]])

    def test_3x3_matrix(self):
        expected = [[1], [2, 4], [3, 5, 7], [6, 8], [9]]
        self.assertEqual(antidiagonals([[1, 2, 3], [4, 5, 6], [7, 8, 9]]), expected)


class AntidiagonalsBugDetectionTests(unittest.TestCase):
    """These tests specifically expose the off_by_one r_start bug.

    The bug computes r_start = max(0, d - cols) instead of max(0, d - cols + 1).
    For d >= cols, this gives a row that is one too low, meaning c = d - r
    yields a negative column index — the element accessed is wrong.
    """

    def test_2x2_last_diagonal_correct(self):
        # 2x2: diagonal d=2 (value 4) — buggy r_start=max(0,2-2)=0 instead of 1
        # buggy: matrix[0][2] would be out-of-range or wrong element
        result = antidiagonals([[1, 2], [3, 4]])
        self.assertEqual(
            result[-1], [4],
            msg=f"Last antidiagonal should be [4] but got {result[-1]}; "
                "buggy version uses wrong r_start for lower-left diagonals",
        )

    def test_3x3_lower_left_diagonals_correct(self):
        # 3x3 matrix: diagonals d=3 ([6,8]) and d=4 ([9]) use r_start > 0
        result = antidiagonals([[1, 2, 3], [4, 5, 6], [7, 8, 9]])
        self.assertEqual(
            result[3], [6, 8],
            msg=f"Antidiagonal d=3 should be [6, 8] but got {result[3]}; "
                "buggy r_start shifts row too low causing wrong column access",
        )
        self.assertEqual(
            result[4], [9],
            msg=f"Antidiagonal d=4 should be [9] but got {result[4]}; "
                "buggy r_start shifts row too low",
        )

    def test_element_count_matches_matrix_size(self):
        matrix = [[1, 2, 3], [4, 5, 6], [7, 8, 9]]
        result = antidiagonals(matrix)
        total = sum(len(d) for d in result)
        self.assertEqual(
            total, 9,
            msg=f"All 9 elements should appear across antidiagonals, got {total}; "
                "buggy version may duplicate or skip elements",
        )
