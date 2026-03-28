"""CLI entry point for the Lumen pilot experiment runner.

Usage
-----
    PYTHONPATH=src python -m experiment.run_pilot \\
        --models claude-sonnet-4-6 \\
        --func-ids clamp \\
        --tasks T1 \\
        --conditions C1 C2 \\
        --dry-run

See: src/experiment/runner.py and docs/experimental-protocol.md
"""

from __future__ import annotations

import argparse
import json
import sys


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="run_pilot",
        description="Lumen Route A — pilot experiment runner",
    )
    p.add_argument(
        "--models",
        nargs="+",
        default=["claude-sonnet-4-6"],
        metavar="MODEL",
        help="One or more model identifiers to test (default: claude-sonnet-4-6).",
    )
    p.add_argument(
        "--func-ids",
        nargs="+",
        default=None,
        metavar="FUNC_ID",
        dest="func_ids",
        help="Restrict to specific function IDs (default: all pilot functions).",
    )
    p.add_argument(
        "--tasks",
        nargs="+",
        default=None,
        choices=["T1", "T2", "T3"],
        metavar="TASK",
        help="Tasks to run: T1 T2 T3 (default: all).",
    )
    p.add_argument(
        "--conditions",
        nargs="+",
        default=None,
        choices=["C1", "C1+", "C2", "C3", "C4"],
        metavar="COND",
        help="Conditions to run: C1 C1+ C2 C3 C4 (default: all).",
    )
    p.add_argument(
        "--run-id",
        default=None,
        dest="run_id",
        help="Use a specific run ID instead of the auto-generated timestamp.",
    )
    p.add_argument(
        "--run-mode",
        default="full",
        choices=["smoke", "full", "preflight"],
        help=(
            "Plan/execute the full matrix, a deterministic smoke subset, or a preflight "
            "run (1 function × 1 model × all tasks × all conditions = 15 items). "
            "(default: full)"
        ),
    )
    p.add_argument(
        "--behavior",
        default="resume",
        choices=["resume", "overwrite", "skip"],
        help=(
            "How to treat existing item state for the same run_id: "
            "resume completed-safe items, overwrite all items, or only run still-planned items."
        ),
    )
    p.add_argument(
        "--force",
        action="store_true",
        default=False,
        help="Deprecated alias for --behavior overwrite.",
    )
    p.add_argument(
        "--dry-run",
        action="store_true",
        default=False,
        dest="dry_run",
        help="Plan only — print the item list and create index.json, but do not call any model.",
    )
    return p


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    if args.force and args.behavior not in {"resume", "overwrite"}:
        parser.error("--force cannot be combined with --behavior skip")

    from experiment.runner import run_pilot_experiment  # noqa: PLC0415

    summary = run_pilot_experiment(
        models=args.models,
        run_id=args.run_id,
        func_ids=args.func_ids,
        tasks=args.tasks,
        conditions=args.conditions,
        force=args.force,
        dry_run=args.dry_run,
        run_mode=args.run_mode,
        execution_behavior=args.behavior,
    )

    print(
        f"\nRun complete: {summary['run_id']}  "
        f"planned={summary['planned']}  "
        f"completed={summary['completed']}  "
        f"running={summary['running']}  "
        f"skipped={summary['skipped']}  "
        f"failed={summary['failed']}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
