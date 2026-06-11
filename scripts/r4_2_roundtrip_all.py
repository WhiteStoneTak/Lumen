#!/usr/bin/env python3
"""R4-2: run the C4->C1+->C4' round trip on all 30 confirmatory functions.

Writes per-function JSONs + an aggregate summary under
results/analysis/exploratory/roundtrip/. Exploratory; no frozen artifact
touched. See docs/roundtrip-comparison-spec.md and src/experiment/roundtrip.py.
"""

from __future__ import annotations

import json
import statistics
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from experiment.roundtrip import run_func  # noqa: E402

GOV = json.loads((ROOT / "data/dataset/confirmatory_governance.json").read_text())
FUNC_IDS = GOV["full_t2_plan"]["retained_func_ids"]
OUT = ROOT / "results/analysis/exploratory/roundtrip"

SCALAR_METRICS = [
    "node_kind_retention",
    "type_annotation_retention",
    "parent_child_retention",
    "cross_reference_retention",
]
CONTRACT_KINDS = ["preconditions", "postconditions", "invariants"]


def _agg(vals: list[float]) -> dict:
    vals = [v for v in vals if v is not None]
    if not vals:
        return {"n": 0, "mean": None, "min": None, "max": None}
    return {
        "n": len(vals),
        "mean": round(statistics.mean(vals), 4),
        "min": round(min(vals), 4),
        "max": round(max(vals), 4),
    }


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    per_func = []
    for fid in FUNC_IDS:
        res = run_func(fid)
        (OUT / f"{fid}.json").write_text(json.dumps(res, indent=2) + "\n")
        per_func.append(res)

    cols: dict[str, list] = {m: [] for m in SCALAR_METRICS}
    contract_cols: dict[str, list] = {k: [] for k in CONTRACT_KINDS}
    hash_matches = 0
    for r in per_func:
        m = r["metrics"]
        for k in SCALAR_METRICS:
            cols[k].append(m[k])
        for k in CONTRACT_KINDS:
            contract_cols[k].append(m["contract_clause_retention"][k])
        hash_matches += 1 if m["canonical_hash_agreement"] else 0

    summary = {
        "lumen_schema": "roundtrip-summary-v1",
        "exploratory": True,
        "n_functions": len(per_func),
        "func_ids": FUNC_IDS,
        "aggregate": {m: _agg(cols[m]) for m in SCALAR_METRICS}
        | {f"contract_{k}": _agg(contract_cols[k]) for k in CONTRACT_KINDS},
        "canonical_hash_agreement_count": hash_matches,
        "note": (
            "EXPLORATORY C4->C1+->C4' recovery over the 30 retained confirmatory "
            "functions. High content retention with hash_agreement=false is the "
            "expected lossy-but-information-preserving C1+ signature (paper §3.3)."
        ),
    }
    (OUT / "roundtrip_summary.json").write_text(json.dumps(summary, indent=2) + "\n")

    print(f"Round-trip over {len(per_func)} functions -> {OUT}")
    for m in SCALAR_METRICS:
        a = summary["aggregate"][m]
        print(f"  {m:28s} mean={a['mean']} min={a['min']} max={a['max']}")
    for k in CONTRACT_KINDS:
        a = summary["aggregate"][f"contract_{k}"]
        print(f"  contract_{k:18s} mean={a['mean']} min={a['min']} max={a['max']}")
    print(f"  canonical_hash_agreement: {hash_matches}/{len(per_func)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
