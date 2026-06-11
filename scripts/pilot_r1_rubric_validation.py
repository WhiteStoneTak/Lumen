#!/usr/bin/env python3
"""R1-5 pilot: validate the new R1 scorers on a held-out set, no live calls.

The three anchor functions (clamp, count_vowels, is_sorted) are NOT among the
30 retained confirmatory functions, so they are a legitimate held-out pilot set
(same segregation rule as the paper's Phase-2 pilot, §3.0). They already have
T1/T2/T3 responses across C1/C1+/C2/C3/C4 from earlier pilot/preflight runs, so
this validation reuses those responses and makes NO new model calls.

It re-scores them with the new measurement-design scorers:
  * T2 location  -> score_t2_continuous.score_response_file (continuous)
  * T1           -> score_t1.score_t1                       (checklist fraction)
  * T3           -> score_t3.score_t3_sandboxed             (test-pass fraction)

and writes a segregated pilot artifact (run id contains "pilot") plus a
distribution / non-degeneracy / parse-failure summary.
"""

from __future__ import annotations

import glob
import json
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from experiment.score_t1 import score_t1  # noqa: E402
from experiment.score_t2_continuous import score_response_file as t2_loc_continuous  # noqa: E402
from experiment.score_t3 import score_t3_sandboxed  # noqa: E402

ANCHORS = {"clamp", "count_vowels", "is_sorted"}
RUN_ID = f"pilot_r1_rubric_validation_{datetime.now(timezone.utc):%Y%m%d}"
OUT_DIR = ROOT / "results" / "runs" / RUN_ID
PILOT_T1_CONDS = {"C1", "C1+", "C4"}  # the conditions the rubric pilot cares about


def _collect_cells() -> dict[tuple, dict]:
    """One scored anchor cell per (func, task, cond, model) with a live response."""
    cells: dict[tuple, dict] = {}
    for f in sorted(glob.glob(str(ROOT / "results/runs/*/scores/*.json"))):
        try:
            d = json.loads(Path(f).read_text())
        except Exception:
            continue
        if d.get("func_id") not in ANCHORS:
            continue
        if d.get("lumen_schema") != "scorer-result-v1":
            continue
        rr = d.get("response_ref", "")
        if not rr or not (ROOT / rr).exists():
            continue
        cells[(d["func_id"], d["task"], d["condition"], d["model_id"])] = d
    return cells


def _response_text(score_record: dict) -> str:
    resp = json.loads((ROOT / score_record["response_ref"]).read_text())
    return resp.get("response_text") or ""


def _scorer_input(rec: dict) -> dict:
    return {
        "lumen_schema": "scorer-input-v1",
        "func_id": rec["func_id"],
        "task": rec["task"],
        "condition": rec["condition"],
        "model_id": rec["model_id"],
        "response_ref": rec["response_ref"],
    }


def _summary(name: str, scores: list[float], statuses: list[str]) -> dict:
    nz = [s for s in scores if s is not None]
    distinct = sorted(set(round(s, 4) for s in nz))
    c = Counter(round(s, 4) for s in nz)
    tied_pairs = sum(v * (v - 1) // 2 for v in c.values())
    total_pairs = len(nz) * (len(nz) - 1) // 2 if len(nz) > 1 else 1
    return {
        "scorer": name,
        "n": len(scores),
        "n_scored": len(nz),
        "distinct_values": len(distinct),
        "min": min(nz) if nz else None,
        "max": max(nz) if nz else None,
        "all_zero": bool(nz) and all(s == 0.0 for s in nz),
        "saturated_single_value": len(distinct) <= 1,
        "tied_pair_fraction": round(tied_pairs / total_pairs, 4),
        "status_counts": dict(Counter(statuses)),
        "distinct_value_sample": distinct[:15],
    }


def main() -> int:
    cells = _collect_cells()
    records = {"T1": [], "T2_location": [], "T3": []}
    t1_scores, t1_status = [], []
    t2_scores, t2_status = [], []
    t3_scores, t3_status = [], []

    for (func, task, cond, model), rec in sorted(cells.items()):
        if task == "T2":
            r = t2_loc_continuous(rec)
            t2_scores.append(r["location_continuous"])
            t2_status.append("ok")
            records["T2_location"].append(r)
        elif task == "T1":
            r = score_t1(_scorer_input(rec), _response_text(rec))
            t1_scores.append(r["score"] if r["status"] == "ok" else None)
            t1_status.append(r["status"])
            records["T1"].append({k: r[k] for k in ("func_id", "condition", "model_id", "score", "status")})
        elif task == "T3":
            r = score_t3_sandboxed(_scorer_input(rec), _response_text(rec))
            t3_scores.append(r["score"] if r["status"] == "ok" else None)
            t3_status.append(r["status"])
            records["T3"].append({k: r[k] for k in ("func_id", "condition", "model_id", "score", "status")})

    summaries = {
        "T1_checklist": _summary("T1_checklist", t1_scores, t1_status),
        "T2_location_continuous": _summary("T2_location_continuous", t2_scores, t2_status),
        "T3_testpass_sandboxed": _summary("T3_testpass_sandboxed", t3_scores, t3_status),
    }

    result = {
        "lumen_schema": "r1-rubric-pilot-v1",
        "pilot": True,
        "segregation_note": (
            "Held-out pilot. Functions clamp/count_vowels/is_sorted are NOT in "
            "the 30 retained confirmatory functions. NOT to be pooled with "
            "confirmatory data (Constitution / paper §3.0). No new model calls; "
            "reuses existing pilot/preflight responses."
        ),
        "run_id": RUN_ID,
        "anchors": sorted(ANCHORS),
        "n_cells": len(cells),
        "summaries": summaries,
        "records": records,
    }

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out = OUT_DIR / "pilot_rubric_validation.json"
    out.write_text(json.dumps(result, indent=2) + "\n")

    print(f"Pilot rubric validation -> {out}  ({len(cells)} anchor cells)")
    for name, s in summaries.items():
        print(
            f"  {name:26s} n_scored={s['n_scored']:>3}  distinct={s['distinct_values']:>2}  "
            f"min={s['min']}  max={s['max']}  all_zero={s['all_zero']}  "
            f"tie_frac={s['tied_pair_fraction']}  status={s['status_counts']}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
