"""Bootstrap CI for confirmatory T2 rank-biserial effect sizes.

Reimplements the kernel from src/experiment/analyze_exploratory.py
(_rank_biserial / _bootstrap_ci_rank_biserial) without importing any
project module. Reads score JSONs from
results/runs/full_t2_confirmatory_v2/scores/ and computes paired
differences per func_id (mean across the two confirmatory models)
for three pairwise hypotheses on T2.

Hypotheses:
    H1: C4 vs C1plus
    H2: C4 vs C1
    H3: C1plus vs C1

Bootstrap: 10000 resamples, percentile method, 95% CI,
seed = 20260427 via np.random.default_rng(20260427).
"""

from __future__ import annotations

import glob
import json
import os
import time
from collections import defaultdict

import numpy as np

ROOT = "/Users/takumi/Code/Lumen"
SCORES_GLOB = os.path.join(
    ROOT, "results/runs/full_t2_confirmatory_v2/scores/*.json"
)
OUTPUT_PATH = os.path.join(ROOT, "scratch/bootstrap_ci_results.json")

SEED = 20260427
N_RESAMPLES = 10000
CI_LEVEL = 0.95
MODELS = ("gpt-5.4", "claude-opus-4-6")
TASK = "T2"


def _rank_biserial(diffs):
    nonzero = [d for d in diffs if d != 0.0]
    if not nonzero:
        return 0.0
    abs_vals = sorted(range(len(nonzero)), key=lambda i: abs(nonzero[i]))
    abs_sorted = [abs(nonzero[i]) for i in abs_vals]
    ranks = [0.0] * len(nonzero)
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


def _bootstrap_ci(diffs, n_resamples, seed, ci_level):
    nonzero_count = sum(1 for d in diffs if d != 0.0)
    if nonzero_count < 2:
        return float("nan"), float("nan")
    rng = np.random.default_rng(seed)
    n = len(diffs)
    arr = np.asarray(diffs, dtype=float)
    samples = np.empty(n_resamples, dtype=float)
    for i in range(n_resamples):
        idx = rng.integers(0, n, size=n)
        samples[i] = _rank_biserial(arr[idx].tolist())
    lo_q = (1.0 - ci_level) / 2.0
    hi_q = 1.0 - lo_q
    return float(np.quantile(samples, lo_q)), float(np.quantile(samples, hi_q))


def load_scores():
    """Returns dict[(func_id, condition, model_id)] -> score and stats."""
    by_key = {}
    files = sorted(glob.glob(SCORES_GLOB))
    n_total = len(files)
    n_ok = 0
    for fp in files:
        with open(fp) as f:
            obj = json.load(f)
        if obj.get("task") != TASK:
            continue
        if obj.get("status") != "ok":
            continue
        n_ok += 1
        key = (obj["func_id"], obj["condition"], obj["model_id"])
        by_key[key] = float(obj["score"])
    return by_key, n_total, n_ok


def paired_diffs(scores, cond_a, cond_b):
    """For each func_id, mean across both models in cond_a minus same in cond_b."""
    by_func_a = defaultdict(list)
    by_func_b = defaultdict(list)
    for (fid, cond, model), s in scores.items():
        if model not in MODELS:
            continue
        if cond == cond_a:
            by_func_a[fid].append(s)
        elif cond == cond_b:
            by_func_b[fid].append(s)
    func_ids = sorted(set(by_func_a) & set(by_func_b))
    diffs = []
    for fid in func_ids:
        a = by_func_a[fid]
        b = by_func_b[fid]
        assert len(a) == len(MODELS), f"{fid} {cond_a}: got {len(a)} models"
        assert len(b) == len(MODELS), f"{fid} {cond_b}: got {len(b)} models"
        diffs.append(sum(a) / len(a) - sum(b) / len(b))
    return func_ids, diffs


def main():
    t0 = time.time()
    scores, n_total, n_ok = load_scores()
    print(f"Loaded {n_ok}/{n_total} score files (status=ok, task=T2)")

    # Note: filenames use "C1plus" but JSON `condition` field uses "C1+".
    hypotheses = [
        ("H1", "C4 vs C1+", "C4", "C1+"),
        ("H2", "C4 vs C1", "C4", "C1"),
        ("H3", "C1+ vs C1", "C1+", "C1"),
    ]

    results = {}
    for hid, label, ca, cb in hypotheses:
        func_ids, diffs = paired_diffs(scores, ca, cb)
        n = len(diffs)
        n_nonzero = sum(1 for d in diffs if d != 0.0)
        r_rb = _rank_biserial(diffs)
        ci_lo, ci_hi = _bootstrap_ci(diffs, N_RESAMPLES, SEED, CI_LEVEL)
        results[hid] = {
            "label": label,
            "cond_a": ca,
            "cond_b": cb,
            "n_pairs": n,
            "n_nonzero": n_nonzero,
            "r_rb": r_rb,
            "ci_low": ci_lo,
            "ci_high": ci_hi,
            "func_ids": func_ids,
            "diffs": diffs,
        }
        print(
            f"{hid} ({label}): r_rb={r_rb:.6f} 95% CI=[{ci_lo:.4f}, {ci_hi:.4f}] "
            f"n={n} n_nonzero={n_nonzero}"
        )

    wall = time.time() - t0

    out = {
        "seed": SEED,
        "resamples": N_RESAMPLES,
        "method": "percentile",
        "ci_level": CI_LEVEL,
        "task": TASK,
        "models": list(MODELS),
        "n_score_files_total": n_total,
        "n_score_files_ok": n_ok,
        "wall_clock_seconds": wall,
        "hypotheses": {
            hid: {k: v for k, v in r.items() if k != "diffs"}
            | {"diffs": r["diffs"]}
            for hid, r in results.items()
        },
    }
    with open(OUTPUT_PATH, "w") as f:
        json.dump(out, f, indent=2)
    print(f"Wrote {OUTPUT_PATH}")
    print(f"Wall clock: {wall:.2f} s")


if __name__ == "__main__":
    main()
