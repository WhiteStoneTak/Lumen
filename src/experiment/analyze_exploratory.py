"""Exploratory (post-hoc) analyses — clearly labeled as non-confirmatory.

This script implements:
  1. E1-E3 structural decomposition (Constitution §6 exploratory hypotheses):
       E1: C2 vs C1   (pure structure effect)
       E2: C3 vs C2   (type effect)
       E3: C4 vs C3   (contract effect)
  2. Per-model split of the H1/H2/H3 family (Constitution §17.4: per-model
     analysis is exploratory only).

Both analyses use the same statistical machinery as `analyze_confirmatory.py`
(Wilcoxon signed-rank one-sided, rank-biserial correlation, Holm-Bonferroni)
plus a 95% percentile bootstrap CI for r_rb that the frozen confirmatory
script does not implement. The bootstrap CI advances Constitution §17.4
compliance for exploratory infrastructure; it is NOT an amendment to the
confirmatory protocol.

Outputs are labeled `lumen_schema = "exploratory-analysis-v1"` (distinct
from `confirmatory-analysis-v1`) and carry a `framing_disclaimer` field
asserting their exploratory status.

Statistical kernels are copied from `analyze_confirmatory.py` private
helpers rather than imported, per the implementation directive that the
frozen analyzer's private internals are not its public surface (D-5).
Each copied block carries a provenance comment.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import subprocess
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np

# --------------------------------------------------------------------------
# Module constants
# --------------------------------------------------------------------------

LUMEN_SCHEMA = "exploratory-analysis-v1"

FRAMING_DISCLAIMER = (
    "All results in this file are exploratory and not part of the "
    "pre-registered confirmatory family. They may use the same statistical "
    "machinery as the confirmatory analysis, but their claim status is "
    "exploratory."
)

# E1-E3 (Constitution §6): structural decomposition. (label, cond_a, cond_b, description)
EXPLORATORY_HYPOTHESES_E = [
    ("E1", "C2", "C1",  "Pure structure effect: C2 (raw AST) > C1 (raw text)"),
    ("E2", "C3", "C2",  "Type effect: C3 (typed AST) > C2 (raw AST)"),
    ("E3", "C4", "C3",  "Contract effect: C4 (typed AST + contracts) > C3 (typed AST)"),
]

# H1-H3 (per-model split — same pairs as confirmatory, but per-model not aggregated)
HYPOTHESES_H = [
    ("H1", "C4",  "C1+", "Structure at constant information: C4 > C1+"),
    ("H2", "C4",  "C1",  "Total enrichment: C4 > C1"),
    ("H3", "C1+", "C1",  "Information enrichment in text: C1+ > C1"),
]

TASKS_ALL = ["T1", "T2", "T3"]

DEFAULT_BOOTSTRAP_RESAMPLES = 10_000
DEFAULT_SEED = 20_260_427
DEFAULT_ALPHA = 0.05
DEFAULT_CI_LEVEL = 0.95
DEFAULT_ALTERNATIVE = "greater"


# --------------------------------------------------------------------------
# Statistical kernels
# (copied with attribution from analyze_confirmatory.py per D-5 directive)
# --------------------------------------------------------------------------

# Adapted from src/experiment/analyze_confirmatory.py:_rank_biserial (L171-L199).
# Copied (not imported) because the source is private. Stay in sync if the
# confirmatory script's formulation is ever updated.
def _rank_biserial(diffs: list[float]) -> float:
    """rank-biserial r_rb = (T+ - T-) / (T+ + T-) on tied-averaged ranks of
    |d_i| over the non-zero subset. Returns 0.0 when all diffs are zero."""
    nonzero = [d for d in diffs if d != 0.0]
    if not nonzero:
        return 0.0
    abs_vals = sorted(range(len(nonzero)), key=lambda i: abs(nonzero[i]))
    abs_sorted = [abs(nonzero[i]) for i in abs_vals]
    ranks: list[float] = [0.0] * len(nonzero)
    i = 0
    while i < len(abs_sorted):
        j = i
        while j < len(abs_sorted) and abs_sorted[j] == abs_sorted[i]:
            j += 1
        avg_rank = (i + 1 + j) / 2.0
        for k in range(i, j):
            ranks[abs_vals[k]] = avg_rank
        i = j
    t_plus = sum(ranks[k] for k, v in enumerate(nonzero) if v > 0)
    t_minus = sum(ranks[k] for k, v in enumerate(nonzero) if v < 0)
    total = t_plus + t_minus
    return (t_plus - t_minus) / total if total > 0 else 0.0


# Adapted from src/experiment/analyze_confirmatory.py:_wilcoxon_signed_rank
# (L202-L222). Configurable `alternative` for exploratory flexibility (the
# confirmatory wrapper hard-codes "greater"). Default remains "greater" to
# match the directional pre-registration.
def _wilcoxon_signed_rank(
    diffs: list[float], alternative: str = "greater"
) -> tuple[float, float]:
    """One-sided Wilcoxon signed-rank test. Returns (statistic, p) or
    (nan, nan) if fewer than 2 non-zero differences remain."""
    from scipy.stats import wilcoxon  # noqa: PLC0415
    nonzero = [d for d in diffs if d != 0.0]
    if len(nonzero) < 2:
        return (float("nan"), float("nan"))
    result = wilcoxon(nonzero, alternative=alternative, zero_method="wilcox")
    return (float(result.statistic), float(result.pvalue))


# Adapted from src/experiment/analyze_confirmatory.py:_holm_bonferroni
# (L225-L244). Identical implementation. NaN-coercion to 1.0 is performed by
# the caller, matching confirmatory script's pattern at its L353-356.
def _holm_bonferroni(p_values: list[float], alpha: float = DEFAULT_ALPHA) -> list[bool]:
    """Holm step-down adjustment. Returns rejection flags aligned to input order."""
    m = len(p_values)
    if m == 0:
        return []
    order = sorted(range(m), key=lambda i: p_values[i])
    rejected = [False] * m
    stop = False
    for rank, idx in enumerate(order, start=1):
        if stop or p_values[idx] > alpha / (m - rank + 1):
            stop = True
        else:
            rejected[idx] = True
    return rejected


def _holm_adjusted_p(p_values: list[float]) -> list[float]:
    """Compute Holm-adjusted p-values aligned to input order. Step-down,
    monotone running-max, capped at 1.0. NaN inputs are coerced to 1.0
    (same convention as analyze_confirmatory.py at its L353-356)."""
    m = len(p_values)
    if m == 0:
        return []
    coerced = [1.0 if math.isnan(p) else p for p in p_values]
    order = sorted(range(m), key=lambda i: coerced[i])
    adjusted = [1.0] * m
    running_max = 0.0
    for rank, idx in enumerate(order, start=1):
        candidate = min(1.0, coerced[idx] * (m - rank + 1))
        running_max = max(running_max, candidate)
        adjusted[idx] = running_max
    return adjusted


def _bootstrap_ci_rank_biserial(
    diffs: list[float],
    n_resamples: int = DEFAULT_BOOTSTRAP_RESAMPLES,
    seed: int = DEFAULT_SEED,
    ci_level: float = DEFAULT_CI_LEVEL,
) -> tuple[float, float]:
    """Percentile-method bootstrap CI for rank-biserial correlation.

    Resamples paired differences with replacement (size = len(diffs)) and
    recomputes r_rb on each resample. Returns (low, high) of the empirical
    distribution at the [(1-ci)/2, 1-(1-ci)/2] percentiles.

    Returns (nan, nan) when fewer than 2 non-zero diffs (matches Wilcoxon
    insufficient-data behavior)."""
    nonzero_count = sum(1 for d in diffs if d != 0.0)
    if nonzero_count < 2:
        return (float("nan"), float("nan"))
    rng = np.random.default_rng(seed)
    n = len(diffs)
    arr = np.asarray(diffs, dtype=float)
    samples = np.empty(n_resamples, dtype=float)
    for i in range(n_resamples):
        idx = rng.integers(0, n, size=n)
        samples[i] = _rank_biserial(arr[idx].tolist())
    lo_q = (1.0 - ci_level) / 2.0
    hi_q = 1.0 - lo_q
    return (float(np.quantile(samples, lo_q)), float(np.quantile(samples, hi_q)))


# --------------------------------------------------------------------------
# Data loading
# --------------------------------------------------------------------------

# Adapted from src/experiment/analyze_confirmatory.py:_load_score_files
# (L88-L109). Modified to filter by a single run_id at the file system level
# (D-4 directive: --run-id is required and replaces the confirmatory script's
# walk-every-run pattern).
def _load_score_records_for_run(results_dir: Path, run_id: str) -> list[dict[str, Any]]:
    """Load scorer-result-v1 records from <results_dir>/runs/<run_id>/scores/*.json."""
    scores_dir = results_dir / "runs" / run_id / "scores"
    records: list[dict[str, Any]] = []
    if not scores_dir.is_dir():
        return records
    for score_file in sorted(scores_dir.glob("*.json")):
        try:
            with score_file.open() as fh:
                data = json.load(fh)
        except (OSError, json.JSONDecodeError):
            continue
        if data.get("lumen_schema") == "scorer-result-v1":
            records.append(data)
    return records


def _build_score_table(
    records: list[dict[str, Any]],
    models: list[str] | tuple[str, ...],
) -> tuple[dict[tuple[str, str, str, str], float], int]:
    """Return ((func_id, task, condition, model_id) -> score, n_excluded_status_not_ok).

    Adapted from src/experiment/analyze_confirmatory.py:_build_score_table
    (L112-L137) but returns the count of status!=ok exclusions explicitly
    (the confirmatory script silently drops them; the exploratory schema
    surfaces the count in input_summary)."""
    table: dict[tuple[str, str, str, str], float] = {}
    excluded = 0
    for rec in records:
        if rec.get("status") != "ok":
            excluded += 1
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
    return table, excluded


# --------------------------------------------------------------------------
# Paired-difference construction
# --------------------------------------------------------------------------

def _build_paired_diffs_aggregated(
    score_table: dict[tuple[str, str, str, str], float],
    func_ids: list[str],
    cond_a: str,
    cond_b: str,
    task: str,
    models: list[str],
) -> list[float]:
    """Per-function paired diffs (cond_a - cond_b) where the per-condition
    score is the mean across `models` (only over models actually present
    for that cell). A function contributes only if both cond_a and cond_b
    have at least one model with a score for it.

    Adapted from analyze_confirmatory.py:run_confirmatory_analyses inline
    aggregation at L325-L333, but with explicit `models` so it is not
    bound to FROZEN_MODELS."""
    diffs: list[float] = []
    for func_id in func_ids:
        a_vals = [
            score_table[(func_id, task, cond_a, m)]
            for m in models
            if (func_id, task, cond_a, m) in score_table
        ]
        b_vals = [
            score_table[(func_id, task, cond_b, m)]
            for m in models
            if (func_id, task, cond_b, m) in score_table
        ]
        if a_vals and b_vals:
            diffs.append((sum(a_vals) / len(a_vals)) - (sum(b_vals) / len(b_vals)))
    return diffs


def _build_paired_diffs_single_model(
    score_table: dict[tuple[str, str, str, str], float],
    func_ids: list[str],
    cond_a: str,
    cond_b: str,
    task: str,
    model: str,
) -> list[float]:
    """Per-function paired diffs for a single model. A function contributes
    only if both cond_a and cond_b have a score for that model."""
    diffs: list[float] = []
    for func_id in func_ids:
        a = score_table.get((func_id, task, cond_a, model))
        b = score_table.get((func_id, task, cond_b, model))
        if a is not None and b is not None:
            diffs.append(a - b)
    return diffs


# --------------------------------------------------------------------------
# Test result container and runner
# --------------------------------------------------------------------------

@dataclass
class ExploratoryTestResult:
    hypothesis: str
    task: str
    cond_a: str
    cond_b: str
    model: str = ""  # empty for aggregated-across-models tests
    n_pairs: int = 0
    n_pos: int = 0
    n_neg: int = 0
    n_tie: int = 0
    median_diff: float = float("nan")
    statistic: float = float("nan")
    raw_p: float = float("nan")
    holm_p: float | None = None
    r_rb: float = 0.0
    ci_low: float = float("nan")
    ci_high: float = float("nan")
    status: str = "ok"  # "ok" | "insufficient_data"
    diffs: list[float] = field(default_factory=list)


def _summarize_diffs(diffs: list[float]) -> tuple[int, int, int, int, float]:
    """(n_pairs, n_pos, n_neg, n_tie, median_diff)."""
    n = len(diffs)
    if n == 0:
        return (0, 0, 0, 0, float("nan"))
    pos = sum(1 for d in diffs if d > 0)
    neg = sum(1 for d in diffs if d < 0)
    tie = sum(1 for d in diffs if d == 0)
    return (n, pos, neg, tie, float(np.median(diffs)))


def _run_one_test(
    hypothesis: str,
    task: str,
    cond_a: str,
    cond_b: str,
    diffs: list[float],
    *,
    alternative: str,
    n_resamples: int,
    seed: int,
    ci_level: float,
    model: str = "",
) -> ExploratoryTestResult:
    """Run the standard kernel on a paired-diffs vector. Returns one result."""
    n, pos, neg, tie, med = _summarize_diffs(diffs)
    if n < 2 or (pos + neg) < 2:
        return ExploratoryTestResult(
            hypothesis=hypothesis, task=task, cond_a=cond_a, cond_b=cond_b,
            model=model, n_pairs=n, n_pos=pos, n_neg=neg, n_tie=tie,
            median_diff=med if n > 0 else float("nan"),
            status="insufficient_data", diffs=list(diffs),
        )
    stat, raw_p = _wilcoxon_signed_rank(diffs, alternative=alternative)
    r = _rank_biserial(diffs)
    ci_lo, ci_hi = _bootstrap_ci_rank_biserial(
        diffs, n_resamples=n_resamples, seed=seed, ci_level=ci_level,
    )
    return ExploratoryTestResult(
        hypothesis=hypothesis, task=task, cond_a=cond_a, cond_b=cond_b,
        model=model, n_pairs=n, n_pos=pos, n_neg=neg, n_tie=tie,
        median_diff=med, statistic=stat, raw_p=raw_p, r_rb=r,
        ci_low=ci_lo, ci_high=ci_hi, status="ok", diffs=list(diffs),
    )


# --------------------------------------------------------------------------
# Analysis 1: E1-E3 structural decomposition (aggregated across models)
# --------------------------------------------------------------------------

def analyze_e1_e3_decomposition(
    score_table: dict[tuple[str, str, str, str], float],
    models: list[str],
    func_ids: list[str],
    tasks: list[str],
    *,
    alternative: str,
    n_resamples: int,
    seed: int,
    ci_level: float,
    correction: str,
    alpha: float,
) -> list[ExploratoryTestResult]:
    """Run E1, E2, E3 across the given tasks. Returns a flat list of results."""
    results: list[ExploratoryTestResult] = []
    for hyp, cond_a, cond_b, _desc in EXPLORATORY_HYPOTHESES_E:
        for task in tasks:
            diffs = _build_paired_diffs_aggregated(
                score_table, func_ids, cond_a, cond_b, task, models,
            )
            results.append(_run_one_test(
                hyp, task, cond_a, cond_b, diffs,
                alternative=alternative, n_resamples=n_resamples,
                seed=seed, ci_level=ci_level,
            ))
    if correction == "holm":
        ps = [r.raw_p for r in results]
        adj = _holm_adjusted_p(ps)
        for r, p in zip(results, adj):
            r.holm_p = p
    return results


# --------------------------------------------------------------------------
# Analysis 2: per-model split of H1/H2/H3
# --------------------------------------------------------------------------

def analyze_per_model_split_h_family(
    score_table: dict[tuple[str, str, str, str], float],
    models: list[str],
    func_ids: list[str],
    tasks: list[str],
    *,
    alternative: str,
    n_resamples: int,
    seed: int,
    ci_level: float,
    correction: str,
    alpha: float,
) -> list[ExploratoryTestResult]:
    """Run H1, H2, H3 per model on the given tasks. Holm correction (when
    requested) is applied SEPARATELY within each model's family — we do not
    pool across models, because the per-model results are exploratory
    breakdowns whose interpretive value lies in the model-by-model pattern."""
    results: list[ExploratoryTestResult] = []
    by_model_ranges: list[tuple[str, int, int]] = []
    for model in models:
        start = len(results)
        for hyp, cond_a, cond_b, _desc in HYPOTHESES_H:
            for task in tasks:
                diffs = _build_paired_diffs_single_model(
                    score_table, func_ids, cond_a, cond_b, task, model,
                )
                results.append(_run_one_test(
                    hyp, task, cond_a, cond_b, diffs,
                    alternative=alternative, n_resamples=n_resamples,
                    seed=seed, ci_level=ci_level, model=model,
                ))
        by_model_ranges.append((model, start, len(results)))
    if correction == "holm":
        for _model, start, end in by_model_ranges:
            ps = [r.raw_p for r in results[start:end]]
            adj = _holm_adjusted_p(ps)
            for r, p in zip(results[start:end], adj):
                r.holm_p = p
    return results


# --------------------------------------------------------------------------
# Output assembly
# --------------------------------------------------------------------------

def _result_to_dict(r: ExploratoryTestResult) -> dict[str, Any]:
    def fmt(x: Any) -> Any:
        if x is None:
            return None
        if isinstance(x, float) and math.isnan(x):
            return None
        return x
    return {
        "hypothesis": r.hypothesis,
        "task": r.task,
        "cond_a": r.cond_a,
        "cond_b": r.cond_b,
        "model": r.model,
        "n_pairs": r.n_pairs,
        "n_pos": r.n_pos,
        "n_neg": r.n_neg,
        "n_tie": r.n_tie,
        "median_diff": fmt(r.median_diff),
        "statistic": fmt(r.statistic),
        "raw_p": fmt(r.raw_p),
        "holm_p": fmt(r.holm_p),
        "r_rb": fmt(r.r_rb),
        "ci_low": fmt(r.ci_low),
        "ci_high": fmt(r.ci_high),
        "status": r.status,
    }


def _git_head(repo: Path) -> str:
    try:
        out = subprocess.check_output(
            ["git", "-C", str(repo), "rev-parse", "HEAD"],
            stderr=subprocess.DEVNULL,
        )
        return out.decode().strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return "unknown"


def _build_input_summary(
    records: list[dict[str, Any]],
    excluded: int,
    func_ids: list[str],
) -> dict[str, Any]:
    ok_records = [r for r in records if r.get("status") == "ok"]
    return {
        "n_score_files_scanned": len(records),
        "n_records_loaded": len(records),
        "n_excluded_status_not_ok": excluded,
        "n_analytical": len(ok_records),
        "models_in_data": sorted({r.get("model_id", "") for r in ok_records}),
        "conditions_in_data": sorted({r.get("condition", "") for r in ok_records}),
        "tasks_in_data": sorted({r.get("task", "") for r in ok_records}),
        "func_ids_used": list(func_ids),
    }


def _build_output(
    *,
    run_id: str,
    results_dir: Path,
    records: list[dict[str, Any]],
    excluded: int,
    func_ids: list[str],
    analyses: dict[str, list[ExploratoryTestResult]],
    method_metadata: dict[str, Any],
) -> dict[str, Any]:
    repo_root = Path(__file__).resolve().parents[2]
    return {
        "lumen_schema": LUMEN_SCHEMA,
        "framing_disclaimer": FRAMING_DISCLAIMER,
        "run_id": run_id,
        "results_dir": str(results_dir),
        "analyzed_at": datetime.now(timezone.utc).isoformat(),
        "git_head": _git_head(repo_root),
        "input_summary": _build_input_summary(records, excluded, func_ids),
        "method_metadata": method_metadata,
        "analyses": {
            name: [_result_to_dict(r) for r in results]
            for name, results in analyses.items()
        },
    }


CSV_FIELDS = [
    "analysis", "hypothesis", "task", "cond_a", "cond_b", "model",
    "n_pairs", "n_pos", "n_neg", "n_tie",
    "median_diff", "statistic", "raw_p", "holm_p", "r_rb",
    "ci_low", "ci_high", "status",
]


def _write_csv(path: Path, analyses: dict[str, list[ExploratoryTestResult]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=CSV_FIELDS, extrasaction="ignore")
        writer.writeheader()
        for analysis_name, results in analyses.items():
            for r in results:
                row = _result_to_dict(r)
                row["analysis"] = analysis_name
                writer.writerow(row)


def _print_summary(output: dict[str, Any]) -> None:
    print("=" * 78)
    print("LUMEN EXPLORATORY ANALYSIS — non-confirmatory results")
    print(f"Run: {output['run_id']}")
    print(f"Analyzed at: {output['analyzed_at']}")
    print(f"git HEAD: {output['git_head']}")
    print(f"Schema: {output['lumen_schema']}")
    md = output["method_metadata"]
    print(f"Wilcoxon alternative: {md['wilcoxon_alternative']}")
    print(f"Bootstrap: {md['bootstrap_resamples']} resamples, "
          f"{int(md['ci_level']*100)}% percentile, seed={md['rng_seed']}")
    print(f"Correction: {md['correction']}  alpha: {md['alpha']}")
    summ = output["input_summary"]
    print(f"Records: {summ['n_records_loaded']} scanned, "
          f"{summ['n_excluded_status_not_ok']} excluded (status!=ok), "
          f"{summ['n_analytical']} analytical")
    print(f"Models in data: {summ['models_in_data']}")
    print(f"Conditions in data: {summ['conditions_in_data']}")
    print(f"Tasks in data: {summ['tasks_in_data']}")
    print(f"func_ids used: {len(summ['func_ids_used'])}")
    print("-" * 78)
    for name, results in output["analyses"].items():
        print(f"\n[{name}]")
        print(
            f"{'Hyp':<4} {'Task':<5} {'A':<5} {'B':<5} {'Model':<18} "
            f"{'n':>3} {'pos':>3} {'neg':>3} {'tie':>3} "
            f"{'med_d':>8} {'W':>9} {'rawP':>7} {'holmP':>7} "
            f"{'r_rb':>7} {'CIlo':>7} {'CIhi':>7}  status"
        )
        for r in results:
            def f(x: Any, width: int = 7, prec: int = 3) -> str:
                if x is None or (isinstance(x, float) and math.isnan(x)):
                    return f"{'nan':>{width}}"
                return f"{x:{width}.{prec}f}"
            print(
                f"{r['hypothesis']:<4} {r['task']:<5} "
                f"{r['cond_a']:<5} {r['cond_b']:<5} {(r['model'] or '-'):<18} "
                f"{r['n_pairs']:>3} {r['n_pos']:>3} {r['n_neg']:>3} {r['n_tie']:>3} "
                f"{f(r['median_diff'], 8, 3)} "
                f"{f(r['statistic'], 9, 3)} "
                f"{f(r['raw_p'], 7, 3)} "
                f"{f(r['holm_p'], 7, 3)} "
                f"{f(r['r_rb'], 7, 3)} "
                f"{f(r['ci_low'], 7, 3)} "
                f"{f(r['ci_high'], 7, 3)}  {r['status']}"
            )
    print("=" * 78)


# --------------------------------------------------------------------------
# Main entry point
# --------------------------------------------------------------------------

def run_exploratory_analyses(
    *,
    results_dir: Path,
    run_id: str,
    func_ids: list[str] | None,
    analyses: list[str],
    correction: str,
    bootstrap_resamples: int,
    seed: int,
    alpha: float,
    alternative: str,
    ci_level: float = DEFAULT_CI_LEVEL,
) -> dict[str, Any]:
    """Library entry point. Returns the output dict; does not write to disk."""
    records = _load_score_records_for_run(results_dir, run_id)

    method_metadata = {
        "wilcoxon_alternative": alternative,
        "effect_size": "rank_biserial_correlation",
        "rank_biserial_formulation": (
            "(T+ - T-) / (T+ + T-) on tied-averaged ranks of |d| over "
            "non-zero diffs (matches analyze_confirmatory.py:_rank_biserial)"
        ),
        "bootstrap_resamples": bootstrap_resamples,
        "ci_level": ci_level,
        "ci_method": "percentile",
        "rng_seed": seed,
        "correction": correction,
        "alpha": alpha,
    }

    if not records:
        return _build_output(
            run_id=run_id, results_dir=results_dir,
            records=records, excluded=0, func_ids=func_ids or [],
            analyses={name: [] for name in analyses},
            method_metadata=method_metadata,
        )

    # Determine models from data (do not impose FROZEN_MODELS)
    models = sorted({str(r["model_id"]) for r in records if r.get("status") == "ok"})

    # Determine func_ids: use --func-ids if provided, else all ok-status func_ids
    if func_ids is None:
        func_ids = sorted({str(r["func_id"]) for r in records if r.get("status") == "ok"})

    # Build score table (status!=ok exclusion happens here)
    score_table, excluded = _build_score_table(records, models)

    # Determine tasks present in data
    tasks_in_data = sorted({str(r["task"]) for r in records if r.get("status") == "ok"})
    tasks = [t for t in TASKS_ALL if t in tasks_in_data]

    out_analyses: dict[str, list[ExploratoryTestResult]] = {}
    if "e1_e3_decomposition" in analyses:
        out_analyses["e1_e3_decomposition"] = analyze_e1_e3_decomposition(
            score_table, models, func_ids, tasks,
            alternative=alternative, n_resamples=bootstrap_resamples,
            seed=seed, ci_level=ci_level, correction=correction, alpha=alpha,
        )
    if "per_model_split_h1_h2_h3" in analyses:
        out_analyses["per_model_split_h1_h2_h3"] = analyze_per_model_split_h_family(
            score_table, models, func_ids, tasks,
            alternative=alternative, n_resamples=bootstrap_resamples,
            seed=seed, ci_level=ci_level, correction=correction, alpha=alpha,
        )

    return _build_output(
        run_id=run_id, results_dir=results_dir,
        records=records, excluded=excluded, func_ids=func_ids,
        analyses=out_analyses, method_metadata=method_metadata,
    )


def _dict_to_result(d: dict[str, Any]) -> ExploratoryTestResult:
    """Reconstruct a result object from its dict form (used by main() for CSV)."""
    def num(v: Any) -> float:
        return float("nan") if v is None else float(v)
    return ExploratoryTestResult(
        hypothesis=d["hypothesis"], task=d["task"],
        cond_a=d["cond_a"], cond_b=d["cond_b"], model=d.get("model", ""),
        n_pairs=d["n_pairs"], n_pos=d["n_pos"], n_neg=d["n_neg"], n_tie=d["n_tie"],
        median_diff=num(d["median_diff"]),
        statistic=num(d["statistic"]),
        raw_p=num(d["raw_p"]),
        holm_p=d["holm_p"],
        r_rb=num(d["r_rb"]),
        ci_low=num(d["ci_low"]),
        ci_high=num(d["ci_high"]),
        status=d["status"],
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Lumen exploratory analyses (non-confirmatory). "
                    "Runs E1-E3 structural decomposition and/or per-model "
                    "split of H1-H3 on a single run's score files.",
    )
    parser.add_argument("--results-dir", required=True, type=Path,
                        help="Root directory containing runs/<run-id>/.")
    parser.add_argument("--run-id", required=True, type=str,
                        help="Single run identifier to analyze.")
    parser.add_argument("--output-json", required=True, type=Path,
                        help="Path to write the JSON results.")
    parser.add_argument("--output-csv", required=True, type=Path,
                        help="Path to write the long-form CSV.")
    parser.add_argument("--func-ids", nargs="+", default=None,
                        help="Restrict to these func_ids (default: all in data).")
    parser.add_argument("--correction", choices=["none", "holm"], default="none",
                        help="Multiplicity correction (default: none, "
                             "per Constitution §17.4 exploratory convention).")
    parser.add_argument("--analyses", nargs="+",
                        default=["e1_e3_decomposition", "per_model_split_h1_h2_h3"],
                        choices=["e1_e3_decomposition", "per_model_split_h1_h2_h3"],
                        help="Which analyses to run.")
    parser.add_argument("--bootstrap-resamples", type=int,
                        default=DEFAULT_BOOTSTRAP_RESAMPLES,
                        help=f"Bootstrap resamples for CI (default: {DEFAULT_BOOTSTRAP_RESAMPLES}).")
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED,
                        help=f"RNG seed for bootstrap reproducibility (default: {DEFAULT_SEED}).")
    parser.add_argument("--alpha", type=float, default=DEFAULT_ALPHA,
                        help="Significance level for Holm correction (default: 0.05).")
    parser.add_argument("--alternative", choices=["two-sided", "greater", "less"],
                        default=DEFAULT_ALTERNATIVE,
                        help="Wilcoxon alternative (default: greater, matches "
                             "confirmatory directional pre-registration).")
    parser.add_argument("--ci-level", type=float, default=DEFAULT_CI_LEVEL,
                        help="Bootstrap CI level (default: 0.95).")
    args = parser.parse_args(argv)

    output = run_exploratory_analyses(
        results_dir=args.results_dir,
        run_id=args.run_id,
        func_ids=args.func_ids,
        analyses=args.analyses,
        correction=args.correction,
        bootstrap_resamples=args.bootstrap_resamples,
        seed=args.seed,
        alpha=args.alpha,
        alternative=args.alternative,
        ci_level=args.ci_level,
    )

    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    with args.output_json.open("w") as fh:
        json.dump(output, fh, indent=2)

    csv_analyses: dict[str, list[ExploratoryTestResult]] = {
        name: [_dict_to_result(d) for d in items]
        for name, items in output["analyses"].items()
    }
    _write_csv(args.output_csv, csv_analyses)

    _print_summary(output)
    print(f"\nJSON: {args.output_json}")
    print(f"CSV:  {args.output_csv}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
