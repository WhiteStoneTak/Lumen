"""Initialize or normalize the candidate tracker file.

Usage
-----
    PYTHONPATH=src python -m experiment.init_candidates [--path PATH] [--seed-anchors]

Creates data/dataset/candidates.json if it does not exist.
If the file already exists, re-validates every row and reports any problems.

The --seed-anchors flag adds the three pilot calibration anchors (clamp,
count_vowels, is_sorted) to an empty tracker.  It is a no-op if those rows
are already present.
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
    TrackerError,
    default_tracker_path,
    empty_tracker,
    load_tracker,
    save_tracker,
    upsert_candidate,
    validate_tracker,
)

# ---------------------------------------------------------------------------
# Anchor seed data
# ---------------------------------------------------------------------------

_ANCHOR_ROWS: list[dict] = [
    {
        "candidate_id": "clamp",
        "source": "pilot-anchor",
        "body_line_count": 5,
        "estimated_complexity": "trivial",
        "t2_bug_family_draft": "wrong_comparison_operator",
        "t3_transform_family_draft": "precondition_enforcement",
        "stage1_result": "PASS",
        "stage1_exclusion_reason": None,
        "stage2_t2_c1_screen_score": 3.0,
        "stage2_t2_subscores": {"location": 1, "diagnosis": 1, "fix": 1},
        "stage2_result": "EXCLUDE",
        "stage2_exclusion_reason": (
            "Anchor calibration function. T2 C1 score=3.0. "
            "Retained as known-easy reference by anchor policy."
        ),
        "stage3_t3_c2_screen_score": 1.0,
        "stage3_result": "ceiling_risk",
        "final_decision": "INCLUDE",
        "is_anchor": True,
        "notes": (
            "Pilot calibration anchor. Stage 2/3 scores from "
            "pilot_full_gpt54_opus46_02 (gpt-5.4)."
        ),
    },
    {
        "candidate_id": "count_vowels",
        "source": "pilot-anchor",
        "body_line_count": 5,
        "estimated_complexity": "trivial",
        "t2_bug_family_draft": "wrong_accumulator_increment",
        "t3_transform_family_draft": "single_constant_substitution",
        "stage1_result": "PASS",
        "stage1_exclusion_reason": None,
        "stage2_t2_c1_screen_score": 3.0,
        "stage2_t2_subscores": {"location": 1, "diagnosis": 1, "fix": 1},
        "stage2_result": "EXCLUDE",
        "stage2_exclusion_reason": (
            "Anchor calibration function. T2 C1 score=3.0. "
            "Retained as known-easy reference by anchor policy."
        ),
        "stage3_t3_c2_screen_score": 1.0,
        "stage3_result": "ceiling_risk",
        "final_decision": "INCLUDE",
        "is_anchor": True,
        "notes": (
            "Pilot calibration anchor. Stage 2/3 scores from "
            "pilot_full_gpt54_opus46_02 (gpt-5.4)."
        ),
    },
    {
        "candidate_id": "is_sorted",
        "source": "pilot-anchor",
        "body_line_count": 4,
        "estimated_complexity": "trivial",
        "t2_bug_family_draft": "wrong_comparison_operator",
        "t3_transform_family_draft": "single_constant_substitution",
        "stage1_result": "PASS",
        "stage1_exclusion_reason": None,
        "stage2_t2_c1_screen_score": 3.0,
        "stage2_t2_subscores": {"location": 1, "diagnosis": 1, "fix": 1},
        "stage2_result": "EXCLUDE",
        "stage2_exclusion_reason": (
            "Anchor calibration function. T2 C1 score=3.0. "
            "Retained as known-easy reference by anchor policy."
        ),
        "stage3_t3_c2_screen_score": 1.0,
        "stage3_result": "ceiling_risk",
        "final_decision": "INCLUDE",
        "is_anchor": True,
        "notes": (
            "Pilot calibration anchor. Stage 2/3 scores from "
            "pilot_full_gpt54_opus46_02 (gpt-5.4)."
        ),
    },
]


# ---------------------------------------------------------------------------
# Main logic
# ---------------------------------------------------------------------------


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="init_candidates",
        description="Initialize or normalize the Lumen candidate tracker.",
    )
    p.add_argument(
        "--path",
        default=None,
        help="Path to candidates.json (default: data/dataset/candidates.json).",
    )
    p.add_argument(
        "--seed-anchors",
        action="store_true",
        default=False,
        dest="seed_anchors",
        help="Add the three pilot anchor rows if not already present.",
    )
    return p


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    path = Path(args.path) if args.path else default_tracker_path()

    if not path.exists():
        # Create a fresh tracker
        data = empty_tracker()
        if args.seed_anchors:
            for row in _ANCHOR_ROWS:
                upsert_candidate(data, row)
            print(f"Created new tracker with {len(_ANCHOR_ROWS)} anchor rows: {path}")
        else:
            print(
                f"Created empty tracker: {path}\n"
                "  (use --seed-anchors to add the pilot calibration anchors)"
            )
        save_tracker(data, path)
        return 0

    # File exists: validate it
    print(f"Tracker file found: {path}")
    try:
        data = load_tracker(path)
    except TrackerError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    errors: list[str] = []
    try:
        validate_tracker(data)
    except TrackerError as exc:
        errors.append(str(exc))

    if errors:
        print("Validation FAILED:", file=sys.stderr)
        for err in errors:
            print(f"  {err}", file=sys.stderr)
        return 1

    candidates = data.get("candidates", [])
    print(f"  {len(candidates)} candidate(s) — all rows valid.")

    if args.seed_anchors:
        added = 0
        for row in _ANCHOR_ROWS:
            existing = next(
                (c for c in data["candidates"] if c["candidate_id"] == row["candidate_id"]),
                None,
            )
            if existing is None:
                upsert_candidate(data, row)
                print(f"  Added anchor: {row['candidate_id']}")
                added += 1
            else:
                print(f"  Anchor already present (skipped): {row['candidate_id']}")
        if added:
            save_tracker(data, path)
        else:
            print("  No changes written.")
    else:
        print("  (use --seed-anchors to add missing pilot anchors)")

    return 0


if __name__ == "__main__":
    sys.exit(main())
