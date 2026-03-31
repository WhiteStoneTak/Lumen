"""Manual candidate intake and Stage 1 workflow CLI.

Usage
-----
Add a new candidate:
    PYTHONPATH=src python -m experiment.manage_candidates add \\
        --id my_func \\
        --source "authored" \\
        --lines 14 \\
        --complexity medium \\
        --t2-family "boundary_interaction" \\
        --t3-family "invariant_preserving_refactor"

Set Stage 1 result:
    PYTHONPATH=src python -m experiment.manage_candidates update-stage1 \\
        my_func --result PASS

    PYTHONPATH=src python -m experiment.manage_candidates update-stage1 \\
        my_func --result EXCLUDE --reason "Single comparison-operator flip, visually obvious"

    PYTHONPATH=src python -m experiment.manage_candidates update-stage1 \\
        my_func --result DEFER --reason "Revisit after checking body line count"

List candidates:
    PYTHONPATH=src python -m experiment.manage_candidates list
    PYTHONPATH=src python -m experiment.manage_candidates list --state pending
    PYTHONPATH=src python -m experiment.manage_candidates list --state pass-blocked
    PYTHONPATH=src python -m experiment.manage_candidates list --state pass-ready

Show one candidate:
    PYTHONPATH=src python -m experiment.manage_candidates show my_func

Validate tracker:
    PYTHONPATH=src python -m experiment.manage_candidates validate

Workflow states (in lifecycle order)
-------------------------------------
  pending        — added to tracker, Stage 1 not yet reviewed
  deferred       — Stage 1 set to DEFER with a stated reason
  excluded       — Stage 1 EXCLUDE
  pass-blocked   — Stage 1 PASS, but prerequisites for Stage 2 not yet met
                   (candidate_id must be in functions_manifest.json with T2 available)
  pass-ready     — Stage 1 PASS AND in manifest with T2 available
  stage2-screened — Stage 2 run result recorded in tracker
  anchor         — pilot calibration anchor (clamp / count_vowels / is_sorted)

Important: Stage 1 PASS ≠ Stage 2-ready
-----------------------------------------
Passing Stage 1 means the researcher has judged the function worth advancing.
It does NOT mean the function can immediately be used in a screening run.
Before a Stage 2 T2 C1 run is possible, the researcher must:
  1. Place the raw source at data/functions/raw/{candidate_id}.py
  2. Add the candidate to data/dataset/functions_manifest.json (T2 available)
  3. Author a draft T2 bug annotation (data/ground_truth/bugs/{candidate_id}.json)
  4. Author a minimal T2 test suite (data/ground_truth/tests/{candidate_id}_t2_test.py)

Only after those prerequisites are in place will the candidate appear as
'pass-ready' and be auto-detected for inclusion in a Stage 2 screening wave.

candidate_id vs func_id
-----------------------
In this tracker, candidate_id is a working name, not yet a committed func_id.
Use a snake_case name that will become the func_id if the candidate passes.
Once a candidate passes Stage 2 and is promoted to the permanent dataset,
its candidate_id becomes its func_id in functions_manifest.json.
Do not use the same name for two different functions.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_SRC = Path(__file__).resolve().parents[1]
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from experiment.candidate_tracker import (  # noqa: E402
    ANCHOR_IDS,
    COMPLEXITY_VALUES,
    STAGE1_VALUES,
    TrackerError,
    default_tracker_path,
    get_candidate,
    is_stage2_ready,
    load_tracker,
    save_tracker,
    upsert_candidate,
    validate_tracker,
    workflow_state,
    workflow_summary,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_STATE_CHOICES = (
    "all",
    "pending",
    "deferred",
    "excluded",
    "pass-blocked",
    "pass-ready",
    "stage2-screened",
    "anchor",
)


def _blank_candidate(candidate_id: str) -> dict:
    """Return a minimal, valid, unreviewed candidate row."""
    return {
        "candidate_id": candidate_id,
        "source": "",
        "body_line_count": 0,
        "estimated_complexity": "medium",
        "t2_bug_family_draft": "unknown",
        "t3_transform_family_draft": "unknown",
        "stage1_result": "DEFER",
        "stage1_exclusion_reason": None,
        "stage2_t2_c1_screen_score": None,
        "stage2_t2_subscores": None,
        "stage2_result": "not_run",
        "stage2_exclusion_reason": None,
        "stage3_t3_c2_screen_score": None,
        "stage3_result": "not_run",
        "final_decision": "DEFER",
        "is_anchor": False,
        "notes": "",
    }


def _load(path: Path) -> dict:
    try:
        return load_tracker(path)
    except TrackerError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(1)


def _save(data: dict, path: Path) -> None:
    try:
        save_tracker(data, path)
    except TrackerError as exc:
        print(f"ERROR saving tracker: {exc}", file=sys.stderr)
        sys.exit(1)


# ---------------------------------------------------------------------------
# Subcommand: add
# ---------------------------------------------------------------------------

def _cmd_add(args: argparse.Namespace) -> int:
    path = Path(args.path) if args.path else default_tracker_path()
    data = _load(path)

    cid = args.id.strip()
    if not cid:
        print("ERROR: --id must not be empty.", file=sys.stderr)
        return 1
    if cid in ANCHOR_IDS:
        print(
            f"ERROR: '{cid}' is a designated anchor (clamp / count_vowels / is_sorted).\n"
            "  Anchors are pre-seeded and must not be added via this command.",
            file=sys.stderr,
        )
        return 1
    if get_candidate(data, cid) is not None:
        print(
            f"ERROR: candidate_id '{cid}' already exists in the tracker.\n"
            "  Use 'update-stage1' to modify an existing candidate.",
            file=sys.stderr,
        )
        return 1
    if args.complexity not in COMPLEXITY_VALUES:
        print(
            f"ERROR: --complexity must be one of: {sorted(COMPLEXITY_VALUES)}",
            file=sys.stderr,
        )
        return 1

    row = _blank_candidate(cid)
    row["source"] = args.source
    row["body_line_count"] = args.lines
    row["estimated_complexity"] = args.complexity
    row["t2_bug_family_draft"] = args.t2_family
    row["t3_transform_family_draft"] = args.t3_family
    row["notes"] = args.notes

    try:
        upsert_candidate(data, row)
    except TrackerError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    _save(data, path)
    print(f"Added: {cid}  (state=pending, stage1_result=DEFER)")
    print(f"  Next: review and run 'update-stage1 {cid} --result PASS|EXCLUDE|DEFER'")
    return 0


# ---------------------------------------------------------------------------
# Subcommand: update-stage1
# ---------------------------------------------------------------------------

def _cmd_update_stage1(args: argparse.Namespace) -> int:
    path = Path(args.path) if args.path else default_tracker_path()
    data = _load(path)

    cid = args.candidate_id
    row = get_candidate(data, cid)
    if row is None:
        print(f"ERROR: candidate_id '{cid}' not found in tracker.", file=sys.stderr)
        return 1

    result = args.result.upper()
    if result not in STAGE1_VALUES:
        print(
            f"ERROR: --result must be one of: {sorted(STAGE1_VALUES)}",
            file=sys.stderr,
        )
        return 1

    # Reason required for EXCLUDE; optional for DEFER; not applicable for PASS
    reason = args.reason or None
    if result == "EXCLUDE" and not reason:
        print(
            "ERROR: --reason is required when --result EXCLUDE.\n"
            "  Provide a brief explanation of why this candidate was rejected.",
            file=sys.stderr,
        )
        return 1
    if result == "PASS":
        # Clear any prior exclusion/deferral reason so the row stays clean
        reason = None

    # Update the row fields
    row["stage1_result"] = result
    row["stage1_exclusion_reason"] = reason

    # Propagate final_decision for EXCLUDE so the row stays internally consistent
    if result == "EXCLUDE":
        row["final_decision"] = "EXCLUDE"

    if args.notes is not None:
        row["notes"] = args.notes

    try:
        upsert_candidate(data, row)
    except TrackerError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    _save(data, path)
    state = workflow_state(row)

    if result == "PASS":
        ready, ready_reason = is_stage2_ready(cid)
        if ready:
            print(f"Updated: {cid}  stage1_result=PASS  state=pass-ready")
            print("  Stage 2 prerequisites are met. Candidate is ready to screen.")
        else:
            print(f"Updated: {cid}  stage1_result=PASS  state=pass-blocked")
            print(f"  Stage 2 prerequisites not yet met: {ready_reason}")
            print("  See 'python -m experiment.manage_candidates --help' for prerequisites.")
    elif result == "EXCLUDE":
        print(f"Updated: {cid}  stage1_result=EXCLUDE  reason='{reason}'")
        print("  Row is preserved in the tracker as an audit record.")
    else:  # DEFER
        if reason:
            print(f"Updated: {cid}  stage1_result=DEFER  reason='{reason}'")
        else:
            print(f"Updated: {cid}  stage1_result=DEFER  (pending review)")

    return 0


# ---------------------------------------------------------------------------
# Subcommand: list
# ---------------------------------------------------------------------------

def _cmd_list(args: argparse.Namespace) -> int:
    path = Path(args.path) if args.path else default_tracker_path()
    data = _load(path)

    state_filter = args.state or "all"
    candidates = data["candidates"]

    rows_with_state = [
        (row, workflow_state(row))
        for row in candidates
    ]

    if state_filter != "all":
        rows_with_state = [(r, s) for r, s in rows_with_state if s == state_filter]

    if not rows_with_state:
        if state_filter == "all":
            print("No candidates in tracker.")
        else:
            print(f"No candidates with state '{state_filter}'.")
        return 0

    # Header
    hdr = f"{'candidate_id':<24} {'state':<16} {'s1':<8} {'cplx':<8} {'s2':<14} {'t2_family'}"
    print(hdr)
    print("-" * len(hdr))

    for row, state in rows_with_state:
        cid = row["candidate_id"]
        s1 = row["stage1_result"]
        cplx = row["estimated_complexity"]
        s2 = row["stage2_result"]
        t2fam = row.get("t2_bug_family_draft", "")
        print(f"{cid:<24} {state:<16} {s1:<8} {cplx:<8} {s2:<14} {t2fam}")

    print(f"\n{len(rows_with_state)} candidate(s)")
    return 0


# ---------------------------------------------------------------------------
# Subcommand: show
# ---------------------------------------------------------------------------

def _cmd_show(args: argparse.Namespace) -> int:
    path = Path(args.path) if args.path else default_tracker_path()
    data = _load(path)

    cid = args.candidate_id
    row = get_candidate(data, cid)
    if row is None:
        print(f"ERROR: candidate_id '{cid}' not found.", file=sys.stderr)
        return 1

    state = workflow_state(row)
    print(json.dumps(row, indent=2))
    print()
    print(f"  workflow_state : {state}")

    if state == "pass-blocked":
        _ready, reason = is_stage2_ready(cid)
        print(f"  blocking reason: {reason}")
        print()
        print("  Prerequisites to become pass-ready:")
        print("    1. data/functions/raw/{cid}.py must exist")
        print("    2. candidate_id must be in functions_manifest.json with T2 available")
        print("    3. data/ground_truth/bugs/{cid}.json must exist")
        print("    4. data/ground_truth/tests/{cid}_t2_test.py must exist")
    elif state == "pass-ready":
        print("  Stage 2 prerequisites met.")
        print(f"  Add '{cid}' to a Stage 2 screening wave when ready.")
    return 0


# ---------------------------------------------------------------------------
# Subcommand: validate
# ---------------------------------------------------------------------------

def _cmd_validate(args: argparse.Namespace) -> int:
    path = Path(args.path) if args.path else default_tracker_path()
    data = _load(path)
    try:
        validate_tracker(data)
        print(f"OK: tracker is valid ({len(data['candidates'])} candidates).")
        return 0
    except TrackerError as exc:
        print(f"INVALID: {exc}", file=sys.stderr)
        return 1


# ---------------------------------------------------------------------------
# Parser
# ---------------------------------------------------------------------------

def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="manage_candidates",
        description="Manual candidate intake and Stage 1 workflow for Lumen dataset expansion.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument(
        "--path",
        default=None,
        help="Path to candidates.json (default: data/dataset/candidates.json).",
    )
    sub = p.add_subparsers(dest="command", metavar="COMMAND")
    sub.required = True

    # --- add ----------------------------------------------------------------
    p_add = sub.add_parser("add", help="Add a new candidate to the tracker.")
    p_add.add_argument("--id", required=True, metavar="CANDIDATE_ID",
                       help="Working name / future func_id (snake_case, unique).")
    p_add.add_argument("--source", required=True,
                       help="Origin of the candidate function (e.g. 'authored', 'stdlib:itertools').")
    p_add.add_argument("--lines", type=int, default=0, metavar="N",
                       help="Executable body line count (default: 0 = not yet counted).")
    p_add.add_argument("--complexity", default="medium",
                       help=(
                           "Estimated complexity (default: medium). "
                           f"Allowed: {', '.join(sorted(COMPLEXITY_VALUES))}"
                       ))
    p_add.add_argument("--t2-family", default="unknown", dest="t2_family",
                       help="Draft T2 bug family (default: unknown).")
    p_add.add_argument("--t3-family", default="unknown", dest="t3_family",
                       help="Draft T3 transform family (default: unknown).")
    p_add.add_argument("--notes", default="",
                       help="Free-form notes (default: empty).")

    # --- update-stage1 -------------------------------------------------------
    p_s1 = sub.add_parser(
        "update-stage1",
        help="Record Stage 1 review decision for a candidate.",
    )
    p_s1.add_argument("candidate_id", metavar="CANDIDATE_ID",
                      help="candidate_id to update.")
    p_s1.add_argument("--result", required=True,
                      help="Stage 1 decision: PASS, EXCLUDE, or DEFER.")
    p_s1.add_argument("--reason", default=None,
                      help="Required for EXCLUDE; optional annotation for DEFER.")
    p_s1.add_argument("--notes", default=None,
                      help="Replace the notes field (omit to leave unchanged).")

    # --- list ----------------------------------------------------------------
    p_list = sub.add_parser("list", help="List candidates, optionally filtered by workflow state.")
    p_list.add_argument(
        "--state",
        default="all",
        choices=_STATE_CHOICES,
        help=(
            "Filter by workflow state.  "
            f"Choices: {', '.join(_STATE_CHOICES)}  (default: all)"
        ),
    )

    # --- show ----------------------------------------------------------------
    p_show = sub.add_parser("show", help="Show all details for one candidate.")
    p_show.add_argument("candidate_id", metavar="CANDIDATE_ID")

    # --- validate ------------------------------------------------------------
    sub.add_parser("validate", help="Validate the tracker file.")

    return p


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------

def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    dispatch = {
        "add": _cmd_add,
        "update-stage1": _cmd_update_stage1,
        "list": _cmd_list,
        "show": _cmd_show,
        "validate": _cmd_validate,
    }
    handler = dispatch.get(args.command)
    if handler is None:
        parser.print_help()
        return 1
    return handler(args)


if __name__ == "__main__":
    sys.exit(main())
