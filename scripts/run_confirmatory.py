"""Drive a frozen confirmatory collection run for R5 (T1 or T3).

Thin, reproducible wrapper over experiment.runner.run_pilot_experiment that
pins the pre-registered matrix: the frozen model pair, all five conditions, the
30 confirmatory (full-tier) functions, and a single task. Resumable
(execution_behavior='resume'): re-running continues an interrupted run.

The runner scores inline with the frozen scorers and writes per-item
prompt/response/score artifacts plus index.json/audit.json under
results/runs/<run_id>/.

Usage:
  PYTHONPATH=src python3 scripts/run_confirmatory.py --task T1 --run-id full_t1_confirmatory_v1 [--dry-run]

Pre-registration: docs/preregistrations/t1-v1.md (T1) / t3-v1.md (T3).
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "src"))

FROZEN_MODELS = ["gpt-5.4", "claude-opus-4-6"]
CONDITIONS = ["C1", "C1+", "C2", "C3", "C4"]


def load_dotenv(path: Path) -> None:
    """Minimal .env loader (no dependency); does not overwrite existing vars."""
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, val = line.partition("=")
        key, val = key.strip(), val.strip().strip('"').strip("'")
        os.environ.setdefault(key, val)


def full_tier_func_ids() -> list[str]:
    m = json.loads((REPO / "data/dataset/functions_manifest.json").read_text())
    return [it["func_id"] for it in m["items"] if it.get("dataset_tier") == "full"]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--task", required=True, choices=["T1", "T2", "T3"])
    ap.add_argument("--run-id", required=True)
    ap.add_argument("--dry-run", action="store_true",
                    help="Plan only; write index.json but make no API calls.")
    args = ap.parse_args()

    load_dotenv(REPO / ".env")
    import experiment.runner as runner_mod
    from experiment.runner import run_pilot_experiment

    # T3 execution safety (R5-3/R5-4 mandate): route the in-runner T3 scorer to
    # the sandboxed subprocess+timeout path WITHOUT editing the frozen runner.
    # dispatch_scorer looks up the module-global `score_t3`; rebinding it makes
    # every T3 score run via score_t3_sandboxed (T3_SANDBOX_TIMEOUT_S = 10 s),
    # so a non-terminating candidate is fenced as execution_timeout. No effect on
    # T1, whose scorer is untouched.
    if args.task == "T3":
        from experiment.score_t3 import score_t3_sandboxed
        runner_mod.score_t3 = score_t3_sandboxed
        print("[run_confirmatory] T3 scoring routed through score_t3_sandboxed "
              "(subprocess + 10s wall-clock timeout)")

    func_ids = full_tier_func_ids()
    if args.task == "T3":
        # Only functions with a frozen post-transform suite are T3-eligible.
        # The 4 without a suite are pre-declared exclusions (see prereg t3-v1).
        m = json.loads((REPO / "data/dataset/functions_manifest.json").read_text())
        avail = {it["func_id"] for it in m["items"]
                 if it.get("tasks", {}).get("T3", {}).get("available")}
        func_ids = [f for f in func_ids if f in avail]
    print(f"[run_confirmatory] task={args.task} run_id={args.run_id} "
          f"funcs={len(func_ids)} models={FROZEN_MODELS} dry_run={args.dry_run}")
    summary = run_pilot_experiment(
        models=FROZEN_MODELS,
        run_id=args.run_id,
        func_ids=func_ids,
        tasks=[args.task],
        conditions=CONDITIONS,
        run_mode="full",
        execution_behavior="resume",
        dry_run=args.dry_run,
    )
    print(f"[run_confirmatory] planned={summary['total_items']} "
          f"completed={summary['completed']} failed={summary['failed']} "
          f"planned-state={summary['planned']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
