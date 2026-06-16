"""Pre-declared sensitivity analyses for the R5 confirmatory studies.

Pre-registered in docs/preregistrations/{t1,t3}-v1.md §5. Reuses the FROZEN
statistical primitives from analyze_confirmatory.py so every quantity is
computed with the same Wilcoxon / rank-biserial / bootstrap-CI code as the
confirmatory result; this script adds only the pre-declared *variants*
(MNAR imputation, tie/effective-n diagnostics, per-model breakdown).

It does NOT alter the frozen confirmatory decision — that is the output of
`analyze_confirmatory.py --with-ci`. This is the sensitivity layer around it.

Run:
  PYTHONPATH=src python3 scripts/r5_sensitivity.py --task T1 \
      --out results/analysis/exploratory/full_t1_confirmatory_v1/sensitivity.json
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from experiment.analyze_confirmatory import (
    FROZEN_MODELS,
    HYPOTHESES,
    _bootstrap_ci_rank_biserial,
    _load_score_files,
    _rank_biserial,
    _wilcoxon_signed_rank,
)

REPO = Path(__file__).resolve().parent.parent
# Worst-case max score per task (the top of the realised scale).
TASK_MAX = {"T1": 1.0, "T2": 3.0, "T3": 1.0}


def _records_for_task(task: str, runs_dir: Path) -> list[dict]:
    recs = _load_score_files(runs_dir)
    return [r for r in recs if r.get("task") == task
            and r.get("model_id") in FROZEN_MODELS]


def _func_ids(records: list[dict]) -> list[str]:
    return sorted({str(r["func_id"]) for r in records})


def _ok_table(records: list[dict]) -> dict[tuple, float]:
    """(func, cond, model) -> score, only status == ok."""
    t = {}
    for r in records:
        if r.get("status") == "ok":
            t[(str(r["func_id"]), str(r["condition"]), str(r["model_id"]))] = float(r["score"])
    return t


def _status_table(records: list[dict]) -> dict[tuple, str]:
    return {(str(r["func_id"]), str(r["condition"]), str(r["model_id"])): str(r.get("status"))
            for r in records}


def _status_counts(records: list[dict]) -> dict:
    out: dict[str, dict[str, int]] = {}
    for r in records:
        key = f"{r['condition']}/{r['model_id']}"
        out.setdefault(key, {})
        s = str(r.get("status"))
        out[key][s] = out[key].get(s, 0) + 1
    return out


def _agg_complete(ok: dict, funcs, cond, models=FROZEN_MODELS):
    """Per-func mean across models, only where ALL present models have an ok score."""
    res = {}
    for f in funcs:
        vals = [ok[(f, cond, m)] for m in models if (f, cond, m) in ok]
        res[f] = (sum(vals) / len(vals)) if len(vals) == len(models) else None
    return res


def _agg_worstcase(ok: dict, funcs, cond, *, favor: str, task: str, models=FROZEN_MODELS):
    """Worst-case imputation for a directional H_a where `cond` is the
    *expected-higher* (favor='A') or *expected-lower* (favor='B') condition.

    To make rejection HARDER: impute missing 'A' cells as 0.0 (min) and missing
    'B' cells as TASK_MAX. Present cells use their ok score; per-func mean across
    models after imputation."""
    mx = TASK_MAX[task]
    res = {}
    for f in funcs:
        vals = []
        for m in models:
            if (f, cond, m) in ok:
                vals.append(ok[(f, cond, m)])
            else:
                vals.append(0.0 if favor == "A" else mx)
        res[f] = sum(vals) / len(vals)
    return res


def _paired_diffs(aggA, aggB, funcs):
    d = []
    for f in funcs:
        a, b = aggA.get(f), aggB.get(f)
        if a is not None and b is not None:
            d.append(a - b)
    return d


def _test_block(diffs: list[float]) -> dict:
    stat, p = _wilcoxon_signed_rank(diffs)
    r = _rank_biserial(diffs)
    lo, hi = _bootstrap_ci_rank_biserial(diffs)
    npos = sum(1 for x in diffs if x > 0)
    nneg = sum(1 for x in diffs if x < 0)
    nzero = sum(1 for x in diffs if x == 0)
    return {
        "n_pairs": len(diffs), "n_pos": npos, "n_neg": nneg, "n_zero": nzero,
        "effective_n": npos + nneg,
        "wilcoxon_W": None if stat != stat else round(stat, 4),
        "raw_p_one_sided": None if p != p else round(p, 6),
        "rank_biserial_r": round(r, 6),
        "ci95": [None if lo != lo else round(lo, 4), None if hi != hi else round(hi, 4)],
        "median_diff": (sorted(diffs)[len(diffs) // 2] if diffs else None),
        "mean_diff": (round(sum(diffs) / len(diffs), 6) if diffs else None),
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--task", required=True, choices=["T1", "T2", "T3"])
    ap.add_argument("--out", required=True)
    ap.add_argument("--runs-dir", default=str(REPO / "results" / "runs"),
                    help="Directory of run dirs to read (use a clean staging dir "
                         "to exclude exploratory C2/C3 advisory runs).")
    args = ap.parse_args()

    recs = _records_for_task(args.task, Path(args.runs_dir))
    funcs = _func_ids(recs)
    ok = _ok_table(recs)

    out: dict = {
        "lumen_schema": "r5-sensitivity-v1",
        "task": args.task,
        "frozen_models": list(FROZEN_MODELS),
        "n_functions": len(funcs),
        "status_counts_by_cell": _status_counts(recs),
    }

    # Confirmatory hypotheses, complete-case vs worst-case imputation
    hyp_out = {}
    for label, condA, condB, desc in HYPOTHESES:
        cc = _paired_diffs(
            _agg_complete(ok, funcs, condA), _agg_complete(ok, funcs, condB), funcs)
        # worst-case: make THIS H_a (A>B) hardest to reject
        wc = _paired_diffs(
            _agg_worstcase(ok, funcs, condA, favor="A", task=args.task),
            _agg_worstcase(ok, funcs, condB, favor="B", task=args.task), funcs)
        hyp_out[f"{label}/{args.task}"] = {
            "comparison": f"{condA} > {condB}", "description": desc,
            "complete_case": _test_block(cc),
            "worst_case_imputation": _test_block(wc),
        }
    out["confirmatory_hypotheses"] = hyp_out

    # Per-model breakdown (exploratory)
    per_model = {}
    for m in FROZEN_MODELS:
        mres = {}
        for label, condA, condB, _ in HYPOTHESES:
            aggA = {f: ok[(f, condA, m)] for f in funcs if (f, condA, m) in ok}
            aggB = {f: ok[(f, condB, m)] for f in funcs if (f, condB, m) in ok}
            mres[f"{label}/{args.task}"] = _test_block(_paired_diffs(aggA, aggB, funcs))
        per_model[m] = mres
    out["per_model_exploratory"] = per_model

    # Realised score distribution (ceiling diagnostic)
    vals = sorted(ok.values())
    out["score_distribution"] = {
        "n_ok": len(vals),
        "distinct_values": len(set(vals)),
        "min": (min(vals) if vals else None),
        "max": (max(vals) if vals else None),
        "frac_at_1.0": (round(sum(1 for v in vals if v == 1.0) / len(vals), 4) if vals else None),
        "mean": (round(sum(vals) / len(vals), 4) if vals else None),
    }

    outp = REPO / args.out
    outp.parent.mkdir(parents=True, exist_ok=True)
    outp.write_text(json.dumps(out, indent=2) + "\n", encoding="utf-8")
    try:
        shown = outp.relative_to(REPO)
    except ValueError:
        shown = outp
    print(f"wrote {shown}")
    # console summary of the primary
    prim = hyp_out[f"H1/{args.task}"]
    print(f"H1/{args.task} complete-case: {prim['complete_case']}")
    print(f"H1/{args.task} worst-case:    {prim['worst_case_imputation']}")
    print("status counts:", json.dumps(out["status_counts_by_cell"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
