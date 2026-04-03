"""Run pre-registered confirmatory analyses on collected results.

ANALYSIS FREEZE DATE: 2026-04-02
Frozen prior to full data collection. See docs/experimental-protocol.md §10.

All analyses in this file are pre-registered and frozen.
Do not add post-hoc analyses here; use analyze_exploratory.py instead.
Any amendment to this file after the freeze date requires a dated note
at the top of the file explaining what was added and why.

Statistical plan (constitution §5, protocol §9):
  Confirmatory family: 9 tests = {H1, H2, H3} × {T1, T2, T3}

  Hypotheses (all directional, condition_A > condition_B):
    H1 (Structure at constant information): C4 > C1+
    H2 (Total enrichment):                 C4 > C1
    H3 (Information enrichment in text):   C1+ > C1

  Aggregation: per-function mean score across the two frozen models
               before computing paired differences.

  Test: Wilcoxon signed-rank, one-sided (alternative='greater').
        Zero-differences handled by scipy default (zero_method='wilcox').

  Effect size: rank-biserial correlation r_rb.
    r_rb = (T+ - T-) / (T+ + T-)
    where T+ = sum of ranks of positive differences,
          T- = sum of ranks of negative differences.

  Correction: Holm-Bonferroni sequential procedure across 9 tests at α=0.05.
    Steps: sort p-values ascending; reject hypothesis k (1-indexed) if
    p_(k) ≤ α / (m - k + 1) for m=9; stop at first non-rejection.

  Frozen model pair:
    Test subject A: gpt-5.4 (OpenAI)
    Test subject B: claude-opus-4-6 (Anthropic)
  See docs/experimental-protocol.md §8 and data/dataset/confirmatory_governance.json.

Primary endpoint:
  H1 on T2 (constitution §14). All 9 tests are confirmatory;
  T2 results carry greatest interpretive weight.
"""

from __future__ import annotations

import csv
import json
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Constants (frozen — do not change without a dated amendment note above)
# ---------------------------------------------------------------------------

FROZEN_MODELS: tuple[str, ...] = ("gpt-5.4", "claude-opus-4-6")
ALPHA = 0.05
N_TESTS = 9  # 3 hypotheses × 3 tasks

# Hypothesis definitions: (label, condition_A, condition_B, description)
# Test: median(score_A - score_B) > 0
HYPOTHESES: list[tuple[str, str, str, str]] = [
    ("H1", "C4", "C1+", "Structure at constant information: C4 > C1+"),
    ("H2", "C4", "C1",  "Total enrichment: C4 > C1"),
    ("H3", "C1+", "C1", "Information enrichment in text: C1+ > C1"),
]

TASKS: list[str] = ["T1", "T2", "T3"]

# Task scoring ranges (for documentation only — not used in the test logic)
TASK_SCORE_RANGE: dict[str, str] = {
    "T1": "0.0–1.0 (property-checklist fraction)",
    "T2": "0–3 (composite: location + diagnosis + fix)",
    "T3": "0.0–1.0 (test pass rate)",
}

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
_RESULTS_RUNS_DIR = _REPO_ROOT / "results" / "runs"
_RESULTS_ANALYSIS_DIR = _REPO_ROOT / "results" / "analysis"


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------

def _load_score_files(runs_dir: Path) -> list[dict[str, Any]]:
    """Load all scorer-result-v1 JSON files from all run directories.

    Returns a flat list of score dicts. Each dict must have keys:
    func_id, task, condition, model_id, score, status.
    """
    records: list[dict[str, Any]] = []
    if not runs_dir.exists():
        return records
    for run_dir in sorted(runs_dir.iterdir()):
        scores_dir = run_dir / "scores"
        if not scores_dir.is_dir():
            continue
        for score_file in sorted(scores_dir.glob("*.json")):
            try:
                with score_file.open() as fh:
                    data = json.load(fh)
                if data.get("lumen_schema") == "scorer-result-v1":
                    records.append(data)
            except Exception:  # noqa: BLE001
                pass
    return records


def _build_score_table(
    records: list[dict[str, Any]],
    models: tuple[str, ...] = FROZEN_MODELS,
) -> dict[tuple[str, str, str, str], float]:
    """Return a dict keyed by (func_id, task, condition, model_id) → score.

    Only includes records for the frozen model pair with status='ok'.
    Duplicate (func_id, task, condition, model_id) tuples from different
    runs are resolved by keeping the last record in run-directory sort order.
    (Later runs are presumed to be rescores superseding earlier ones.)
    """
    table: dict[tuple[str, str, str, str], float] = {}
    for rec in records:
        if rec.get("status") != "ok":
            continue
        model = rec.get("model_id", "")
        if model not in models:
            continue
        key = (
            str(rec["func_id"]),
            str(rec["task"]),
            str(rec["condition"]),
            str(model),
        )
        table[key] = float(rec["score"])
    return table


def _aggregate_across_models(
    score_table: dict[tuple[str, str, str, str], float],
    func_ids: list[str],
    models: tuple[str, ...] = FROZEN_MODELS,
) -> dict[tuple[str, str, str], float | None]:
    """Aggregate scores across models per (func_id, task, condition).

    Returns None for cells where no model has a score (missing data).
    Averages across whichever models are present (logs partial coverage).
    """
    agg: dict[tuple[str, str, str], float | None] = {}
    tasks = TASKS
    conditions = [h[1] for h in HYPOTHESES] + [h[2] for h in HYPOTHESES]
    conditions_unique = list(dict.fromkeys(conditions))  # preserves order, deduped

    for func_id in func_ids:
        for task in tasks:
            for cond in conditions_unique:
                vals = [
                    score_table[(func_id, task, cond, m)]
                    for m in models
                    if (func_id, task, cond, m) in score_table
                ]
                agg[(func_id, task, cond)] = (sum(vals) / len(vals)) if vals else None
    return agg


# ---------------------------------------------------------------------------
# Statistical routines (protocol-faithful)
# ---------------------------------------------------------------------------

def _rank_biserial(diffs: list[float]) -> float:
    """Compute rank-biserial correlation r_rb for paired signed-rank test.

    r_rb = (T+ - T-) / (T+ + T-)
    where T+ = sum of ranks of positive differences (after dropping zeros),
          T- = sum of ranks of negative differences.

    Returns 0.0 if all differences are zero (no signal).
    """
    nonzero = [d for d in diffs if d != 0.0]
    if not nonzero:
        return 0.0
    abs_vals = sorted(range(len(nonzero)), key=lambda i: abs(nonzero[i]))
    # Compute tied average ranks
    abs_sorted = [abs(nonzero[i]) for i in abs_vals]
    ranks: list[float] = [0.0] * len(nonzero)
    i = 0
    while i < len(abs_sorted):
        j = i
        while j < len(abs_sorted) and abs_sorted[j] == abs_sorted[i]:
            j += 1
        avg_rank = (i + 1 + j) / 2.0  # 1-indexed average rank
        for k in range(i, j):
            ranks[abs_vals[k]] = avg_rank
        i = j
    t_plus = sum(ranks[k] for k, v in enumerate(nonzero) if v > 0)
    t_minus = sum(ranks[k] for k, v in enumerate(nonzero) if v < 0)
    total = t_plus + t_minus
    return (t_plus - t_minus) / total if total > 0 else 0.0


def _wilcoxon_signed_rank(diffs: list[float]) -> tuple[float, float]:
    """One-sided Wilcoxon signed-rank test: H_a: median(diffs) > 0.

    Returns (statistic, p_value). Uses scipy.stats.wilcoxon with
    alternative='greater' and zero_method='wilcox' (protocol default).

    Returns (nan, nan) if fewer than 2 non-zero differences remain.
    """
    try:
        from scipy.stats import wilcoxon  # noqa: PLC0415
    except ImportError as exc:
        raise ImportError(
            "scipy is required for confirmatory analysis. "
            "Install with: pip install scipy"
        ) from exc

    nonzero = [d for d in diffs if d != 0.0]
    if len(nonzero) < 2:
        return (float("nan"), float("nan"))
    result = wilcoxon(nonzero, alternative="greater", zero_method="wilcox")
    return (float(result.statistic), float(result.pvalue))


def _holm_bonferroni(
    p_values: list[float], alpha: float = ALPHA
) -> list[bool]:
    """Apply Holm-Bonferroni correction to a list of p-values.

    Returns a list of booleans: True = reject H_0 at family-wise α.

    Procedure: sort p-values ascending; reject hypothesis at rank k (1-indexed)
    if p_(k) ≤ α / (m - k + 1) for m = len(p_values); stop at first failure.
    """
    m = len(p_values)
    order = sorted(range(m), key=lambda i: p_values[i])
    rejected = [False] * m
    stop = False
    for rank, idx in enumerate(order, start=1):
        if stop or p_values[idx] > alpha / (m - rank + 1):
            stop = True
        else:
            rejected[idx] = True
    return rejected


# ---------------------------------------------------------------------------
# Core analysis
# ---------------------------------------------------------------------------

@dataclass
class TestResult:
    hypothesis: str
    task: str
    condition_a: str
    condition_b: str
    n_functions: int
    n_complete_pairs: int
    statistic: float
    p_value: float
    r_rb: float
    rejected: bool = False  # filled in after Holm-Bonferroni
    diffs: list[float] = field(default_factory=list)


def run_confirmatory_analyses(
    results_dir: str | None = None,
    func_ids: list[str] | None = None,
    models: tuple[str, ...] = FROZEN_MODELS,
) -> dict[str, Any]:
    """Load scored results and run all 9 confirmatory tests.

    Parameters
    ----------
    results_dir:
        Path to the results/ directory (default: repo-root/results).
    func_ids:
        List of function IDs to include. If None, all functions found in
        the score table are used.
    models:
        Tuple of model identifiers for the frozen pair (default: FROZEN_MODELS).

    Returns
    -------
    A dict with keys:
        'tests': list of TestResult dicts
        'holm_bonferroni_alpha': float
        'n_tests': int
        'frozen_models': list[str]
        'data_completeness': dict
        'run_timestamp': str
    """
    runs_dir = Path(results_dir) / "runs" if results_dir else _RESULTS_RUNS_DIR

    # Load and build score table
    records = _load_score_files(runs_dir)
    score_table = _build_score_table(records, models=models)

    # Determine function set
    if func_ids is None:
        func_ids = sorted({k[0] for k in score_table})

    # All conditions used by confirmatory hypotheses
    all_conditions = ["C1", "C1+", "C2", "C3", "C4"]

    # Aggregate per (func, task, condition)
    agg = _aggregate_across_models(score_table, func_ids, models=models)

    # Data completeness report
    completeness: dict[str, Any] = {
        "total_functions": len(func_ids),
        "score_records_loaded": len(records),
        "score_records_for_frozen_models": len(score_table),
    }
    for task in TASKS:
        for cond in all_conditions:
            key_label = f"{task}/{cond}"
            have = sum(
                1 for f in func_ids if agg.get((f, task, cond)) is not None
            )
            completeness[key_label] = f"{have}/{len(func_ids)}"

    # Run all 9 tests
    raw_results: list[TestResult] = []
    for hyp_label, cond_a, cond_b, _ in HYPOTHESES:
        for task in TASKS:
            diffs = []
            for func_id in func_ids:
                score_a = agg.get((func_id, task, cond_a))
                score_b = agg.get((func_id, task, cond_b))
                if score_a is not None and score_b is not None:
                    diffs.append(score_a - score_b)

            stat, pval = _wilcoxon_signed_rank(diffs)
            r_rb = _rank_biserial(diffs)

            raw_results.append(
                TestResult(
                    hypothesis=hyp_label,
                    task=task,
                    condition_a=cond_a,
                    condition_b=cond_b,
                    n_functions=len(func_ids),
                    n_complete_pairs=len(diffs),
                    statistic=stat,
                    p_value=pval,
                    r_rb=r_rb,
                    diffs=diffs,
                )
            )

    # Holm-Bonferroni correction
    p_values = [r.p_value for r in raw_results]
    # Replace nan with 1.0 for correction (conservative: not rejected)
    p_for_correction = [p if p == p else 1.0 for p in p_values]
    rejection_flags = _holm_bonferroni(p_for_correction, alpha=ALPHA)
    for result, rejected in zip(raw_results, rejection_flags):
        result.rejected = rejected

    # Serialize
    def _fmt(x: float) -> float | str:
        if x != x:  # nan
            return "nan"
        return round(x, 6)

    tests_out = [
        {
            "hypothesis": r.hypothesis,
            "task": r.task,
            "condition_A": r.condition_a,
            "condition_B": r.condition_b,
            "description": next(
                d for (h, ca, cb, d) in HYPOTHESES if h == r.hypothesis
            ),
            "n_functions": r.n_functions,
            "n_complete_pairs": r.n_complete_pairs,
            "wilcoxon_statistic": _fmt(r.statistic),
            "p_value_one_sided": _fmt(r.p_value),
            "rank_biserial_r": _fmt(r.r_rb),
            "holm_bonferroni_rejected": r.rejected,
            "interpretation": (
                f"Reject H₀ at α={ALPHA} (Holm–Bonferroni corrected)"
                if r.rejected
                else (
                    "Insufficient data"
                    if r.n_complete_pairs < 2
                    else f"Fail to reject H₀ at α={ALPHA} (Holm–Bonferroni corrected)"
                )
            ),
        }
        for r in raw_results
    ]

    return {
        "lumen_schema": "confirmatory-analysis-v1",
        "analysis_freeze_date": "2026-04-02",
        "run_timestamp": datetime.now(tz=timezone.utc).isoformat(),
        "frozen_models": list(models),
        "alpha": ALPHA,
        "n_tests_in_family": N_TESTS,
        "correction_method": "Holm-Bonferroni",
        "test_method": "Wilcoxon signed-rank (one-sided, alternative='greater')",
        "effect_size_method": "rank-biserial correlation",
        "aggregation_method": "per-function mean across frozen models before testing",
        "primary_endpoint": "H1 on T2 (constitution §14)",
        "data_completeness": completeness,
        "tests": tests_out,
    }


# ---------------------------------------------------------------------------
# Output helpers
# ---------------------------------------------------------------------------

def _print_summary_table(output: dict[str, Any]) -> None:
    """Print a formatted summary of confirmatory test results."""
    print("\n" + "=" * 78)
    print("LUMEN CONFIRMATORY ANALYSIS — PRE-REGISTERED RESULTS")
    print(f"Freeze date: {output['analysis_freeze_date']}")
    print(f"Run timestamp: {output['run_timestamp']}")
    print(f"Frozen models: {', '.join(output['frozen_models'])}")
    print(f"N tests: {output['n_tests_in_family']}  |  α: {output['alpha']}  |  Correction: {output['correction_method']}")
    print("=" * 78)
    print(
        f"{'Test':<10} {'N pairs':>8} {'W stat':>10} {'p (1-sided)':>12} "
        f"{'r_rb':>8} {'Reject?':>8}"
    )
    print("-" * 78)
    for t in output["tests"]:
        hyp_task = f"{t['hypothesis']}/{t['task']}"
        stat = t["wilcoxon_statistic"]
        pval = t["p_value_one_sided"]
        r_rb = t["rank_biserial_r"]
        rejected = "YES *" if t["holm_bonferroni_rejected"] else "no"
        n = t["n_complete_pairs"]
        stat_str = f"{stat:.2f}" if isinstance(stat, float) else str(stat)
        pval_str = f"{pval:.4f}" if isinstance(pval, float) else str(pval)
        r_str = f"{r_rb:.3f}" if isinstance(r_rb, float) else str(r_rb)
        print(
            f"{hyp_task:<10} {n:>8} {stat_str:>10} {pval_str:>12} "
            f"{r_str:>8} {rejected:>8}"
        )
    print("=" * 78)

    # Primary endpoint callout
    primary = next(
        (t for t in output["tests"] if t["hypothesis"] == "H1" and t["task"] == "T2"),
        None,
    )
    if primary:
        verdict = "REJECTED" if primary["holm_bonferroni_rejected"] else "NOT REJECTED"
        print(f"\nPrimary endpoint (H1/T2: C4 > C1+): H₀ {verdict}")

    print()


def _write_csv(output: dict[str, Any], path: Path) -> None:
    fieldnames = [
        "hypothesis", "task", "condition_A", "condition_B",
        "n_complete_pairs", "wilcoxon_statistic", "p_value_one_sided",
        "rank_biserial_r", "holm_bonferroni_rejected", "interpretation",
    ]
    with path.open("w", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(output["tests"])


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main(argv: list[str] | None = None) -> int:
    """Run confirmatory analyses and write outputs to results/analysis/."""
    import argparse  # noqa: PLC0415

    parser = argparse.ArgumentParser(
        prog="analyze_confirmatory",
        description="Run pre-registered confirmatory analyses (frozen 2026-04-02).",
    )
    parser.add_argument(
        "--results-dir",
        default=None,
        dest="results_dir",
        help="Path to results/ directory (default: repo root/results).",
    )
    parser.add_argument(
        "--func-ids",
        nargs="+",
        default=None,
        dest="func_ids",
        metavar="FUNC_ID",
        help="Restrict to specific function IDs (default: all with scores).",
    )
    parser.add_argument(
        "--output-json",
        default=None,
        dest="output_json",
        help="Write JSON output to this path (default: results/analysis/confirmatory_results_{date}.json).",
    )
    parser.add_argument(
        "--output-csv",
        default=None,
        dest="output_csv",
        help="Write CSV output to this path (default: results/analysis/confirmatory_results_{date}.csv).",
    )
    args = parser.parse_args(argv)

    output = run_confirmatory_analyses(
        results_dir=args.results_dir,
        func_ids=args.func_ids,
    )

    _print_summary_table(output)

    # Write outputs
    date_str = datetime.now(tz=timezone.utc).strftime("%Y-%m-%d")
    _RESULTS_ANALYSIS_DIR.mkdir(parents=True, exist_ok=True)

    json_path = Path(args.output_json) if args.output_json else (
        _RESULTS_ANALYSIS_DIR / f"confirmatory_results_{date_str}.json"
    )
    csv_path = Path(args.output_csv) if args.output_csv else (
        _RESULTS_ANALYSIS_DIR / f"confirmatory_results_{date_str}.csv"
    )

    with json_path.open("w") as fh:
        json.dump(output, fh, indent=2)
    print(f"JSON output: {json_path}")

    _write_csv(output, csv_path)
    print(f"CSV output:  {csv_path}")

    # Data completeness warning
    completeness = output["data_completeness"]
    missing_keys = [
        k for k, v in completeness.items()
        if isinstance(v, str) and not v.startswith(str(completeness["total_functions"]))
    ]
    if missing_keys:
        print(
            f"\nWARNING: Incomplete data for {len(missing_keys)} condition/task cells. "
            "Re-run after full data collection for valid confirmatory results."
        )
        for k in sorted(missing_keys)[:10]:
            print(f"  {k}: {completeness[k]}")
        if len(missing_keys) > 10:
            print(f"  ... and {len(missing_keys) - 10} more.")

    return 0


if __name__ == "__main__":
    sys.exit(main())
