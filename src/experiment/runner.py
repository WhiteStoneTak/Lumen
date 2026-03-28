"""Pilot experiment runner with resumable execution, audit, and export.

Executes the pilot experiment pipeline:
  plan → resolve representation → build prompt → invoke model
  → save raw artifacts → dispatch scorer → save score
  → persist run state → emit audit + long-form export

Unit of execution: (func_id, task, condition, model)

See: docs/experimental-protocol.md

Design notes
------------
- T2 uses buggy-source representations for all conditions (C1–C4).  Buggy
  artifacts exist for all conditions: C2/C3/C4 use the _buggy variants of
  ast-v1/typed_ast-v1/ir-v1 derived from the buggy source file; C1+ uses the
  buggy source annotated with correct reviewed contracts as specification.
- PROMPT_VERSION is a stable identifier embedded in every prompt artifact.
  The prompt *wording* must be identical across C1/C1+/C2/C3/C4 — only the
  representation_content block differs.
"""

from __future__ import annotations

import csv
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
RUN_INDEX_SCHEMA = "pilot-run-index-v2"
RUN_AUDIT_SCHEMA = "pilot-run-audit-v1"
RUN_MODES = ("smoke", "full")
EXECUTION_BEHAVIORS = ("resume", "overwrite", "skip")
ITEM_STATUS_LIFECYCLE = ("planned", "running", "completed", "failed", "skipped")
DEFAULT_TASKS = ("T1", "T2", "T3")
DEFAULT_CONDITIONS = ("C1", "C1+", "C2", "C3", "C4")

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
# Time / identity helpers
# ---------------------------------------------------------------------------

def _utcnow_iso() -> str:
    """Return an ISO-8601 UTC timestamp string."""
    return datetime.now(tz=timezone.utc).isoformat()


def slugify_model(model_id: str) -> str:
    """Return a filename-safe version of *model_id*.

    Replaces '/' and ':' with '_'.  All other characters are kept.
    """
    return model_id.replace("/", "_").replace(":", "_")


def make_run_id() -> str:
    """Return a short UTC timestamp string suitable for a run directory name.

    Format: YYYYMMDD_HHMMSS_microseconds
    """
    return datetime.now(tz=timezone.utc).strftime("%Y%m%d_%H%M%S_%f")


def _item_key(item: dict[str, Any]) -> str:
    """Return a deterministic unique identifier for *item*."""
    return "::".join(
        [item["func_id"], item["task"], item["condition"], item["model"]]
    )


def _item_slug(item: dict[str, Any]) -> str:
    """Return a filename slug for *item*."""
    fid = item["func_id"]
    task = item["task"]
    cond = item["condition"].replace("+", "plus")
    model_slug = slugify_model(item["model"])
    return f"{fid}_{task}_{cond}_{model_slug}"


def _failure_reason(code: str, message: str, *, details: dict[str, Any] | None = None) -> dict[str, Any]:
    """Return a normalized failure-reason payload."""
    payload: dict[str, Any] = {"code": code, "message": message}
    if details is not None:
        payload["details"] = details
    return payload


def _failure_code(row: dict[str, Any]) -> str | None:
    """Return the failure code for a persisted item row, if any."""
    failure_reason = row.get("failure_reason")
    if isinstance(failure_reason, dict):
        code = failure_reason.get("code")
        if isinstance(code, str):
            return code
    return None


def _unique_in_order(values: list[str]) -> list[str]:
    """Return unique values preserving first-seen order."""
    seen: set[str] = set()
    ordered: list[str] = []
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        ordered.append(value)
    return ordered


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

    T2 is fully crossed with all 5 conditions.  Buggy-source representations
    exist for C1 (raw source), C1+ (annotated buggy text), C2 (buggy AST),
    C3 (buggy typed AST), and C4 (buggy IR with correct contracts).
    """
    allowed_tasks = set(tasks) if tasks else set(DEFAULT_TASKS)
    allowed_conditions = set(conditions) if conditions else set(DEFAULT_CONDITIONS)
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


def select_smoke_items(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Return a deterministic smoke subset from *items*.

    Smoke mode selects the first planned item for each (model, task) pair.
    This keeps the subset small while still exercising every selected task on
    every selected model through the full execution/scoring/audit pipeline.
    """
    selected: list[dict[str, Any]] = []
    seen_pairs: set[tuple[str, str]] = set()

    for item in items:
        pair = (item["model"], item["task"])
        if pair in seen_pairs:
            continue
        seen_pairs.add(pair)
        selected.append(item)

    return selected


def _apply_run_mode(items: list[dict[str, Any]], run_mode: str) -> list[dict[str, Any]]:
    """Return the planned items after applying *run_mode*."""
    if run_mode == "full":
        return items
    if run_mode == "smoke":
        return select_smoke_items(items)
    raise ValueError(f"Unknown run_mode: {run_mode!r}")


def _build_run_spec(
    *,
    run_id: str,
    items: list[dict[str, Any]],
    models: list[str],
    func_ids: list[str] | None,
    tasks: list[str] | None,
    conditions: list[str] | None,
    run_mode: str,
    execution_behavior: str,
    dry_run: bool,
) -> dict[str, Any]:
    """Build a machine-readable run-spec payload."""
    return {
        "run_id": run_id,
        "selected_models": list(models),
        "selected_functions": _unique_in_order([item["func_id"] for item in items]),
        "selected_tasks": _unique_in_order([item["task"] for item in items]),
        "selected_conditions": _unique_in_order([item["condition"] for item in items]),
        "requested_function_filter": list(func_ids) if func_ids else None,
        "requested_task_filter": list(tasks) if tasks else None,
        "requested_condition_filter": list(conditions) if conditions else None,
        "run_mode": run_mode,
        "execution_behavior": execution_behavior,
        "dry_run": dry_run,
        "planned_item_count": len(items),
        "planned_item_ids": [_item_key(item) for item in items],
        "status_lifecycle": list(ITEM_STATUS_LIFECYCLE),
        "smoke_selection_rule": (
            "first planned item for each (model, task) pair"
            if run_mode == "smoke"
            else None
        ),
    }


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
        When ``"T2"``, returns the *buggy* representation artifact instead of
        the correct one.  Buggy artifacts exist for all conditions:

        - C1: raw buggy source (``data/ground_truth/bugs/{func_id}_buggy.py``)
        - C1+: buggy annotated text (``data/functions/annotated_text/{func_id}_buggy.py``)
        - C2: buggy AST (``data/functions/ast/{func_id}_buggy.json``)
        - C3: buggy typed AST (``data/functions/typed_ast/{func_id}_buggy.json``)
        - C4: buggy IR (``data/functions/ir/{func_id}_buggy.json``)

    Returns
    -------
    dict with ``path`` (repo-relative str) and ``content`` (str), or ``None``
    when the artifact is unavailable.
    """
    # T2 special handling: use buggy-source representations for all conditions
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
        if condition == "C1+":
            buggy_path = f"data/functions/annotated_text/{func_id}_buggy.py"
            full = (repo_root() / buggy_path).resolve()
            if not full.exists():
                return None
            return {
                "path": buggy_path,
                "content": full.read_text(encoding="utf-8"),
                "note": "buggy_source",
            }
        if condition == "C2":
            buggy_path = f"data/functions/ast/{func_id}_buggy.json"
            full = (repo_root() / buggy_path).resolve()
            if not full.exists():
                return None
            raw_content = full.read_text(encoding="utf-8")
            try:
                parsed = json.loads(raw_content)
                content = json.dumps(parsed, indent=2, ensure_ascii=False)
            except json.JSONDecodeError:
                content = raw_content
            return {"path": buggy_path, "content": content, "note": "buggy_source"}
        if condition == "C3":
            buggy_path = f"data/functions/typed_ast/{func_id}_buggy.json"
            full = (repo_root() / buggy_path).resolve()
            if not full.exists():
                return None
            raw_content = full.read_text(encoding="utf-8")
            try:
                parsed = json.loads(raw_content)
                content = json.dumps(parsed, indent=2, ensure_ascii=False)
            except json.JSONDecodeError:
                content = raw_content
            return {"path": buggy_path, "content": content, "note": "buggy_source"}
        if condition == "C4":
            buggy_path = f"data/functions/ir/{func_id}_buggy.json"
            full = (repo_root() / buggy_path).resolve()
            if not full.exists():
                return None
            raw_content = full.read_text(encoding="utf-8")
            try:
                parsed = json.loads(raw_content)
                content = json.dumps(parsed, indent=2, ensure_ascii=False)
            except json.JSONDecodeError:
                content = raw_content
            return {"path": buggy_path, "content": content, "note": "buggy_source"}
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
    del max_tokens
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


def _path_exists(path_ref: str | None) -> bool:
    """Return whether *path_ref* exists beneath the repository root."""
    if not path_ref:
        return False
    return (repo_root() / path_ref).exists()


def _load_json_if_exists(path_ref: str | None) -> dict[str, Any] | None:
    """Load a repo-relative JSON artifact when present and valid."""
    if not path_ref:
        return None
    full_path = repo_root() / path_ref
    if not full_path.exists():
        return None
    try:
        return json.loads(full_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None


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
) -> dict[str, Any]:
    """Execute a single experiment item end-to-end.

    Returns a terminal result-row fragment suitable for the run index.
    """
    func_id: str = item["func_id"]
    task: str = item["task"]
    condition: str = item["condition"]
    model: str = item["model"]

    base_row: dict[str, Any] = {
        "func_id": func_id,
        "task": task,
        "condition": condition,
        "model": model,
        "status": "failed",
        "score": None,
        "prompt_path": None,
        "response_path": None,
        "score_path": None,
        "skip_reason": None,
        "failure_reason": None,
        "error": None,
    }

    artifact = resolve_representation_artifact(func_id, condition, manifest, task=task)
    if artifact is None:
        message = "Representation artifact is unavailable for the planned item."
        return {
            **base_row,
            "failure_reason": _failure_reason(
                "representation_artifact_missing",
                message,
                details={"func_id": func_id, "task": task, "condition": condition},
            ),
            "error": message,
        }

    representation_content: str = artifact["content"]

    truth_context: dict[str, Any] = {}
    if task == "T3":
        try:
            truth_context["transform_instruction"] = _load_t3_transform_instruction(
                func_id, manifest
            )
        except Exception as exc:  # noqa: BLE001
            message = f"T3 instruction load failed: {exc}"
            return {
                **base_row,
                "failure_reason": _failure_reason("t3_instruction_load_failed", message),
                "error": message,
            }

    prompt_text = build_task_prompt(func_id, task, condition, representation_content, truth_context)
    prompt_path = save_prompt_artifact(run_dir, item, prompt_text)
    base_row["prompt_path"] = prompt_path

    response_dict = invoke_model(prompt_text, model)
    response_path = save_response_artifact(run_dir, item, response_dict)
    base_row["response_path"] = response_path

    if response_dict["error"]:
        message = response_dict["error"]
        return {
            **base_row,
            "failure_reason": _failure_reason("model_invocation_failed", message),
            "error": message,
        }

    try:
        score_result = dispatch_scorer(item, response_dict["response_text"], response_path)
    except Exception as exc:  # noqa: BLE001
        message = f"Scorer error: {exc}"
        return {
            **base_row,
            "failure_reason": _failure_reason("scorer_error", message),
            "error": f"{message}\n{traceback.format_exc()}",
        }

    score_rel_path = save_score_artifact(run_dir, item, score_result)
    score_val = score_result.get("score")
    return {
        **base_row,
        "status": "completed",
        "score": score_val,
        "score_path": score_rel_path,
        "failure_reason": None,
        "error": None,
    }


# ---------------------------------------------------------------------------
# Run-state / audit helpers
# ---------------------------------------------------------------------------

def _empty_item_row(item: dict[str, Any]) -> dict[str, Any]:
    """Return a planned item row for *item*."""
    return {
        "item_id": _item_key(item),
        "func_id": item["func_id"],
        "task": item["task"],
        "condition": item["condition"],
        "model": item["model"],
        "status": "planned",
        "score": None,
        "prompt_path": None,
        "response_path": None,
        "score_path": None,
        "skip_reason": None,
        "failure_reason": None,
        "error": None,
        "started_at": None,
        "finished_at": None,
        "attempt_count": 0,
    }


def _normalize_existing_row(item: dict[str, Any], row: dict[str, Any]) -> dict[str, Any]:
    """Upgrade a persisted item row to the current runner schema."""
    normalized = _empty_item_row(item)
    normalized.update(row)
    normalized["item_id"] = _item_key(item)

    if normalized.get("status") == "error":
        normalized["status"] = "failed"
        error_message = normalized.get("error") or "Legacy runner recorded an error."
        normalized["failure_reason"] = normalized.get("failure_reason") or _failure_reason(
            "legacy_error_status",
            error_message,
        )

    if normalized.get("status") not in ITEM_STATUS_LIFECYCLE:
        normalized["status"] = "failed"
        normalized["failure_reason"] = _failure_reason(
            "invalid_persisted_status",
            f"Persisted status {row.get('status')!r} is not recognized.",
        )

    return normalized


def _expected_missing_artifacts(row: dict[str, Any]) -> list[str]:
    """Return missing artifact labels required by *row*'s status."""
    expected: list[tuple[str, str | None]] = []

    if row["status"] == "completed":
        expected = [
            ("prompt", row.get("prompt_path")),
            ("response", row.get("response_path")),
            ("score", row.get("score_path")),
        ]
    elif row["status"] == "running":
        expected = [("prompt", row.get("prompt_path"))]

    return [label for label, path_ref in expected if not _path_exists(path_ref)]


def _artifact_presence(row: dict[str, Any]) -> dict[str, bool]:
    """Return artifact existence flags for *row*."""
    return {
        "prompt": _path_exists(row.get("prompt_path")),
        "response": _path_exists(row.get("response_path")),
        "score": _path_exists(row.get("score_path")),
    }


def _audit_missing_artifacts(row: dict[str, Any]) -> list[str]:
    """Return missing artifacts that should be surfaced by audit/export."""
    if _failure_code(row) == "completed_artifacts_missing":
        failure_reason = row.get("failure_reason")
        if isinstance(failure_reason, dict):
            details = failure_reason.get("details")
            if isinstance(details, dict):
                missing = details.get("missing_artifacts")
                if isinstance(missing, list):
                    return [value for value in missing if isinstance(value, str)]
    return _expected_missing_artifacts(row)


def _mark_existing_integrity_failures(rows: list[dict[str, Any]]) -> None:
    """Normalize interrupted or incomplete persisted rows in-place."""
    for row in rows:
        if row["status"] == "running":
            message = "Previous run stopped after the item started but before it completed."
            row["status"] = "failed"
            row["failure_reason"] = _failure_reason(
                "interrupted_before_completion",
                message,
            )
            row["error"] = message
            row["finished_at"] = row.get("finished_at") or _utcnow_iso()
            continue

        if row["status"] == "completed":
            missing = _expected_missing_artifacts(row)
            if missing:
                message = (
                    "Completed item is missing required artifacts and cannot be trusted "
                    "for resume without explicit overwrite."
                )
                row["status"] = "failed"
                row["failure_reason"] = _failure_reason(
                    "completed_artifacts_missing",
                    message,
                    details={"missing_artifacts": missing},
                )
                row["error"] = message
                row["finished_at"] = row.get("finished_at") or _utcnow_iso()


def _load_existing_index(run_dir: Path) -> dict[str, Any] | None:
    """Load an existing run index when present."""
    index_path = run_dir / "index.json"
    if not index_path.exists():
        return None
    return json.loads(index_path.read_text(encoding="utf-8"))


def _selection_signature(run_spec: dict[str, Any]) -> dict[str, Any]:
    """Return the immutable part of *run_spec* used for mismatch checks."""
    return {
        "run_mode": run_spec["run_mode"],
        "planned_item_ids": list(run_spec["planned_item_ids"]),
    }


def _build_state_from_existing(
    *,
    existing: dict[str, Any] | None,
    run_spec: dict[str, Any],
    items: list[dict[str, Any]],
) -> tuple[str, dict[str, dict[str, Any]]]:
    """Return (started_at, item_rows_by_id) seeded from any existing index."""
    if existing is None:
        return _utcnow_iso(), {_item_key(item): _empty_item_row(item) for item in items}

    existing_run_spec = existing.get("run_spec")
    if isinstance(existing_run_spec, dict):
        if _selection_signature(existing_run_spec) != _selection_signature(run_spec):
            raise ValueError(
                "Existing run_id maps to a different planned matrix. "
                "Use a new run_id instead of merging incompatible run specs."
            )

    started_at = existing.get("started_at") or _utcnow_iso()
    existing_rows = existing.get("items", [])
    existing_map: dict[str, dict[str, Any]] = {}
    for raw_row in existing_rows:
        if not isinstance(raw_row, dict):
            continue
        row_item = {
            "func_id": raw_row.get("func_id"),
            "task": raw_row.get("task"),
            "condition": raw_row.get("condition"),
            "model": raw_row.get("model"),
        }
        if not all(isinstance(v, str) and v for v in row_item.values()):
            continue
        key = _item_key(row_item)
        existing_map[key] = raw_row

    rows_by_id: dict[str, dict[str, Any]] = {}
    ordered_rows: list[dict[str, Any]] = []
    for item in items:
        key = _item_key(item)
        if key in existing_map:
            row = _normalize_existing_row(item, existing_map[key])
        else:
            row = _empty_item_row(item)
        rows_by_id[key] = row
        ordered_rows.append(row)

    _mark_existing_integrity_failures(ordered_rows)
    return started_at, rows_by_id


def _ordered_rows(items: list[dict[str, Any]], rows_by_id: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    """Return item rows in deterministic planned order."""
    return [rows_by_id[_item_key(item)] for item in items]


def _summarize_rows(rows: list[dict[str, Any]]) -> dict[str, int]:
    """Return item-level counts for run-state rows."""
    counts = {status: 0 for status in ITEM_STATUS_LIFECYCLE}
    started = 0

    for row in rows:
        status = row.get("status", "failed")
        if status not in counts:
            status = "failed"
        counts[status] += 1
        if row.get("started_at"):
            started += 1

    counts["started"] = started
    counts["total_items"] = len(rows)
    return counts


def _build_audit(run_id: str, rows: list[dict[str, Any]]) -> dict[str, Any]:
    """Return a machine-readable audit payload for *rows*."""
    counts = _summarize_rows(rows)
    item_audit_rows: list[dict[str, Any]] = []
    missing_expected: list[dict[str, Any]] = []

    for row in rows:
        presence = _artifact_presence(row)
        missing = _audit_missing_artifacts(row)
        audit_row = {
            "item_id": row["item_id"],
            "func_id": row["func_id"],
            "task": row["task"],
            "condition": row["condition"],
            "model": row["model"],
            "status": row["status"],
            "prompt_path": row.get("prompt_path"),
            "prompt_exists": presence["prompt"],
            "response_path": row.get("response_path"),
            "response_exists": presence["response"],
            "score_path": row.get("score_path"),
            "score_exists": presence["score"],
            "missing_expected_artifacts": missing,
            "failure_reason": row.get("failure_reason"),
            "skip_reason": row.get("skip_reason"),
        }
        item_audit_rows.append(audit_row)
        if missing:
            missing_expected.append(audit_row)

    return {
        "lumen_schema": RUN_AUDIT_SCHEMA,
        "run_id": run_id,
        "generated_at": _utcnow_iso(),
        "counts": counts,
        "missing_expected_output_count": len(missing_expected),
        "missing_expected_outputs": missing_expected,
        "items": item_audit_rows,
    }


def _export_rows(run_id: str, rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Return canonical long-form export rows."""
    exported: list[dict[str, Any]] = []

    for row in rows:
        score_payload = _load_json_if_exists(row.get("score_path"))
        failure_reason = row.get("failure_reason")
        scorer_failure_reason = (
            score_payload.get("failure_reason") if isinstance(score_payload, dict) else None
        )
        export_row = {
            "run_id": run_id,
            "item_id": row["item_id"],
            "model": row["model"],
            "function": row["func_id"],
            "task": row["task"],
            "condition": row["condition"],
            "item_status": row["status"],
            "started_at": row.get("started_at"),
            "finished_at": row.get("finished_at"),
            "attempt_count": row.get("attempt_count"),
            "prompt_artifact_path": row.get("prompt_path"),
            "response_artifact_path": row.get("response_path"),
            "score_artifact_path": row.get("score_path"),
            "prompt_artifact_exists": _path_exists(row.get("prompt_path")),
            "response_artifact_exists": _path_exists(row.get("response_path")),
            "score_artifact_exists": _path_exists(row.get("score_path")),
            "score": row.get("score"),
            "scorer_status": score_payload.get("status") if isinstance(score_payload, dict) else None,
            "scorer_failure_reason_code": (
                scorer_failure_reason.get("code")
                if isinstance(scorer_failure_reason, dict)
                else None
            ),
            "scorer_failure_reason_message": (
                scorer_failure_reason.get("message")
                if isinstance(scorer_failure_reason, dict)
                else None
            ),
            "score_subscores_json": (
                json.dumps(score_payload.get("subscores"), sort_keys=True)
                if isinstance(score_payload, dict) and score_payload.get("subscores") is not None
                else None
            ),
            "score_evidence_json": (
                json.dumps(score_payload.get("evidence"), sort_keys=True)
                if isinstance(score_payload, dict) and score_payload.get("evidence") is not None
                else None
            ),
            "execution_failure_reason_code": (
                failure_reason.get("code") if isinstance(failure_reason, dict) else None
            ),
            "execution_failure_reason_message": (
                failure_reason.get("message") if isinstance(failure_reason, dict) else None
            ),
            "skip_reason": row.get("skip_reason"),
            "missing_expected_artifacts_json": json.dumps(_audit_missing_artifacts(row)),
        }
        exported.append(export_row)

    return exported


def _write_analysis_export(run_dir: Path, rows: list[dict[str, Any]], run_id: str) -> str:
    """Write the canonical long-form CSV export and return its repo-relative path."""
    export_rows = _export_rows(run_id, rows)
    export_path = run_dir / "analysis_long.csv"
    fieldnames = list(export_rows[0].keys()) if export_rows else [
        "run_id",
        "item_id",
        "model",
        "function",
        "task",
        "condition",
        "item_status",
    ]

    with export_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in export_rows:
            writer.writerow(row)

    return str(export_path.relative_to(repo_root()))


def _persist_run_outputs(
    *,
    run_dir: Path,
    run_id: str,
    prompt_version: str,
    models: list[str],
    run_spec: dict[str, Any],
    started_at: str,
    finished_at: str | None,
    rows: list[dict[str, Any]],
    dry_run: bool,
) -> dict[str, Any]:
    """Persist index, audit, and export artifacts and return the run summary."""
    counts = _summarize_rows(rows)
    audit = _build_audit(run_id, rows)
    export_rel_path = _write_analysis_export(run_dir, rows, run_id)
    index_rel_path = str((run_dir / "index.json").relative_to(repo_root()))
    audit_rel_path = str((run_dir / "audit.json").relative_to(repo_root()))

    summary: dict[str, Any] = {
        "lumen_schema": RUN_INDEX_SCHEMA,
        "run_id": run_id,
        "prompt_version": prompt_version,
        "models": list(models),
        "run_spec": run_spec,
        "started_at": started_at,
        "finished_at": finished_at,
        "updated_at": _utcnow_iso(),
        "dry_run": dry_run,
        "total_items": counts["total_items"],
        "started": counts["started"],
        "planned": counts["planned"],
        "running": counts["running"],
        "completed": counts["completed"],
        "failed": counts["failed"],
        "skipped": counts["skipped"],
        "artifacts": {
            "index_path": index_rel_path,
            "audit_path": audit_rel_path,
            "analysis_export_path": export_rel_path,
        },
        "audit": {
            "missing_expected_output_count": audit["missing_expected_output_count"],
            "counts": audit["counts"],
        },
        "items": rows,
    }

    (run_dir / "audit.json").write_text(
        json.dumps(audit, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    (run_dir / "index.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    return summary


def _should_execute_item(row: dict[str, Any], execution_behavior: str) -> bool:
    """Return whether *row* should be executed under *execution_behavior*."""
    if execution_behavior == "overwrite":
        return True
    if execution_behavior == "resume":
        if row["status"] == "completed":
            return False
        if _failure_code(row) == "completed_artifacts_missing":
            return False
        return True
    if execution_behavior == "skip":
        return row["status"] == "planned"
    raise ValueError(f"Unknown execution_behavior: {execution_behavior!r}")


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
    run_mode: str = "full",
    execution_behavior: str = "resume",
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
        Back-compat alias for ``execution_behavior='overwrite'``.
    dry_run:
        Plan only — do not call the LLM.
    run_mode:
        ``"full"`` or ``"smoke"``.
    execution_behavior:
        ``"resume"``, ``"overwrite"``, or ``"skip"``.

    Returns
    -------
    A run-summary dict (also written to ``results/runs/{run_id}/index.json``).
    """
    if run_mode not in RUN_MODES:
        raise ValueError(f"run_mode must be one of {RUN_MODES}, got {run_mode!r}")

    if force:
        execution_behavior = "overwrite"
    if execution_behavior not in EXECUTION_BEHAVIORS:
        raise ValueError(
            f"execution_behavior must be one of {EXECUTION_BEHAVIORS}, "
            f"got {execution_behavior!r}"
        )

    if run_id is None:
        run_id = make_run_id()

    run_dir = repo_root() / "results" / "runs" / run_id
    run_dir.mkdir(parents=True, exist_ok=True)

    manifest = load_dataset_manifest(check_paths=True)
    planned_items = plan_experiment_items(
        manifest,
        models=models,
        tasks=tasks,
        conditions=conditions,
        func_ids=func_ids,
    )
    items = _apply_run_mode(planned_items, run_mode)
    run_spec = _build_run_spec(
        run_id=run_id,
        items=items,
        models=models,
        func_ids=func_ids,
        tasks=tasks,
        conditions=conditions,
        run_mode=run_mode,
        execution_behavior=execution_behavior,
        dry_run=dry_run,
    )

    existing = _load_existing_index(run_dir)
    started_at, rows_by_id = _build_state_from_existing(
        existing=existing,
        run_spec=run_spec,
        items=items,
    )

    print(
        f"[runner] run_id={run_id}  items={len(items)}  dry_run={dry_run}  "
        f"mode={run_mode}  behavior={execution_behavior}"
    )

    if dry_run:
        summary = _persist_run_outputs(
            run_dir=run_dir,
            run_id=run_id,
            prompt_version=PROMPT_VERSION,
            models=models,
            run_spec=run_spec,
            started_at=started_at,
            finished_at=_utcnow_iso(),
            rows=_ordered_rows(items, rows_by_id),
            dry_run=True,
        )
        print(f"[runner] index written → {run_dir / 'index.json'}")
        return summary

    for item in items:
        item_id = _item_key(item)
        row = rows_by_id[item_id]

        if not _should_execute_item(row, execution_behavior):
            label = (
                f"{item['func_id']}/{item['task']}/{item['condition']}/"
                f"{slugify_model(item['model'])}"
            )
            print(f"  [{row['status']}] {label}  score={row.get('score')}")
            continue

        row["status"] = "running"
        row["skip_reason"] = None
        row["failure_reason"] = None
        row["error"] = None
        row["started_at"] = row.get("started_at") or _utcnow_iso()
        row["finished_at"] = None
        row["attempt_count"] = int(row.get("attempt_count", 0)) + 1

        _persist_run_outputs(
            run_dir=run_dir,
            run_id=run_id,
            prompt_version=PROMPT_VERSION,
            models=models,
            run_spec=run_spec,
            started_at=started_at,
            finished_at=None,
            rows=_ordered_rows(items, rows_by_id),
            dry_run=False,
        )

        try:
            result = run_experiment_item(run_dir, item, manifest)
        except Exception as exc:  # noqa: BLE001
            message = f"Unhandled error: {exc}"
            result = {
                "status": "failed",
                "score": None,
                "prompt_path": row.get("prompt_path"),
                "response_path": row.get("response_path"),
                "score_path": row.get("score_path"),
                "skip_reason": None,
                "failure_reason": _failure_reason("unhandled_runner_error", message),
                "error": f"{message}\n{traceback.format_exc()}",
            }

        row.update(result)
        row["item_id"] = item_id
        row["finished_at"] = _utcnow_iso()

        label = (
            f"{item['func_id']}/{item['task']}/{item['condition']}/"
            f"{slugify_model(item['model'])}"
        )
        print(f"  [{row['status']}] {label}  score={row.get('score')}")

        _persist_run_outputs(
            run_dir=run_dir,
            run_id=run_id,
            prompt_version=PROMPT_VERSION,
            models=models,
            run_spec=run_spec,
            started_at=started_at,
            finished_at=None,
            rows=_ordered_rows(items, rows_by_id),
            dry_run=False,
        )

    summary = _persist_run_outputs(
        run_dir=run_dir,
        run_id=run_id,
        prompt_version=PROMPT_VERSION,
        models=models,
        run_spec=run_spec,
        started_at=started_at,
        finished_at=_utcnow_iso(),
        rows=_ordered_rows(items, rows_by_id),
        dry_run=False,
    )
    print(f"[runner] index written → {run_dir / 'index.json'}")
    return summary
