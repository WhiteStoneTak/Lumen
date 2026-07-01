"""Continuous T2 *patch-correctness* + *semantic-equivalence* metrics (EXPLORATORY).

Status: exploratory measurement-design instrument (backlog W-04). This module is
**not** part of the frozen confirmatory pipeline. It re-reads existing frozen T2
responses and produces separate, clearly-labelled exploratory scores; it never
mutates or re-runs ``score_t2.py`` or ``analyze_confirmatory.py``. It imports only
*pure, side-effect-free* helpers from the frozen scorers (fix extraction / patch
application / the sandboxed test runner) — importing does not alter them.

Why this exists
---------------
R1-2 (WOV-236) decided, with data, to keep the T2 *fix* sub-score **binary**,
deferring a continuous test-pass fraction and a semantic-equivalence metric as
*conditional follow-ups* — because (a) the execution sandbox (R1-4) did not yet
exist and (b) continuous *location* alone de-saturated the T2 composite. Both
conditions have since changed: the sandbox exists (``score_t3.run_t3_tests_
sandboxed``) and W-04 needs the fuller, ceiling-free battery for the falsifiable-
prediction test battery. This module builds the two parked metrics.

Metrics
-------
1. **patch_pass_fraction** ∈ [0, 1] — the model's extracted fix is applied to the
   buggy source and the linked T2 suite is run in a sandboxed subprocess;
   the score is ``passed / total`` instead of the frozen all-or-nothing 0/1.
2. **behavioral_agreement** ∈ [0, 1] (primary semantic-equivalence) — the model's
   patched function and the canonical reference implementation
   (``data/functions/raw/{func_id}.py``) are run over a deterministic, type-driven
   input battery (``diff_sampling``); the score is the output-agreement rate.
   Unsupported signatures (e.g. a callable parameter) → ``not_applicable``, never
   a silent 0.
3. **structural_equivalence** (secondary diagnostic) — normalized-AST equality
   (docstrings stripped) between the patched function and the reference, plus a
   node-sequence similarity ratio. Cheap and fully deterministic but near-binary;
   reported alongside the behavioral metric, not as the primary signal.

All three are reported next to the frozen binary ``fix`` sub-score. The
accompanying ``--reanalyze`` reports realised distinct-value counts and tie mass
so the anti-saturation claim is checked empirically, not asserted.
"""

from __future__ import annotations

import ast
import difflib
import json
import subprocess
import sys
import tempfile
import textwrap
from pathlib import Path
from typing import Any

from experiment import diff_sampling
from experiment.score_t2 import (
    _apply_fix_to_source,
    _extract_best_fix_line,
    extract_t2_claims,
)
from experiment.score_t3 import run_t3_tests_sandboxed

REPO_ROOT = Path(__file__).resolve().parents[2]
SCHEMA = "t2-patch-semantic-v1"

# Wall-clock budget for the differential-testing child process (whole battery).
_DIFF_TIMEOUT_S = 10.0
_DIFF_TIMEOUT_SENTINEL = "TIMEOUT:"


# ---------------------------------------------------------------------------
# Truth / reference loading
# ---------------------------------------------------------------------------

def _load_bug_truth(func_id: str) -> dict[str, Any]:
    path = REPO_ROOT / "data" / "ground_truth" / "bugs" / f"{func_id}.json"
    return json.loads(path.read_text(encoding="utf-8"))


def _reference_source(func_id: str) -> str:
    """Canonical correct implementation — the differential/structural oracle."""
    return (REPO_ROOT / "data" / "functions" / "raw" / f"{func_id}.py").read_text(
        encoding="utf-8"
    )


def _param_types(func_id: str) -> list[str] | None:
    """Parameter mypy types from the frozen IR layer, or None if unavailable."""
    ir_path = REPO_ROOT / "data" / "functions" / "ir" / f"{func_id}.json"
    if not ir_path.exists():
        return None
    ir = json.loads(ir_path.read_text(encoding="utf-8"))
    params = ir.get("type_info", {}).get("params")
    if params is None:
        return None
    return [p.get("mypy_type", "Any") for p in params]


# ---------------------------------------------------------------------------
# 1. Continuous patch correctness (test-pass fraction)
# ---------------------------------------------------------------------------

def patch_pass_fraction(
    buggy_source: str,
    truth: dict[str, Any],
    fix_line: str,
) -> dict[str, Any]:
    """Apply the model's fix and run the linked T2 suite → passed/total ∈ [0,1]."""
    patched = _apply_fix_to_source(buggy_source, truth["reference_fix"], fix_line)
    test_suite_path = (REPO_ROOT / truth["test_suite_ref"]).resolve()
    passed, total, err = run_t3_tests_sandboxed(patched, truth["func_id"], test_suite_path)
    if err:
        status = "timeout" if err.startswith("TIMEOUT:") else "exec_error"
        return {"status": status, "fraction": None, "passed": passed, "total": total,
                "detail": err[:200]}
    if total == 0:
        return {"status": "zero_tests", "fraction": None, "passed": 0, "total": 0}
    return {"status": "ok", "fraction": round(passed / total, 6),
            "passed": passed, "total": total}


# ---------------------------------------------------------------------------
# 2. Behavioral semantic equivalence (differential testing)
# ---------------------------------------------------------------------------

_DIFF_DRIVER = textwrap.dedent(
    '''
    import copy, importlib.util, json, math, sys

    def _load(name, path):
        spec = importlib.util.spec_from_file_location(name, path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod

    def _deep_equal(a, b):
        if isinstance(a, bool) or isinstance(b, bool):
            return a is b or a == b
        if isinstance(a, (int, float)) and isinstance(b, (int, float)):
            return math.isclose(a, b, rel_tol=1e-9, abs_tol=1e-9)
        if isinstance(a, (list, tuple)) and isinstance(b, (list, tuple)):
            return len(a) == len(b) and all(_deep_equal(x, y) for x, y in zip(a, b))
        if isinstance(a, dict) and isinstance(b, dict):
            return a.keys() == b.keys() and all(_deep_equal(a[k], b[k]) for k in a)
        return a == b

    ref_path, cand_path, func_id, inputs_path = sys.argv[1:5]
    try:
        ref = getattr(_load("_ref_" + func_id, ref_path), func_id)
        cand = getattr(_load("_cand_" + func_id, cand_path), func_id)
    except Exception as exc:  # noqa: BLE001
        print(json.dumps({"error": f"load: {type(exc).__name__}: {exc}"})); sys.exit(0)

    rows = json.load(open(inputs_path))
    agree = 0; evaluated = 0
    for args in rows:
        try:
            ra = ref(*copy.deepcopy(args)); r_exc = None
        except Exception as e:  # noqa: BLE001
            ra = None; r_exc = type(e).__name__
        try:
            ca = cand(*copy.deepcopy(args)); c_exc = None
        except Exception as e:  # noqa: BLE001
            ca = None; c_exc = type(e).__name__
        evaluated += 1
        if r_exc is not None or c_exc is not None:
            if r_exc == c_exc:
                agree += 1
        else:
            try:
                if _deep_equal(ra, ca):
                    agree += 1
            except Exception:  # noqa: BLE001
                pass
    print(json.dumps({"agree": agree, "evaluated": evaluated}))
    '''
)


def behavioral_agreement(
    cand_source: str,
    ref_source: str,
    func_id: str,
    param_types: list[str] | None,
) -> dict[str, Any]:
    """Output-agreement rate of ``cand`` vs the reference over a seeded battery."""
    if param_types is None or not diff_sampling.is_supported(param_types):
        return {"status": "not_applicable", "reason": "unsupported_param_types",
                "agreement": None}
    rows = diff_sampling.sample_inputs(param_types)
    if rows is None:
        return {"status": "not_applicable", "reason": "unsupported_param_types",
                "agreement": None}

    tmp: list[str] = []
    try:
        def _w(text: str, suffix: str) -> str:
            f = tempfile.NamedTemporaryFile(mode="w", suffix=suffix, delete=False,
                                            encoding="utf-8")
            f.write(text); f.close(); tmp.append(f.name); return f.name

        ref_p = _w(ref_source, ".py")
        cand_p = _w(cand_source, ".py")
        drv_p = _w(_DIFF_DRIVER, ".py")
        in_p = _w(json.dumps(rows), ".json")
        try:
            proc = subprocess.run(
                [sys.executable, drv_p, ref_p, cand_p, func_id, in_p],
                capture_output=True, text=True, timeout=_DIFF_TIMEOUT_S,
            )
        except subprocess.TimeoutExpired:
            return {"status": "timeout", "agreement": None}
        out = (proc.stdout or "").strip().splitlines()
        if not out:
            return {"status": "driver_error", "agreement": None,
                    "detail": (proc.stderr or "")[:200]}
        payload = json.loads(out[-1])
        if "error" in payload:
            return {"status": "driver_error", "agreement": None, "detail": payload["error"]}
        ev = payload["evaluated"]
        if ev == 0:
            return {"status": "zero_inputs", "agreement": None}
        return {"status": "ok", "agreement": round(payload["agree"] / ev, 6),
                "agree": payload["agree"], "evaluated": ev}
    finally:
        for p in tmp:
            try:
                Path(p).unlink()
            except OSError:
                pass


# ---------------------------------------------------------------------------
# 3. Structural (normalized-AST) equivalence — secondary diagnostic
# ---------------------------------------------------------------------------

def _extract_funcdef(source: str, func_id: str) -> ast.FunctionDef | None:
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return None
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == func_id:
            return node
    return None


def _strip_docstring(node: ast.FunctionDef) -> ast.FunctionDef:
    body = list(node.body)
    if (
        body
        and isinstance(body[0], ast.Expr)
        and isinstance(getattr(body[0], "value", None), ast.Constant)
        and isinstance(body[0].value.value, str)
    ):
        body = body[1:]
    clone = ast.FunctionDef(
        name=node.name, args=node.args, body=body or [ast.Pass()],
        decorator_list=[], returns=None, type_comment=None,
    )
    return ast.fix_missing_locations(clone)


def structural_equivalence(cand_source: str, ref_source: str, func_id: str) -> dict[str, Any]:
    """Normalized-AST equality + node-sequence similarity of patch vs reference."""
    cand_fn = _extract_funcdef(cand_source, func_id)
    ref_fn = _extract_funcdef(ref_source, func_id)
    if cand_fn is None or ref_fn is None:
        return {"status": "not_applicable", "ast_equivalent": None, "similarity": None}
    cand_dump = ast.dump(_strip_docstring(cand_fn))
    ref_dump = ast.dump(_strip_docstring(ref_fn))
    similarity = difflib.SequenceMatcher(None, cand_dump, ref_dump).ratio()
    return {"status": "ok", "ast_equivalent": cand_dump == ref_dump,
            "similarity": round(similarity, 6)}


# ---------------------------------------------------------------------------
# Scoring one frozen response
# ---------------------------------------------------------------------------

def score_response_file(score_record: dict[str, Any]) -> dict[str, Any]:
    """Re-score one frozen scorer-result-v1 T2 record with the patch/semantic metrics."""
    func_id = score_record["func_id"]
    truth = _load_bug_truth(func_id)
    buggy_source = (REPO_ROOT / truth["location"]["path"]).read_text(encoding="utf-8")
    ref_source = _reference_source(func_id)
    param_types = _param_types(func_id)

    response_ref = score_record["response_ref"]
    resp = json.loads((REPO_ROOT / response_ref).read_text(encoding="utf-8"))
    response_text = resp.get("response_text") or ""

    claims = extract_t2_claims(response_text)
    fix_line = _extract_best_fix_line(claims, truth)

    record: dict[str, Any] = {
        "lumen_schema": SCHEMA,
        "exploratory": True,
        "func_id": func_id,
        "task": "T2",
        "condition": score_record["condition"],
        "model_id": score_record["model_id"],
        "response_ref": response_ref,
        "fix_binary_frozen": (score_record.get("subscores") or {}).get("fix"),
    }

    if fix_line is None:
        record.update({
            "patch": {"status": "no_candidate", "fraction": None},
            "behavioral": {"status": "no_candidate", "agreement": None},
            "structural": {"status": "no_candidate", "ast_equivalent": None,
                           "similarity": None},
        })
        return record

    cand_source = _apply_fix_to_source(buggy_source, truth["reference_fix"], fix_line)
    record["patch"] = patch_pass_fraction(buggy_source, truth, fix_line)
    record["behavioral"] = behavioral_agreement(cand_source, ref_source, func_id, param_types)
    record["structural"] = structural_equivalence(cand_source, ref_source, func_id)
    return record


# ---------------------------------------------------------------------------
# Exploratory re-analysis over an existing run
# ---------------------------------------------------------------------------

def _tie_mass(vals: list[float]) -> dict[str, Any]:
    from collections import Counter

    n = len(vals)
    if n < 2:
        return {"n": n, "distinct_values": len(set(vals)), "tied_pair_fraction": 0.0}
    counts = Counter(vals)
    tied_pairs = sum(c * (c - 1) // 2 for c in counts.values())
    total_pairs = n * (n - 1) // 2
    return {"n": n, "distinct_values": len(counts),
            "tied_pair_fraction": round(tied_pairs / total_pairs, 4)}


def reanalyze_run(run_id: str, *, limit: int | None = None) -> dict[str, Any]:
    """Re-score every ok T2 record in ``results/runs/<run_id>`` with the new metrics."""
    scores_dir = REPO_ROOT / "results" / "runs" / run_id / "scores"
    records: list[dict[str, Any]] = []
    for f in sorted(scores_dir.glob("*.json")):
        rec = json.loads(f.read_text(encoding="utf-8"))
        if rec.get("lumen_schema") != "scorer-result-v1":
            continue
        if rec.get("task") != "T2" or rec.get("status") != "ok":
            continue
        records.append(score_response_file(rec))
        if limit is not None and len(records) >= limit:
            break

    patch_ok = [r["patch"]["fraction"] for r in records
                if r["patch"]["status"] == "ok" and r["patch"]["fraction"] is not None]
    beh_ok = [r["behavioral"]["agreement"] for r in records
              if r["behavioral"]["status"] == "ok" and r["behavioral"]["agreement"] is not None]
    fix_bin = [float(r["fix_binary_frozen"]) for r in records
               if r["fix_binary_frozen"] is not None]

    return {
        "lumen_schema": SCHEMA + "-reanalysis",
        "exploratory": True,
        "source_run": run_id,
        "note": (
            "EXPLORATORY re-scoring of frozen T2 responses with continuous patch-"
            "correctness and semantic-equivalence metrics. Does not modify the "
            "frozen fix sub-score or the confirmatory analysis. Not for "
            "confirmatory inference."
        ),
        "n_records": len(records),
        "tie_comparison": {
            "fix_binary_frozen": _tie_mass(fix_bin),
            "patch_pass_fraction": _tie_mass(patch_ok),
            "behavioral_agreement": _tie_mass(beh_ok),
        },
        "coverage": {
            "patch_ok": len(patch_ok),
            "behavioral_ok": len(beh_ok),
            "behavioral_not_applicable": sum(
                1 for r in records if r["behavioral"]["status"] == "not_applicable"
            ),
        },
        "records": records,
    }


def _main(argv: list[str] | None = None) -> int:
    import argparse

    parser = argparse.ArgumentParser(
        prog="score_t2_patch",
        description="EXPLORATORY continuous T2 patch-correctness + semantic-equivalence (W-04).",
    )
    parser.add_argument("--reanalyze", metavar="RUN_ID", required=True)
    parser.add_argument("--limit", type=int, default=None,
                        help="Cap records (for a quick smoke check).")
    parser.add_argument("--output-json", default=None)
    args = parser.parse_args(argv)

    result = reanalyze_run(args.reanalyze, limit=args.limit)
    out = (
        Path(args.output_json)
        if args.output_json
        else REPO_ROOT / "results" / "analysis" / "exploratory"
        / f"t2_patch_semantic_{args.reanalyze}" / "exploratory_patch_semantic.json"
    )
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")

    tc = result["tie_comparison"]
    print(f"Re-analyzed {result['n_records']} T2 records from run {args.reanalyze!r}.")
    for name in ("fix_binary_frozen", "patch_pass_fraction", "behavioral_agreement"):
        m = tc[name]
        print(f"  {name:24s} distinct={m['distinct_values']:3d}  "
              f"tied_pair_fraction={m['tied_pair_fraction']}  n={m['n']}")
    print(f"  coverage: {result['coverage']}")
    print(f"  wrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(_main())
