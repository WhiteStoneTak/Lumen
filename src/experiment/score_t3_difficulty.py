"""Difficulty-adjusted, ceiling-free T3 quality metric (EXPLORATORY).

Status: exploratory measurement-design instrument (backlog W-04). It re-reads
existing frozen T3 responses and produces a separate, clearly-labelled
exploratory score; it never mutates or re-runs ``score_t3.py`` or
``analyze_confirmatory.py``. It imports only the pure code-extractor from the
frozen scorer.

The problem it solves
---------------------
On ``full_t3_confirmatory_v1`` **93.7 % of T3 records score exactly 1.0** — both
frozen models pass *every* authored test. This is a **difficulty** ceiling, not a
scorer-granularity one: re-weighting or partial-credit over suites that everyone
already passes keeps a perfect score perfect. The only way to de-saturate is to
add checks the passing solutions can *fail*.

The instrument
--------------
For each candidate this computes a difficulty-weighted quality score over three
tiers of checks:

1. **base / edge** — the *existing* authored suite, per-test, tiered by a
   deterministic method-name heuristic (edge = empty/boundary/raise/large/... ).
2. **adversarial** — the hidden + metamorphic layer authored for the subset
   (``data/ground_truth/t3_hidden/{func_id}.py``): held-out inputs differential-
   tested against a reference implementation, plus oracle-free metamorphic
   invariants. This tier is what a "passes everything visible" solution can fail.

``quality = Σ_tier w_tier · passed_tier / Σ_tier w_tier · total_tier`` with
``w = {base: 1, edge: 2, adversarial: 3}`` (documented, tunable). The frozen
unweighted pass fraction over the existing suite is reported alongside for
comparison, and ``--reanalyze`` reports the realised distinct-value / tie mass so
the de-saturation is checked empirically.
"""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import textwrap
from pathlib import Path
from typing import Any

from experiment.score_t3 import extract_t3_code_candidate

REPO_ROOT = Path(__file__).resolve().parents[2]
SCHEMA = "t3-difficulty-quality-v1"
HIDDEN_DIR = REPO_ROOT / "data" / "ground_truth" / "t3_hidden"

# Tier weights: harder checks are worth more, so a candidate that clears every
# visible test but violates a metamorphic invariant cannot reach 1.0.
TIER_WEIGHTS = {"base": 1.0, "edge": 2.0, "adversarial": 3.0}

_DIFF_TIMEOUT_S = 15.0
_TIMEOUT_SENTINEL = "TIMEOUT:"

# Method-name substrings that mark a *visible* test as edge-tier (weight 2).
_EDGE_KEYWORDS = (
    "empty", "edge", "boundary", "single", "zero", "negative", "large", "huge",
    "big", "unicode", "overflow", "invalid", "raise", "error", "exception",
    "duplicate", "dup", "unsorted", "precondition", "out_of_range", "nan", "inf",
    "deep", "nested", "wide", "stress", "tie", "reverse", "alternating",
    "identity", "idempot", "acronym", "min", "max", "one_element", "two_element",
)


def _tier_of(test_id: str) -> str:
    """base | edge from the test method name (deterministic)."""
    method = test_id.rsplit(".", 1)[-1].lower()
    return "edge" if any(k in method for k in _EDGE_KEYWORDS) else "base"


# ---------------------------------------------------------------------------
# Sandboxed driver: existing suite (per-test) + hidden differential + metamorphic
# ---------------------------------------------------------------------------

_DIFF_DRIVER = textwrap.dedent(
    '''
    import copy, importlib.util, io, json, math, sys, unittest

    cand_path, func_id, test_path, hidden_path = sys.argv[1:5]

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

    out = {}
    try:
        cand = getattr(_load("_cand_" + func_id, cand_path), func_id)
    except Exception as exc:  # noqa: BLE001
        print(json.dumps({"error": f"cand_load: {type(exc).__name__}: {exc}"})); sys.exit(0)

    # --- existing suite, per-test ---
    try:
        tmod = _load("_suite_" + func_id, test_path)
        setattr(tmod, func_id, cand)
        for attr in dir(tmod):
            obj = getattr(tmod, attr)
            if isinstance(obj, type) and issubclass(obj, unittest.TestCase):
                for mn in obj.__dict__:
                    m = getattr(obj, mn, None)
                    if callable(m) and hasattr(m, "__func__"):
                        if func_id in m.__func__.__globals__:
                            m.__func__.__globals__[func_id] = cand
        suite = unittest.TestLoader().loadTestsFromModule(tmod)

        def _iter(s):
            for t in s:
                if isinstance(t, unittest.TestSuite):
                    yield from _iter(t)
                else:
                    yield t

        all_ids = [t.id() for t in _iter(suite)]
        res = unittest.TextTestRunner(verbosity=0, stream=io.StringIO()).run(suite)
        failed = {tc.id() for tc, _ in list(res.failures) + list(res.errors)}
        out["per_test"] = {tid: (tid not in failed) for tid in all_ids}
    except Exception as exc:  # noqa: BLE001
        out["suite_error"] = f"{type(exc).__name__}: {exc}"

    # --- hidden differential + metamorphic ---
    if hidden_path != "-":
        try:
            hid = _load("_hidden_" + func_id, hidden_path)
            ref = getattr(hid, "reference")
            hidden_inputs = getattr(hid, "HIDDEN_INPUTS", [])
            metamorphic = getattr(hid, "METAMORPHIC", [])
            hp = 0
            for args in hidden_inputs:
                try:
                    ra = ref(*copy.deepcopy(args)); rexc = None
                except Exception as e:  # noqa: BLE001
                    ra = None; rexc = type(e).__name__
                try:
                    ca = cand(*copy.deepcopy(args)); cexc = None
                except Exception as e:  # noqa: BLE001
                    ca = None; cexc = type(e).__name__
                if rexc is not None or cexc is not None:
                    if rexc == cexc:
                        hp += 1
                elif _deep_equal(ra, ca):
                    hp += 1
            out["hidden"] = {"passed": hp, "total": len(hidden_inputs)}
            mp = 0
            for rel in metamorphic:
                try:
                    if rel(cand):
                        mp += 1
                except Exception:  # noqa: BLE001
                    pass
            out["meta"] = {"passed": mp, "total": len(metamorphic)}
        except Exception as exc:  # noqa: BLE001
            out["hidden_error"] = f"{type(exc).__name__}: {exc}"

    print(json.dumps(out))
    '''
)


def run_difficulty(
    cand_code: str,
    func_id: str,
    test_path: Path,
    hidden_path: Path | None,
    timeout_s: float = _DIFF_TIMEOUT_S,
) -> dict[str, Any]:
    """Run the driver in a child process; return its JSON dict (or an error dict)."""
    tmp: list[str] = []
    try:
        def _w(text: str, suffix: str) -> str:
            f = tempfile.NamedTemporaryFile(mode="w", suffix=suffix, delete=False,
                                            encoding="utf-8")
            f.write(text); f.close(); tmp.append(f.name); return f.name

        cand_p = _w(cand_code, ".py")
        drv_p = _w(_DIFF_DRIVER, ".py")
        hid_arg = str(hidden_path) if hidden_path is not None else "-"
        try:
            proc = subprocess.run(
                [sys.executable, drv_p, cand_p, func_id, str(test_path), hid_arg],
                capture_output=True, text=True, timeout=timeout_s,
            )
        except subprocess.TimeoutExpired:
            return {"error": f"{_TIMEOUT_SENTINEL} exceeded {timeout_s}s"}
        out = (proc.stdout or "").strip().splitlines()
        if not out:
            return {"error": f"no driver output (stderr: {(proc.stderr or '')[:200]})"}
        try:
            return json.loads(out[-1])
        except json.JSONDecodeError:
            return {"error": f"unparseable driver output: {out[-1][:200]}"}
    finally:
        for p in tmp:
            try:
                Path(p).unlink()
            except OSError:
                pass


# ---------------------------------------------------------------------------
# Quality computation
# ---------------------------------------------------------------------------

def compute_quality(driver_out: dict[str, Any]) -> dict[str, Any]:
    """Difficulty-weighted quality + the unweighted frozen-equivalent fraction."""
    per_test: dict[str, bool] = driver_out.get("per_test", {})
    base_p = base_t = edge_p = edge_t = 0
    for tid, passed in per_test.items():
        if _tier_of(tid) == "edge":
            edge_t += 1
            edge_p += int(bool(passed))
        else:
            base_t += 1
            base_p += int(bool(passed))

    hidden = driver_out.get("hidden") or {"passed": 0, "total": 0}
    meta = driver_out.get("meta") or {"passed": 0, "total": 0}
    adv_p = hidden["passed"] + meta["passed"]
    adv_t = hidden["total"] + meta["total"]

    w = TIER_WEIGHTS
    wp = base_p * w["base"] + edge_p * w["edge"] + adv_p * w["adversarial"]
    wt = base_t * w["base"] + edge_t * w["edge"] + adv_t * w["adversarial"]
    quality = round(wp / wt, 6) if wt else None

    visible_t = base_t + edge_t
    frozen_frac = round((base_p + edge_p) / visible_t, 6) if visible_t else None

    return {
        "difficulty_quality": quality,
        "frozen_equiv_fraction": frozen_frac,
        "tiers": {
            "base": {"passed": base_p, "total": base_t},
            "edge": {"passed": edge_p, "total": edge_t},
            "adversarial": {"passed": adv_p, "total": adv_t,
                            "hidden": hidden, "metamorphic": meta},
        },
        "has_adversarial": adv_t > 0,
    }


# ---------------------------------------------------------------------------
# Scoring one frozen response
# ---------------------------------------------------------------------------

def score_response_file(score_record: dict[str, Any]) -> dict[str, Any]:
    func_id = score_record["func_id"]
    response_ref = score_record["response_ref"]
    resp = json.loads((REPO_ROOT / response_ref).read_text(encoding="utf-8"))
    response_text = resp.get("response_text") or ""

    record: dict[str, Any] = {
        "lumen_schema": SCHEMA,
        "exploratory": True,
        "func_id": func_id,
        "task": "T3",
        "condition": score_record["condition"],
        "model_id": score_record["model_id"],
        "response_ref": response_ref,
        "frozen_score": score_record.get("score"),
    }

    candidate = extract_t3_code_candidate(response_text, func_id)
    if candidate is None:
        record.update({"status": "no_candidate", "difficulty_quality": None,
                       "has_adversarial": False})
        return record

    test_path = (REPO_ROOT / score_record["ground_truth_ref"]).resolve()
    hidden_file = HIDDEN_DIR / f"{func_id}.py"
    hidden_path = hidden_file if hidden_file.exists() else None

    driver_out = run_difficulty(candidate, func_id, test_path, hidden_path)
    if "error" in driver_out:
        status = "timeout" if driver_out["error"].startswith(_TIMEOUT_SENTINEL) else "exec_error"
        record.update({"status": status, "difficulty_quality": None,
                       "has_adversarial": hidden_path is not None,
                       "detail": driver_out["error"][:200]})
        return record

    record.update(compute_quality(driver_out))
    record["status"] = "ok"
    record["has_hidden_layer"] = hidden_path is not None
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
    scores_dir = REPO_ROOT / "results" / "runs" / run_id / "scores"
    records: list[dict[str, Any]] = []
    for f in sorted(scores_dir.glob("*.json")):
        rec = json.loads(f.read_text(encoding="utf-8"))
        if rec.get("lumen_schema") != "scorer-result-v1":
            continue
        if rec.get("task") != "T3" or rec.get("status") != "ok":
            continue
        records.append(score_response_file(rec))
        if limit is not None and len(records) >= limit:
            break

    # Subset records that actually have the adversarial layer.
    sub = [r for r in records if r.get("has_hidden_layer") and r.get("status") == "ok"]
    sub_frozen = [float(r["frozen_score"]) for r in sub if r.get("frozen_score") is not None]
    sub_quality = [r["difficulty_quality"] for r in sub if r.get("difficulty_quality") is not None]

    # How many perfect frozen scores the instrument pulls below 1.0.
    broke = sum(
        1 for r in sub
        if r.get("frozen_score") == 1.0
        and r.get("difficulty_quality") is not None
        and r["difficulty_quality"] < 1.0
    )
    n_frozen_perfect = sum(1 for r in sub if r.get("frozen_score") == 1.0)

    return {
        "lumen_schema": SCHEMA + "-reanalysis",
        "exploratory": True,
        "source_run": run_id,
        "note": (
            "EXPLORATORY difficulty-adjusted re-scoring of frozen T3 responses. "
            "Adds a hidden + metamorphic adversarial tier for a subset of "
            "functions to de-saturate the 93.7% all-pass ceiling. Does not modify "
            "the frozen T3 scorer or the confirmatory analysis. Not for "
            "confirmatory inference."
        ),
        "tier_weights": TIER_WEIGHTS,
        "n_records": len(records),
        "subset_functions": sorted({r["func_id"] for r in sub}),
        "n_subset_records": len(sub),
        "de_saturation_on_subset": {
            "frozen_score": _tie_mass(sub_frozen),
            "difficulty_quality": _tie_mass(sub_quality),
            "frozen_perfect_records": n_frozen_perfect,
            "pulled_below_1.0_by_instrument": broke,
        },
        "records": records,
    }


def _main(argv: list[str] | None = None) -> int:
    import argparse

    parser = argparse.ArgumentParser(
        prog="score_t3_difficulty",
        description="EXPLORATORY difficulty-adjusted T3 quality metric (W-04).",
    )
    parser.add_argument("--reanalyze", metavar="RUN_ID", required=True)
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--output-json", default=None)
    args = parser.parse_args(argv)

    result = reanalyze_run(args.reanalyze, limit=args.limit)
    out = (
        Path(args.output_json)
        if args.output_json
        else REPO_ROOT / "results" / "analysis" / "exploratory"
        / f"t3_difficulty_{args.reanalyze}" / "exploratory_difficulty_quality.json"
    )
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")

    ds = result["de_saturation_on_subset"]
    print(f"Re-analyzed {result['n_records']} T3 records from run {args.reanalyze!r}.")
    print(f"  subset functions: {result['subset_functions']}")
    print(f"  subset records: {result['n_subset_records']}")
    print("  frozen score (subset):      "
          f"distinct={ds['frozen_score']['distinct_values']}, "
          f"tied_pair_fraction={ds['frozen_score']['tied_pair_fraction']}")
    print("  difficulty quality (subset):"
          f"distinct={ds['difficulty_quality']['distinct_values']}, "
          f"tied_pair_fraction={ds['difficulty_quality']['tied_pair_fraction']}")
    print(f"  frozen-perfect records pulled below 1.0: "
          f"{ds['pulled_below_1.0_by_instrument']}/{ds['frozen_perfect_records']}")
    print(f"  wrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(_main())
