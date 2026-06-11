#!/usr/bin/env python3
"""R2-2 (L3-05): parse-failure baseline + worst-case-imputation sensitivity.

EXPLORATORY. Quantifies the missing-not-at-random (MNAR) risk in the gpt-5.5
successor replication, where 12/120 gpt-5.5 items were parse failures
concentrated in non-C1 conditions, and tests whether the H3 directional
inversion survives imputing those failures at the worst-case score (0) instead
of excluding them.

Reuses the exploratory analysis kernel (same Wilcoxon/r_rb/bootstrap as the
confirmatory pipeline). Does not modify any frozen artifact. Writes an
exploratory JSON under results/analysis/exploratory/.
"""

from __future__ import annotations

import glob
import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from experiment.analyze_exploratory import (  # noqa: E402
    HYPOTHESES_H,
    _build_paired_diffs_single_model,
    _run_one_test,
)

SEED = 20260427
N_RESAMPLES = 10000
CI_LEVEL = 0.95
ALT = "greater"
TASK = "T2"
CONFIRMATORY_RUN = "full_t2_confirmatory_v2"
SUCCESSOR_RUN = "t2_frontier_successor_replication"


def _load_records(run_id: str) -> list[dict]:
    recs = []
    for f in sorted(glob.glob(str(ROOT / f"results/runs/{run_id}/scores/*.json"))):
        d = json.loads(Path(f).read_text())
        if d.get("lumen_schema") == "scorer-result-v1" and d.get("task") == TASK:
            recs.append(d)
    return recs


def _parse_failure_table(recs: list[dict]) -> dict:
    cells = Counter()
    by_cond = Counter()
    total = Counter()
    for r in recs:
        total[r["model_id"]] += 1
        if r.get("status") != "ok":
            cells[f'{r["condition"]}|{r["model_id"]}|{r["status"]}'] += 1
            by_cond[r["condition"]] += 1
    n_fail = sum(cells.values())
    return {
        "n_records": len(recs),
        "n_parse_failures": n_fail,
        "per_cell": dict(sorted(cells.items())),
        "per_condition": dict(sorted(by_cond.items())),
        "rate": round(n_fail / len(recs), 4) if recs else 0.0,
    }


def _score_table(recs: list[dict], *, impute_zero: bool) -> dict:
    """(func,task,cond,model)->score. exclude: drop non-ok; impute_zero: non-ok->0.0."""
    table = {}
    for r in recs:
        key = (r["func_id"], r["task"], r["condition"], r["model_id"])
        if r.get("status") == "ok":
            table[key] = float(r["score"])
        elif impute_zero:
            table[key] = 0.0
    return table


def _per_model_h(table: dict, models: list[str], func_ids: list[str]) -> list[dict]:
    out = []
    for model in models:
        for hyp, cond_a, cond_b, _desc in HYPOTHESES_H:
            diffs = _build_paired_diffs_single_model(table, func_ids, cond_a, cond_b, TASK, model)
            r = _run_one_test(
                hyp, TASK, cond_a, cond_b, diffs,
                alternative=ALT, n_resamples=N_RESAMPLES, seed=SEED, ci_level=CI_LEVEL,
                model=model,
            )
            out.append({
                "hypothesis": hyp, "model": model, "n_pairs": r.n_pairs,
                "r_rb": round(r.r_rb, 6), "ci": [round(r.ci_low, 6), round(r.ci_high, 6)],
                "raw_p": round(r.raw_p, 6) if r.raw_p == r.raw_p else None,
                "status": r.status,
            })
    return out


def main() -> int:
    conf = _load_records(CONFIRMATORY_RUN)
    succ = _load_records(SUCCESSOR_RUN)
    func_ids = sorted({r["func_id"] for r in succ})
    succ_models = sorted({r["model_id"] for r in succ})

    baseline_excl = _per_model_h(_score_table(succ, impute_zero=False), succ_models, func_ids)
    worstcase_imp = _per_model_h(_score_table(succ, impute_zero=True), succ_models, func_ids)

    # H3 direction survival check
    def h3(rows):
        return {r["model"]: r["r_rb"] for r in rows if r["hypothesis"] == "H3"}
    h3_excl, h3_imp = h3(baseline_excl), h3(worstcase_imp)
    survives = all(h3_imp[m] < 0 for m in h3_imp) and all(h3_excl[m] < 0 for m in h3_excl)

    result = {
        "lumen_schema": "r2-2-parse-failure-sensitivity-v1",
        "exploratory": True,
        "note": (
            "EXPLORATORY. Parse-failure MNAR sensitivity for the successor "
            "replication. Not confirmatory. Frozen artifacts untouched."
        ),
        "parse_failure_tables": {
            "confirmatory_pair": _parse_failure_table(conf),
            "successor_pair": _parse_failure_table(succ),
        },
        "successor_H_family_per_model": {
            "exclude_parse_failures": baseline_excl,
            "worstcase_impute_zero": worstcase_imp,
        },
        "h3_inversion": {
            "h3_r_rb_exclude": h3_excl,
            "h3_r_rb_worstcase_impute": h3_imp,
            "inversion_survives_worstcase": survives,
        },
        "params": {"seed": SEED, "resamples": N_RESAMPLES, "ci_level": CI_LEVEL,
                   "alternative": ALT, "task": TASK},
    }

    out = ROOT / "results/analysis/exploratory/r2_2_parse_failure_sensitivity/sensitivity.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, indent=2) + "\n")

    pf = result["parse_failure_tables"]
    print("Parse-failure baseline:")
    print(f"  confirmatory pair: {pf['confirmatory_pair']['n_parse_failures']}/{pf['confirmatory_pair']['n_records']} "
          f"(rate {pf['confirmatory_pair']['rate']})")
    print(f"  successor pair:    {pf['successor_pair']['n_parse_failures']}/{pf['successor_pair']['n_records']} "
          f"(rate {pf['successor_pair']['rate']})  per-cell {pf['successor_pair']['per_cell']}")
    print("H3 r_rb (exclude -> worstcase impute):")
    for m in h3_imp:
        print(f"  {m}: {h3_excl[m]:+.4f} -> {h3_imp[m]:+.4f}")
    print(f"H3 inversion survives worst-case imputation: {survives}")
    print(f"wrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
