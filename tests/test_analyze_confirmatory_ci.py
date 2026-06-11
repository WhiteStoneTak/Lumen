"""Tests for the R2-1 bootstrap-CI back-port in analyze_confirmatory.py.

Confirms: (1) the back-ported CI reproduces the paper's H1/T2 interval
[+0.077, +0.917] exactly when scoped to the 30 confirmatory functions, and
(2) the default (no --with-ci) serialization carries no CI keys, so the frozen
output is unchanged.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from experiment.analyze_confirmatory import (  # noqa: E402
    _bootstrap_ci_rank_biserial,
    run_confirmatory_analyses,
)

CONFIRMATORY_FUNCS = [
    "antidiagonals", "batch_list", "camel_to_snake", "chunk_on_change",
    "count_true_segments", "dense_rank", "equal_width_buckets",
    "find_balanced_spans", "first_index_of_max", "frequency_table",
    "group_and_aggregate", "group_by_key", "longest_plateau",
    "max_subarray_bounds", "merge_intervals", "merge_sorted",
    "peak_valley_indices", "remove_adjacent_dups", "rle_encode", "rotate_list",
    "segments_above_threshold", "sliding_window_max", "sorted_list_intersection",
    "spiral_order", "stable_partition", "strided_windows", "tokenize_arithmetic",
    "top_k_by", "two_sum_sorted_pairs", "welford_running_stats",
]


def _h1_t2(output):
    return next(t for t in output["tests"] if t["hypothesis"] == "H1" and t["task"] == "T2")


class TestBootstrapCIKernel(unittest.TestCase):
    def test_few_nonzero_returns_nan(self):
        lo, hi = _bootstrap_ci_rank_biserial([0.0, 0.0, 1.0])
        self.assertNotEqual(lo, lo)  # nan
        self.assertNotEqual(hi, hi)

    def test_deterministic_across_calls(self):
        diffs = [1.0, -1.0, 2.0, 0.0, 1.0, -2.0, 1.0, 1.0]
        a = _bootstrap_ci_rank_biserial(diffs)
        b = _bootstrap_ci_rank_biserial(diffs)
        self.assertEqual(a, b)  # fresh seeded rng per call


class TestConfirmatoryCIReproduction(unittest.TestCase):
    def test_h1_t2_ci_matches_paper(self):
        out = run_confirmatory_analyses(func_ids=CONFIRMATORY_FUNCS, with_ci=True)
        t = _h1_t2(out)
        # Paper Table: r_rb = +0.581, CI [+0.077, +0.917].
        self.assertAlmostEqual(t["rank_biserial_r"], 0.580952, places=5)
        self.assertAlmostEqual(t["rank_biserial_ci_low"], 0.076923, places=5)
        self.assertAlmostEqual(t["rank_biserial_ci_high"], 0.916667, places=5)

    def test_bootstrap_metadata_present_with_ci(self):
        out = run_confirmatory_analyses(func_ids=CONFIRMATORY_FUNCS, with_ci=True)
        self.assertIn("bootstrap_ci", out)
        self.assertEqual(out["bootstrap_ci"]["seed"], 20260427)
        self.assertEqual(out["bootstrap_ci"]["resamples"], 10000)

    def test_default_output_has_no_ci_keys(self):
        out = run_confirmatory_analyses(func_ids=CONFIRMATORY_FUNCS, with_ci=False)
        self.assertNotIn("bootstrap_ci", out)
        for t in out["tests"]:
            self.assertNotIn("rank_biserial_ci_low", t)
            self.assertNotIn("rank_biserial_ci_high", t)


if __name__ == "__main__":
    unittest.main()
