"""Ingest Stage 2 or Stage 3 screening results into the candidate tracker.

Usage
-----
Stage 2 (T2 C1 screen):
    PYTHONPATH=src python -m experiment.update_candidates_from_run \\
        --run-id t2_screen_wave1 --stage 2 --model gpt-5.4

Stage 3 (T3 C2 screen, advisory):
    PYTHONPATH=src python -m experiment.update_candidates_from_run \\
        --run-id t3_screen_wave1 --stage 3 --model gpt-5.4

Options
-------
--run-id     Required.  The run ID to read scores from (directory name under results/runs/).
--stage      Required.  2 or 3.
--model      Required.  The model whose score files to read (e.g. gpt-5.4).
--overwrite  Allow overwriting rows that already have Stage 2/3 results.
--path       Path to candidates.json (default: data/dataset/candidates.json).
--dry-run    Show what would be updated without writing.

Artifact conventions (copied from runner.py):
  Score file location : results/runs/{run_id}/scores/
  Score file name     : {func_id}_{task}_{cond_clean}_{model_slug}.json
    where cond_clean  = condition.replace("+", "plus")
    and   model_slug  = model_id.replace("/", "_").replace(":", "_")

Stage 2 looks for: {candidate_id}_T2_C1_{model_slug}.json
Stage 3 looks for: {candidate_id}_T3_C2_{model_slug}.json

If a score file does not exist for a given candidate, that candidate is
skipped with a notice (it may simply not have been included in this run).
If a score file exists but is malformed or contains a scorer_error, the
script fails loudly with a specific message.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

_SRC = Path(__file__).resolve().parents[1]
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from experiment.candidate_tracker import (  # noqa: E402
    TrackerError,
    apply_stage2_result,
    apply_stage3_result,
    default_tracker_path,
    load_tracker,
    save_tracker,
    validate_tracker,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_RESULTS_ROOT = Path(__file__).resolve().parents[2] / "results" / "runs"


def _slugify_model(model_id: str) -> str:
    """Mirror runner.py slugify_model — replaces / and : with _."""
    return model_id.replace("/", "_").replace(":", "_")


def _score_filename(func_id: str, task: str, condition: str, model_id: str) -> str:
    cond_clean = condition.replace("+", "plus")
    model_slug = _slugify_model(model_id)
    return f"{func_id}_{task}_{cond_clean}_{model_slug}.json"


def _load_score_file(path: Path) -> dict[str, Any]:
    """Load and minimally validate a scorer-result-v1 JSON file."""
    if not path.exists():
        return {}  # caller handles missing → skip
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"Score file is not valid JSON ({path}): {exc}") from exc
    if payload.get("lumen_schema") != "scorer-result-v1":
        raise RuntimeError(
            f"Unexpected score file schema '{payload.get('lumen_schema')}' in {path}"
        )
    return payload


def _check_scorer_ok(payload: dict[str, Any], path: Path) -> None:
    """Raise RuntimeError if the scorer reported an error or failure."""
    status = payload.get("status", "")
    if status != "ok":
        reason = payload.get("failure_reason") or "(no failure_reason in file)"
        raise RuntimeError(
            f"Scorer status='{status}' (not 'ok') in {path}.\n"
            f"  failure_reason: {reason}\n"
            "  Diagnose and fix the scorer issue before ingesting results."
        )


# ---------------------------------------------------------------------------
# Stage 2 ingestion
# ---------------------------------------------------------------------------


def _ingest_stage2(
    data: dict[str, Any],
    run_id: str,
    model_id: str,
    overwrite: bool,
    dry_run: bool,
) -> tuple[int, int, int]:
    """Process Stage 2 T2 C1 results.  Returns (updated, skipped, not_found)."""
    scores_dir = _RESULTS_ROOT / run_id / "scores"
    if not scores_dir.is_dir():
        raise RuntimeError(
            f"Scores directory not found: {scores_dir}\n"
            f"  Is run_id '{run_id}' correct?  "
            f"  Run results must exist before ingestion."
        )

    candidates = data["candidates"]
    eligible = [c for c in candidates if c["stage1_result"] == "PASS"]

    updated = skipped = not_found = 0

    for row in eligible:
        cid = row["candidate_id"]

        # Check if already has Stage 2 results
        if row["stage2_result"] != "not_run" and not overwrite:
            print(
                f"  SKIP  {cid}: already has stage2_result='{row['stage2_result']}' "
                "(use --overwrite to replace)"
            )
            skipped += 1
            continue

        filename = _score_filename(cid, "T2", "C1", model_id)
        score_path = scores_dir / filename

        if not score_path.exists():
            print(f"  MISS  {cid}: score file not found ({filename}) — not in this run")
            not_found += 1
            continue

        payload = _load_score_file(score_path)
        _check_scorer_ok(payload, score_path)

        score = payload["score"]
        subscores = payload.get("subscores") or {}

        if dry_run:
            decision_preview = _preview_stage2(score)
            print(
                f"  DRY   {cid}: T2 C1 score={score:.1f} "
                f"subscores={subscores} -> would set stage2_result={decision_preview}"
            )
            updated += 1
            continue

        apply_stage2_result(row, score=score, subscores=subscores)
        print(
            f"  OK    {cid}: T2 C1 score={score:.1f} "
            f"subscores={subscores} -> stage2_result='{row['stage2_result']}' "
            f"final_decision='{row['final_decision']}'"
        )
        updated += 1

    return updated, skipped, not_found


def _preview_stage2(score: float) -> str:
    from experiment.candidate_tracker import stage2_decision_from_score
    return stage2_decision_from_score(score)


# ---------------------------------------------------------------------------
# Stage 3 ingestion
# ---------------------------------------------------------------------------


def _ingest_stage3(
    data: dict[str, Any],
    run_id: str,
    model_id: str,
    overwrite: bool,
    dry_run: bool,
) -> tuple[int, int, int]:
    """Process Stage 3 T3 C2 results.  Returns (updated, skipped, not_found)."""
    scores_dir = _RESULTS_ROOT / run_id / "scores"
    if not scores_dir.is_dir():
        raise RuntimeError(
            f"Scores directory not found: {scores_dir}\n"
            f"  Is run_id '{run_id}' correct?"
        )

    candidates = data["candidates"]
    # Stage 3 is advisory; technically eligible after Stage 2 INCLUDE, but we
    # allow anchors too since they have known Stage 3 results from the pilot.
    eligible = [
        c
        for c in candidates
        if c["stage2_result"] == "INCLUDE" or c.get("is_anchor")
    ]

    updated = skipped = not_found = 0

    for row in eligible:
        cid = row["candidate_id"]

        if row["stage3_result"] != "not_run" and not overwrite:
            print(
                f"  SKIP  {cid}: already has stage3_result='{row['stage3_result']}' "
                "(use --overwrite to replace)"
            )
            skipped += 1
            continue

        filename = _score_filename(cid, "T3", "C2", model_id)
        score_path = scores_dir / filename

        if not score_path.exists():
            print(f"  MISS  {cid}: score file not found ({filename}) — not in this run")
            not_found += 1
            continue

        payload = _load_score_file(score_path)
        _check_scorer_ok(payload, score_path)

        score = payload["score"]

        if dry_run:
            from experiment.candidate_tracker import stage3_decision_from_score
            decision_preview = stage3_decision_from_score(score)
            print(
                f"  DRY   {cid}: T3 C2 score={score:.3f} "
                f"-> would set stage3_result={decision_preview}"
            )
            updated += 1
            continue

        apply_stage3_result(row, score=score)
        print(
            f"  OK    {cid}: T3 C2 score={score:.3f} "
            f"-> stage3_result='{row['stage3_result']}'"
        )
        updated += 1

    return updated, skipped, not_found


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="update_candidates_from_run",
        description="Ingest screening run results into the candidate tracker.",
    )
    p.add_argument("--run-id", required=True, dest="run_id", help="Run ID to read scores from.")
    p.add_argument(
        "--stage",
        required=True,
        type=int,
        choices=[2, 3],
        help="Which screening stage to ingest (2 = T2 C1, 3 = T3 C2).",
    )
    p.add_argument(
        "--model",
        required=True,
        help="Model ID whose score files to read (e.g. gpt-5.4).",
    )
    p.add_argument(
        "--overwrite",
        action="store_true",
        default=False,
        help="Overwrite existing Stage 2/3 results for already-screened candidates.",
    )
    p.add_argument(
        "--dry-run",
        action="store_true",
        default=False,
        dest="dry_run",
        help="Show what would be updated without writing to the tracker.",
    )
    p.add_argument(
        "--path",
        default=None,
        help="Path to candidates.json (default: data/dataset/candidates.json).",
    )
    return p


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    path = Path(args.path) if args.path else default_tracker_path()

    try:
        data = load_tracker(path)
    except TrackerError as exc:
        print(f"ERROR loading tracker: {exc}", file=sys.stderr)
        return 1

    print(
        f"Ingesting Stage {args.stage} results from run '{args.run_id}' "
        f"(model={args.model}{', DRY RUN' if args.dry_run else ''})..."
    )

    try:
        if args.stage == 2:
            updated, skipped, not_found = _ingest_stage2(
                data, args.run_id, args.model, args.overwrite, args.dry_run
            )
        else:
            updated, skipped, not_found = _ingest_stage3(
                data, args.run_id, args.model, args.overwrite, args.dry_run
            )
    except RuntimeError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    print(
        f"\nDone.  updated={updated}  skipped={skipped}  not_in_run={not_found}"
    )

    if not args.dry_run and updated > 0:
        try:
            save_tracker(data, path)
            print(f"Tracker saved: {path}")
        except TrackerError as exc:
            print(f"ERROR saving tracker: {exc}", file=sys.stderr)
            return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
