"""Continuous-valued T2 *location* metric (EXPLORATORY).

Status: exploratory measurement-design instrument (Linear R1-1 / WOV-235,
backlog W-04). This module is **not** part of the frozen confirmatory
pipeline. It never imports, mutates, or re-runs the frozen scorer
(``score_t2.py``) or ``analyze_confirmatory.py``. It re-reads the existing
frozen model responses and produces a *separate*, clearly-labelled
exploratory score so the frozen-script regime is preserved until
Constitution v0.3.

Motivation
----------
The frozen integer T2 composite (0-3) saturated at 2; its ceiling of 3 was
never reached, collapsing the effective Wilcoxon n from 30 to ~14 through
ties (paper Sec. 5.3). The binary location sub-score is the main culprit:
the frozen ``score_t2_location`` awards 1 only when an explicit ground-truth
line number appears (or one of three hard-coded code patterns matches), so
the overwhelmingly common "model quotes the buggy line without a line
number" case scores 0. That makes location near-binary and highly tied.

This module replaces the binary location signal with a continuous score in
[0, 1] built from two recovered signals:

1. **Explicit line numbers** parsed from the response (``line 29``, ``L29``,
   ``#29``), compared against the ground-truth line span.
2. **Quoted-code recovery**: fenced / back-ticked code fragments are matched
   against the ground-truth source file (``data/functions/raw/{func_id}.py``,
   the coordinate system of the truth span) to recover the line numbers the
   model implicitly referred to. This rescues the dominant "quoted the line,
   no line number" case the binary scorer misses.

Both signals yield a predicted line set ``P``. With the truth line set ``T``:

* If ``P ∩ T`` is non-empty:   score = IoU(P, T) = |P∩T| / |P∪T|.
* Else if ``P`` is non-empty:  score = ``PROX_WEIGHT`` * max(0, 1 - (d-1)/W),
  where ``d`` is the minimum line distance from ``P`` to ``T`` and ``W`` is a
  per-function proximity window (scaled by function length). Disjoint-and-far
  predictions decay to exactly 0.0.
* Else (unmappable: no lines, no recoverable quote): score = 0.0.

Anti-saturation argument
------------------------
The frozen composite's location sub-score takes 2 values {0, 1}. This metric
takes values on a continuum: IoU over line sets produces fractions
(1, 1/2, 2/3, 1/3, 1/4, ...) whose denominator depends on the predicted and
truth span lengths, and the proximity branch produces a length-normalised
ramp in (0, PROX_WEIGHT). Because the 30 functions have differing source
lengths and bug-span positions, and models emit differing numbers of line
references / quotes, the realised value set cannot collapse to <=3 discrete
levels. The accompanying re-analysis (``--reanalyze``) reports the realised
distinct-value count and tie mass so the claim is checked empirically rather
than asserted (see docs/reproducibility/R1-1-t2-continuous-location.md).
"""

from __future__ import annotations

import ast
import json
import re
from pathlib import Path
from typing import Any

# Repo root = three parents up from this file (src/experiment/<this>).
REPO_ROOT = Path(__file__).resolve().parents[2]

# Maximum partial credit awarded to a near-miss prediction that does not
# overlap the truth span at all. Strictly below the smallest possible
# overlap-branch score so "touched the line" always beats "near the line".
PROX_WEIGHT = 0.5

SCHEMA = "t2-continuous-location-v1"


# ---------------------------------------------------------------------------
# Signal extraction
# ---------------------------------------------------------------------------

def _normalize(s: str) -> str:
    """Collapse whitespace and lowercase for tolerant code matching."""
    return re.sub(r"\s+", " ", s).strip().lower()


def extract_predicted_lines(response_text: str, source_lines: list[str]) -> set[int]:
    """Recover the set of 1-indexed source line numbers a response points at.

    Combines explicit line-number mentions with quoted-code recovery against
    ``source_lines`` (the ground-truth source file's lines).
    """
    text = response_text or ""
    predicted: set[int] = set()
    n_lines = len(source_lines)

    # (1) Explicit line numbers: "line 29", "at line 7"
    for m in re.finditer(r"\bline\s+(\d+)\b", text, re.IGNORECASE):
        ln = int(m.group(1))
        if 1 <= ln <= n_lines:
            predicted.add(ln)
    # Bare "#29" or "L29"
    for m in re.finditer(r"(?:^|[^a-z\d])(?:#|L)(\d+)\b", text, re.IGNORECASE):
        ln = int(m.group(1))
        if 1 <= ln <= n_lines:
            predicted.add(ln)

    # (2) Quoted-code recovery: fenced blocks + inline backticks.
    fragments: list[str] = []
    for m in re.finditer(r"```(?:[a-z]*)?\n?(.*?)```", text, re.DOTALL):
        fragments.extend(m.group(1).splitlines())
    for m in re.finditer(r"`([^`]+)`", text):
        fragments.append(m.group(1))

    norm_source = [_normalize(line) for line in source_lines]
    for frag in fragments:
        nf = _normalize(frag)
        # Ignore trivially short fragments to avoid spurious matches.
        if len(nf) < 6:
            continue
        for idx, nsrc in enumerate(norm_source):
            if not nsrc:
                continue
            # Match in either direction: the quote may include a trailing
            # comment ("...  # BUG") or be a substring of the source line.
            if nf in nsrc or nsrc in nf:
                predicted.add(idx + 1)

    return predicted


# ---------------------------------------------------------------------------
# Continuous score
# ---------------------------------------------------------------------------

def _proximity_window(func_len: int) -> int:
    """Per-function proximity window W, scaled by source length."""
    return max(4, func_len // 4)


def continuous_location_score(
    predicted: set[int],
    truth_start: int,
    truth_end: int,
    func_len: int,
) -> float:
    """Continuous location score in [0, 1].

    Exact overlap -> IoU; near-miss -> length-normalised proximity ramp;
    unmappable -> 0.0. See module docstring for the full definition.
    """
    truth = set(range(truth_start, truth_end + 1))
    if not predicted:
        return 0.0

    inter = predicted & truth
    if inter:
        union = predicted | truth
        return len(inter) / len(union)

    # No overlap: decay by distance from the truth span.
    d = min(min(abs(p - t) for t in truth) for p in predicted)
    w = _proximity_window(func_len)
    ramp = max(0.0, 1.0 - (d - 1) / w)
    return PROX_WEIGHT * ramp


# ---------------------------------------------------------------------------
# AST-node-distance location signal (orthogonal to the line-IoU above)
# ---------------------------------------------------------------------------
# R1-1 chose line-span IoU + proximity and parked "AST proximity ... a future
# option for span-level bugs". W-04 adds it as a *second*, orthogonal continuous
# location signal reported alongside the IoU. Where line-IoU measures overlap in
# the flat line coordinate system, this measures distance in the *syntax tree*:
# a prediction one node away in the AST (e.g. sibling statement) scores higher
# than one in an unrelated branch even at the same line distance.


def _node_span(node: ast.AST) -> tuple[int, int] | None:
    lineno = getattr(node, "lineno", None)
    end = getattr(node, "end_lineno", None)
    if lineno is None:
        return None
    return (lineno, end if end is not None else lineno)


def _parent_depth_maps(tree: ast.AST) -> tuple[dict[int, ast.AST | None], dict[int, int]]:
    """Return (parent-by-id, depth-by-id) for every node, root depth 0."""
    parent: dict[int, ast.AST | None] = {id(tree): None}
    depth: dict[int, int] = {id(tree): 0}
    for node in ast.walk(tree):
        for child in ast.iter_child_nodes(node):
            parent[id(child)] = node
            depth[id(child)] = depth[id(node)] + 1
    return parent, depth


def _smallest_node_covering(tree: ast.AST, line: int) -> ast.AST | None:
    """Deepest, tightest-span node whose line range covers ``line``."""
    best: ast.AST | None = None
    best_key: tuple[int, int] | None = None  # (span_width, -has_lineno) minimise
    _, depth = _parent_depth_maps(tree)
    for node in ast.walk(tree):
        span = _node_span(node)
        if span is None:
            continue
        lo, hi = span
        if lo <= line <= hi:
            key = (hi - lo, -depth[id(node)])
            if best_key is None or key < best_key:
                best_key, best = key, node
    return best


def _tree_distance(
    a: ast.AST, b: ast.AST, parent: dict[int, ast.AST | None], depth: dict[int, int]
) -> int:
    """Number of edges between ``a`` and ``b`` through their lowest common ancestor."""
    if a is b:
        return 0
    # Collect ancestor chain of a (including a).
    anc_a: dict[int, int] = {}
    node: ast.AST | None = a
    while node is not None:
        anc_a[id(node)] = depth[id(node)]
        node = parent.get(id(node))
    # Walk up from b until we hit a common ancestor.
    node = b
    while node is not None and id(node) not in anc_a:
        node = parent.get(id(node))
    if node is None:
        return depth[id(a)] + depth[id(b)]  # disjoint trees (shouldn't happen)
    lca_depth = depth[id(node)]
    return (depth[id(a)] - lca_depth) + (depth[id(b)] - lca_depth)


def ast_location_distance_score(
    predicted: set[int],
    truth_start: int,
    truth_end: int,
    source_text: str,
) -> float | None:
    """Continuous AST-node-distance location score in [0, 1], or ``None``.

    Exact truth node → 1.0; farther apart in the syntax tree → lower; unrelated
    branch → toward 0.0. Returns ``None`` (→ ``not_applicable``) if the source
    does not parse, so an un-parseable file never masquerades as a hard 0.
    """
    if not predicted:
        return 0.0
    try:
        tree = ast.parse(source_text)
    except SyntaxError:
        return None

    parent, depth = _parent_depth_maps(tree)
    truth_line = (truth_start + truth_end) // 2
    truth_node = _smallest_node_covering(tree, truth_line)
    if truth_node is None:
        return None

    best: float = 0.0
    saw_node = False
    for p in predicted:
        pred_node = _smallest_node_covering(tree, p)
        if pred_node is None:
            continue
        saw_node = True
        dist = _tree_distance(truth_node, pred_node, parent, depth)
        denom = depth[id(truth_node)] + depth[id(pred_node)]
        score = 1.0 if denom == 0 else max(0.0, 1.0 - dist / denom)
        best = max(best, score)
    if not saw_node:
        return 0.0
    return best


# ---------------------------------------------------------------------------
# Scoring one frozen response
# ---------------------------------------------------------------------------

def _load_truth(func_id: str) -> dict[str, Any]:
    path = REPO_ROOT / "data" / "ground_truth" / "bugs" / f"{func_id}.json"
    return json.loads(path.read_text(encoding="utf-8"))


def score_response_file(score_record: dict[str, Any]) -> dict[str, Any]:
    """Re-score the location of one frozen scorer-result-v1 record.

    Reads the referenced response and the ground-truth source, computes the
    continuous location score, and returns an exploratory record. Does not
    write anything and does not touch frozen artifacts.
    """
    func_id = score_record["func_id"]
    truth = _load_truth(func_id)
    src_path = REPO_ROOT / truth["location"]["path"]
    source_text = src_path.read_text(encoding="utf-8")
    source_lines = source_text.splitlines()

    response_ref = score_record["response_ref"]
    resp = json.loads((REPO_ROOT / response_ref).read_text(encoding="utf-8"))
    response_text = resp.get("response_text") or ""

    start_line = truth["location"]["start_line"]
    end_line = truth["location"]["end_line"]

    predicted = extract_predicted_lines(response_text, source_lines)
    score = continuous_location_score(predicted, start_line, end_line, len(source_lines))
    ast_score = ast_location_distance_score(predicted, start_line, end_line, source_text)

    return {
        "lumen_schema": SCHEMA,
        "exploratory": True,
        "func_id": func_id,
        "task": "T2",
        "condition": score_record["condition"],
        "model_id": score_record["model_id"],
        "response_ref": response_ref,
        "ground_truth_ref": f"data/ground_truth/bugs/{func_id}.json",
        "location_continuous": round(score, 6),
        "location_iou": round(score, 6),
        "location_ast": round(ast_score, 6) if ast_score is not None else None,
        "location_binary_frozen": score_record.get("subscores", {}).get("location"),
        "predicted_lines": sorted(predicted),
        "truth_span": [start_line, end_line],
    }


# ---------------------------------------------------------------------------
# Exploratory re-analysis over an existing run's frozen responses
# ---------------------------------------------------------------------------

def reanalyze_run(run_id: str) -> dict[str, Any]:
    """Re-score the location of every T2 record in ``results/runs/<run_id>``.

    Returns an exploratory result dict (also includes a tie comparison of the
    continuous metric against the frozen binary location sub-score). Reads
    only; never writes frozen artifacts.
    """
    scores_dir = REPO_ROOT / "results" / "runs" / run_id / "scores"
    records: list[dict[str, Any]] = []
    for f in sorted(scores_dir.glob("*.json")):
        rec = json.loads(f.read_text(encoding="utf-8"))
        if rec.get("lumen_schema") != "scorer-result-v1":
            continue
        if rec.get("task") != "T2" or rec.get("status") != "ok":
            continue
        records.append(score_response_file(rec))

    cont = [r["location_continuous"] for r in records]
    astv = [r["location_ast"] for r in records if r["location_ast"] is not None]
    binr = [r["location_binary_frozen"] for r in records if r["location_binary_frozen"] is not None]

    def _tie_mass(vals: list[float]) -> dict[str, Any]:
        """Fraction of value pairs that are tied (drives Wilcoxon n collapse)."""
        n = len(vals)
        if n < 2:
            return {"n": n, "distinct_values": len(set(vals)), "tied_pair_fraction": 0.0}
        from collections import Counter

        counts = Counter(vals)
        tied_pairs = sum(c * (c - 1) // 2 for c in counts.values())
        total_pairs = n * (n - 1) // 2
        return {
            "n": n,
            "distinct_values": len(counts),
            "tied_pair_fraction": round(tied_pairs / total_pairs, 4),
        }

    return {
        "lumen_schema": SCHEMA + "-reanalysis",
        "exploratory": True,
        "source_run": run_id,
        "note": (
            "EXPLORATORY re-scoring of frozen T2 responses with a continuous "
            "location metric. Does not modify the frozen composite or the "
            "confirmatory analysis. Not for confirmatory inference."
        ),
        "n_records": len(records),
        "tie_comparison": {
            "continuous_location": _tie_mass(cont),
            "location_iou": _tie_mass(cont),
            "location_ast": _tie_mass(astv),
            "binary_location_frozen": _tie_mass([float(x) for x in binr]),
        },
        "records": records,
    }


def _main(argv: list[str] | None = None) -> int:
    import argparse

    parser = argparse.ArgumentParser(
        prog="score_t2_continuous",
        description="EXPLORATORY continuous T2 location metric (R1-1 / W-04).",
    )
    parser.add_argument(
        "--reanalyze",
        metavar="RUN_ID",
        help="Re-score all T2 responses in results/runs/<RUN_ID>.",
    )
    parser.add_argument(
        "--output-json",
        default=None,
        help="Where to write the exploratory re-analysis JSON.",
    )
    args = parser.parse_args(argv)

    if not args.reanalyze:
        parser.error("nothing to do: pass --reanalyze RUN_ID")

    result = reanalyze_run(args.reanalyze)
    out = (
        Path(args.output_json)
        if args.output_json
        else REPO_ROOT
        / "results"
        / "analysis"
        / "exploratory"
        / f"t2_continuous_location_{args.reanalyze}"
        / "exploratory_location_continuous.json"
    )
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")

    tc = result["tie_comparison"]
    print(f"Re-analyzed {result['n_records']} T2 records from run {args.reanalyze!r}.")
    print(
        "  binary  location (frozen): "
        f"distinct={tc['binary_location_frozen']['distinct_values']}, "
        f"tied_pair_fraction={tc['binary_location_frozen']['tied_pair_fraction']}"
    )
    print(
        "  continuous location (IoU): "
        f"distinct={tc['location_iou']['distinct_values']}, "
        f"tied_pair_fraction={tc['location_iou']['tied_pair_fraction']}"
    )
    print(
        "  continuous location (AST): "
        f"distinct={tc['location_ast']['distinct_values']}, "
        f"tied_pair_fraction={tc['location_ast']['tied_pair_fraction']}, "
        f"n={tc['location_ast']['n']}"
    )
    print(f"  wrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(_main())
