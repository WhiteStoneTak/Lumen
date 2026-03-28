"""Minimal pilot experiment runner for Lumen Route A.

Executes the pilot experiment pipeline:
  plan → resolve representation → build prompt → invoke model
  → save raw artifacts → dispatch scorer → save score → index

Unit of execution: (func_id, task, condition, model)

See: docs/experimental-protocol.md

Design notes
------------
- T2 for non-C1 conditions is SKIPPED in this pilot runner.  Buggy-source
  representations in non-text formats (AST, typed-AST, IR) do not exist yet.
  Only C1 (raw buggy Python text) is available for T2.  This is an honest
  deferral — do not silently run T2 against the correct source.
- PROMPT_VERSION is a stable identifier embedded in every prompt artifact.
  The prompt *wording* must be identical across C1/C1+/C2/C3/C4 — only the
  representation_content block differs.
"""

from __future__ import annotations

import json
import traceback
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from experiment.contracts import (
    get_manifest_item,
    load_dataset_manifest,
    repo_root,
)
from experiment.score_t1_checklist import score_t1_checklist
from experiment.score_t2 import score_t2
from experiment.score_t3 import score_t3

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

PROMPT_VERSION = "pilot-v1"

# Condition → artifact key in manifest["artifacts"]
_CONDITION_TO_ARTIFACT_KEY: dict[str, str] = {
    "C1": "raw_source",
    "C1+": "annotated_text",
    "C2": "ast",
    "C3": "typed_ast",
    "C4": "ir",
}

# Conditions that use JSON artifacts (returned as pretty-printed JSON string)
_JSON_CONDITIONS = {"C2", "C3", "C4"}


# ---------------------------------------------------------------------------
# Slug / run-id helpers
# ---------------------------------------------------------------------------

def slugify_model(model_id: str) -> str:
    """Return a filename-safe version of *model_id*.

    Replaces '/' and ':' with '_'.  All other characters are kept.
    """
    return model_id.replace("/", "_").replace(":", "_")


def make_run_id() -> str:
    """Return a short UTC timestamp string suitable for a run directory name.

    Format: YYYYMMDD_HHMMSS
    """
    return datetime.now(tz=timezone.utc).strftime("%Y%m%d_%H%M%S")


# ---------------------------------------------------------------------------
# Planning
# ---------------------------------------------------------------------------

def plan_experiment_items(
    manifest: dict[str, Any],
    models: list[str],
    tasks: list[str] | None = None,
    conditions: list[str] | None = None,
    func_ids: list[str] | None = None,
) -> list[dict[str, Any]]:
    """Return a list of (func_id, task, condition, model) item dicts to run.

    Filters applied:
    - Only ``included`` manifest items.
    - Only tasks that are ``available`` in the manifest for the function.
    - Only conditions where the representation is available in the manifest.
    - Optional caller-supplied filters on func_ids, tasks, conditions.

    T2 for non-C1 conditions is excluded with a note: buggy representations
    in non-text formats have not been generated for this pilot.
    """
    allowed_tasks = set(tasks) if tasks else {"T1", "T2", "T3"}
    allowed_conditions = set(conditions) if conditions else {"C1", "C1+", "C2", "C3", "C4"}
    allowed_funcs = set(func_ids) if func_ids else None

    items: list[dict[str, Any]] = []

    for manifest_item in manifest.get("items", []):
        fid: str = manifest_item["func_id"]

        if manifest_item.get("inclusion_status") != "included":
            continue
        if allowed_funcs is not None and fid not in allowed_funcs:
            continue

        representations: dict[str, bool] = manifest_item.get("representations", {})
        task_info: dict[str, Any] = manifest_item.get("tasks", {})

        for task in sorted(allowed_tasks):
            task_data = task_info.get(task, {})
            if not task_data.get("available", False):
                continue

            for condition in sorted(allowed_conditions):
                if not representations.get(condition, False):
                    continue

                # T2 pilot constraint: only C1 has a buggy source file.
                if task == "T2" and condition != "C1":
                    continue

                for model in models:
                    items.append(
                        {
                            "func_id": fid,
                            "task": task,
                            "condition": condition,
                            "model": model,
                        }
                    )

    return items


# ---------------------------------------------------------------------------
# Representation resolver
# ---------------------------------------------------------------------------

def resolve_representation_artifact(
    func_id: str,
    condition: str,
    manifest: dict[str, Any],
    task: str | None = None,
) -> dict[str, Any] | None:
    """Resolve the representation artifact for *(func_id, condition)*.

    Parameters
    ----------
    func_id:
        Function identifier (e.g. ``"clamp"``).
    condition:
        Condition code — one of C1, C1+, C2, C3, C4.
    manifest:
        Loaded manifest dict.
    task:
        When ``"T2"`` and ``condition == "C1"``, returns the *buggy* source
        file content instead of the correct source.
        When ``"T2"`` and ``condition != "C1"``, returns ``None`` (buggy
        representations for non-text conditions are not yet generated).

    Returns
    -------
    dict with ``path`` (repo-relative str) and ``content`` (str), or ``None``
    when the artifact is unavailable.
    """
    # T2 special handling
    if task == "T2":
        if condition == "C1":
            buggy_path = f"data/ground_truth/bugs/{func_id}_buggy.py"
            full = (repo_root() / buggy_path).resolve()
            if not full.exists():
                return None
            return {
                "path": buggy_path,
                "content": full.read_text(encoding="utf-8"),
                "note": "buggy_source",
            }
        else:
            # Buggy representations for C1+/C2/C3/C4 do not exist in this pilot.
            return None

    # Normal path resolution
    artifact_key = _CONDITION_TO_ARTIFACT_KEY.get(condition)
    if artifact_key is None:
        return None

    manifest_item = get_manifest_item(manifest, func_id)
    artifacts: dict[str, Any] = manifest_item.get("artifacts", {})
    path_ref: str | None = artifacts.get(artifact_key)

    if not path_ref:
        return None

    full = (repo_root() / path_ref).resolve()
    if not full.exists():
        return None

    raw_content = full.read_text(encoding="utf-8")

    # JSON conditions — return pretty-printed JSON string
    if condition in _JSON_CONDITIONS:
        try:
            parsed = json.loads(raw_content)
            content = json.dumps(parsed, indent=2, ensure_ascii=False)
        except json.JSONDecodeError:
            content = raw_content
    else:
        content = raw_content

    return {"path": path_ref, "content": content}


# ---------------------------------------------------------------------------
# T3 transform instruction loader
# ---------------------------------------------------------------------------

def _load_t3_transform_instruction(func_id: str, manifest: dict[str, Any]) -> str:
    """Load the T3 transformation instruction from the ground-truth artifact."""
    manifest_item = get_manifest_item(manifest, func_id)
    gt_ref: str = manifest_item["tasks"]["T3"]["ground_truth_ref"]
    gt_path = (repo_root() / gt_ref).resolve()
    truth = json.loads(gt_path.read_text(encoding="utf-8"))
    return truth["instruction"]


# ---------------------------------------------------------------------------
# Prompt builder
# ---------------------------------------------------------------------------

_T1_TEMPLATE = """\
# prompt_version: {prompt_version}
You are analyzing a Python function. Your task is to identify and describe the properties of this function.

The function is provided below in a specific representation format.

---
{representation_content}
---

For each of the following aspects, describe what the function does:
1. What are the input parameters (names, types, constraints)?
2. What does the function return (type, value, conditions)?
3. What is the overall behavior of the function?
4. Are there any edge cases or boundary conditions?

Provide a clear, factual description of each aspect."""

_T2_TEMPLATE = """\
# prompt_version: {prompt_version}
You are analyzing a Python function that contains exactly one bug. Your task is to identify the bug and propose a fix.

The function is provided below in a specific representation format.

---
{representation_content}
---

Please provide:
1. The location of the bug (line number or code snippet)
2. An explanation of what is wrong (the diagnosis)
3. A corrected version of the buggy line(s) (the fix)

Be precise and specific."""

_T3_TEMPLATE = """\
# prompt_version: {prompt_version}
You are given a Python function and a transformation task. Your task is to implement the transformation.

The function is provided below in a specific representation format.

---
{representation_content}
---

Transformation task: {transform_instruction}

Please provide the complete transformed Python function. Your response must include the full function definition in a Python code block."""


def build_task_prompt(
    func_id: str,
    task: str,
    condition: str,
    representation_content: str,
    truth_context: dict[str, Any],
) -> str:
    """Build the task prompt for *(func_id, task, condition)*.

    The prompt *wording* is identical across all conditions — only
    ``representation_content`` varies.  This is enforced by the template
    constants above.

    Parameters
    ----------
    func_id:
        Function identifier.
    task:
        Task code — T1, T2, or T3.
    condition:
        Condition code — C1, C1+, C2, C3, C4.
    representation_content:
        The raw content string to embed in the prompt.
    truth_context:
        Optional context dict.  For T3 this must include
        ``transform_instruction``; supply it via
        ``{"transform_instruction": ...}``.
    """
    if task == "T1":
        return _T1_TEMPLATE.format(
            prompt_version=PROMPT_VERSION,
            representation_content=representation_content,
        )
    if task == "T2":
        return _T2_TEMPLATE.format(
            prompt_version=PROMPT_VERSION,
            representation_content=representation_content,
        )
    if task == "T3":
        transform_instruction = truth_context.get("transform_instruction", "")
        return _T3_TEMPLATE.format(
            prompt_version=PROMPT_VERSION,
            representation_content=representation_content,
            transform_instruction=transform_instruction,
        )
    raise ValueError(f"Unknown task: {task!r}")


# ---------------------------------------------------------------------------
# Model invocation
# ---------------------------------------------------------------------------

def invoke_model(
    prompt_text: str,
    model_id: str,
    max_tokens: int = 2048,
) -> dict[str, Any]:
    """Call the LLM and return a response dict.

    Uses ``src/utils/llm_client.py``.  Wraps all errors and returns an error
    dict rather than raising.

    Returns
    -------
    dict with keys: model_id, response_text, prompt_tokens, total_tokens, error
    """
    try:
        from utils.llm_client import call  # noqa: PLC0415

        # llm_client.call does not return token counts; set sentinel values.
        response_text = call(prompt_text, model=model_id)
        return {
            "model_id": model_id,
            "response_text": response_text,
            "prompt_tokens": None,
            "total_tokens": None,
            "error": None,
        }
    except Exception as exc:  # noqa: BLE001
        return {
            "model_id": model_id,
            "response_text": "",
            "prompt_tokens": None,
            "total_tokens": None,
            "error": f"{type(exc).__name__}: {exc}",
        }


# ---------------------------------------------------------------------------
# Artifact I/O helpers
# ---------------------------------------------------------------------------

def _item_slug(item: dict[str, Any]) -> str:
    """Return a filename slug for *item*."""
    fid = item["func_id"]
    task = item["task"]
    cond = item["condition"].replace("+", "plus")
    model_slug = slugify_model(item["model"])
    return f"{fid}_{task}_{cond}_{model_slug}"


def save_prompt_artifact(
    run_dir: Path,
    item: dict[str, Any],
    prompt_text: str,
) -> str:
    """Write the prompt text to disk and return the repo-relative path string."""
    slug = _item_slug(item)
    prompts_dir = run_dir / "prompts"
    prompts_dir.mkdir(parents=True, exist_ok=True)
    path = prompts_dir / f"{slug}.txt"
    path.write_text(prompt_text, encoding="utf-8")
    # Return repo-relative path
    return str(path.relative_to(repo_root()))


def save_response_artifact(
    run_dir: Path,
    item: dict[str, Any],
    response_dict: dict[str, Any],
) -> str:
    """Write the response JSON to disk and return the repo-relative path string."""
    slug = _item_slug(item)
    responses_dir = run_dir / "responses"
    responses_dir.mkdir(parents=True, exist_ok=True)
    path = responses_dir / f"{slug}.json"
    path.write_text(
        json.dumps(response_dict, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    return str(path.relative_to(repo_root()))


def save_score_artifact(
    run_dir: Path,
    item: dict[str, Any],
    score_dict: dict[str, Any],
) -> str:
    """Write the score JSON to disk and return the repo-relative path string."""
    slug = _item_slug(item)
    scores_dir = run_dir / "scores"
    scores_dir.mkdir(parents=True, exist_ok=True)
    path = scores_dir / f"{slug}.json"
    path.write_text(
        json.dumps(score_dict, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    return str(path.relative_to(repo_root()))


def _score_artifact_path(run_dir: Path, item: dict[str, Any]) -> Path:
    slug = _item_slug(item)
    return run_dir / "scores" / f"{slug}.json"


# ---------------------------------------------------------------------------
# Scorer dispatcher
# ---------------------------------------------------------------------------

def dispatch_scorer(
    item: dict[str, Any],
    response_text: str,
    response_ref: str,
) -> dict[str, Any]:
    """Build scorer-input-v1 payload and dispatch to the correct scorer.

    Parameters
    ----------
    item:
        Experiment item dict (func_id, task, condition, model).
    response_text:
        Raw model response string.
    response_ref:
        Repo-relative path to the saved response JSON artifact.

    Returns
    -------
    A scorer-result-v1 dict.
    """
    scorer_input: dict[str, Any] = {
        "lumen_schema": "scorer-input-v1",
        "func_id": item["func_id"],
        "task": item["task"],
        "condition": item["condition"],
        "model_id": item["model"],
        "response_ref": response_ref,
    }

    task = item["task"]
    if task == "T1":
        return score_t1_checklist(scorer_input, response_text)
    if task == "T2":
        return score_t2(scorer_input, response_text)
    if task == "T3":
        return score_t3(scorer_input, response_text)
    raise ValueError(f"Unknown task: {task!r}")


# ---------------------------------------------------------------------------
# Per-item runner
# ---------------------------------------------------------------------------

def run_experiment_item(
    run_dir: Path,
    item: dict[str, Any],
    manifest: dict[str, Any],
    force: bool = False,
    dry_run: bool = False,
) -> dict[str, Any]:
    """Execute a single experiment item end-to-end.

    Returns a result-row dict suitable for the index file.
    """
    func_id: str = item["func_id"]
    task: str = item["task"]
    condition: str = item["condition"]
    model: str = item["model"]
    slug = _item_slug(item)

    base_row: dict[str, Any] = {
        "func_id": func_id,
        "task": task,
        "condition": condition,
        "model": model,
        "status": "planned",
        "score": None,
        "prompt_path": None,
        "response_path": None,
        "score_path": None,
        "skip_reason": None,
        "error": None,
    }

    # Idempotency check
    score_path = _score_artifact_path(run_dir, item)
    if not force and score_path.exists():
        existing = json.loads(score_path.read_text(encoding="utf-8"))
        score_val = existing.get("score")
        return {
            **base_row,
            "status": "skipped",
            "score": score_val,
            "score_path": str(score_path.relative_to(repo_root())),
            "skip_reason": "already_completed",
        }

    # Resolve representation artifact
    artifact = resolve_representation_artifact(func_id, condition, manifest, task=task)
    if artifact is None:
        skip_reason = (
            "buggy_representation_not_available"
            if task == "T2" and condition != "C1"
            else "representation_artifact_missing"
        )
        return {
            **base_row,
            "status": "skipped",
            "skip_reason": skip_reason,
        }

    representation_content: str = artifact["content"]

    # Build truth context (T3 needs transform instruction)
    truth_context: dict[str, Any] = {}
    if task == "T3":
        try:
            truth_context["transform_instruction"] = _load_t3_transform_instruction(
                func_id, manifest
            )
        except Exception as exc:  # noqa: BLE001
            return {
                **base_row,
                "status": "error",
                "error": f"T3 instruction load failed: {exc}",
            }

    # Build prompt
    prompt_text = build_task_prompt(func_id, task, condition, representation_content, truth_context)

    if dry_run:
        return {
            **base_row,
            "status": "planned",
        }

    # Save prompt artifact
    prompt_path = save_prompt_artifact(run_dir, item, prompt_text)
    base_row["prompt_path"] = prompt_path

    # Invoke model
    response_dict = invoke_model(prompt_text, model)

    if response_dict["error"]:
        return {
            **base_row,
            "status": "error",
            "error": response_dict["error"],
        }

    # Save response artifact
    response_path = save_response_artifact(run_dir, item, response_dict)
    base_row["response_path"] = response_path

    # Dispatch scorer
    try:
        score_result = dispatch_scorer(item, response_dict["response_text"], response_path)
    except Exception as exc:  # noqa: BLE001
        return {
            **base_row,
            "status": "error",
            "error": f"Scorer error: {exc}\n{traceback.format_exc()}",
        }

    # Save score artifact
    score_rel_path = save_score_artifact(run_dir, item, score_result)

    score_val = score_result.get("score")
    return {
        **base_row,
        "status": "completed",
        "score": score_val,
        "score_path": score_rel_path,
    }


# ---------------------------------------------------------------------------
# Run orchestration
# ---------------------------------------------------------------------------

def run_pilot_experiment(
    models: list[str],
    run_id: str | None = None,
    func_ids: list[str] | None = None,
    tasks: list[str] | None = None,
    conditions: list[str] | None = None,
    force: bool = False,
    dry_run: bool = False,
) -> dict[str, Any]:
    """Execute the pilot experiment and return a run-summary dict.

    Parameters
    ----------
    models:
        List of model identifiers to run.
    run_id:
        Optional explicit run ID.  Auto-generated if None.
    func_ids:
        Optional filter to specific function IDs.
    tasks:
        Optional filter to specific tasks (T1, T2, T3).
    conditions:
        Optional filter to specific conditions.
    force:
        Re-run items that already have score artifacts.
    dry_run:
        Plan only — do not call the LLM.

    Returns
    -------
    A run-summary dict (also written to ``results/runs/{run_id}/index.json``).
    """
    if run_id is None:
        run_id = make_run_id()

    started_at = datetime.now(tz=timezone.utc).isoformat()

    # Create run directory
    run_dir = repo_root() / "results" / "runs" / run_id
    run_dir.mkdir(parents=True, exist_ok=True)

    # Load manifest
    manifest = load_dataset_manifest(check_paths=True)

    # Plan items
    items = plan_experiment_items(
        manifest,
        models=models,
        tasks=tasks,
        conditions=conditions,
        func_ids=func_ids,
    )

    print(f"[runner] run_id={run_id}  items={len(items)}  dry_run={dry_run}")

    # Also count T2 non-C1 that were excluded from the plan
    all_conditions = set(conditions) if conditions else {"C1", "C1+", "C2", "C3", "C4"}
    t2_skipped_conditions = all_conditions - {"C1"}
    t2_excluded_note = (
        f"T2 for conditions {sorted(t2_skipped_conditions)} excluded: "
        "buggy representations not yet generated for non-C1 formats."
        if t2_skipped_conditions
        else None
    )

    item_rows: list[dict[str, Any]] = []
    completed = 0
    skipped = 0
    failed = 0

    for item in items:
        try:
            row = run_experiment_item(run_dir, item, manifest, force=force, dry_run=dry_run)
        except Exception as exc:  # noqa: BLE001
            row = {
                "func_id": item["func_id"],
                "task": item["task"],
                "condition": item["condition"],
                "model": item["model"],
                "status": "error",
                "score": None,
                "prompt_path": None,
                "response_path": None,
                "score_path": None,
                "skip_reason": None,
                "error": f"Unhandled error: {exc}\n{traceback.format_exc()}",
            }

        status = row.get("status", "error")
        if status == "completed":
            completed += 1
        elif status in {"skipped", "planned"}:
            skipped += 1
        else:
            failed += 1

        item_rows.append(row)

        _label = f"{item['func_id']}/{item['task']}/{item['condition']}/{slugify_model(item['model'])}"
        print(f"  [{status}] {_label}  score={row.get('score')}")

    finished_at = datetime.now(tz=timezone.utc).isoformat()

    summary: dict[str, Any] = {
        "run_id": run_id,
        "prompt_version": PROMPT_VERSION,
        "models": models,
        "started_at": started_at,
        "finished_at": finished_at,
        "dry_run": dry_run,
        "total_items": len(items),
        "completed": completed,
        "skipped": skipped,
        "failed": failed,
        "items": item_rows,
    }
    if t2_excluded_note:
        summary["notes"] = [t2_excluded_note]

    index_path = run_dir / "index.json"
    index_path.write_text(
        json.dumps(summary, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    print(f"[runner] index written → {index_path}")

    return summary
