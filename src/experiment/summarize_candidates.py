"""Human-readable summary of the candidate tracker state.

Usage
-----
    PYTHONPATH=src python -m experiment.summarize_candidates
    PYTHONPATH=src python -m experiment.summarize_candidates --list stage2-eligible
    PYTHONPATH=src python -m experiment.summarize_candidates --list stage3-eligible

The --list flag outputs only a space-separated list of candidate_ids (no
other text) for easy use in shell commands and Makefile variables.

    FUNC_IDS=$(PYTHONPATH=src python -m experiment.summarize_candidates --list stage2-eligible)
    make t2-screen-wave1 SCREEN_FUNC_IDS="$FUNC_IDS"
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

_SRC = Path(__file__).resolve().parents[1]
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from experiment.candidate_tracker import (  # noqa: E402
    TrackerError,
    default_tracker_path,
    load_tracker,
    summarize_tracker,
    workflow_summary,
)


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="summarize_candidates",
        description="Show the current state of the Lumen candidate tracker.",
    )
    p.add_argument(
        "--path",
        default=None,
        help="Path to candidates.json (default: data/dataset/candidates.json).",
    )
    p.add_argument(
        "--list",
        default=None,
        choices=["stage2-eligible", "stage3-eligible"],
        dest="list_mode",
        metavar="MODE",
        help=(
            "Output only a space-separated list of candidate_ids. "
            "Choices: stage2-eligible, stage3-eligible"
        ),
    )
    return p


def _print_summary(summary: dict) -> None:
    print("=" * 60)
    print("LUMEN CANDIDATE TRACKER SUMMARY")
    print("=" * 60)
    print(f"  Total candidates  : {summary['total']}")
    print(f"    Anchors         : {summary['anchors']}")
    print(f"    Non-anchors     : {summary['non_anchors']}")
    print()

    print("Stage 1 results:")
    for val, count in summary["stage1_counts"].items():
        print(f"  {val:<20} {count}")
    print()

    print("Stage 2 results (T2 C1 screen):")
    for val, count in summary["stage2_counts"].items():
        print(f"  {val:<20} {count}")
    awaiting2 = summary["stage2_eligible_awaiting"]
    print(f"  -> {awaiting2} Stage-1-PASS candidate(s) awaiting Stage 2 screen")
    if awaiting2 and summary["stage2_eligible_ids"]:
        ids = " ".join(summary["stage2_eligible_ids"])
        print(f"     IDs: {ids}")
    print()

    print("Stage 3 results (T3 C2 screen, advisory):")
    for val, count in summary["stage3_counts"].items():
        print(f"  {val:<20} {count}")
    awaiting3 = summary["stage3_eligible_awaiting"]
    print(f"  -> {awaiting3} Stage-2-INCLUDE candidate(s) awaiting Stage 3 screen")
    if awaiting3 and summary["stage3_eligible_ids"]:
        ids = " ".join(summary["stage3_eligible_ids"])
        print(f"     IDs: {ids}")
    print()

    print("Final decisions:")
    for val, count in summary["final_decision_counts"].items():
        print(f"  {val:<20} {count}")
    screened_in = summary["screened_in_non_anchor"]
    print(
        f"\n  Screened-in (non-anchor) : {screened_in}  "
        f"(target: 20–30 for Phase 2 run)"
    )
    print()

    if summary["t2_family_diversity"]:
        print("T2 bug family diversity (screened-in non-anchors):")
        for family, count in summary["t2_family_diversity"].items():
            print(f"  {family:<40} {count}")
        print()

    if summary["t3_family_diversity"]:
        print("T3 transform family diversity (screened-in non-anchors):")
        for family, count in summary["t3_family_diversity"].items():
            print(f"  {family:<40} {count}")
        print()

    print("=" * 60)


def _print_workflow_readiness(ws: dict) -> None:
    """Print the workflow-state breakdown including stage2-ready detection."""
    sc = ws["state_counts"]
    total = ws["total"]

    print()
    print("=" * 60)
    print("WORKFLOW READINESS (stage2-ready detection)")
    print("=" * 60)
    print(f"  {'State':<20} {'Count':>5}")
    print(f"  {'-'*20} {'-'*5}")
    for state in (
        "anchor",
        "pending",
        "deferred",
        "excluded",
        "pass-blocked",
        "pass-ready",
        "stage2-screened",
    ):
        count = sc.get(state, 0)
        if count or state in ("pass-blocked", "pass-ready"):
            print(f"  {state:<20} {count:>5}")
    print()

    blocked = ws["pass_blocked"]
    if blocked:
        print("  Blocked candidates (Stage 1 PASS but not yet Stage 2-ready):")
        for item in blocked:
            print(f"    {item['candidate_id']:<24} — {item['reason']}")
        print()
        print(
            "  To unblock: complete truth-authoring prerequisites for each candidate.\n"
            "  See: docs/candidate-workflow.md"
        )
        print()

    ready_ids = ws["pass_ready_ids"]
    if ready_ids:
        print(f"  Stage-2-ready candidate(s): {' '.join(ready_ids)}")
        print()

    print("=" * 60)


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    path = Path(args.path) if args.path else default_tracker_path()

    try:
        data = load_tracker(path)
    except TrackerError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    summary = summarize_tracker(data)
    ws = workflow_summary(data)  # includes manifest-based stage2-ready check

    if args.list_mode == "stage2-eligible":
        ids = summary["stage2_eligible_ids"]
        if ids:
            print(" ".join(ids))
        # Print nothing (not to stdout) if empty — shell will get empty string
        return 0

    if args.list_mode == "stage3-eligible":
        ids = summary["stage3_eligible_ids"]
        if ids:
            print(" ".join(ids))
        return 0

    _print_summary(summary)
    _print_workflow_readiness(ws)
    return 0


if __name__ == "__main__":
    sys.exit(main())
