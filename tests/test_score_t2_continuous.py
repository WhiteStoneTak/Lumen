"""Unit tests for src/experiment/score_t2_continuous.py (R1-1 / W-04).

unittest.TestCase to match the project convention (see test_score_t2.py).
Covers: exact match -> 1.0, disjoint-and-far -> 0.0, partial-overlap
monotonicity, quoted-code recovery, and unmappable-output handling.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from experiment.score_t2_continuous import (  # noqa: E402
    PROX_WEIGHT,
    ast_location_distance_score,
    continuous_location_score,
    extract_predicted_lines,
)


class TestContinuousLocationScore(unittest.TestCase):
    FUNC_LEN = 40  # proximity window W = max(4, 40//4) = 10

    def test_exact_single_line_match_is_one(self):
        self.assertEqual(
            continuous_location_score({29}, 29, 29, self.FUNC_LEN), 1.0
        )

    def test_exact_span_match_is_one(self):
        self.assertEqual(
            continuous_location_score({10, 11, 12}, 10, 12, self.FUNC_LEN), 1.0
        )

    def test_disjoint_and_far_is_zero(self):
        # distance 20 > window 10 -> ramp clamps to 0.0
        self.assertEqual(
            continuous_location_score({5}, 29, 29, self.FUNC_LEN), 0.0
        )

    def test_partial_overlap_is_iou(self):
        # predicted {10,11}, truth {10,11,12}: inter=2, union=3 -> 2/3
        self.assertAlmostEqual(
            continuous_location_score({10, 11}, 10, 12, self.FUNC_LEN), 2 / 3
        )

    def test_overlap_monotonic_in_precision(self):
        # Same single-line hit; fewer spurious extra lines -> higher IoU.
        truth_s, truth_e = 20, 20
        tight = continuous_location_score({20}, truth_s, truth_e, self.FUNC_LEN)
        loose = continuous_location_score({20, 21, 22}, truth_s, truth_e, self.FUNC_LEN)
        looser = continuous_location_score(
            {20, 21, 22, 23, 24}, truth_s, truth_e, self.FUNC_LEN
        )
        self.assertGreater(tight, loose)
        self.assertGreater(loose, looser)

    def test_proximity_monotonic_in_distance(self):
        # No overlap; closer predictions score higher, all below any overlap.
        near = continuous_location_score({28}, 30, 30, self.FUNC_LEN)  # d=2
        far = continuous_location_score({25}, 30, 30, self.FUNC_LEN)   # d=5
        self.assertGreater(near, far)
        self.assertGreater(far, 0.0)
        self.assertLessEqual(near, PROX_WEIGHT)

    def test_adjacent_proximity_below_minimal_overlap(self):
        # Adjacent (d=1) near-miss must not beat a real (if thin) overlap.
        adjacent = continuous_location_score({29}, 30, 30, self.FUNC_LEN)  # d=1
        # Minimal overlap: huge predicted span barely touching truth.
        big_span = set(range(30, 30 + 50))
        overlap = continuous_location_score(big_span, 30, 30, 200)
        self.assertLessEqual(adjacent, PROX_WEIGHT)
        self.assertGreater(overlap, 0.0)

    def test_unmappable_empty_prediction_is_zero(self):
        self.assertEqual(
            continuous_location_score(set(), 10, 10, self.FUNC_LEN), 0.0
        )


class TestExtractPredictedLines(unittest.TestCase):
    SOURCE = [
        "def f(x):",                                  # 1
        "    total = 0",                              # 2
        "    for i in range(len(x)):",                # 3
        "        total += x[i] * 2",                  # 4  (buggy line)
        "    return total",                           # 5
    ]

    def test_explicit_line_number(self):
        pred = extract_predicted_lines("The bug is on line 4.", self.SOURCE)
        self.assertIn(4, pred)

    def test_bare_hash_and_L_reference(self):
        self.assertIn(4, extract_predicted_lines("see #4", self.SOURCE))
        self.assertIn(4, extract_predicted_lines("at L4 here", self.SOURCE))

    def test_quoted_code_recovery(self):
        # No line number; the buggy line is quoted in a fenced block.
        resp = "The defect:\n```python\ntotal += x[i] * 2\n```\nshould be *1."
        pred = extract_predicted_lines(resp, self.SOURCE)
        self.assertIn(4, pred)

    def test_inline_backtick_recovery(self):
        pred = extract_predicted_lines("`total += x[i] * 2` is wrong", self.SOURCE)
        self.assertIn(4, pred)

    def test_out_of_range_line_ignored(self):
        self.assertEqual(extract_predicted_lines("line 999", self.SOURCE), set())

    def test_trivial_short_fragment_ignored(self):
        # "x" is too short to be a reliable code anchor.
        self.assertEqual(extract_predicted_lines("`x`", self.SOURCE), set())

    def test_unmappable_prose_is_empty(self):
        pred = extract_predicted_lines(
            "There is an arithmetic mistake somewhere.", self.SOURCE
        )
        self.assertEqual(pred, set())


class TestAstLocationDistanceScore(unittest.TestCase):
    SOURCE = (
        "def f(x):\n"           # 1
        "    total = 0\n"       # 2
        "    for i in range(len(x)):\n"   # 3
        "        total += x[i] * 2\n"     # 4  (buggy line)
        "    if total > 10:\n"  # 5
        "        return total\n"  # 6
        "    return total\n"    # 7
    )

    def test_exact_node_is_one(self):
        # Prediction on the truth line -> same node -> 1.0
        self.assertEqual(
            ast_location_distance_score({4}, 4, 4, self.SOURCE), 1.0
        )

    def test_empty_prediction_is_zero(self):
        self.assertEqual(
            ast_location_distance_score(set(), 4, 4, self.SOURCE), 0.0
        )

    def test_closer_node_scores_higher(self):
        # Sibling in the same loop (line 4 truth) should beat an unrelated
        # statement outside the loop body.
        near = ast_location_distance_score({3}, 4, 4, self.SOURCE)  # for-loop header
        far = ast_location_distance_score({7}, 4, 4, self.SOURCE)   # trailing return
        self.assertGreaterEqual(near, far)
        self.assertGreaterEqual(near, 0.0)
        self.assertLessEqual(near, 1.0)

    def test_in_range_and_bounded(self):
        for pred in ({2}, {3}, {5}, {6}, {7}):
            s = ast_location_distance_score(pred, 4, 4, self.SOURCE)
            self.assertGreaterEqual(s, 0.0)
            self.assertLessEqual(s, 1.0)

    def test_unparseable_source_is_none(self):
        self.assertIsNone(
            ast_location_distance_score({1}, 1, 1, "def f(:\n  broken")
        )


if __name__ == "__main__":
    unittest.main()
