"""Unit + integration tests for src/experiment/analyze_exploratory.py.

Uses unittest.TestCase to match the project's existing test convention
(see tests/test_score_t2.py preamble). pytest can also discover and run
these classes without modification.
"""

from __future__ import annotations

import json
import math
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from experiment.analyze_exploratory import (  # noqa: E402
    LUMEN_SCHEMA,
    FRAMING_DISCLAIMER,
    EXPLORATORY_HYPOTHESES_E,
    HYPOTHESES_H,
    _bootstrap_ci_rank_biserial,
    _build_paired_diffs_aggregated,
    _build_paired_diffs_single_model,
    _build_score_table,
    _holm_adjusted_p,
    _holm_bonferroni,
    _load_score_records_for_run,
    _rank_biserial,
    _wilcoxon_signed_rank,
    run_exploratory_analyses,
)


# --------------------------------------------------------------------------
# Helpers
# --------------------------------------------------------------------------

CONFIRMATORY_RUN_DIR = ROOT / "results" / "runs" / "full_t2_confirmatory_v2"
SUCCESSOR_RUN_DIR = ROOT / "results" / "runs" / "t2_frontier_successor_replication"


def _confirmatory_present() -> bool:
    return (CONFIRMATORY_RUN_DIR / "scores").is_dir()


def _successor_present() -> bool:
    return (SUCCESSOR_RUN_DIR / "scores").is_dir()


def _make_synthetic_run(tmp: Path, run_id: str, records: list[dict]) -> Path:
    """Create a synthetic results directory with a single run's scores/."""
    scores_dir = tmp / "runs" / run_id / "scores"
    scores_dir.mkdir(parents=True)
    for i, rec in enumerate(records):
        with (scores_dir / f"score_{i:04d}.json").open("w") as fh:
            json.dump(rec, fh)
    return tmp


def _ok(func_id: str, task: str, condition: str, model_id: str, score: float) -> dict:
    return {
        "lumen_schema": "scorer-result-v1",
        "func_id": func_id,
        "task": task,
        "condition": condition,
        "model_id": model_id,
        "score": score,
        "status": "ok",
    }


def _parse_failure(func_id: str, task: str, condition: str, model_id: str) -> dict:
    return {
        "lumen_schema": "scorer-result-v1",
        "func_id": func_id,
        "task": task,
        "condition": condition,
        "model_id": model_id,
        "score": 0.0,
        "status": "parse_failure",
    }


# --------------------------------------------------------------------------
# 1. Wilcoxon wrapper
# --------------------------------------------------------------------------

class TestWilcoxonWrapper(unittest.TestCase):
    """test_wilcoxon_wrapper_matches_scipy"""

    def test_matches_scipy_directly(self) -> None:
        from scipy.stats import wilcoxon
        diffs = [0.5, 1.0, -0.5, 1.5, 0.0, 2.0]
        stat, p = _wilcoxon_signed_rank(diffs, alternative="greater")
        # Reference: drop zeros and call scipy with same params
        nz = [d for d in diffs if d != 0.0]
        ref = wilcoxon(nz, alternative="greater", zero_method="wilcox")
        self.assertAlmostEqual(stat, float(ref.statistic), places=10)
        self.assertAlmostEqual(p, float(ref.pvalue), places=10)

    def test_insufficient_data_returns_nan(self) -> None:
        stat, p = _wilcoxon_signed_rank([0.0, 0.0, 0.0])
        self.assertTrue(math.isnan(stat))
        self.assertTrue(math.isnan(p))
        stat, p = _wilcoxon_signed_rank([1.5])
        self.assertTrue(math.isnan(stat))
        self.assertTrue(math.isnan(p))


# --------------------------------------------------------------------------
# 2. Rank-biserial manual
# --------------------------------------------------------------------------

class TestRankBiserialManual(unittest.TestCase):
    """test_rank_biserial_manual"""

    def test_simple_all_positive(self) -> None:
        # All non-zero diffs positive => r_rb = +1
        self.assertAlmostEqual(_rank_biserial([1.0, 2.0, 3.0]), 1.0, places=10)

    def test_simple_all_negative(self) -> None:
        self.assertAlmostEqual(_rank_biserial([-1.0, -2.0, -3.0]), -1.0, places=10)

    def test_mixed_with_tie_at_zero(self) -> None:
        # diffs = [+1, +1, -1, 0, +1]
        # nonzero abs values: [1, 1, 1, 1] all rank-tied → mid-rank (1+4)/2 = 2.5 each
        # T+ = 2.5 * 3 = 7.5; T- = 2.5; total = 10
        # r_rb = (7.5 - 2.5) / 10 = 0.5
        diffs = [1.0, 1.0, -1.0, 0.0, 1.0]
        self.assertAlmostEqual(_rank_biserial(diffs), 0.5, places=10)

    def test_all_zero_returns_zero(self) -> None:
        self.assertEqual(_rank_biserial([0.0, 0.0, 0.0]), 0.0)
        self.assertEqual(_rank_biserial([]), 0.0)


# --------------------------------------------------------------------------
# 3, 4. Bootstrap CI reproducibility
# --------------------------------------------------------------------------

class TestBootstrapCI(unittest.TestCase):
    """test_bootstrap_ci_reproducible / test_bootstrap_ci_different_seed_different_result"""

    def test_same_seed_same_ci(self) -> None:
        diffs = [1.0, 2.0, -0.5, 0.5, 0.0, 1.5, -1.0, 0.5, 0.5, 2.0]
        a = _bootstrap_ci_rank_biserial(diffs, n_resamples=500, seed=42)
        b = _bootstrap_ci_rank_biserial(diffs, n_resamples=500, seed=42)
        self.assertEqual(a, b)

    def test_different_seed_different_ci(self) -> None:
        diffs = [1.0, 2.0, -0.5, 0.5, 0.0, 1.5, -1.0, 0.5, 0.5, 2.0]
        a = _bootstrap_ci_rank_biserial(diffs, n_resamples=500, seed=42)
        b = _bootstrap_ci_rank_biserial(diffs, n_resamples=500, seed=43)
        self.assertNotEqual(a, b)

    def test_insufficient_data_returns_nan_pair(self) -> None:
        lo, hi = _bootstrap_ci_rank_biserial([0.0, 0.0, 0.0], n_resamples=100, seed=1)
        self.assertTrue(math.isnan(lo))
        self.assertTrue(math.isnan(hi))

    def test_ci_within_minus_one_to_one(self) -> None:
        diffs = [1.0, -1.0, 0.5, -0.5, 0.25, -0.25]
        lo, hi = _bootstrap_ci_rank_biserial(diffs, n_resamples=500, seed=42)
        self.assertGreaterEqual(lo, -1.0)
        self.assertLessEqual(hi, 1.0)
        self.assertLessEqual(lo, hi)


# --------------------------------------------------------------------------
# 5. Holm known input
# --------------------------------------------------------------------------

class TestHolm(unittest.TestCase):
    """test_holm_known_input"""

    def test_textbook_three_p_values(self) -> None:
        # p = [0.01, 0.04, 0.5], m=3, alpha=0.05.
        # Sorted: 0.01, 0.04, 0.5.
        #   k=1: 0.01 vs 0.05/3 = 0.0167 → reject
        #   k=2: 0.04 vs 0.05/2 = 0.025 → fail → stop
        #   k=3: not reject
        rejected = _holm_bonferroni([0.01, 0.04, 0.5], alpha=0.05)
        self.assertEqual(rejected, [True, False, False])

    def test_holm_adjusted_p_textbook(self) -> None:
        # Adjusted p:
        #   k=1: 0.01 * 3 = 0.03
        #   k=2: max(0.03, 0.04 * 2) = 0.08
        #   k=3: max(0.08, 0.5 * 1) = 0.5
        adj = _holm_adjusted_p([0.01, 0.04, 0.5])
        self.assertAlmostEqual(adj[0], 0.03, places=10)
        self.assertAlmostEqual(adj[1], 0.08, places=10)
        self.assertAlmostEqual(adj[2], 0.5,  places=10)

    def test_holm_adjusted_p_caps_at_one(self) -> None:
        # m=3, p=0.5 at k=1 → 0.5*3 = 1.5, capped to 1.0
        adj = _holm_adjusted_p([0.5, 0.6, 0.7])
        self.assertEqual(adj[0], 1.0)

    def test_holm_adjusted_p_nan_coerced_to_one(self) -> None:
        adj = _holm_adjusted_p([0.01, float("nan"), 0.5])
        # nan-coerced p=1.0; sorted order = [0.01, 0.5, 1.0]
        # k=1: 0.01*3 = 0.03 → input position 0
        # k=2: max(0.03, 0.5*2)=1.0 (capped) → position 2
        # k=3: max(1.0, 1.0*1)=1.0 → position 1
        self.assertAlmostEqual(adj[0], 0.03, places=10)
        self.assertEqual(adj[1], 1.0)
        self.assertEqual(adj[2], 1.0)


# --------------------------------------------------------------------------
# 6, 7. Loader filters
# --------------------------------------------------------------------------

class TestLoaderFilters(unittest.TestCase):
    """test_load_records_filters_status_not_ok / test_load_records_filters_run_id"""

    def test_filters_status_not_ok_at_score_table(self) -> None:
        recs = [
            _ok("f1", "T2", "C1", "m", 1.0),
            _parse_failure("f1", "T2", "C2", "m"),
            _ok("f1", "T2", "C2", "m", 2.0),
        ]
        table, excluded = _build_score_table(recs, models=["m"])
        self.assertEqual(excluded, 1)
        self.assertEqual(len(table), 2)
        self.assertNotIn(("f1", "T2", "C2", "m"), [k for k in table if False])  # syntactic
        # parse_failure entry should not poison the C2 cell since the OK record
        # is later in the list and overrides
        self.assertEqual(table[("f1", "T2", "C2", "m")], 2.0)

    def test_loader_filters_by_run_id(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            _make_synthetic_run(tmp, "run_a", [_ok("f1", "T2", "C1", "m", 1.0)])
            _make_synthetic_run(tmp, "run_b", [_ok("f2", "T2", "C1", "m", 9.9)])
            recs_a = _load_score_records_for_run(tmp, "run_a")
            recs_b = _load_score_records_for_run(tmp, "run_b")
            self.assertEqual(len(recs_a), 1)
            self.assertEqual(recs_a[0]["func_id"], "f1")
            self.assertEqual(len(recs_b), 1)
            self.assertEqual(recs_b[0]["func_id"], "f2")

    def test_loader_ignores_wrong_schema(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            scores = tmp / "runs" / "r" / "scores"
            scores.mkdir(parents=True)
            with (scores / "good.json").open("w") as fh:
                json.dump(_ok("f1", "T2", "C1", "m", 1.0), fh)
            with (scores / "wrong_schema.json").open("w") as fh:
                json.dump({"lumen_schema": "other-v1", "score": 5}, fh)
            recs = _load_score_records_for_run(tmp, "r")
            self.assertEqual(len(recs), 1)


# --------------------------------------------------------------------------
# 8. Insufficient data handling
# --------------------------------------------------------------------------

class TestInsufficientDataHandling(unittest.TestCase):
    """test_insufficient_data_handling"""

    def test_empty_run_returns_clean_output(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            (tmp / "runs" / "empty" / "scores").mkdir(parents=True)
            output = run_exploratory_analyses(
                results_dir=tmp, run_id="empty", func_ids=None,
                analyses=["e1_e3_decomposition", "per_model_split_h1_h2_h3"],
                correction="none", bootstrap_resamples=100, seed=1,
                alpha=0.05, alternative="greater",
            )
            self.assertEqual(output["lumen_schema"], LUMEN_SCHEMA)
            self.assertEqual(output["framing_disclaimer"], FRAMING_DISCLAIMER)
            self.assertEqual(output["analyses"]["e1_e3_decomposition"], [])
            self.assertEqual(output["analyses"]["per_model_split_h1_h2_h3"], [])

    def test_single_pair_yields_insufficient_data_status(self) -> None:
        # One func, T2, only C1 scores → no E-test can pair against C2
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            recs = [_ok("f1", "T2", "C1", "m", 1.0)]
            _make_synthetic_run(tmp, "r", recs)
            output = run_exploratory_analyses(
                results_dir=tmp, run_id="r", func_ids=None,
                analyses=["e1_e3_decomposition"],
                correction="none", bootstrap_resamples=50, seed=1,
                alpha=0.05, alternative="greater",
            )
            for r in output["analyses"]["e1_e3_decomposition"]:
                self.assertEqual(r["status"], "insufficient_data")
                self.assertIsNone(r["statistic"])
                self.assertIsNone(r["raw_p"])


# --------------------------------------------------------------------------
# 9. Integration: confirmatory v2
# --------------------------------------------------------------------------

class TestE1E3OnConfirmatoryV2(unittest.TestCase):
    """test_e1_e3_on_v2_runs_clean"""

    def setUp(self) -> None:
        if not _confirmatory_present():
            self.skipTest("full_t2_confirmatory_v2 artifacts not present")

    def test_runs_and_validates_schema(self) -> None:
        results_root = ROOT / "results"
        output = run_exploratory_analyses(
            results_dir=results_root, run_id="full_t2_confirmatory_v2",
            func_ids=None,
            analyses=["e1_e3_decomposition"],
            correction="none", bootstrap_resamples=200, seed=20_260_427,
            alpha=0.05, alternative="greater",
        )
        self.assertEqual(output["lumen_schema"], LUMEN_SCHEMA)
        self.assertEqual(output["framing_disclaimer"], FRAMING_DISCLAIMER)
        self.assertIn("input_summary", output)
        self.assertIn("method_metadata", output)
        self.assertEqual(output["input_summary"]["n_excluded_status_not_ok"], 0)
        self.assertEqual(output["input_summary"]["n_analytical"], 300)

        # E1-E3 × T2 (only T2 collected) → 3 rows
        e_rows = output["analyses"]["e1_e3_decomposition"]
        self.assertEqual(len(e_rows), 3)
        labels = {(r["hypothesis"], r["task"]) for r in e_rows}
        self.assertEqual(labels, {("E1", "T2"), ("E2", "T2"), ("E3", "T2")})
        for r in e_rows:
            self.assertEqual(r["status"], "ok")
            self.assertEqual(r["n_pairs"], 30)
            self.assertIsNotNone(r["statistic"])
            self.assertIsNotNone(r["raw_p"])
            self.assertIsNotNone(r["r_rb"])
            self.assertIsNotNone(r["ci_low"])
            self.assertIsNotNone(r["ci_high"])


# --------------------------------------------------------------------------
# 10. Integration: per-model split
# --------------------------------------------------------------------------

class TestPerModelSplitOnConfirmatoryV2(unittest.TestCase):
    """test_per_model_split_on_v2_returns_two_models"""

    def setUp(self) -> None:
        if not _confirmatory_present():
            self.skipTest("full_t2_confirmatory_v2 artifacts not present")

    def test_two_models_present(self) -> None:
        results_root = ROOT / "results"
        output = run_exploratory_analyses(
            results_dir=results_root, run_id="full_t2_confirmatory_v2",
            func_ids=None, analyses=["per_model_split_h1_h2_h3"],
            correction="none", bootstrap_resamples=200, seed=20_260_427,
            alpha=0.05, alternative="greater",
        )
        rows = output["analyses"]["per_model_split_h1_h2_h3"]
        models_seen = {r["model"] for r in rows}
        self.assertEqual(models_seen, {"gpt-5.4", "claude-opus-4-6"})
        # 3 hypotheses × 1 task (T2) × 2 models = 6 rows
        self.assertEqual(len(rows), 6)
        for r in rows:
            self.assertEqual(r["status"], "ok")
            self.assertEqual(r["n_pairs"], 30)


# --------------------------------------------------------------------------
# 11. Integration: successor run excludes 12 parse_failures
# --------------------------------------------------------------------------

class TestSuccessorRunParseFailureExclusion(unittest.TestCase):
    """test_successor_run_excludes_12_parse_failures"""

    def setUp(self) -> None:
        if not _successor_present():
            self.skipTest("t2_frontier_successor_replication artifacts not present")

    def test_excluded_12_analytical_288(self) -> None:
        results_root = ROOT / "results"
        output = run_exploratory_analyses(
            results_dir=results_root, run_id="t2_frontier_successor_replication",
            func_ids=None,
            analyses=["e1_e3_decomposition", "per_model_split_h1_h2_h3"],
            correction="none", bootstrap_resamples=200, seed=20_260_427,
            alpha=0.05, alternative="greater",
        )
        self.assertEqual(output["input_summary"]["n_excluded_status_not_ok"], 12)
        self.assertEqual(output["input_summary"]["n_analytical"], 288)
        self.assertEqual(
            set(output["input_summary"]["models_in_data"]),
            {"gpt-5.5", "claude-opus-4-7"},
        )


# --------------------------------------------------------------------------
# 12. Holm-per-model (not pooled across models)
# --------------------------------------------------------------------------

class TestHolmPerModelNotPooled(unittest.TestCase):
    def test_holm_correction_is_per_model_family(self) -> None:
        if not _confirmatory_present():
            self.skipTest("v2 not present")
        results_root = ROOT / "results"
        output = run_exploratory_analyses(
            results_dir=results_root, run_id="full_t2_confirmatory_v2",
            func_ids=None, analyses=["per_model_split_h1_h2_h3"],
            correction="holm", bootstrap_resamples=200, seed=20_260_427,
            alpha=0.05, alternative="greater",
        )
        rows = output["analyses"]["per_model_split_h1_h2_h3"]
        # Per-model family size is 3 (H1,H2,H3 on T2). Smallest holm_p
        # within each model should equal min(raw_p)*3 (Holm step 1).
        for model in {"gpt-5.4", "claude-opus-4-6"}:
            mr = [r for r in rows if r["model"] == model]
            self.assertEqual(len(mr), 3)
            min_raw = min(r["raw_p"] for r in mr if r["raw_p"] is not None)
            min_holm = min(r["holm_p"] for r in mr if r["holm_p"] is not None)
            # Holm-adjusted at rank 1 = raw * (m - 1 + 1) = raw * 3
            # (capped at 1.0). For typical effect-size data this isn't capped.
            self.assertAlmostEqual(min_holm, min(1.0, min_raw * 3), places=6)


# --------------------------------------------------------------------------
# Paired-diff builders
# --------------------------------------------------------------------------

class TestPairedDiffBuilders(unittest.TestCase):
    def test_aggregated_averages_across_models(self) -> None:
        table = {
            ("f1", "T2", "C2", "mA"): 1.0,
            ("f1", "T2", "C2", "mB"): 3.0,
            ("f1", "T2", "C1", "mA"): 0.0,
            ("f1", "T2", "C1", "mB"): 0.0,
        }
        diffs = _build_paired_diffs_aggregated(
            table, ["f1"], "C2", "C1", "T2", ["mA", "mB"],
        )
        # mean(C2) = 2.0, mean(C1) = 0.0, diff = 2.0
        self.assertEqual(diffs, [2.0])

    def test_single_model_isolates(self) -> None:
        table = {
            ("f1", "T2", "C4", "mA"): 2.0,
            ("f1", "T2", "C4", "mB"): 0.0,
            ("f1", "T2", "C1", "mA"): 1.0,
            ("f1", "T2", "C1", "mB"): 1.0,
        }
        diffs_a = _build_paired_diffs_single_model(
            table, ["f1"], "C4", "C1", "T2", "mA",
        )
        diffs_b = _build_paired_diffs_single_model(
            table, ["f1"], "C4", "C1", "T2", "mB",
        )
        self.assertEqual(diffs_a, [1.0])
        self.assertEqual(diffs_b, [-1.0])

    def test_function_skipped_when_one_side_missing(self) -> None:
        table = {("f1", "T2", "C1", "m"): 1.0}  # no C2 record
        diffs = _build_paired_diffs_aggregated(
            table, ["f1"], "C2", "C1", "T2", ["m"],
        )
        self.assertEqual(diffs, [])


if __name__ == "__main__":
    unittest.main()
